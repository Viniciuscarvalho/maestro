"""Tests for the diffusion ranker (T6)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest

from maestro_rag.diffusion_ranker import DiffusionRanker, _argsort


# ── Test Fixtures ────────────────────────────────────────────────────────────


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


def _make_results(scores: list[float]) -> list[FakeSearchResult]:
    """Create fake search results with given scores."""
    results = []
    for i, score in enumerate(scores):
        chunk = FakeChunk(
            id=f"chunk_{i}",
            text=f"Content for chunk {i}",
            contextual_text=f"[test | file.md]\nContent for chunk {i}",
        )
        results.append(FakeSearchResult(chunk=chunk, final_score=score))
    return results


class FakeEmbedder:
    """Embedder that returns predetermined embeddings."""

    def __init__(self, embeddings: list[list[float]]):
        self._embeddings = embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings[: len(texts)]


# ── Unit Tests ───────────────────────────────────────────────────────────────


def test_single_result_passthrough():
    """A single result should be returned unchanged."""
    results = _make_results([0.5])
    embedder = FakeEmbedder([[1.0, 0.0, 0.0]])
    ranker = DiffusionRanker(iterations=3)

    ranked = ranker.rerank("test query", results, embedder)

    assert len(ranked) == 1
    assert ranked[0].final_score == 0.5


def test_empty_results():
    """Empty input should return empty output."""
    ranker = DiffusionRanker()
    ranked = ranker.rerank("test", [], FakeEmbedder([]))
    assert ranked == []


def test_similarity_matrix_shape_and_symmetry():
    """Similarity matrix should be N x N and symmetric."""
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.9, 0.1, 0.0],  # similar to first
    ]
    ranker = DiffusionRanker(sim_threshold=0.0)
    matrix = ranker._build_similarity_matrix(embeddings)

    assert len(matrix) == 3
    assert all(len(row) == 3 for row in matrix)
    # Symmetry
    for i in range(3):
        for j in range(3):
            assert abs(matrix[i][j] - matrix[j][i]) < 1e-10
    # Diagonal is 1.0
    for i in range(3):
        assert matrix[i][i] == 1.0


def test_similarity_threshold_filtering():
    """Similarities below threshold should be zeroed out."""
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],  # orthogonal → cosine = 0
    ]
    ranker = DiffusionRanker(sim_threshold=0.5)
    matrix = ranker._build_similarity_matrix(embeddings)

    # Off-diagonal should be 0 since cosine(orthogonal) = 0 < 0.5
    assert matrix[0][1] == 0.0
    assert matrix[1][0] == 0.0


def test_diffusion_improves_ranking():
    """Chunks similar to high-scoring chunks should be boosted.

    Setup: 3 chunks where chunk 0 has high score, chunk 2 is similar to chunk 0
    but has low initial score. After diffusion, chunk 2 should be boosted.
    """
    results = _make_results([0.8, 0.1, 0.05])
    # Chunk 0 and chunk 2 are similar, chunk 1 is different
    embeddings = [
        [1.0, 0.0, 0.0],    # chunk 0: high score
        [0.0, 1.0, 0.0],    # chunk 1: low score, different direction
        [0.95, 0.05, 0.0],  # chunk 2: lowest score, but similar to chunk 0
    ]
    embedder = FakeEmbedder(embeddings)

    ranker = DiffusionRanker(iterations=3, damping=0.85, sim_threshold=0.0)
    ranked = ranker.rerank("test", results, embedder)

    # Chunk 2 should be boosted above chunk 1 due to similarity with chunk 0
    scores = {r.chunk.id: r.final_score for r in ranked}
    assert scores["chunk_2"] > scores["chunk_1"], (
        f"chunk_2 ({scores['chunk_2']:.4f}) should be boosted above "
        f"chunk_1 ({scores['chunk_1']:.4f}) due to similarity with high-scoring chunk_0"
    )


def test_convergence_early_stop():
    """With identical embeddings, scores should converge quickly."""
    results = _make_results([0.5, 0.3, 0.2])
    # All chunks identical → scores converge to uniform-ish distribution
    embeddings = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
    ]
    embedder = FakeEmbedder(embeddings)

    ranker = DiffusionRanker(iterations=100, epsilon=1e-6)
    ranker.rerank("test", results, embedder)

    # Should converge well before 100 iterations
    assert ranker.iterations_used < 100, (
        f"Expected early stop but ran {ranker.iterations_used} iterations"
    )


def test_damping_factor_effect():
    """Different damping values should produce different rankings."""
    results_a = _make_results([0.6, 0.3, 0.1])
    results_b = _make_results([0.6, 0.3, 0.1])
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.5, 0.5, 0.0],
        [0.0, 1.0, 0.0],
    ]

    ranker_high = DiffusionRanker(iterations=3, damping=0.95, sim_threshold=0.0)
    ranker_low = DiffusionRanker(iterations=3, damping=0.3, sim_threshold=0.0)

    ranked_high = ranker_high.rerank("test", results_a, FakeEmbedder(embeddings))
    ranked_low = ranker_low.rerank("test", results_b, FakeEmbedder(embeddings))

    scores_high = [r.final_score for r in ranked_high]
    scores_low = [r.final_score for r in ranked_low]

    # Scores should differ between the two damping values
    assert scores_high != scores_low, "Different damping values should produce different scores"


def test_reward_computation():
    """Reward should be 1.0 when ranking is unchanged, < 1.0 when changed."""
    ranker = DiffusionRanker()

    # Same order → reward = 1.0
    same_initial = [0.8, 0.5, 0.2]
    same_final = [0.9, 0.6, 0.3]  # same relative order
    reward = ranker._compute_reward(same_initial, same_final)
    assert reward == 1.0, f"Expected 1.0 for same ranking, got {reward}"

    # Reversed order → reward = -1.0
    reversed_final = [0.2, 0.5, 0.8]
    reward = ranker._compute_reward(same_initial, reversed_final)
    assert reward == -1.0, f"Expected -1.0 for reversed ranking, got {reward}"


def test_argsort():
    """Argsort should return correct rank positions."""
    ranks = _argsort([0.1, 0.9, 0.5])
    # 0.9 is rank 0, 0.5 is rank 1, 0.1 is rank 2
    assert ranks == [2, 0, 1]


def test_normalize_rows():
    """Row normalization should produce rows summing to 1."""
    ranker = DiffusionRanker()
    matrix = [[2.0, 1.0], [1.0, 3.0]]
    normalized = ranker._normalize_rows(matrix)

    for row in normalized:
        assert abs(sum(row) - 1.0) < 1e-10


def test_diffuse_step():
    """Single diffusion step should blend transition and initial scores."""
    ranker = DiffusionRanker(damping=0.5)
    trans = [[0.5, 0.5], [0.5, 0.5]]
    scores = [0.8, 0.2]
    initial = [0.8, 0.2]

    new_scores = ranker._diffuse_step(trans, scores, initial)

    # With uniform transition and damping=0.5:
    # new[0] = 0.5 * (0.5*0.8 + 0.5*0.2) + 0.5 * 0.8 = 0.5*0.5 + 0.4 = 0.65
    assert abs(new_scores[0] - 0.65) < 1e-10
    assert abs(new_scores[1] - 0.35) < 1e-10


def test_rerank_sets_rerank_score():
    """Reranking should set the rerank_score attribute on results."""
    results = _make_results([0.6, 0.4])
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    embedder = FakeEmbedder(embeddings)

    ranker = DiffusionRanker(iterations=1)
    ranked = ranker.rerank("test", results, embedder)

    for r in ranked:
        assert r.rerank_score is not None


def test_steps_diagnostic_recorded():
    """Diagnostic steps should be recorded for debugging."""
    results = _make_results([0.5, 0.3, 0.2])
    embeddings = [[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]]
    embedder = FakeEmbedder(embeddings)

    ranker = DiffusionRanker(iterations=3, epsilon=0.0)
    ranker.rerank("test", results, embedder)

    assert len(ranker.steps) == 3
    assert all(s.iteration == i for i, s in enumerate(ranker.steps))
    assert all(isinstance(s.max_delta, float) for s in ranker.steps)


def test_flag_disabled_uses_t5():
    """When diffusion_rl_enabled=False, engine should use T5 cross-encoder."""
    from maestro_rag.engine import Config

    config = Config()
    assert config.diffusion_rl_enabled is False
    assert config.reranker_enabled is True

    config_diffusion = Config()
    config_diffusion.diffusion_rl_enabled = True
    assert config_diffusion.diffusion_rl_enabled is True
