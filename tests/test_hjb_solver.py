"""Tests for the HJB-Bellman solver (Phase 2)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pytest

from maestro_rag.hjb_solver import HJBSolver, RewardCache, RewardSignal, _cosine


# ── Fixtures ─────────────────────────────────────────────────────────────────


@dataclass
class FakeChunk:
    id: str = ""
    text: str = ""
    contextual_text: str = ""
    skill: str = "test"
    file: str = "test.md"
    file_path: str = "/test.md"
    section: str = "main"
    domains: list[str] = field(default_factory=list)


@dataclass
class FakeSearchResult:
    chunk: FakeChunk
    final_score: float
    semantic_rank: int | None = None
    bm25_rank: int | None = None
    rerank_score: float | None = None


class FakeEmbedder:
    def __init__(self, query_emb: list[float], doc_embs: list[list[float]]):
        self._query_emb = query_emb
        self._doc_embs = doc_embs

    def embed_query(self, text: str) -> list[float]:
        return self._query_emb

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._doc_embs[: len(texts)]


def _make_results(
    scores: list[float],
    skills: list[str] | None = None,
    domains: list[list[str]] | None = None,
) -> list[FakeSearchResult]:
    results = []
    for i, score in enumerate(scores):
        skill = skills[i] if skills else "test"
        doms = domains[i] if domains else ["testing"]
        chunk = FakeChunk(
            id=f"chunk_{i}",
            text=f"Content {i}",
            contextual_text=f"[{skill}] Content {i}",
            skill=skill,
            domains=doms,
        )
        results.append(FakeSearchResult(chunk=chunk, final_score=score))
    return results


# ── RewardSignal Tests ───────────────────────────────────────────────────────


def test_reward_signal_total_default_weights():
    r = RewardSignal(relevance_score=1.0, context_fit=1.0, skill_affinity=1.0)
    assert abs(r.total() - 1.0) < 1e-10


def test_reward_signal_total_custom_weights():
    r = RewardSignal(relevance_score=0.8, context_fit=0.6, skill_affinity=0.4)
    total = r.total(weights=(0.5, 0.3, 0.2))
    expected = 0.5 * 0.8 + 0.3 * 0.6 + 0.2 * 0.4
    assert abs(total - expected) < 1e-10


def test_reward_signal_components():
    r = RewardSignal(relevance_score=0.9, context_fit=0.7, skill_affinity=0.5)
    d = r.as_dict()
    assert d["relevance_score"] == 0.9
    assert d["context_fit"] == 0.7
    assert d["skill_affinity"] == 0.5
    assert "total" in d


# ── RewardCache Tests ────────────────────────────────────────────────────────


def test_reward_cache_store_lookup():
    cache = RewardCache()  # in-memory
    cache.store("hash_a", 0.75, query="test query")
    result = cache.lookup("hash_a")
    assert result == 0.75


def test_reward_cache_lookup_missing():
    cache = RewardCache()
    assert cache.lookup("nonexistent") is None


def test_reward_cache_value_function():
    cache = RewardCache()
    cache.set_value("state_1", 0.5)
    assert cache.get_value("state_1") == 0.5

    # Update
    cache.set_value("state_1", 0.7)
    assert cache.get_value("state_1") == 0.7


def test_reward_cache_stats():
    cache = RewardCache()
    cache.store("h1", 0.5, query="q1")
    cache.store("h1", 0.7, query="q2")
    cache.store("h2", 0.9, query="q3")

    stats = cache.stats()
    assert stats["total_episodes"] == 3
    assert stats["unique_states"] == 2
    assert stats["avg_reward"] > 0


def test_reward_cache_episode_count():
    cache = RewardCache()
    assert cache.episode_count() == 0
    cache.store("h1", 0.5)
    cache.store("h2", 0.6)
    assert cache.episode_count() == 2


def test_reward_cache_training_data():
    cache = RewardCache()
    cache.store("h1", 0.5)
    cache.store("h1", 0.7)
    cache.store("h2", 0.9)

    data = cache.get_training_data()
    assert len(data) == 2
    # h1 has more episodes, should come first
    assert data[0][0] == "h1"
    assert abs(data[0][1] - 0.6) < 1e-10  # avg of 0.5, 0.7


# ── HJBSolver Tests ─────────────────────────────────────────────────────────


def test_bellman_update():
    solver = HJBSolver(discount=0.9, learning_rate=0.1, cache=RewardCache())
    new_v = solver.update_value("s1", reward=1.0)
    # V(s1) was 0, td_error = 1.0 + 0.9*0 - 0 = 1.0, new_v = 0 + 0.1 * 1.0 = 0.1
    assert abs(new_v - 0.1) < 1e-10


def test_bellman_update_with_next_state():
    solver = HJBSolver(discount=0.9, learning_rate=0.1, cache=RewardCache())
    solver._value_table["s2"] = 0.5
    new_v = solver.update_value("s1", reward=1.0, next_state_hash="s2")
    # td_error = 1.0 + 0.9*0.5 - 0 = 1.45, new_v = 0 + 0.1 * 1.45 = 0.145
    assert abs(new_v - 0.145) < 1e-10


def test_bellman_update_persists():
    cache = RewardCache()
    solver = HJBSolver(cache=cache)
    solver.update_value("s1", reward=0.8, query="test")
    assert cache.get_value("s1") is not None
    assert cache.lookup("s1") == 0.8


def test_optimal_damping_default_insufficient_data():
    solver = HJBSolver(min_episodes=10, default_damping=0.85, cache=RewardCache())
    # No episodes yet
    damping = solver.get_optimal_damping("any_state")
    assert damping == 0.85


def test_optimal_damping_learned():
    cache = RewardCache()
    solver = HJBSolver(min_episodes=2, cache=cache)

    # Add enough episodes
    for i in range(5):
        solver.update_value(f"s{i}", reward=0.9)

    # Set a high value for a specific state
    solver._value_table["target"] = 1.0

    damping = solver.get_optimal_damping("target")
    # High value → damping should be > default (0.85)
    assert damping > 0.85
    assert 0.5 <= damping <= 0.95


def test_optimal_damping_low_value():
    cache = RewardCache()
    solver = HJBSolver(min_episodes=2, cache=cache)
    for i in range(5):
        solver.update_value(f"s{i}", reward=0.1)

    solver._value_table["low"] = -1.0
    damping = solver.get_optimal_damping("low")
    # Low value → damping should be < default
    assert damping < 0.85


# ── State Hashing Tests ─────────────────────────────────────────────────────


def test_state_hash_deterministic():
    solver = HJBSolver(cache=RewardCache())
    h1 = solver.hash_state([0.8, 0.5, 0.2])
    h2 = solver.hash_state([0.8, 0.5, 0.2])
    assert h1 == h2


def test_state_hash_different_for_different_scores():
    solver = HJBSolver(cache=RewardCache())
    h1 = solver.hash_state([0.9, 0.1])
    h2 = solver.hash_state([0.1, 0.9])
    assert h1 != h2


def test_state_hash_bins_similar():
    """Scores within the same bin should produce the same hash."""
    solver = HJBSolver(cache=RewardCache())
    # Both in same bin (0.81 and 0.82 both map to bin 8 when normalized)
    h1 = solver.hash_state([0.81, 0.51])
    h2 = solver.hash_state([0.82, 0.52])
    assert h1 == h2


def test_state_hash_empty():
    solver = HJBSolver(cache=RewardCache())
    h = solver.hash_state([])
    assert isinstance(h, str)
    assert len(h) == 16


# ── Reward Computation Tests ────────────────────────────────────────────────


def test_compute_reward_relevance():
    solver = HJBSolver(cache=RewardCache())
    query_emb = [1.0, 0.0, 0.0]
    doc_embs = [
        [0.9, 0.1, 0.0],  # high similarity
        [0.8, 0.2, 0.0],  # high similarity
    ]
    embedder = FakeEmbedder(query_emb, doc_embs)
    results = _make_results([0.8, 0.6])

    reward = solver.compute_reward("test query", results, embedder)
    assert reward.relevance_score > 0.8  # high similarity chunks


def test_compute_reward_context_fit_diverse():
    solver = HJBSolver(cache=RewardCache())
    embedder = FakeEmbedder([1.0, 0.0], [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]])
    results = _make_results(
        [0.8, 0.6, 0.4],
        skills=["swift", "testing", "architecture"],
    )

    reward = solver.compute_reward("test", results, embedder)
    assert reward.context_fit == 1.0  # perfect entropy (3 unique skills, uniform)


def test_compute_reward_context_fit_single_skill():
    solver = HJBSolver(cache=RewardCache())
    embedder = FakeEmbedder([1.0, 0.0], [[0.5, 0.5], [0.5, 0.5]])
    results = _make_results([0.8, 0.6], skills=["swift", "swift"])

    reward = solver.compute_reward("test", results, embedder)
    assert reward.context_fit == 0.0  # all same skill


def test_compute_reward_skill_affinity():
    solver = HJBSolver(cache=RewardCache())
    embedder = FakeEmbedder([1.0, 0.0], [[0.5, 0.5]])
    results = _make_results(
        [0.8],
        skills=["swift-concurrency"],
        domains=[["concurrency", "swift"]],
    )

    reward = solver.compute_reward("swift concurrency", results, embedder)
    assert reward.skill_affinity > 0.5  # query terms match domains


def test_compute_reward_empty_results():
    solver = HJBSolver(cache=RewardCache())
    embedder = FakeEmbedder([1.0, 0.0], [])
    reward = solver.compute_reward("test", [], embedder)
    assert reward.relevance_score == 0.0
    assert reward.context_fit == 0.0
    assert reward.skill_affinity == 0.0


# ── Integration Tests ────────────────────────────────────────────────────────


def test_integration_diffusion_hjb():
    """End-to-end: DiffusionRanker + HJBSolver together."""
    from maestro_rag.diffusion_ranker import DiffusionRanker

    cache = RewardCache()
    solver = HJBSolver(
        discount=0.95,
        learning_rate=0.1,
        min_episodes=0,  # enable learning immediately
        cache=cache,
    )

    results = _make_results(
        [0.8, 0.5, 0.2],
        skills=["swift", "testing", "architecture"],
        domains=[["swift"], ["testing"], ["architecture"]],
    )
    embeddings = [[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]]
    embedder = FakeEmbedder([1.0, 0.0], embeddings)

    ranker = DiffusionRanker(iterations=3)
    ranked = ranker.rerank("swift testing", results, embedder, hjb_solver=solver)

    # Results should still be ranked
    assert len(ranked) == 3
    assert ranked[0].final_score >= ranked[1].final_score

    # HJB should have recorded an episode
    assert cache.episode_count() == 1
    stats = cache.stats()
    assert stats["total_episodes"] == 1
    assert stats["value_entries"] >= 1


def test_integration_backward_compat_no_hjb():
    """DiffusionRanker works without HJB solver (Phase 1 behavior)."""
    from maestro_rag.diffusion_ranker import DiffusionRanker

    results = _make_results([0.8, 0.5, 0.2])
    embeddings = [[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]]
    embedder = FakeEmbedder([1.0, 0.0], embeddings)

    ranker = DiffusionRanker(iterations=3)
    ranked = ranker.rerank("test", results, embedder)  # no hjb_solver

    assert len(ranked) == 3
    assert ranked[0].final_score >= ranked[1].final_score


def test_contextual_embeddings_integration():
    """Reward computation uses T3 contextual embeddings via embedder."""
    solver = HJBSolver(cache=RewardCache())
    # Contextual embeddings carry skill context
    query_emb = [1.0, 0.0, 0.0]
    doc_embs = [
        [0.95, 0.05, 0.0],  # very similar to query
        [0.1, 0.9, 0.0],    # different from query
    ]
    embedder = FakeEmbedder(query_emb, doc_embs)
    results = _make_results([0.8, 0.3])

    reward = solver.compute_reward("test", results, embedder)

    # Relevance should reflect that first chunk is much more relevant
    assert reward.relevance_score > 0.4
    assert reward.total() > 0
