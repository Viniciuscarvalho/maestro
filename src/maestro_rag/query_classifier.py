"""
Query Classifier — context-aware diffusion scheduling per query type (Phase 3).

Classifies queries into types (architecture, api, pattern, tool, general)
and assigns per-type diffusion parameters: iterations, reward weights,
and early-stop thresholds. This enables adaptive scheduling where
architecture queries get more diffusion iterations (diversity) while
API queries get fewer iterations (precision).

Classification is keyword-based — lightweight, no external model needed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class QueryType(Enum):
    ARCHITECTURE = "architecture"
    API = "api"
    PATTERN = "pattern"
    TOOL = "tool"
    GENERAL = "general"


@dataclass(frozen=True)
class QueryProfile:
    """Diffusion scheduling profile for a query type.

    Attributes:
        query_type: Classified query category.
        confidence: Classification confidence (0-1).
        iterations: Recommended diffusion iterations.
        reward_weights: (relevance, context_fit, skill_affinity) weights for HJB reward.
        early_stop_threshold: Epsilon for convergence detection.
    """
    query_type: QueryType
    confidence: float
    iterations: int
    reward_weights: tuple[float, float, float]
    early_stop_threshold: float


# ── Per-type profiles ────────────────────────────────────────────────────────

_PROFILES: dict[QueryType, dict] = {
    QueryType.ARCHITECTURE: {
        "iterations": 5,
        "reward_weights": (0.3, 0.5, 0.2),
        "early_stop_threshold": 1e-3,
    },
    QueryType.API: {
        "iterations": 2,
        "reward_weights": (0.7, 0.1, 0.2),
        "early_stop_threshold": 1e-5,
    },
    QueryType.PATTERN: {
        "iterations": 3,
        "reward_weights": (0.5, 0.3, 0.2),
        "early_stop_threshold": 1e-4,
    },
    QueryType.TOOL: {
        "iterations": 2,
        "reward_weights": (0.6, 0.2, 0.2),
        "early_stop_threshold": 1e-5,
    },
    QueryType.GENERAL: {
        "iterations": 3,
        "reward_weights": (0.5, 0.3, 0.2),
        "early_stop_threshold": 1e-4,
    },
}

# ── Keyword patterns ────────────────────────────────────────────────────────

_PATTERNS: dict[QueryType, list[re.Pattern]] = {
    QueryType.ARCHITECTURE: [
        re.compile(r"\b(architect\w*|mvvm|tca|viper|coordinator|repository\s*pattern)\b", re.I),
        re.compile(r"\b(design\s*pattern|layer|module|dependency\s*inject|clean\s*arch)\b", re.I),
        re.compile(r"\b(system\s*design|scalab|micro\s*service|separation\s*of\s*concern)\b", re.I),
        re.compile(r"\b(refactor|restructur|decompos|organiz\w+\s*code)\b", re.I),
    ],
    QueryType.API: [
        re.compile(r"\b(api|method|function|property|parameter|return\s*type)\b", re.I),
        re.compile(r"\b(NavigationStack|NavigationPath|SwiftUI\.\w+|UIKit\.\w+)\b"),
        re.compile(r"\b(syntax|signature|initializer|protocol\s*conform)\b", re.I),
        re.compile(r"\b(how\s*to\s*(?:use|call|create|init))\b", re.I),
        re.compile(r"`[A-Z]\w+(?:\.\w+)+`"),  # e.g. `View.onAppear`
    ],
    QueryType.PATTERN: [
        re.compile(r"\b(best\s*practic|pattern|idiom|convention|anti.?pattern)\b", re.I),
        re.compile(r"\b(error\s*handl|guard|do.?catch|result\s*type|typed\s*throw)\b", re.I),
        re.compile(r"\b(state\s*manag|observable|binding|environment)\b", re.I),
        re.compile(r"\b(concurren|async|await|actor|sendable|isolation)\b", re.I),
    ],
    QueryType.TOOL: [
        re.compile(r"\b(xcodebuild|swift\s*package|spm|cocoapods|carthage)\b", re.I),
        re.compile(r"\b(cli|command\s*line|terminal|shell|script)\b", re.I),
        re.compile(r"\b(build|compile|archive|export|sign|provision|certificate)\b", re.I),
        re.compile(r"\b(config|setup|install|environment|debug\w*|profil\w*)\b", re.I),
    ],
}


class QueryClassifier:
    """Classify queries into types for adaptive diffusion scheduling."""

    def classify(self, query: str) -> QueryProfile:
        """Classify a query and return its diffusion profile.

        Scoring: Each pattern match adds 1 point to its category.
        The category with the most matches wins. Confidence is
        proportional to the gap between the winner and the runner-up.
        """
        scores: dict[QueryType, int] = {t: 0 for t in QueryType}

        for qtype, patterns in _PATTERNS.items():
            for pattern in patterns:
                matches = pattern.findall(query)
                scores[qtype] += len(matches)

        # Find winner
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_type, best_score = ranked[0]
        runner_up_score = ranked[1][1] if len(ranked) > 1 else 0

        # Fallback to GENERAL if no matches
        if best_score == 0:
            best_type = QueryType.GENERAL

        # Confidence based on margin
        total = sum(scores.values()) or 1
        confidence = (best_score - runner_up_score) / total if best_score > 0 else 0.5
        confidence = max(0.1, min(1.0, confidence))

        profile_data = _PROFILES[best_type]

        return QueryProfile(
            query_type=best_type,
            confidence=round(confidence, 2),
            iterations=profile_data["iterations"],
            reward_weights=profile_data["reward_weights"],
            early_stop_threshold=profile_data["early_stop_threshold"],
        )
