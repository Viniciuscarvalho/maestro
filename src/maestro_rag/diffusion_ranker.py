"""
Diffusion Ranker — iterative reranking via score diffusion (T6).

Unlike T5 (cross-encoder) which scores each (query, chunk) pair independently,
the diffusion ranker builds a similarity graph between result chunks and
iteratively propagates relevance scores. Semantically similar chunks reinforce
each other, producing more coherent result sets.

Algorithm:
    1. Embed all candidate chunks
    2. Build pairwise cosine similarity matrix
    3. Normalize into a row-stochastic transition matrix
    4. Iteratively diffuse: s_{t+1} = damping * T @ s_t + (1-damping) * s_0
    5. Early-stop when max score change < epsilon
    6. Re-sort results by diffused scores

Prepares for Phase 2 (HJB-Bellman) by computing session-level reward signals.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class DiffusionStep:
    """Diagnostic record for one diffusion iteration."""
    iteration: int
    max_delta: float
    scores: list[float]


class DiffusionRanker:
    """Iterative diffusion-based reranker.

    Args:
        iterations: Maximum diffusion steps (default 3).
        damping: Teleport probability, analogous to PageRank damping.
                 Higher values weight the diffusion more vs. initial scores.
        epsilon: Convergence threshold for early stopping.
        sim_threshold: Minimum cosine similarity to keep in the transition matrix.
    """

    def __init__(
        self,
        iterations: int = 3,
        damping: float = 0.85,
        epsilon: float = 1e-4,
        sim_threshold: float = 0.1,
    ):
        self.iterations = iterations
        self.damping = damping
        self.epsilon = epsilon
        self.sim_threshold = sim_threshold
        self.steps: list[DiffusionStep] = []

    def rerank(
        self,
        query: str,
        results: list,
        embedder,
        hjb_solver=None,
        query_profile=None,
        feedback_aggregator=None,
    ) -> list:
        """Run diffusion reranking on search results.

        Args:
            query: Original search query (used for embedding context).
            results: List of SearchResult objects with chunk.text and final_score.
            embedder: Embedder instance with embed_documents() method.
            hjb_solver: Optional HJBSolver for adaptive damping and reward learning.
            query_profile: Optional QueryProfile for per-type scheduling.
            feedback_aggregator: Optional FeedbackAggregator for usage tracking.

        Returns:
            Results re-sorted by diffused scores.
        """
        self.steps.clear()
        n = len(results)

        if n <= 1:
            return results

        # Phase 3: Adaptive scheduling from query profile
        if query_profile is not None:
            self.iterations = query_profile.iterations
            self.epsilon = query_profile.early_stop_threshold

        # Extract chunk texts and embed them
        texts = [r.chunk.contextual_text for r in results]
        embeddings = embedder.embed_documents(texts)

        # Build similarity and transition matrices
        sim_matrix = self._build_similarity_matrix(embeddings)
        trans_matrix = self._normalize_rows(sim_matrix)

        # Initial scores from upstream pipeline (RRF)
        initial_scores = [r.final_score for r in results]

        # HJB: adapt damping based on learned value function
        state_hash = None
        if hjb_solver is not None:
            state_hash = hjb_solver.hash_state(initial_scores)
            optimal_damping = hjb_solver.get_optimal_damping(state_hash)
            self.damping = optimal_damping

        # Normalize to sum=1 for stable diffusion
        score_sum = sum(initial_scores) or 1.0
        scores = [s / score_sum for s in initial_scores]
        initial_norm = scores[:]

        # Diffusion loop
        for iteration in range(self.iterations):
            new_scores = self._diffuse_step(trans_matrix, scores, initial_norm)
            max_delta = max(abs(a - b) for a, b in zip(new_scores, scores))

            self.steps.append(DiffusionStep(
                iteration=iteration,
                max_delta=max_delta,
                scores=new_scores[:],
            ))

            scores = new_scores

            if max_delta < self.epsilon:
                break

        # Update results with diffused scores
        for r, score in zip(results, scores):
            r.rerank_score = score
            r.final_score = score

        results.sort(key=lambda x: x.final_score, reverse=True)

        # HJB: compute reward and update value function
        if hjb_solver is not None and state_hash is not None:
            reward_weights = query_profile.reward_weights if query_profile else None
            reward = hjb_solver.compute_reward(
                query, results, embedder, reward_weights=reward_weights,
            )
            final_hash = hjb_solver.hash_state([r.final_score for r in results])
            hjb_solver.update_value(
                state_hash,
                reward.total(),
                next_state_hash=final_hash,
                query=query,
                components=reward.as_dict(),
            )

        # Phase 3: Log feedback for skill affinity learning
        if feedback_aggregator is not None and query_profile is not None:
            feedback_aggregator.log_usage(query_profile.query_type.value, results)

        return results

    def _build_similarity_matrix(
        self, embeddings: list[list[float]]
    ) -> list[list[float]]:
        """Build pairwise cosine similarity matrix with threshold filtering."""
        n = len(embeddings)
        matrix: list[list[float]] = [[0.0] * n for _ in range(n)]

        for i in range(n):
            matrix[i][i] = 1.0
            for j in range(i + 1, n):
                sim = self._cosine(embeddings[i], embeddings[j])
                if sim >= self.sim_threshold:
                    matrix[i][j] = sim
                    matrix[j][i] = sim

        return matrix

    def _normalize_rows(self, matrix: list[list[float]]) -> list[list[float]]:
        """Normalize matrix rows to sum to 1 (row-stochastic)."""
        n = len(matrix)
        result: list[list[float]] = [[0.0] * n for _ in range(n)]
        for i in range(n):
            row_sum = sum(matrix[i]) or 1.0
            for j in range(n):
                result[i][j] = matrix[i][j] / row_sum
        return result

    def _diffuse_step(
        self,
        trans_matrix: list[list[float]],
        scores: list[float],
        initial_scores: list[float],
    ) -> list[float]:
        """One diffusion step: s_{t+1} = damping * T @ s_t + (1-damping) * s_0."""
        n = len(scores)
        new_scores: list[float] = [0.0] * n
        for i in range(n):
            diffused = sum(trans_matrix[i][j] * scores[j] for j in range(n))
            new_scores[i] = self.damping * diffused + (1 - self.damping) * initial_scores[i]
        return new_scores

    def _compute_reward(
        self,
        initial_scores: list[float],
        final_scores: list[float],
    ) -> float:
        """Compute Kendall tau rank correlation as session reward signal.

        Returns a value in [-1, 1] where:
            1  = perfect agreement (no reranking needed)
            -1 = complete reversal
            0  = no correlation

        This metric measures how much the diffusion changed the ranking order.
        Used for logging and as a foundation for Phase 2 HJB reward learning.
        """
        n = len(initial_scores)
        if n < 2:
            return 1.0

        # Build rank orders
        initial_order = _argsort(initial_scores)
        final_order = _argsort(final_scores)

        concordant = 0
        discordant = 0
        for i in range(n):
            for j in range(i + 1, n):
                init_cmp = initial_order[i] - initial_order[j]
                final_cmp = final_order[i] - final_order[j]
                product = init_cmp * final_cmp
                if product > 0:
                    concordant += 1
                elif product < 0:
                    discordant += 1

        pairs = n * (n - 1) // 2
        if pairs == 0:
            return 1.0
        return (concordant - discordant) / pairs

    @property
    def last_reward(self) -> float:
        """Get the reward from the most recent rerank call."""
        if not self.steps:
            return 1.0
        initial = self.steps[0].scores
        final = self.steps[-1].scores
        return self._compute_reward(initial, final)

    @property
    def iterations_used(self) -> int:
        """Number of iterations actually executed (may be less due to early stop)."""
        return len(self.steps)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na and nb else 0.0


def _argsort(values: list[float]) -> list[int]:
    """Return rank positions (0-indexed) for each element."""
    indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=True)
    ranks = [0] * len(values)
    for rank, (idx, _) in enumerate(indexed):
        ranks[idx] = rank
    return ranks
