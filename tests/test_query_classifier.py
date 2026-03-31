"""Tests for query classifier and Phase 3 integration."""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from maestro_rag.query_classifier import QueryClassifier, QueryProfile, QueryType


# ── Classification Tests ─────────────────────────────────────────────────────


def test_classify_architecture_query():
    c = QueryClassifier()
    profile = c.classify("MVVM vs TCA architecture for SwiftUI app")
    assert profile.query_type == QueryType.ARCHITECTURE


def test_classify_api_query():
    c = QueryClassifier()
    profile = c.classify("NavigationStack push method syntax")
    assert profile.query_type == QueryType.API


def test_classify_pattern_query():
    c = QueryClassifier()
    profile = c.classify("best practice for error handling with async await")
    assert profile.query_type == QueryType.PATTERN


def test_classify_tool_query():
    c = QueryClassifier()
    profile = c.classify("xcodebuild archive command for release build")
    assert profile.query_type == QueryType.TOOL


def test_classify_general_query():
    c = QueryClassifier()
    profile = c.classify("hello world")
    assert profile.query_type == QueryType.GENERAL


def test_classify_returns_query_profile():
    c = QueryClassifier()
    profile = c.classify("MVVM architecture")
    assert isinstance(profile, QueryProfile)
    assert isinstance(profile.query_type, QueryType)
    assert 0 <= profile.confidence <= 1.0
    assert profile.iterations > 0
    assert len(profile.reward_weights) == 3
    assert profile.early_stop_threshold > 0


# ── Profile Configuration Tests ──────────────────────────────────────────────


def test_profile_iterations_architecture_more_than_api():
    c = QueryClassifier()
    arch = c.classify("system design architecture layers")
    api = c.classify("NavigationStack push method API syntax")
    assert arch.iterations > api.iterations


def test_profile_reward_weights_api_high_relevance():
    c = QueryClassifier()
    api = c.classify("NavigationStack push method API")
    w_rel, w_ctx, w_aff = api.reward_weights
    assert w_rel > w_ctx, "API queries should weight relevance > context_fit"


def test_profile_reward_weights_architecture_high_context():
    c = QueryClassifier()
    arch = c.classify("MVVM architecture design pattern layers")
    w_rel, w_ctx, w_aff = arch.reward_weights
    assert w_ctx > w_rel, "Architecture queries should weight context_fit > relevance"


def test_profile_early_stop_api_stricter():
    c = QueryClassifier()
    api = c.classify("NavigationStack method API syntax")
    general = c.classify("hello world")
    assert api.early_stop_threshold < general.early_stop_threshold


# ── Feedback Aggregator Tests ────────────────────────────────────────────────


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


def _make_results(
    scores: list[float],
    skills: list[str] | None = None,
) -> list[FakeSearchResult]:
    results = []
    for i, score in enumerate(scores):
        skill = skills[i] if skills else "test"
        chunk = FakeChunk(id=f"c_{i}", skill=skill)
        results.append(FakeSearchResult(chunk=chunk, final_score=score))
    return results


def test_feedback_aggregator_log():
    from maestro_rag.hjb_solver import FeedbackAggregator, RewardCache

    cache = RewardCache()
    agg = FeedbackAggregator(cache=cache)
    results = _make_results([0.8, 0.5], skills=["swift", "testing"])

    agg.log_usage("architecture", results)

    stats = agg.get_skill_stats()
    assert "swift" in stats
    assert "testing" in stats
    assert stats["swift"]["count"] == 1


def test_feedback_aggregator_stats_per_type():
    from maestro_rag.hjb_solver import FeedbackAggregator, RewardCache

    cache = RewardCache()
    agg = FeedbackAggregator(cache=cache)

    agg.log_usage("api", _make_results([0.9], skills=["swift"]))
    agg.log_usage("api", _make_results([0.7], skills=["swift"]))
    agg.log_usage("architecture", _make_results([0.6], skills=["testing"]))

    type_stats = agg.get_type_stats()
    assert "api" in type_stats
    assert type_stats["api"]["count"] == 2
    assert "architecture" in type_stats


def test_feedback_aggregator_retrain_trigger():
    from maestro_rag.hjb_solver import FeedbackAggregator, RewardCache

    cache = RewardCache()
    agg = FeedbackAggregator(cache=cache, retrain_interval=3)

    assert not agg.should_retrain()
    for i in range(3):
        agg.log_usage("api", _make_results([0.5]))

    assert agg.should_retrain()
    agg.reset_counter()
    assert not agg.should_retrain()


def test_feedback_aggregator_affinity_weights():
    from maestro_rag.hjb_solver import FeedbackAggregator, RewardCache

    cache = RewardCache()
    agg = FeedbackAggregator(cache=cache)

    # Swift appears more in API queries
    agg.log_usage("api", _make_results([0.9, 0.8], skills=["swift", "swift"]))
    agg.log_usage("architecture", _make_results([0.5], skills=["testing"]))

    weights = agg.compute_affinity_weights()
    assert "api" in weights
    assert "swift" in weights["api"]
    assert weights["api"]["swift"] == 1.0  # only skill in API type


# ── Reward Weights Integration ───────────────────────────────────────────────


def test_reward_signal_custom_weights():
    from maestro_rag.hjb_solver import RewardSignal

    signal = RewardSignal(relevance_score=1.0, context_fit=0.0, skill_affinity=0.0)

    # Default weights: 0.5 * 1.0 = 0.5
    assert abs(signal.total() - 0.5) < 1e-10

    # Custom weights: API-style (0.7, 0.1, 0.2) → 0.7 * 1.0 = 0.7
    signal._custom_weights = (0.7, 0.1, 0.2)
    assert abs(signal.total() - 0.7) < 1e-10


# ── Full Pipeline Integration ────────────────────────────────────────────────


class FakeEmbedder:
    def __init__(self, query_emb, doc_embs):
        self._q = query_emb
        self._d = doc_embs

    def embed_query(self, text):
        return self._q

    def embed_documents(self, texts):
        return self._d[: len(texts)]


def test_integration_full_pipeline():
    """End-to-end: QueryClassifier + DiffusionRanker + HJBSolver + FeedbackAggregator."""
    from maestro_rag.diffusion_ranker import DiffusionRanker
    from maestro_rag.hjb_solver import HJBSolver, RewardCache, FeedbackAggregator

    cache = RewardCache()
    solver = HJBSolver(discount=0.95, min_episodes=0, cache=cache)
    feedback = FeedbackAggregator(cache=cache)
    classifier = QueryClassifier()

    profile = classifier.classify("MVVM architecture design")
    assert profile.query_type == QueryType.ARCHITECTURE

    results = _make_results(
        [0.8, 0.5, 0.2],
        skills=["swift", "testing", "architecture"],
    )
    embeddings = [[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]]
    embedder = FakeEmbedder([1.0, 0.0], embeddings)

    ranker = DiffusionRanker(iterations=3)
    ranked = ranker.rerank(
        "MVVM architecture design",
        results,
        embedder,
        hjb_solver=solver,
        query_profile=profile,
        feedback_aggregator=feedback,
    )

    assert len(ranked) == 3
    assert ranked[0].final_score >= ranked[1].final_score

    # Verify HJB learned
    assert cache.episode_count() == 1

    # Verify feedback logged
    skill_stats = feedback.get_skill_stats()
    assert len(skill_stats) > 0

    # Verify architecture profile was used (more iterations)
    assert ranker.iterations == profile.iterations


def test_adaptive_scheduling_early_stop():
    """API queries should converge faster (fewer iterations used) than architecture."""
    from maestro_rag.diffusion_ranker import DiffusionRanker

    results_api = _make_results([0.8, 0.5, 0.2])
    results_arch = _make_results([0.8, 0.5, 0.2])
    embeddings = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
    embedder = FakeEmbedder([1.0, 0.0, 0.0], embeddings)

    classifier = QueryClassifier()

    api_profile = classifier.classify("NavigationStack method API syntax")
    ranker_api = DiffusionRanker()
    ranker_api.rerank("api query", results_api, embedder, query_profile=api_profile)

    arch_profile = classifier.classify("MVVM architecture design layers")
    ranker_arch = DiffusionRanker()
    ranker_arch.rerank("arch query", results_arch, embedder, query_profile=arch_profile)

    # API has fewer max iterations → should use fewer or equal iterations
    assert ranker_api.iterations <= ranker_arch.iterations
