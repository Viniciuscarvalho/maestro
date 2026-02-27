"""
Maestro RAG Engine — auto-indexing, change detection, ChromaDB + BM25 hybrid search.

Architecture:
    1. Gateway SKILL.md (.claude/skills/maestro/) → Claude sees ONLY this (~750 tokens)
    2. RAG Engine (this file) → searches ~/.maestro/skills/
    3. Knowledge Base (ChromaDB) → thousands of chunks from 100+ skills

5 Quality Techniques:
    T1: Concept graph expansion (recall)
    T2: Skill fingerprinting (prune irrelevant skills)
    T3: Contextual embeddings (chunks carry full meaning)
    T4: Hybrid search + RRF (semantic + BM25)
    T5: Cross-encoder reranking (precision)
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

from .concept_graph import get_swift_concept_graph

# ── Paths ────────────────────────────────────────────────────────────────────

MAESTRO_HOME = Path.home() / ".maestro"
INDEX_META = MAESTRO_HOME / "index_meta.json"


# ── Config ───────────────────────────────────────────────────────────────────

@dataclass
class Config:
    skill_paths: list[Path] = field(default_factory=lambda: [
        MAESTRO_HOME / "skills",
        Path.home() / ".claude" / "skills",
        Path(".claude") / "skills",
    ])
    vectordb_path: Path = field(default_factory=lambda: MAESTRO_HOME / "vectordb")
    embedding_provider: Literal["local", "voyage"] = "local"
    local_model: str = "all-MiniLM-L6-v2"
    voyage_model: str = "voyage-code-3"
    reranker_enabled: bool = True
    reranker_candidates: int = 20
    top_k: int = 7
    min_relevance: float = 0.15
    chunk_max_tokens: int = 400
    cache_enabled: bool = True
    cache_similarity: float = 0.92

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        p = path or (MAESTRO_HOME / "config.yaml")
        if p.exists():
            d = yaml.safe_load(p.read_text()) or {}
            c = cls()
            if "skill_paths" in d:
                c.skill_paths = [Path(x) for x in d["skill_paths"]]
            c.embedding_provider = d.get("embedding_provider", "local")
            c.reranker_enabled = d.get("reranker_enabled", True)
            c.top_k = d.get("top_k", 7)
            return c
        return cls()


# ── Data Types ───────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    id: str
    text: str
    contextual_text: str   # T3: text + context prefix
    skill: str
    file: str
    file_path: str
    section: str
    domains: list[str]


@dataclass
class SkillFingerprint:
    name: str
    description: str
    domains: list[str]
    chunk_count: int = 0
    embedding: list[float] | None = None

    @property
    def fingerprint_text(self) -> str:
        return f"{self.name}: {self.description}. Domains: {', '.join(self.domains)}"


@dataclass
class SearchResult:
    chunk: Chunk
    final_score: float
    semantic_rank: int | None = None
    bm25_rank: int | None = None
    rerank_score: float | None = None


@dataclass
class SearchResponse:
    query: str
    results: list[SearchResult]
    skills_used: list[str]
    time_ms: float
    from_cache: bool = False
    expanded_terms: list[str] | None = None

    def as_context(self, max_tokens: int = 3000) -> str:
        if not self.results:
            return ""
        lines = [f"# Relevant Knowledge ({', '.join(self.skills_used)})\n"]
        used = 0
        for r in self.results:
            header = f"## [{r.chunk.skill}] {r.chunk.file} — {r.chunk.section}"
            block = f"{header}\n\n{r.chunk.text}\n\n---\n"
            t = len(block) // 4
            if used + t > max_tokens:
                break
            lines.append(block)
            used += t
        return "\n".join(lines)


# ── Embedder ─────────────────────────────────────────────────────────────────

class Embedder:
    def __init__(self, config: Config):
        self.config = config
        self._model = None
        self._voyage = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.config.embedding_provider == "voyage":
            return self._voyage_embed(texts, "document")
        return self._local_embed(texts)

    def embed_query(self, text: str) -> list[float]:
        if self.config.embedding_provider == "voyage":
            return self._voyage_embed([text], "query")[0]
        return self._local_embed([text])[0]

    def _local_embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.config.local_model)
        vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]

    def _voyage_embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        if self._voyage is None:
            import os
            import voyageai
            self._voyage = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY", ""))
        all_embs: list[list[float]] = []
        for i in range(0, len(texts), 128):
            r = self._voyage.embed(
                texts[i : i + 128],
                model=self.config.voyage_model,
                input_type=input_type,
            )
            all_embs.extend(r.embeddings)
        return all_embs


# ── BM25 ─────────────────────────────────────────────────────────────────────

class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self._docs: list[list[str]] = []
        self._ids: list[str] = []
        self._df: dict[str, int] = defaultdict(int)
        self._avgdl: float = 0.0
        self._N: int = 0

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def fit(self, docs: list[str], ids: list[str]) -> None:
        self._docs = [self._tokenize(d) for d in docs]
        self._ids = ids
        self._N = len(docs)
        self._df = defaultdict(int)
        total = 0
        for tokens in self._docs:
            total += len(tokens)
            for t in set(tokens):
                self._df[t] += 1
        self._avgdl = total / self._N if self._N else 1.0

    def score(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        q_tokens = self._tokenize(query)
        scores: dict[str, float] = {}
        for i, tokens in enumerate(self._docs):
            tf_map: dict[str, int] = defaultdict(int)
            for t in tokens:
                tf_map[t] += 1
            s = 0.0
            dl = len(tokens)
            for qt in q_tokens:
                if qt not in tf_map:
                    continue
                tf = tf_map[qt]
                idf = math.log((self._N - self._df[qt] + 0.5) / (self._df[qt] + 0.5) + 1)
                s += idf * (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * dl / self._avgdl)
                )
            if s > 0:
                scores[self._ids[i]] = s
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]


# ── Chunker ──────────────────────────────────────────────────────────────────

class Chunker:
    def __init__(self, max_tokens: int = 400):
        self.max_tokens = max_tokens

    def chunk_file(self, path: Path, skill_name: str, domains: list[str]) -> list[Chunk]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        sections = self._split_sections(text)
        chunks: list[Chunk] = []

        # T3: build context prefix from file header
        file_context = self._extract_context(text, path.name, skill_name)

        for section_title, section_body in sections:
            for sub in self._split_long(section_body):
                raw_id = f"{skill_name}/{path.name}/{section_title}/{sub[:50]}"
                chunk_id = hashlib.md5(raw_id.encode()).hexdigest()
                contextual = f"[{skill_name} | {path.name}]\n{file_context}\n\n{sub}"
                chunks.append(Chunk(
                    id=chunk_id,
                    text=sub,
                    contextual_text=contextual,
                    skill=skill_name,
                    file=path.name,
                    file_path=str(path),
                    section=section_title,
                    domains=domains,
                ))
        return chunks

    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        pattern = re.compile(r"^(#{1,3} .+)$", re.MULTILINE)
        parts = pattern.split(text)
        if not parts:
            return [("main", text)]
        sections: list[tuple[str, str]] = []
        if parts[0].strip():
            sections.append(("intro", parts[0].strip()))
        for i in range(1, len(parts), 2):
            title = parts[i].lstrip("#").strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if body:
                sections.append((title, body))
        return sections or [("main", text)]

    def _split_long(self, text: str) -> list[str]:
        words = text.split()
        if len(words) <= self.max_tokens:
            return [text] if text.strip() else []
        chunks, current = [], []
        for word in words:
            current.append(word)
            if len(current) >= self.max_tokens:
                chunks.append(" ".join(current))
                current = current[-50:]  # 50-token overlap
        if current:
            chunks.append(" ".join(current))
        return chunks

    def _extract_context(self, text: str, filename: str, skill: str) -> str:
        lines = text.splitlines()[:8]
        for line in lines:
            if line.startswith("description:"):
                return line.replace("description:", "").strip().strip("'\"")
        return f"{skill} — {filename}"


# ── Main Engine ──────────────────────────────────────────────────────────────

class MaestroEngine:
    def __init__(self, config: Config):
        self.config = config
        self._embedder = Embedder(config)
        self._bm25 = BM25()
        self._collection = None
        self._fingerprints: dict[str, SkillFingerprint] = {}
        self._cache: dict[str, SearchResponse] = {}
        self._concept_graph = get_swift_concept_graph()
        self._indexed = False
        self._init_db()

    def _init_db(self) -> None:
        try:
            import chromadb
            self.config.vectordb_path.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.config.vectordb_path))
            self._collection = client.get_or_create_collection(
                "maestro_skills",
                metadata={"hnsw:space": "cosine"},
            )
            # Load BM25 if index exists
            meta_path = INDEX_META
            if meta_path.exists() and self._collection.count() > 0:
                self._indexed = True
                self._load_bm25_index()
        except Exception as e:
            print(f"[maestro] ChromaDB init error: {e}", flush=True)

    def _ensure_indexed(self) -> None:
        """Auto-index on first search if no index exists."""
        if not self._indexed or (self._collection and self._collection.count() == 0):
            self.index()

    def index(
        self,
        paths: list[Path] | None = None,
        force: bool = False,
    ) -> dict:
        t0 = time.time()
        skill_dirs = paths or self._discover_skills()
        all_chunks: list[Chunk] = []
        skill_count = 0
        errors: list[str] = []

        chunker = Chunker(self.config.chunk_max_tokens)

        for skill_dir in skill_dirs:
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            domains = self._extract_domains(skill_dir)

            skill_chunks: list[Chunk] = []
            for md_file in skill_dir.rglob("*.md"):
                if md_file.name.startswith("."):
                    continue
                try:
                    skill_chunks.extend(chunker.chunk_file(md_file, skill_name, domains))
                except Exception as e:
                    errors.append(f"{skill_name}/{md_file.name}: {e}")

            if skill_chunks:
                all_chunks.extend(skill_chunks)
                skill_count += 1
                fp = SkillFingerprint(
                    name=skill_name,
                    description=self._extract_description(skill_dir),
                    domains=domains,
                    chunk_count=len(skill_chunks),
                )
                self._fingerprints[skill_name] = fp

        if not all_chunks:
            return {"skills": 0, "files": 0, "chunks": 0, "fingerprints": 0,
                    "duration_s": 0, "errors": errors}

        # Embed + store (T2: embed fingerprints too)
        self._store_chunks(all_chunks, force)
        self._embed_fingerprints()
        self._build_bm25(all_chunks)
        self._save_index_meta()
        self._indexed = True

        return {
            "skills": skill_count,
            "files": len({c.file_path for c in all_chunks}),
            "chunks": len(all_chunks),
            "fingerprints": len(self._fingerprints),
            "duration_s": round(time.time() - t0, 1),
            "errors": errors,
        }

    def search(self, query: str, top_k: int | None = None) -> SearchResponse:
        self._ensure_indexed()
        top_k = top_k or self.config.top_k
        t0 = time.time()

        # Cache check
        if self.config.cache_enabled:
            cached = self._check_cache(query)
            if cached:
                cached.from_cache = True
                return cached

        # T1: Concept expansion
        expanded = self._concept_graph.expand(query)
        search_query = query + (" " + " ".join(expanded) if expanded else "")

        # T2: Skill fingerprinting
        query_emb = self._embedder.embed_query(search_query)
        matched_skills = self._match_skills(query_emb)

        # T4a: Semantic search
        where = {"skill": {"$in": matched_skills}} if matched_skills else None
        sem_candidates = self.config.reranker_candidates if self.config.reranker_enabled else top_k * 2
        sem_results = self._semantic_search(query_emb, sem_candidates, where)

        # T4b: BM25 search
        bm25_results = dict(self._bm25.score(search_query, top_k=sem_candidates))

        # T4c: RRF fusion
        fused = self._rrf_fuse(sem_results, bm25_results)

        # T5: Cross-encoder reranking
        if self.config.reranker_enabled and fused:
            fused = self._rerank(query, fused)

        final = fused[:top_k]
        skills_used = sorted({r.chunk.skill for r in final})

        response = SearchResponse(
            query=query,
            results=final,
            skills_used=skills_used,
            time_ms=(time.time() - t0) * 1000,
            expanded_terms=expanded if expanded else None,
        )

        if self.config.cache_enabled:
            self._cache[query] = response

        return response

    def get_context(self, query: str, max_tokens: int = 3000) -> str:
        return self.search(query).as_context(max_tokens)

    def status(self) -> dict:
        count = self._collection.count() if self._collection else 0
        return {
            "indexed": self._indexed and count > 0,
            "total_chunks": count,
            "bm25_docs": len(self._bm25._docs),
            "skills": {
                name: {
                    "chunks": fp.chunk_count,
                    "domains": fp.domains,
                    "description": fp.description,
                }
                for name, fp in self._fingerprints.items()
            },
        }

    # ── Private ──────────────────────────────────────────────────────────────

    def _discover_skills(self) -> list[Path]:
        skills: list[Path] = []
        for base in self.config.skill_paths:
            if base.exists():
                for d in base.iterdir():
                    if d.is_dir() and not d.name.startswith("."):
                        skills.append(d)
        return skills

    def _extract_domains(self, skill_dir: Path) -> list[str]:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return [skill_dir.name]
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        # Parse YAML front matter
        match = re.search(r"^---\n(.+?)\n---", text, re.DOTALL)
        if match:
            try:
                meta = yaml.safe_load(match.group(1)) or {}
                return meta.get("domains", [skill_dir.name])
            except Exception:
                pass
        return [skill_dir.name]

    def _extract_description(self, skill_dir: Path) -> str:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return skill_dir.name
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"^---\n(.+?)\n---", text, re.DOTALL)
        if match:
            try:
                meta = yaml.safe_load(match.group(1)) or {}
                desc = meta.get("description", "")
                if desc:
                    return str(desc)[:200]
            except Exception:
                pass
        # Fallback: first non-empty line after front matter
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---"):
                return line[:200]
        return skill_dir.name

    def _store_chunks(self, chunks: list[Chunk], force: bool) -> None:
        if not self._collection:
            return
        if force:
            try:
                self._collection.delete(where={"skill": {"$exists": True}})
            except Exception:
                pass

        batch_size = 64
        texts = [c.contextual_text for c in chunks]

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]
            embeddings = self._embedder.embed_documents(batch_texts)
            self._collection.add(
                ids=[c.id for c in batch],
                embeddings=embeddings,
                documents=[c.text for c in batch],
                metadatas=[{
                    "skill": c.skill,
                    "file": c.file,
                    "file_path": c.file_path,
                    "section": c.section,
                    "domains": json.dumps(c.domains),
                } for c in batch],
            )

    def _embed_fingerprints(self) -> None:
        if not self._fingerprints:
            return
        names = list(self._fingerprints.keys())
        texts = [self._fingerprints[n].fingerprint_text for n in names]
        embs = self._embedder.embed_documents(texts)
        for name, emb in zip(names, embs):
            self._fingerprints[name].embedding = emb

    def _build_bm25(self, chunks: list[Chunk]) -> None:
        self._bm25.fit(
            docs=[c.text for c in chunks],
            ids=[c.id for c in chunks],
        )

    def _match_skills(self, query_emb: list[float]) -> list[str]:
        """T2: Skill fingerprinting — prune irrelevant skills."""
        if not self._fingerprints:
            return []
        scores: list[tuple[str, float]] = []
        for name, fp in self._fingerprints.items():
            if fp.embedding:
                sim = self._cosine(query_emb, fp.embedding)
                scores.append((name, sim))
        if not scores:
            return []
        scores.sort(key=lambda x: x[1], reverse=True)
        # Keep skills within 40% of top score
        threshold = scores[0][1] * 0.6
        matched = [name for name, score in scores if score >= threshold]
        return matched[:8]  # cap at 8 skills

    def _semantic_search(
        self,
        query_emb: list[float],
        top_k: int,
        where: dict | None,
    ) -> list[tuple[str, float, int]]:
        if not self._collection or self._collection.count() == 0:
            return []
        kwargs: dict = {"query_embeddings": [query_emb], "n_results": min(top_k, self._collection.count())}
        if where:
            kwargs["where"] = where
        results = self._collection.query(**kwargs)
        out: list[tuple[str, float, int]] = []
        ids = results["ids"][0]
        distances = results["distances"][0]
        for rank, (chunk_id, dist) in enumerate(zip(ids, distances)):
            score = 1.0 - dist  # cosine distance → similarity
            out.append((chunk_id, score, rank))
        return out

    def _rrf_fuse(
        self,
        sem: list[tuple[str, float, int]],
        bm25: dict[str, float],
        k: int = 60,
    ) -> list[SearchResult]:
        rrf: dict[str, float] = defaultdict(float)
        sem_map: dict[str, tuple[float, int]] = {}

        for rank, (chunk_id, score, _) in enumerate(sem):
            rrf[chunk_id] += 1 / (k + rank + 1)
            sem_map[chunk_id] = (score, rank)

        bm25_sorted = sorted(bm25.items(), key=lambda x: x[1], reverse=True)
        bm25_rank_map: dict[str, int] = {cid: r for r, (cid, _) in enumerate(bm25_sorted)}
        for rank, (chunk_id, _) in enumerate(bm25_sorted):
            rrf[chunk_id] += 1 / (k + rank + 1)

        if not rrf:
            return []

        # Fetch chunk metadata from ChromaDB
        all_ids = list(rrf.keys())
        try:
            fetched = self._collection.get(ids=all_ids, include=["documents", "metadatas"])
        except Exception:
            return []

        id_to_data: dict[str, tuple[str, dict]] = {
            cid: (doc, meta)
            for cid, doc, meta in zip(
                fetched["ids"], fetched["documents"], fetched["metadatas"]
            )
        }

        results: list[SearchResult] = []
        for chunk_id, rrf_score in sorted(rrf.items(), key=lambda x: x[1], reverse=True):
            if chunk_id not in id_to_data:
                continue
            doc, meta = id_to_data[chunk_id]
            sem_score, sem_rank = sem_map.get(chunk_id, (0.0, None))
            chunk = Chunk(
                id=chunk_id,
                text=doc,
                contextual_text=doc,
                skill=meta.get("skill", "unknown"),
                file=meta.get("file", ""),
                file_path=meta.get("file_path", ""),
                section=meta.get("section", ""),
                domains=json.loads(meta.get("domains", "[]")),
            )
            results.append(SearchResult(
                chunk=chunk,
                final_score=rrf_score,
                semantic_rank=sem_rank,
                bm25_rank=bm25_rank_map.get(chunk_id),
            ))
        return results

    def _rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        """T5: Cross-encoder reranking."""
        try:
            from sentence_transformers import CrossEncoder
            reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            pairs = [(query, r.chunk.text) for r in results]
            scores = reranker.predict(pairs)
            for r, score in zip(results, scores):
                r.rerank_score = float(score)
                r.final_score = float(score)
            results.sort(key=lambda x: x.final_score, reverse=True)
        except Exception:
            pass  # Reranker optional — fall back to RRF scores
        return results

    def _check_cache(self, query: str) -> SearchResponse | None:
        if query in self._cache:
            return self._cache[query]
        # Semantic cache: find similar query
        if not self._cache:
            return None
        try:
            q_emb = self._embedder.embed_query(query)
            best_sim = 0.0
            best_resp = None
            for cached_q, resp in self._cache.items():
                c_emb = self._embedder.embed_query(cached_q)
                sim = self._cosine(q_emb, c_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_resp = resp
            if best_sim >= self.config.cache_similarity:
                return best_resp
        except Exception:
            pass
        return None

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na and nb else 0.0

    def _save_index_meta(self) -> None:
        MAESTRO_HOME.mkdir(parents=True, exist_ok=True)
        INDEX_META.write_text(json.dumps({
            "skills": list(self._fingerprints.keys()),
            "chunk_count": self._collection.count() if self._collection else 0,
        }, indent=2))

    def _load_bm25_index(self) -> None:
        """Reload BM25 from ChromaDB after restart."""
        if not self._collection:
            return
        try:
            all_data = self._collection.get(include=["documents"])
            if all_data["ids"]:
                self._bm25.fit(all_data["documents"], all_data["ids"])
        except Exception:
            pass
