"""
Concept Graph — pre-computed relationships between programming concepts.

This is the secret weapon for recall: when someone searches "Sendable warning",
the graph expands the query with "actor isolation", "data race", "crossing boundary".

The graph is:
- Pre-computed (no LLM call at search time)
- Extensible (auto-extracts concepts from skill content)
- Weighted (stronger relationships rank higher)

Usage:
    graph = get_swift_concept_graph()
    expanded = graph.expand("Sendable warning actor")
    # → ["actor isolation", "data race", "thread safety", "nonisolated"]
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ConceptGraph:
    """Weighted graph of concept relationships for query expansion."""

    edges: dict[str, list[tuple[str, float]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    aliases: dict[str, str] = field(default_factory=dict)

    def add_relation(self, a: str, b: str, weight: float = 1.0) -> None:
        a, b = a.lower(), b.lower()
        self.edges[a].append((b, weight))
        self.edges[b].append((a, weight))

    def add_alias(self, alias: str, canonical: str) -> None:
        self.aliases[alias.lower()] = canonical.lower()

    def expand(
        self,
        query: str,
        max_expansions: int = 6,
        min_weight: float = 0.5,
        depth: int = 1,
    ) -> list[str]:
        query_lower = query.lower()
        query_tokens = set(re.findall(r"[@#]?\w+", query_lower))

        resolved = set()
        for token in query_tokens:
            canonical = self.aliases.get(token, token)
            resolved.add(canonical)

        candidates: dict[str, float] = {}
        for token in resolved:
            self._collect_neighbors(token, candidates, depth, min_weight, visited=set())

        for token in resolved | query_tokens:
            candidates.pop(token, None)

        ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        return [concept for concept, _ in ranked[:max_expansions]]

    def _collect_neighbors(
        self,
        concept: str,
        candidates: dict[str, float],
        depth: int,
        min_weight: float,
        visited: set[str],
    ) -> None:
        if depth <= 0 or concept in visited:
            return
        visited.add(concept)
        for neighbor, weight in self.edges.get(concept, []):
            if weight >= min_weight:
                current = candidates.get(neighbor, 0.0)
                candidates[neighbor] = max(current, weight)
                if depth > 1:
                    self._collect_neighbors(
                        neighbor, candidates, depth - 1, min_weight * 0.7, visited
                    )

    def extract_concepts_from_text(self, text: str) -> list[str]:
        concepts = set()
        patterns = [
            r"@\w+",
            r"#\w+",
            r"`([^`]+)`",
            r"\b(?:async|await|actor|sendable|nonisolated|isolated)\b",
            r"\b(?:Task|TaskGroup|AsyncSequence|AsyncStream)\b",
            r"\b(?:@Observable|@State|@Binding|@Environment|@Published)\b",
            r"\b(?:NavigationStack|NavigationPath|Sheet|Alert)\b",
            r"\b(?:ForEach|LazyVStack|LazyHStack|ScrollView)\b",
            r"\b(?:MVVM|TCA|VIPER|Coordinator)\b",
            r"\b(?:XCTest|Swift Testing|@Test|@Suite)\b",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                concepts.add(match.group(0).strip("`").lower())
        return sorted(concepts)


def get_swift_concept_graph() -> ConceptGraph:
    """Return the pre-built Swift concept graph."""
    g = ConceptGraph()

    # ── Concurrency ─────────────────────────────────────────────────────────
    g.add_relation("sendable", "actor isolation", 1.0)
    g.add_relation("sendable", "data race", 1.0)
    g.add_relation("sendable", "crossing boundary", 0.9)
    g.add_relation("sendable", "thread safety", 0.8)
    g.add_relation("sendable", "nonisolated", 0.7)
    g.add_relation("sendable", "@unchecked sendable", 0.8)

    g.add_relation("actor", "isolation", 1.0)
    g.add_relation("actor", "actor isolation", 1.0)
    g.add_relation("actor", "reentrancy", 0.8)
    g.add_relation("actor", "sendable", 0.9)
    g.add_relation("actor", "nonisolated", 0.8)
    g.add_relation("actor", "async", 0.7)

    g.add_relation("@mainactor", "ui thread", 1.0)
    g.add_relation("@mainactor", "main thread", 1.0)
    g.add_relation("@mainactor", "global actor", 0.9)
    g.add_relation("@mainactor", "isolation domain", 0.8)
    g.add_relation("@mainactor", "viewmodel", 0.7)
    g.add_relation("@mainactor", "actor isolation", 0.9)

    g.add_relation("async", "await", 1.0)
    g.add_relation("async", "task", 0.9)
    g.add_relation("async", "suspension point", 0.8)
    g.add_relation("async", "structured concurrency", 0.8)
    g.add_relation("async", "async let", 0.9)
    g.add_relation("async", "concurrency", 1.0)

    g.add_relation("task", "cancellation", 0.9)
    g.add_relation("task", "task group", 0.9)
    g.add_relation("task", "structured concurrency", 0.9)
    g.add_relation("task", "unstructured task", 0.7)
    g.add_relation("task", "task.detached", 0.7)
    g.add_relation("task", "priority", 0.6)

    g.add_relation("data race", "thread safety", 1.0)
    g.add_relation("data race", "sendable", 1.0)
    g.add_relation("data race", "actor isolation", 0.9)
    g.add_relation("data race", "strict concurrency", 0.9)
    g.add_relation("data race", "mutable state", 0.8)

    g.add_relation("swift 6", "strict concurrency", 1.0)
    g.add_relation("swift 6", "region-based isolation", 0.9)
    g.add_relation("swift 6", "sendable", 0.9)
    g.add_relation("swift 6", "breaking changes", 0.8)
    g.add_relation("swift 6", "migration", 0.9)

    g.add_relation("continuation", "async", 0.9)
    g.add_relation("continuation", "callback", 0.9)
    g.add_relation("continuation", "bridging", 0.8)

    # ── SwiftUI ─────────────────────────────────────────────────────────────
    g.add_relation("@state", "source of truth", 1.0)
    g.add_relation("@state", "view update", 0.9)
    g.add_relation("@state", "private", 0.7)
    g.add_relation("@state", "@binding", 0.9)

    g.add_relation("@observable", "observation", 1.0)
    g.add_relation("@observable", "@state", 0.8)
    g.add_relation("@observable", "viewmodel", 0.9)
    g.add_relation("@observable", "ios 17", 0.8)
    g.add_relation("@observable", "macro", 0.7)

    g.add_relation("@binding", "two-way binding", 1.0)
    g.add_relation("@binding", "child view", 0.8)
    g.add_relation("@binding", "@state", 0.9)

    g.add_relation("@environment", "dependency injection", 0.9)
    g.add_relation("@environment", "environment values", 1.0)
    g.add_relation("@environment", "view hierarchy", 0.8)

    g.add_relation("navigationstack", "navigation", 1.0)
    g.add_relation("navigationstack", "navigationpath", 0.9)
    g.add_relation("navigationstack", "programmatic navigation", 0.9)
    g.add_relation("navigationstack", "deep link", 0.7)
    g.add_relation("navigationstack", "ios 16", 0.7)

    g.add_relation("viewmodel", "mvvm", 1.0)
    g.add_relation("viewmodel", "@observable", 0.9)
    g.add_relation("viewmodel", "business logic", 0.9)
    g.add_relation("viewmodel", "@mainactor", 0.8)
    g.add_relation("viewmodel", "separation of concerns", 0.8)

    g.add_relation("performance", "lazy loading", 0.9)
    g.add_relation("performance", "identity", 0.8)
    g.add_relation("performance", "equatable", 0.8)
    g.add_relation("performance", "redraw", 0.9)
    g.add_relation("performance", "profiling", 0.7)

    # ── Testing ─────────────────────────────────────────────────────────────
    g.add_relation("@test", "swift testing", 1.0)
    g.add_relation("@test", "#expect", 0.9)
    g.add_relation("@test", "@suite", 0.8)
    g.add_relation("@test", "parameterized", 0.8)

    g.add_relation("#expect", "assertion", 1.0)
    g.add_relation("#expect", "swift testing", 0.9)
    g.add_relation("#expect", "xctest", 0.6)

    g.add_relation("mock", "test double", 1.0)
    g.add_relation("mock", "stub", 0.8)
    g.add_relation("mock", "protocol", 0.9)
    g.add_relation("mock", "dependency injection", 0.8)

    g.add_relation("xctest", "unit test", 1.0)
    g.add_relation("xctest", "xctestcase", 1.0)
    g.add_relation("xctest", "xcassertion", 0.9)
    g.add_relation("xctest", "swift testing", 0.7)

    # ── Architecture ─────────────────────────────────────────────────────────
    g.add_relation("mvvm", "viewmodel", 1.0)
    g.add_relation("mvvm", "separation of concerns", 0.9)
    g.add_relation("mvvm", "data binding", 0.8)
    g.add_relation("mvvm", "testability", 0.8)

    g.add_relation("clean architecture", "use case", 0.9)
    g.add_relation("clean architecture", "repository", 0.9)
    g.add_relation("clean architecture", "dependency inversion", 0.9)
    g.add_relation("clean architecture", "testability", 0.8)

    g.add_relation("dependency injection", "protocol", 0.9)
    g.add_relation("dependency injection", "testability", 0.9)
    g.add_relation("dependency injection", "inversion of control", 0.9)

    # ── Aliases ──────────────────────────────────────────────────────────────
    g.add_alias("di", "dependency injection")
    g.add_alias("vm", "viewmodel")
    g.add_alias("s6", "swift 6")
    g.add_alias("tca", "the composable architecture")
    g.add_alias("async/await", "async")
    g.add_alias("mainactor", "@mainactor")
    g.add_alias("observable", "@observable")
    g.add_alias("state", "@state")

    return g
