# Skill Registry

Complete catalog of available skills with domains, triggers, reference files, and compatibility information. The orchestrator uses this registry to route tasks to the right skills automatically.

## Registry Format

Each skill entry follows this schema:

```yaml
- name: <skill-name>
  path: <filesystem-path>
  description: <what it does>
  domains: [<domain-tags>]
  actions: [<action-tags>]
  languages: [<language-tags>]
  frameworks: [<framework-tags>]
  references: [<available-reference-files>]
  triggers: [<phrases-that-activate-this-skill>]
  depends_on: [<other-skills-it-references>]
  priority: <1-10, higher = more specialized>
```

---

## Built-in Swift Skills

### swift-best-practices
```yaml
name: swift-best-practices
domains: [api-design, naming, concurrency-basics, swift6, availability]
actions: [create, review, explain, migrate]
languages: [swift]
frameworks: [ios, macos, swiftpm]
references:
  - api-design.md          # API naming, parameters, documentation
  - concurrency.md         # Async/await patterns, actor basics
  - swift6-features.md     # Swift 6 breaking changes, new features
  - availability-patterns.md  # @available, deprecation, platform checks
triggers:
  - "Swift API design"
  - "naming convention"
  - "Swift 6 migration"
  - "@available"
  - "deprecation"
  - "clarity at point of use"
depends_on: []
priority: 5
semantic_signature:
  description: >
    Guides idiomatic Swift API design, naming conventions, and language-level
    best practices. Covers Swift API Design Guidelines (clarity at point of use),
    Swift 6 language features, and platform availability annotations.
  clusters:
    - api-design-and-naming
    - swift-6-language-features
    - platform-availability
    - code-organization
    - protocol-oriented-design
  disambiguation: >
    Do NOT use for concurrency-specific patterns (use swift-concurrency),
    SwiftUI view building (use swiftui-expert-skill), or code review
    workflows (use swift-code-reviewer).
```

### swift-concurrency
```yaml
name: swift-concurrency
domains: [concurrency, async, actors, sendable, threading, tasks, isolation]
actions: [create, review, fix, migrate, explain, debug]
languages: [swift]
frameworks: [ios, macos, swift6]
references:
  - async-await-basics.md    # Syntax, execution order, async let
  - tasks.md                 # Task lifecycle, cancellation, groups
  - threading.md             # Thread/task relationship, isolation
  - memory-management.md     # Retain cycles in tasks
  - actors.md                # Actor isolation, @MainActor, Mutex
  - sendable.md              # Sendable conformance, region isolation
  - linting.md               # Concurrency lint rules
  - async-sequences.md       # AsyncSequence, AsyncStream
  - core-data.md             # NSManagedObject sendability
  - performance.md           # Profiling, suspension points
  - testing.md               # XCTest async patterns
  - migration.md             # Swift 6 migration strategy
triggers:
  - "async/await"
  - "actor"
  - "Sendable"
  - "data race"
  - "@MainActor"
  - "Task {"
  - "concurrency warning"
  - "isolation"
  - "DispatchQueue"
  - "Swift 6 strict concurrency"
  - "nonisolated"
depends_on: []
priority: 8
semantic_signature:
  description: >
    Deep expertise in Swift's structured concurrency: async/await, actors,
    Sendable protocol, Task groups, AsyncSequence, and Swift 6 strict
    concurrency migration. Solves data races, isolation boundary issues,
    and GCD-to-modern-concurrency migration.
  clusters:
    - async-await-and-continuations
    - actor-isolation-and-mainactor
    - sendable-and-data-safety
    - task-lifecycle-and-cancellation
    - swift-6-concurrency-migration
  disambiguation: >
    Do NOT use for SwiftUI view building or state management (use
    swiftui-expert-skill), Swift naming conventions (use swift-best-practices),
    or writing test assertions (use swift-testing-expert).
```

### swift-testing
```yaml
name: swift-testing
domains: [testing, unit-tests, mocks, fixtures, tdd]
actions: [create, review, fix, migrate, explain]
languages: [swift]
frameworks: [swift-testing-framework, xctest]
references:
  - test-organization.md       # Suites, tags, traits
  - parameterized-tests.md     # Multiple inputs
  - async-testing.md           # Async patterns, confirmation
  - migration-xctest.md        # XCTest migration
  - test-doubles.md            # Mock, stub, spy taxonomy
  - fixtures.md                # Test data patterns
  - integration-testing.md     # Module interaction testing
  - snapshot-testing.md        # UI regression testing
triggers:
  - "@Test"
  - "#expect"
  - "#require"
  - "@Suite"
  - "test double"
  - "mock"
  - "stub"
  - "fixture"
  - "unit test"
  - "XCTest migration"
  - "Arrange-Act-Assert"
  - "F.I.R.S.T."
depends_on: []
priority: 7
semantic_signature:
  description: >
    Covers testing methodology and patterns: test doubles (mocks, stubs, spies,
    fakes), fixture management, integration testing strategies, and snapshot
    testing. Provides the "how to structure tests" knowledge independent of
    any specific testing framework.
  clusters:
    - test-double-patterns
    - fixture-and-test-data
    - integration-testing-strategy
    - snapshot-and-ui-regression
    - test-organization-and-naming
  disambiguation: >
    Do NOT use for Swift Testing framework syntax like @Test or #expect (use
    swift-testing-expert), for code review workflows (use swift-code-reviewer),
    or for building production features (use domain-specific skills).
```

### swift-testing-expert
```yaml
name: swift-testing-expert
domains: [testing, test-organization, parameterized, traits, parallel]
actions: [create, review, fix, migrate, explain]
languages: [swift]
frameworks: [swift-testing-framework]
references:
  - _index.md
  - fundamentals.md                    # Building blocks, suites
  - expectations.md                    # #expect, #require
  - traits-and-tags.md                 # Traits, tags, filtering
  - parameterized-testing.md           # @Test(arguments:)
  - parallelization-and-isolation.md   # Parallel execution, .serialized
  - performance-and-best-practices.md  # Speed, determinism
  - async-testing-and-waiting.md       # Async waiting patterns
  - migration-from-xctest.md           # XCTest coexistence
  - xcode-workflows.md                # Navigator, diagnostics
triggers:
  - "Swift Testing"
  - "@Test"
  - "#expect"
  - "parameterized test"
  - "test trait"
  - "test tag"
  - ".serialized"
  - "flaky test"
  - "test plan"
depends_on: [swift-testing]
priority: 9
semantic_signature:
  description: >
    Expert-level knowledge of the Swift Testing framework: @Test macro,
    #expect/#require assertions, traits and tags, parameterized testing
    with @Test(arguments:), parallel execution control, and XCTest
    migration. Handles framework-specific syntax and advanced features.
  clusters:
    - test-macro-and-assertions
    - parameterized-test-arguments
    - traits-tags-and-filtering
    - parallel-execution-control
    - xctest-migration-path
  disambiguation: >
    Do NOT use for general testing methodology like mock/stub patterns (use
    swift-testing), for reviewing existing test quality (use swift-code-reviewer),
    or for testing concurrency code specifically (use swift-concurrency).
```

### swiftui-expert-skill
```yaml
name: swiftui-expert-skill
domains: [ui, swiftui, state-management, view-composition, performance, accessibility, navigation]
actions: [create, review, fix, refactor, explain, migrate]
languages: [swift]
frameworks: [swiftui, ios, macos, watchos, tvos, visionos]
references:
  - state-management.md             # Property wrappers, @Observable
  - view-structure.md               # View composition, extraction
  - performance-patterns.md         # Update optimization
  - list-patterns.md                # ForEach, identity, stability
  - layout-best-practices.md        # Layout patterns, testability
  - modern-apis.md                  # Deprecated → modern replacements
  - sheet-navigation-patterns.md    # Sheets, navigation
  - scroll-patterns.md              # ScrollView, programmatic scrolling
  - text-formatting.md              # Modern text formatting
  - image-optimization.md           # AsyncImage, downsampling
  - liquid-glass.md                 # iOS 26+ Liquid Glass
triggers:
  - "SwiftUI"
  - "@State"
  - "@Binding"
  - "@Observable"
  - "@Environment"
  - "NavigationStack"
  - "view body"
  - "ForEach"
  - "property wrapper"
  - ".sheet"
  - "SwiftUI performance"
  - "view update"
  - "Liquid Glass"
depends_on: []
priority: 8
semantic_signature:
  description: >
    Comprehensive SwiftUI expertise: view composition, state management
    (@Observable, property wrappers), navigation (NavigationStack, sheets),
    layout systems, performance optimization, and platform-specific patterns
    from iOS 14 through iOS 26 Liquid Glass.
  clusters:
    - state-management-and-data-flow
    - view-composition-and-extraction
    - navigation-and-presentation
    - performance-and-identity
    - platform-apis-and-modernization
  disambiguation: >
    Do NOT use for concurrency compiler warnings (use swift-concurrency),
    writing test assertions (use swift-testing-expert), code review
    workflows (use swift-code-reviewer), or Swift naming conventions
    (use swift-best-practices).
```

### swift-code-reviewer
```yaml
name: swift-code-reviewer
domains: [code-review, quality, security, architecture, performance, testing]
actions: [review, audit]
languages: [swift]
frameworks: [swiftui, ios, macos]
references:
  - review-workflow.md          # Step-by-step review process
  - swift-quality-checklist.md  # Concurrency, errors, optionals
  - swiftui-review-checklist.md # State, property wrappers, APIs
  - performance-review.md       # View updates, ForEach, layout
  - security-checklist.md       # Input validation, sensitive data
  - architecture-patterns.md    # MVVM, DI, testing strategies
  - custom-guidelines.md        # .claude/CLAUDE.md parsing
  - feedback-templates.md       # Review comment templates
triggers:
  - "review"
  - "PR"
  - "pull request"
  - "MR"
  - "merge request"
  - "code review"
  - "code quality"
  - "audit"
  - "check this code"
depends_on: [swift-best-practices, swiftui-expert-skill]
priority: 7
semantic_signature:
  description: >
    Structured code review methodology for Swift projects: PR review
    workflows, quality checklists, security audits, performance reviews,
    and architecture validation. Operates in review/audit mode — evaluates
    existing code, does not create new code.
  clusters:
    - pr-review-workflow
    - swift-quality-and-idioms
    - security-and-vulnerability-audit
    - performance-and-memory-review
    - architecture-and-solid-validation
  disambiguation: >
    Do NOT use for creating new code or features (use domain-specific skills),
    for writing tests (use swift-testing-expert), or for explaining Swift
    concepts (use swift-best-practices or swift-concurrency).
```

---

## Domain → Skill Mapping

Quick lookup table for the routing engine:

| Domain | Primary Skill | Secondary Skills |
|--------|--------------|------------------|
| `ui` | swiftui-expert-skill | swift-best-practices |
| `concurrency` | swift-concurrency | swift-best-practices |
| `testing` | swift-testing-expert | swift-testing |
| `code-review` | swift-code-reviewer | all Swift skills |
| `api-design` | swift-best-practices | — |
| `performance` | swiftui-expert-skill | swift-concurrency |
| `security` | swift-code-reviewer | — |
| `architecture` | swift-best-practices | swift-code-reviewer |
| `migration` | swift-concurrency | swift-best-practices |
| `accessibility` | swiftui-expert-skill | — |
| `data` | swift-concurrency (core-data) | — |

---

## Adding New Skills to the Registry

When a new skill is discovered (via filesystem scan or user installation):

1. Read the SKILL.md frontmatter for `name` and `description`
2. Parse the description for trigger patterns
3. List the `references/` directory for available deep knowledge
4. Infer domains from the description and reference file names
5. Add to the registry with appropriate priority

### Auto-Detection Heuristics

```
Reference file name → Domain inference:
  *concurrency* → concurrency
  *state* → state-management, ui
  *performance* → performance
  *security* → security
  *test* → testing
  *migration* → migration
  *api* → api-design
  *navigation* → navigation
  *network* → networking
  *data*, *core-data* → data
  *accessibility*, *a11y* → accessibility
```

---

## Extensibility: Non-Swift Skill Slots

The registry supports any language. Placeholder entries for future skills:

### TypeScript/React
```yaml
# Install skills for these domains:
- typescript-best-practices     # TS patterns, type safety
- react-expert                  # Hooks, state, composition
- nextjs-patterns               # SSR, RSC, routing
- frontend-testing              # Vitest, React Testing Library
```

### Python
```yaml
- python-best-practices         # Type hints, patterns
- fastapi-expert                # API design, async
- django-patterns               # ORM, views, middleware
- python-testing                # pytest, fixtures, mocks
```

### Rust
```yaml
- rust-best-practices           # Ownership, lifetimes, traits
- rust-async                    # Tokio, futures
- rust-testing                  # cargo test patterns
```

When these skills are installed, the routing engine automatically incorporates them based on detected tech stack.
