"""
HJB-Bellman Solver — optimal ranking via value function learning (Phase 2).

Replaces static diffusion with adaptive optimization using the
Hamilton-Jacobi-Bellman equation. Each search episode contributes
a reward signal that trains a value function V(s), enabling the
diffusion ranker to adapt its damping factor per-query.

Reward is tri-component:
    - relevance_score: avg cosine(query, chunk) for top results
    - context_fit: entropy-based diversity of skills in results
    - skill_affinity: domain match between query and result skills

The Bellman update rule:
    V(s) ← V(s) + α * [R + γ * V(s') - V(s)]
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path


# ── Reward Signal ────────────────────────────────────────────────────────────


@dataclass
class RewardSignal:
    """Tri-component reward for ranking quality assessment.

    Each component is normalized to [0, 1]:
        relevance_score: How well results match the query (avg cosine similarity)
        context_fit: How diverse the skill coverage is (Shannon entropy, normalized)
        skill_affinity: How well result domains match query intent
    """
    relevance_score: float
    context_fit: float
    skill_affinity: float
    _custom_weights: tuple[float, float, float] | None = None

    def total(
        self,
        weights: tuple[float, float, float] | None = None,
    ) -> float:
        """Weighted sum of reward components.

        Uses custom weights from QueryProfile if set, otherwise defaults.
        """
        w = weights or self._custom_weights or (0.5, 0.3, 0.2)
        w_rel, w_ctx, w_aff = w
        return (
            w_rel * self.relevance_score
            + w_ctx * self.context_fit
            + w_aff * self.skill_affinity
        )

    def as_dict(self) -> dict:
        return {
            "relevance_score": round(self.relevance_score, 4),
            "context_fit": round(self.context_fit, 4),
            "skill_affinity": round(self.skill_affinity, 4),
            "total": round(self.total(), 4),
        }


# ── Reward Cache (SQLite) ───────────────────────────────────────────────────


class RewardCache:
    """SQLite-backed storage for reward signals and value function.

    Tables:
        rewards — episode-level reward records
        value_function — learned V(s) for each state hash
    """

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = str(db_path) if db_path else ":memory:"
        self._conn: sqlite3.Connection | None = None
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_tables(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state_hash TEXT NOT NULL,
                reward REAL NOT NULL,
                query TEXT,
                components TEXT,
                timestamp INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS value_function (
                state_hash TEXT PRIMARY KEY,
                value REAL NOT NULL,
                update_count INTEGER DEFAULT 1,
                last_updated INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rewards_state ON rewards(state_hash);
        """)
        conn.commit()

    def store(
        self,
        state_hash: str,
        reward: float,
        query: str = "",
        components: dict | None = None,
    ) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO rewards (state_hash, reward, query, components, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (state_hash, reward, query, json.dumps(components or {}), int(time.time())),
        )
        conn.commit()

    def lookup(self, state_hash: str) -> float | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT reward FROM rewards WHERE state_hash = ? ORDER BY timestamp DESC LIMIT 1",
            (state_hash,),
        ).fetchone()
        return row[0] if row else None

    def get_value(self, state_hash: str) -> float | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value FROM value_function WHERE state_hash = ?",
            (state_hash,),
        ).fetchone()
        return row[0] if row else None

    def set_value(self, state_hash: str, value: float) -> None:
        conn = self._get_conn()
        now = int(time.time())
        conn.execute(
            "INSERT INTO value_function (state_hash, value, update_count, last_updated) "
            "VALUES (?, ?, 1, ?) "
            "ON CONFLICT(state_hash) DO UPDATE SET "
            "value = ?, update_count = update_count + 1, last_updated = ?",
            (state_hash, value, now, value, now),
        )
        conn.commit()

    def get_training_data(self, limit: int = 1000) -> list[tuple[str, float]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT state_hash, AVG(reward) FROM rewards "
            "GROUP BY state_hash ORDER BY COUNT(*) DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def episode_count(self) -> int:
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM rewards").fetchone()
        return row[0] if row else 0

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM rewards").fetchone()[0]
        unique_states = conn.execute(
            "SELECT COUNT(DISTINCT state_hash) FROM rewards"
        ).fetchone()[0]
        avg_reward = conn.execute("SELECT AVG(reward) FROM rewards").fetchone()[0]
        value_entries = conn.execute(
            "SELECT COUNT(*) FROM value_function"
        ).fetchone()[0]
        return {
            "total_episodes": total,
            "unique_states": unique_states,
            "avg_reward": round(avg_reward, 4) if avg_reward else 0.0,
            "value_entries": value_entries,
        }

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


# ── Feedback Aggregator ──────────────────────────────────────────────────────


class FeedbackAggregator:
    """Tracks chunk usage per query type for skill affinity learning.

    Logs which chunks are returned for each query type, enabling
    per-skill per-type affinity scores. After N queries, recalculates
    affinity weights for retraining.
    """

    def __init__(
        self,
        cache: RewardCache,
        retrain_interval: int = 100,
    ):
        self.cache = cache
        self.retrain_interval = retrain_interval
        self._query_count = 0
        self._ensure_feedback_table()

    def _ensure_feedback_table(self) -> None:
        conn = self.cache._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_type TEXT NOT NULL,
                skill TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                score REAL NOT NULL,
                timestamp INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(query_type);
            CREATE INDEX IF NOT EXISTS idx_feedback_skill ON feedback(skill);
        """)
        conn.commit()

    def log_usage(
        self,
        query_type: str,
        results: list,
    ) -> None:
        """Log which chunks were used in a search result."""
        conn = self.cache._get_conn()
        now = int(time.time())
        for r in results:
            conn.execute(
                "INSERT INTO feedback (query_type, skill, chunk_id, score, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (query_type, r.chunk.skill, r.chunk.id, r.final_score, now),
            )
        conn.commit()
        self._query_count += 1

    def should_retrain(self) -> bool:
        """Check if enough queries have accumulated to trigger retraining."""
        return self._query_count >= self.retrain_interval

    def reset_counter(self) -> None:
        self._query_count = 0

    def get_skill_stats(self, query_type: str | None = None) -> dict[str, dict]:
        """Get per-skill usage stats, optionally filtered by query type.

        Returns:
            {skill_name: {"count": N, "avg_score": float, "query_types": [...]}}
        """
        conn = self.cache._get_conn()
        if query_type:
            rows = conn.execute(
                "SELECT skill, COUNT(*), AVG(score) FROM feedback "
                "WHERE query_type = ? GROUP BY skill ORDER BY COUNT(*) DESC",
                (query_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT skill, COUNT(*), AVG(score) FROM feedback "
                "GROUP BY skill ORDER BY COUNT(*) DESC"
            ).fetchall()

        stats: dict[str, dict] = {}
        for skill, count, avg_score in rows:
            # Get query types for this skill
            types_rows = conn.execute(
                "SELECT DISTINCT query_type FROM feedback WHERE skill = ?",
                (skill,),
            ).fetchall()
            stats[skill] = {
                "count": count,
                "avg_score": round(avg_score, 4),
                "query_types": [r[0] for r in types_rows],
            }
        return stats

    def get_type_stats(self) -> dict[str, dict]:
        """Get per-query-type usage stats.

        Returns:
            {query_type: {"count": N, "avg_score": float, "top_skills": [...]}}
        """
        conn = self.cache._get_conn()
        rows = conn.execute(
            "SELECT query_type, COUNT(*), AVG(score) FROM feedback "
            "GROUP BY query_type ORDER BY COUNT(*) DESC"
        ).fetchall()

        stats: dict[str, dict] = {}
        for qtype, count, avg_score in rows:
            top = conn.execute(
                "SELECT skill, COUNT(*) as c FROM feedback "
                "WHERE query_type = ? GROUP BY skill ORDER BY c DESC LIMIT 5",
                (qtype,),
            ).fetchall()
            stats[qtype] = {
                "count": count,
                "avg_score": round(avg_score, 4),
                "top_skills": [r[0] for r in top],
            }
        return stats

    def compute_affinity_weights(self) -> dict[str, dict[str, float]]:
        """Compute per-skill per-type affinity weights for retraining.

        Returns:
            {query_type: {skill: affinity_weight}}
        """
        conn = self.cache._get_conn()
        rows = conn.execute(
            "SELECT query_type, skill, COUNT(*) * AVG(score) as affinity "
            "FROM feedback GROUP BY query_type, skill"
        ).fetchall()

        weights: dict[str, dict[str, float]] = {}
        for qtype, skill, affinity in rows:
            if qtype not in weights:
                weights[qtype] = {}
            weights[qtype][skill] = round(affinity, 4)

        # Normalize per type
        for qtype in weights:
            total = sum(weights[qtype].values()) or 1.0
            for skill in weights[qtype]:
                weights[qtype][skill] = round(weights[qtype][skill] / total, 4)

        return weights


# ── HJB Solver ───────────────────────────────────────────────────────────────


class HJBSolver:
    """Bellman value-iteration solver for optimal ranking.

    Learns a value function V(s) over ranking states, where each state
    is a quantized snapshot of result scores. Uses the Bellman update:

        V(s) ← V(s) + α * [R + γ * V(s') - V(s)]

    The learned values inform the diffusion ranker's damping factor,
    adapting the ranking strategy per-query based on accumulated experience.

    Args:
        discount: Discount factor γ for future rewards.
        learning_rate: Step size α for Bellman updates.
        min_episodes: Minimum episodes before adapting damping.
        default_damping: Fallback damping when insufficient data.
        cache: RewardCache instance for persistence.
    """

    def __init__(
        self,
        discount: float = 0.95,
        learning_rate: float = 0.01,
        min_episodes: int = 10,
        default_damping: float = 0.85,
        cache: RewardCache | None = None,
    ):
        self.discount = discount
        self.learning_rate = learning_rate
        self.min_episodes = min_episodes
        self.default_damping = default_damping
        self.cache = cache or RewardCache()
        self._value_table: dict[str, float] = {}
        self._load_values()

    def _load_values(self) -> None:
        """Load value function from cache into memory."""
        for state_hash, avg_reward in self.cache.get_training_data():
            stored = self.cache.get_value(state_hash)
            if stored is not None:
                self._value_table[state_hash] = stored
            else:
                self._value_table[state_hash] = avg_reward

    def compute_reward(
        self,
        query: str,
        results: list,
        embedder,
        reward_weights: tuple[float, float, float] | None = None,
    ) -> RewardSignal:
        """Compute tri-component reward for a set of ranked results.

        Args:
            query: The search query.
            results: Ranked SearchResult list (post-diffusion).
            embedder: Embedder with embed_query() and embed_documents().
            reward_weights: Optional per-type weights from QueryProfile.

        Returns:
            RewardSignal with relevance, context_fit, and skill_affinity.
        """
        if not results:
            return RewardSignal(0.0, 0.0, 0.0)

        # 1. Relevance: avg cosine(query_emb, chunk_emb) for top results
        query_emb = embedder.embed_query(query)
        chunk_texts = [r.chunk.contextual_text for r in results]
        chunk_embs = embedder.embed_documents(chunk_texts)
        similarities = [_cosine(query_emb, ce) for ce in chunk_embs]
        relevance = sum(similarities) / len(similarities) if similarities else 0.0

        # 2. Context fit: Shannon entropy of skill distribution (normalized)
        context_fit = self._compute_context_fit(results)

        # 3. Skill affinity: domain overlap between query terms and result domains
        skill_affinity = self._compute_skill_affinity(query, results)

        signal = RewardSignal(
            relevance_score=max(0.0, min(1.0, relevance)),
            context_fit=context_fit,
            skill_affinity=skill_affinity,
        )
        # Store the per-type weights so total() uses them
        if reward_weights is not None:
            signal._custom_weights = reward_weights
        return signal

    def update_value(
        self,
        state_hash: str,
        reward: float,
        next_state_hash: str | None = None,
        query: str = "",
        components: dict | None = None,
    ) -> float:
        """Apply Bellman update: V(s) ← V(s) + α * [R + γ * V(s') - V(s)].

        Args:
            state_hash: Current state identifier.
            reward: Observed reward R.
            next_state_hash: Next state s' (if available).
            query: Query for logging.
            components: Reward breakdown for logging.

        Returns:
            Updated value V(s).
        """
        current_v = self._value_table.get(state_hash, 0.0)
        next_v = self._value_table.get(next_state_hash, 0.0) if next_state_hash else 0.0

        # Bellman update
        td_error = reward + self.discount * next_v - current_v
        new_v = current_v + self.learning_rate * td_error

        self._value_table[state_hash] = new_v
        self.cache.set_value(state_hash, new_v)
        self.cache.store(state_hash, reward, query, components)

        return new_v

    def get_optimal_damping(self, state_hash: str) -> float:
        """Compute optimal damping factor based on learned values.

        Strategy:
            - If insufficient data (< min_episodes), return default.
            - High value states → higher damping (trust diffusion more).
            - Low value states → lower damping (lean on initial scores).

        Maps value ∈ [-1, 1] to damping ∈ [0.5, 0.95] via sigmoid-like scaling.
        """
        if self.cache.episode_count() < self.min_episodes:
            return self.default_damping

        value = self._value_table.get(state_hash)
        if value is None:
            return self.default_damping

        # Map value to damping range [0.5, 0.95]
        # Sigmoid: 1 / (1 + exp(-value * 3)) maps to [0, 1]
        sigmoid = 1.0 / (1.0 + math.exp(-value * 3.0))
        damping = 0.5 + sigmoid * 0.45  # range [0.5, 0.95]

        return round(damping, 4)

    def hash_state(self, scores: list[float]) -> str:
        """Quantize scores into bins and hash for efficient lookup.

        Scores are quantized into 10 bins (0.0-0.1, 0.1-0.2, ..., 0.9-1.0).
        This groups similar ranking states together, enabling generalization
        across queries with similar score distributions.
        """
        if not scores:
            return hashlib.md5(b"empty").hexdigest()[:16]

        # Normalize scores to [0, 1]
        max_score = max(scores) or 1.0
        normalized = [s / max_score for s in scores]

        # Quantize into 10 bins
        bins = tuple(min(int(s * 10), 9) for s in normalized)

        return hashlib.md5(str(bins).encode()).hexdigest()[:16]

    def _compute_context_fit(self, results: list) -> float:
        """Shannon entropy of skill distribution, normalized to [0, 1]."""
        if not results:
            return 0.0

        skill_counts: dict[str, int] = {}
        for r in results:
            skill = r.chunk.skill
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

        n = len(results)
        if len(skill_counts) <= 1:
            return 0.0

        entropy = 0.0
        for count in skill_counts.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)

        # Normalize by max entropy (uniform distribution)
        max_entropy = math.log2(len(skill_counts))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _compute_skill_affinity(self, query: str, results: list) -> float:
        """Domain overlap between query terms and result skill domains."""
        if not results:
            return 0.0

        query_terms = set(query.lower().split())

        # Collect all domains from results
        result_domains: set[str] = set()
        for r in results:
            for d in r.chunk.domains:
                result_domains.add(d.lower())

        if not result_domains:
            return 0.0

        # Count how many query terms appear in domains
        matches = sum(1 for t in query_terms if t in result_domains)
        # Also check partial matches (query term is substring of domain)
        partial = sum(
            1 for t in query_terms
            for d in result_domains
            if t in d or d in t
        )

        # Combine exact + partial (partial weighted 0.5)
        score = (matches + 0.5 * max(0, partial - matches)) / max(len(query_terms), 1)
        return min(1.0, score)


# ── Utility ──────────────────────────────────────────────────────────────────


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0
