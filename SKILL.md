---
name: maestro
description: >
  Skill knowledge gateway. MUST call search_skills MCP tool before any coding
  task to retrieve expert knowledge from the indexed skill base. Use for every
  coding task, code review, architecture decision, debugging, refactoring, or
  feature implementation. Searches 100+ skills with semantic RAG retrieval.
---

# Maestro — Skill Knowledge Gateway

## Critical Rule

**BEFORE writing, reviewing, or modifying any code, ALWAYS call the `search_skills`
MCP tool.**

```
EVERY task → search_skills("what you need to know") → apply knowledge → respond
```

## How to Search

Be specific. Include context. Use the vocabulary of the problem:

```
search_skills("Sendable conformance warning in actor class")
search_skills("SwiftUI @Observable state management pattern")
search_skills("unit tests Swift Testing #expect mock")
search_skills("NavigationStack programmatic push iOS 16")
search_skills("@MainActor ViewModels thread safety")
```

For compound tasks, make **multiple focused calls**:
```
# Building a feature screen:
search_skills("SwiftUI view composition state management")
search_skills("async data loading viewmodel pattern")
search_skills("error handling user feedback SwiftUI")
```

## Tools

| Tool | When to use |
|------|-------------|
| `search_skills(query, top_k?)` | Before any coding — auto-indexes on first call |
| `reindex_skills(paths?)` | After adding or updating skills |
| `skill_status()` | To see what is indexed |

## Without MCP

Ask the user to run:
```bash
maestro context "task description"
```
Paste the output here before proceeding.

## Architecture

```
This file (~750 tokens)           ← Claude loads this
        ↓
search_skills MCP call            ← Claude calls this
        ↓
RAG Engine (Python)               ← runs locally
  T1: Concept graph expansion
  T2: Skill fingerprinting
  T3: Contextual embeddings
  T4: Hybrid search + RRF
  T5: Cross-encoder reranking
        ↓
Relevant chunks (ChromaDB)        ← returned to Claude
        ↓
Expert knowledge applied          ← better output
```
