# Maestro - The skill orchestrator that makes Claude Code smarter.

<p align="center">
  <img src="assets/banner.svg" alt="Maestro Banner" width="100%"/>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-ffd60a?style=flat-square" alt="License: MIT"/></a>
  <a href="https://claude.ai/"><img src="https://img.shields.io/badge/Claude_Code-compatible-6c5ce7?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjEwIi8+PC9zdmc+&logoColor=white&style=flat-square" alt="Claude Code"/></a>
  <a href="#language-agnostic"><img src="https://img.shields.io/badge/Language-Agnostic-2ea44f?style=flat-square" alt="Language Agnostic"/></a>
  <a href="#install"><img src="https://img.shields.io/badge/Setup-2_minutes-0078d7?style=flat-square" alt="Quick Setup"/></a>
</p>

Maestro is an autonomous agent that sits between you and your Claude Code skills. It scans your project, indexes every installed skill, and automatically routes the right expertise to every task — so you focus on building, not on tooling.

> You have 6+ specialized skills installed. Manually knowing which to invoke for each task is cognitive overhead you shouldn't carry. Maestro eliminates that friction entirely.

## What you get

- **Zero-config orchestration** — automatically detects your project, tech stack, and installed skills on every task.
- **Intelligent routing** — classifies tasks by domain, action, and scope, then loads only the reference files that matter.
- **Multi-skill composition** — real tasks need 2-3 skills at once; Maestro combines them seamlessly.
- **Project-first intelligence** — reads your `CLAUDE.md`, respects your conventions, and never overrides your rules.
- **Continuous learning** — builds a knowledge graph of your project's patterns, decisions, and idioms over time.
- **Skill gap detection** — identifies missing expertise and suggests skills to fill the gap.
- **Language agnostic** — ships with deep Swift knowledge but works with any tech stack.

## Install

### Claude Code (recommended)

```bash
# Install as a user skill (available in all projects)
git clone https://github.com/Viniciuscarvalho/maestro.git ~/.claude/skills/maestro

# Or install as a project skill (this project only)
git clone https://github.com/Viniciuscarvalho/maestro.git .claude/skills/maestro
```

### Claude.ai Projects

Upload these files to your Project's knowledge:

1. `SKILL.md` (required — the orchestrator brain)
2. `skill-registry.md`
3. `routing-engine.md`
4. `project-scanner.md`
5. `knowledge-graph.md`

## Quick start

```
You: "Build a user profile screen with async data loading"

Maestro (silently):
  ├── Detects: SwiftUI (ui) + async/await (concurrency) + data flow
  ├── Loads: swiftui-expert-skill → state-management.md, modern-apis.md
  ├── Loads: swift-concurrency → async-await-basics.md
  ├── Reads: CLAUDE.md → MVVM pattern, @Observable, AppColors
  └── Applies: All knowledge combined

You get: Production-quality SwiftUI view with correct state management,
         proper async patterns, following your project's conventions.
```

No `/slash-command`. No manual skill selection. Just describe what you want.

## How it works

Every task flows through a 5-phase pipeline:

| Phase | What happens |
| --- | --- |
| **Scan** | Reads `CLAUDE.md`, `Package.swift` / `package.json` / `Cargo.toml`, detects tech stack, indexes installed skills |
| **Classify** | Determines domain (`ui`, `concurrency`, `testing`...), action (`create`, `fix`, `review`...), and scope (`file`, `module`, `system`) |
| **Route** | Matches task to best skills, resolves conflicts (project rules > skill defaults), loads only needed references |
| **Execute** | Applies all matched skill knowledge silently — you never see "loading skill X", just better output |
| **Learn** | Updates the project knowledge graph with discovered patterns, decisions, and skill gaps |

## How routing works

Maestro uses a two-path routing architecture to match tasks to skills:

```
┌──────────────────────────────────────────────────────────────┐
│  TASK RECEIVED                                                │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Fast Path: Keyword + Decision Tree                      │  │
│  │  ├── Match trigger words against skill registry          │  │
│  │  ├── Walk decision tree (review? create? fix? migrate?)  │  │
│  │  └── Clear match? → Load references → Execute            │  │
│  └──────────────────────┬──────────────────────────────────┘  │
│                         │ No clear match?                      │
│  ┌──────────────────────▼──────────────────────────────────┐  │
│  │  Semantic Path: RAG Engine                               │  │
│  │  ├── RAG-1: Decompose query (intent, domain, implicit)   │  │
│  │  ├── RAG-2: Score skills by semantic similarity          │  │
│  │  ├── RAG-3: Lazy-load only relevant references           │  │
│  │  ├── RAG-4: Merge multi-skill context, deduplicate       │  │
│  │  └── RAG-5: Confidence check (>70 route, <50 flag gap)   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  → Phase 4: Execute with full skill context                   │
└──────────────────────────────────────────────────────────────┘
```

**Fast path** handles the majority of tasks — when you mention `@Test`, `SwiftUI`, `async/await`, or say "review this PR", keyword matching instantly routes to the right skill. This path is zero-overhead and deterministic.

**Semantic path** activates when keywords fail: natural language queries, conceptual questions, or ambiguous multi-domain tasks. The RAG engine decomposes your query, scores each skill using a weighted similarity rubric, and loads only the references that matter.

### Example: RAG improving routing

```
You: "I want to make sure my data model updates are reflected
      everywhere in the app without causing any threading issues"

Without RAG (keyword only):
  - "data model" → maybe swift-best-practices?
  - "threading" → maybe swift-concurrency?
  - "reflected everywhere" → maybe swiftui-expert-skill?
  - Result: AMBIGUOUS — three skills match equally, no clear winner

With RAG:
  - RAG-1: intent=create, domain=state-management+concurrency, implicit=@Observable
  - RAG-2: swiftui-expert-skill (80), swift-concurrency (65), swift-best-practices (25)
  - RAG-3: Loads state-management.md + actors.md (3 files, not 52)
  - RAG-5: Score 80 → CONFIDENT
  - Result: Primary swiftui-expert-skill, secondary swift-concurrency
```

The RAG engine's scoring rubric uses anti-examples to actively reject false matches (e.g., "fix this Sendable warning" will not trigger swiftui-expert-skill even though it mentions state), producing more assertive routing than keyword matching alone.

See [rag-engine.md](rag-engine.md) and [semantic-index.md](semantic-index.md) for full details.

## Example workflows

| Task | Skills routed | What loads |
| --- | --- | --- |
| `"Add a settings screen with theme selection"` | swiftui-expert, swift-best-practices | state-management.md, modern-apis.md, CLAUDE.md (design system) |
| `"Review PR #42"` | swift-code-reviewer + per-file specialists | review-workflow.md, checklists based on diff content |
| `"Fix: Sending value of non-Sendable type..."` | swift-concurrency | sendable.md, threading.md, actors.md |
| `"Migrate UserService tests to Swift Testing"` | swift-testing-expert | migration-from-xctest.md, fundamentals.md |
| `"Build a login screen"` | swiftui-expert, swift-concurrency, swift-code-reviewer | state-management.md, async-await-basics.md, security-checklist.md |

## Built-in skill catalog

Ships pre-configured for these Swift skills (auto-discovered at runtime):

| Skill | Domains | References | Priority |
| --- | --- | --- | --- |
| `swift-best-practices` | API design, naming, Swift 6 | 4 files | 5 |
| `swift-concurrency` | async/await, actors, Sendable, threading | 12 files | 8 |
| `swift-testing` | Test doubles, fixtures, TDD | 8 files | 7 |
| `swift-testing-expert` | @Test, traits, parameterized tests | 9 files | 9 |
| `swiftui-expert-skill` | State, views, performance, navigation | 11 files | 8 |
| `swift-code-reviewer` | Review, security, architecture | 8 files | 7 |

**Total**: 52 reference files, automatically routed.

## Language agnostic

While it ships with Swift expertise, the architecture supports any language:

- **Tech stack detection** — Swift, TypeScript, Python, Rust, Go, and more
- **Auto-discovery** — install a skill for any language and Maestro routes to it automatically
- **Universal patterns** — code review, testing principles, architecture, and security apply across stacks
- **CLAUDE.md reading** — works with any project type

```
# To extend to TypeScript, just install TS skills:
git clone <ts-skill-repo> ~/.claude/skills/typescript-expert

# Maestro discovers and routes to them automatically.
# No configuration needed.
```

## Knowledge graph

Maestro builds project intelligence over time in `.claude/knowledge/`:

```
.claude/knowledge/
├── context.yaml     → Auto-generated project scan results
├── patterns.md      → Discovered code patterns and idioms
├── decisions.md     → Architecture decision records (ADRs)
├── skill-gaps.md    → Missing skills with suggestions
└── learnings.md     → Task insights for future reference
```

This knowledge persists across sessions and can be committed to git for team sharing.

## Architecture

```
maestro/
├── SKILL.md                 # Orchestrator brain — the full agent logic
├── skill-registry.md        # Complete skill catalog with domains and triggers
├── routing-engine.md        # Task → skill decision trees and routing tables
├── semantic-index.md        # Per-skill semantic signatures for RAG matching
├── rag-engine.md            # 5-phase RAG retrieval protocol
├── project-scanner.md       # Project context detection procedures
└── knowledge-graph.md       # Continuous learning system specification
```

## Learn more

| Document | What it covers |
| --- | --- |
| [SKILL.md](SKILL.md) | Full orchestrator agent behavior, execution flow, all 5 phases |
| [skill-registry.md](skill-registry.md) | Complete skill catalog, registry format, domain mapping |
| [routing-engine.md](routing-engine.md) | Decision trees, compound task routing, priority resolution |
| [semantic-index.md](semantic-index.md) | Per-skill semantic signatures, example queries, anti-examples, capability matrices |
| [rag-engine.md](rag-engine.md) | 5-phase RAG retrieval protocol, scoring rubric, confidence thresholds |
| [project-scanner.md](project-scanner.md) | Project scanning procedures, tech stack detection, multi-project support |
| [knowledge-graph.md](knowledge-graph.md) | Knowledge graph spec, update protocols, skill gap analysis |

## Philosophy

- **Zero configuration** — works out of the box with any installed skills
- **Invisible orchestration** — you never think about which skill to use
- **Project-first** — your `CLAUDE.md` rules override everything else
- **Additive knowledge** — skills combine, they don't compete
- **Continuous learning** — gets smarter with every task

## Requirements

- Any Claude interface (Claude Code, Claude.ai, API)
- Skills installed in discoverable paths (`~/.claude/skills/` or `.claude/skills/`)
- Project with `CLAUDE.md` (optional but recommended)

## License

[MIT](https://opensource.org/licenses/MIT)
