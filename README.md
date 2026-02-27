# Maestro - The skill orchestrator that makes Claude Code smarter.

<p align="center">
  <img src="assets/banner.svg" alt="Maestro Banner" width="100%"/>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-ffd60a?style=flat-square" alt="License: MIT"/></a>
  <a href="https://claude.ai/"><img src="https://img.shields.io/badge/Claude_Code-compatible-6c5ce7?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjEwIi8+PC9zdmc+&logoColor=white&style=flat-square" alt="Claude Code"/></a>
  <a href="#any-language-any-stack"><img src="https://img.shields.io/badge/Language-Agnostic-2ea44f?style=flat-square" alt="Language Agnostic"/></a>
  <a href="#install"><img src="https://img.shields.io/badge/Setup-2_minutes-0078d7?style=flat-square" alt="Quick Setup"/></a>
</p>

Maestro is an autonomous skill orchestrator for Claude Code. It scans your project, indexes every skill you have installed, and automatically routes the right expertise to every task. You describe what you want — Maestro figures out which skills to load and applies them silently.

> You already have specialized skills installed. Manually remembering which one to invoke on each task is friction you shouldn't carry. Maestro removes that entirely.

## What you get

- **Automatic skill routing** — you never type `/skill-name` again. Just describe your task in plain language.
- **RAG-powered semantic search** — when keywords aren't enough, a 5-phase retrieval engine understands the _meaning_ of your request and matches it to the right skills.
- **Multi-skill composition** — real tasks span 2-3 domains at once. Maestro loads and merges them seamlessly.
- **Lazy reference loading** — out of 52+ reference files, only the 2-3 relevant ones are loaded per task. Your context window stays clean.
- **Project-first intelligence** — reads your `CLAUDE.md`, respects your conventions, and never overrides your project rules.
- **Continuous learning** — builds a knowledge graph of your project's patterns, decisions, and idioms over sessions.
- **Skill gap detection** — identifies missing expertise and suggests what to install.

## Install

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- At least one skill installed in `~/.claude/skills/` or `.claude/skills/` (Maestro discovers them automatically)
- A project with `CLAUDE.md` (optional but recommended for best results)

### Option 1: User skill (available in all your projects)

```bash
git clone https://github.com/Viniciuscarvalho/maestro.git ~/.claude/skills/maestro
```

### Option 2: Project skill (only this project)

```bash
git clone https://github.com/Viniciuscarvalho/maestro.git .claude/skills/maestro
```

### Option 3: Claude.ai Projects

Upload these files to your Project's knowledge:

1. `SKILL.md` (required)
2. `skill-registry.md`
3. `routing-engine.md`
4. `rag-engine.md`
5. `semantic-index.md`
6. `project-scanner.md`
7. `knowledge-graph.md`

### After installing

That's it. There is no configuration step. The next time you start a Claude Code session, Maestro activates automatically on every task. You just keep working exactly as before — the difference is better, more informed output.

## Quick start

```
You: "Build a user profile screen with async data loading"

Maestro (silently):
  ├── Scans: Package.swift → Swift 6.0, SwiftUI, iOS 17+
  ├── Classifies: domain=ui+concurrency, action=create, scope=module
  ├── Routes: swiftui-expert-skill (primary) + swift-concurrency (secondary)
  ├── Loads: state-management.md, modern-apis.md, async-await-basics.md
  ├── Reads: CLAUDE.md → MVVM pattern, @Observable, AppColors
  └── Applies: All knowledge combined

You get: Production-quality SwiftUI view with correct state management,
         proper async patterns, following your project's conventions.
```

No `/slash-command`. No manual skill selection. Just describe what you want.

## How routing works

Maestro uses two paths to match your task to the right skills:

```
Task received
  │
  ▼
┌─────────────────────────────────────────────┐
│  Fast Path: Keyword matching                │
│  Matches trigger words like @Test, SwiftUI, │
│  async/await, "review this PR"              │
│  ✓ Instant, deterministic                   │
└──────────────────┬──────────────────────────┘
                   │ No clear match?
                   ▼
┌─────────────────────────────────────────────┐
│  Semantic Path: RAG Engine                  │
│  Decomposes your natural language query,    │
│  scores skills by meaning, loads only the   │
│  references that matter                     │
│  ✓ Handles ambiguous & conceptual tasks     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
              Execute task
```

**Fast path** covers the majority of tasks. When you mention `@Test`, `SwiftUI`, `async/await`, or say "review this PR", keyword matching instantly finds the right skill.

**Semantic path (RAG)** activates when keywords aren't enough — natural language queries, conceptual questions, or ambiguous multi-domain tasks. The RAG engine runs a 5-phase pipeline:

| Phase | What it does |
| --- | --- |
| **RAG-1: Decompose** | Breaks your query into intent, domain, complexity, and implicit requirements |
| **RAG-2: Score** | Rates each skill using a weighted rubric (domain match, intent, framework, semantic similarity, anti-examples) |
| **RAG-3: Retrieve** | Lazy-loads only the 2-3 reference files relevant to THIS specific task |
| **RAG-4: Optimize** | Merges multi-skill context, deduplicates, stays within context budget (~5000 tokens) |
| **RAG-5: Decide** | Confidence check — score >70 routes confidently, <50 flags a skill gap |

### Why RAG matters

Without RAG, ambiguous requests get fuzzy routing:

```
You: "Make sure my data model updates are reflected everywhere
      without causing threading issues"

Keyword-only routing:
  - "data model" → maybe swift-best-practices?
  - "threading" → maybe swift-concurrency?
  - "reflected everywhere" → maybe swiftui-expert-skill?
  - Result: AMBIGUOUS — no clear winner

With RAG:
  - Understands you need state management + concurrency safety
  - Scores: swiftui-expert-skill (80), swift-concurrency (65)
  - Loads: state-management.md + actors.md (3 files, not 52)
  - Result: CONFIDENT — the right skills, the right references
```

The RAG engine also uses **anti-examples** — patterns that _look like_ they match a skill but shouldn't. For example, "fix this Sendable warning" mentions state but won't trigger `swiftui-expert-skill` because the anti-example system knows that's a concurrency problem.

## Adding your own skills

Maestro works with **any skill** that follows the standard Claude Code skill format. To create a skill that Maestro can route to:

### 1. Create the skill structure

```
~/.claude/skills/my-skill/
├── SKILL.md                    # Required: skill logic + YAML frontmatter
└── references/
    ├── topic-a.md              # Deep knowledge files
    ├── topic-b.md
    └── topic-c.md
```

### 2. Add YAML frontmatter to SKILL.md

```yaml
---
name: my-skill
description: 'What this skill does and when to trigger it.
  List keywords and phrases that should activate it.'
---
```

### 3. Install and go

```bash
# Drop it in the skills directory
cp -r my-skill ~/.claude/skills/my-skill

# Maestro discovers it automatically on the next task.
# No registration step needed.
```

Maestro reads the `name`, `description`, and `references/` directory at runtime and routes to your skill whenever the task matches.

### Adding semantic signatures (optional, improves RAG routing)

For better RAG matching on ambiguous tasks, add a `semantic_signature` to `skill-registry.md`:

```yaml
semantic_signature:
  description: >
    Natural language description of what this skill covers.
  clusters:
    - semantic-cluster-1
    - semantic-cluster-2
  disambiguation: >
    When NOT to use this skill (prevents false matches).
```

And add an entry to `semantic-index.md` with example queries and anti-examples. See the existing entries for the format.

## Example workflows

| What you say | Skills routed | References loaded |
| --- | --- | --- |
| "Add a settings screen with theme selection" | swiftui-expert + swift-best-practices | state-management.md, modern-apis.md |
| "Review PR #42" | swift-code-reviewer + per-file specialists | review-workflow.md, relevant checklists |
| "Fix: Sending value of non-Sendable type..." | swift-concurrency | sendable.md, threading.md, actors.md |
| "Migrate tests to Swift Testing" | swift-testing-expert | migration-from-xctest.md, fundamentals.md |
| "Build a login screen" | swiftui-expert + swift-concurrency + swift-code-reviewer | state-management.md, async-await-basics.md, security-checklist.md |
| "Make my app handle background refresh" | swift-concurrency + swiftui-expert (via RAG) | async-await-basics.md, tasks.md, state-management.md |

## Built-in skill catalog

Ships pre-configured for 6 Swift skills. These are auto-discovered at runtime:

| Skill | What it covers | References | Priority |
| --- | --- | --- | --- |
| `swift-best-practices` | API design, naming, Swift 6 features | 4 files | 5 |
| `swift-concurrency` | async/await, actors, Sendable, threading | 12 files | 8 |
| `swift-testing` | Test doubles, fixtures, TDD methodology | 8 files | 7 |
| `swift-testing-expert` | @Test, #expect, traits, parameterized tests | 9 files | 9 |
| `swiftui-expert-skill` | State, views, performance, navigation | 11 files | 8 |
| `swift-code-reviewer` | Code review, security, architecture audit | 8 files | 7 |

**Total**: 52 reference files across 6 skills, automatically routed per task.

> These skills are examples. Maestro works with **any skill** you install — Swift, TypeScript, Python, Rust, or anything else.

## Any language, any stack

While it ships with Swift expertise, the architecture is language-agnostic:

```bash
# Install skills for any language and Maestro routes to them automatically

# TypeScript
git clone <ts-skill-repo> ~/.claude/skills/typescript-expert

# Python
git clone <py-skill-repo> ~/.claude/skills/python-fastapi

# Rust
git clone <rs-skill-repo> ~/.claude/skills/rust-concurrency

# No configuration needed. Maestro detects your tech stack from
# Package.swift, package.json, Cargo.toml, pyproject.toml, go.mod
# and routes to matching skills automatically.
```

Maestro detects your tech stack from project config files and only activates skills that match.

## Knowledge graph

Maestro builds project-specific intelligence over time in `.claude/knowledge/`:

```
.claude/knowledge/
├── context.yaml     → Auto-generated project scan (tech stack, deps, architecture)
├── patterns.md      → Discovered code patterns and idioms
├── decisions.md     → Architecture decision records (ADRs)
├── skill-gaps.md    → Missing skills with installation suggestions
└── learnings.md     → Insights from completed tasks
```

This knowledge persists across sessions. You can commit it to git so your entire team benefits from the accumulated intelligence.

## Architecture

```
maestro/
├── SKILL.md                 # Orchestrator brain — the full agent logic
├── skill-registry.md        # Skill catalog with domains, triggers, semantic signatures
├── routing-engine.md        # Task → skill decision trees and routing tables
├── rag-engine.md            # 5-phase RAG retrieval protocol
├── semantic-index.md        # Per-skill semantic signatures for RAG matching
├── project-scanner.md       # Project context detection procedures
└── knowledge-graph.md       # Continuous learning system specification
```

## Learn more

| Document | What it covers |
| --- | --- |
| [SKILL.md](SKILL.md) | Full orchestrator agent behavior, execution flow, all 5 phases + Phase 3b RAG |
| [skill-registry.md](skill-registry.md) | Complete skill catalog, registry format, domain mapping, semantic signatures |
| [routing-engine.md](routing-engine.md) | Decision trees, compound task routing, priority resolution |
| [rag-engine.md](rag-engine.md) | 5-phase RAG retrieval protocol, scoring rubric, confidence thresholds |
| [semantic-index.md](semantic-index.md) | Per-skill semantic signatures, example queries, anti-examples, capability matrices |
| [project-scanner.md](project-scanner.md) | Project scanning procedures, tech stack detection, multi-project support |
| [knowledge-graph.md](knowledge-graph.md) | Knowledge graph spec, update protocols, skill gap analysis |

## Philosophy

- **Zero configuration** — install and forget. No setup, no config files, no registration.
- **Invisible orchestration** — you never think about which skill to use.
- **Project-first** — your `CLAUDE.md` rules override everything else.
- **Additive knowledge** — skills combine, they don't compete.
- **Continuous learning** — gets smarter with every task.

## License

[MIT](https://opensource.org/licenses/MIT)
