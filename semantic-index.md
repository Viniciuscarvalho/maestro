# Semantic Index

Rich semantic signatures for each skill, enabling RAG-based retrieval when keyword matching fails. Each entry provides natural language descriptions, diverse example queries, anti-examples, semantic clusters, and a capability matrix.

---

## swift-best-practices

### Natural Language Description

Covers Swift language-level API design, naming conventions, and idiomatic patterns. This skill guides developers in writing clear, expressive Swift code that follows the Swift API Design Guidelines — clarity at the point of use, fluent naming, proper parameter labeling, and documentation. Also covers Swift 6 language features, `@available` annotations, platform availability checks, and deprecation strategies.

### Example Queries

1. "How should I name this function that fetches a user from the database?"
2. "What's the best way to design a public API for my networking layer?"
3. "Help me make this code more Swifty and idiomatic"
4. "I want to deprecate an old method without breaking existing callers"
5. "How do I add platform availability checks for iOS 17 features?"
6. "Review my naming conventions — are they following Swift guidelines?"
7. "What changed in Swift 6 that I need to know about?"
8. "Help me design a builder pattern that feels natural in Swift"
9. "Should this be a struct or a class for my data model?"
10. "How do I write good documentation comments for my public API?"
11. "What's the idiomatic way to handle optional chaining here?"
12. "I need to support both iOS 16 and iOS 17 with different implementations"
13. "Clean up this function signature — it's hard to read at the call site"
14. "How should I organize my Swift package targets and modules?"
15. "What are the new features in the latest Swift version I should adopt?"

### Anti-Examples (Should NOT Trigger)

- "Fix this concurrency warning about Sendable" → swift-concurrency
- "My SwiftUI view isn't updating when the data changes" → swiftui-expert-skill
- "Write unit tests for my UserService" → swift-testing-expert
- "Review this pull request" → swift-code-reviewer
- "How do I use async/await in my network call?" → swift-concurrency

### Semantic Clusters

1. **API Design** — function signatures, parameter labels, return types, overloads, generics, protocol-oriented design
2. **Naming Conventions** — clarity at point of use, grammatical phrasing, abbreviation rules, term of art
3. **Swift 6 Features** — language evolution, breaking changes, new syntax, typed throws, noncopyable types
4. **Platform Availability** — `@available`, deployment targets, conditional compilation, feature detection
5. **Code Organization** — modules, access control, file structure, SwiftPM package design

### Capability Matrix

| Capability | Rating (0-3) | Notes |
|---|---|---|
| API design guidance | 3 | Core strength — Swift API Design Guidelines |
| Naming review | 3 | Deep knowledge of Swift naming conventions |
| Swift 6 migration | 2 | Covers language features, not concurrency specifics |
| Code architecture | 2 | General patterns; defer to swift-code-reviewer for audits |
| Concurrency patterns | 1 | Basics only; defer to swift-concurrency |
| UI guidance | 0 | Not applicable — defer to swiftui-expert-skill |
| Testing guidance | 0 | Not applicable — defer to swift-testing |
| Security review | 0 | Not applicable — defer to swift-code-reviewer |

---

## swift-concurrency

### Natural Language Description

Deep expertise in Swift's structured concurrency system: async/await, actors, Sendable, Task groups, AsyncSequence, and the Swift 6 strict concurrency model. This skill helps developers write correct, race-free concurrent code, migrate from GCD/completion handlers to modern concurrency, understand actor isolation boundaries, and resolve concurrency compiler warnings. Also covers performance profiling of async code and Core Data integration with concurrency.

### Example Queries

1. "I'm getting a 'Sendable' warning — how do I fix it?"
2. "Help me migrate this completion handler code to async/await"
3. "What's the difference between an actor and a class with a lock?"
4. "How do I run multiple async operations in parallel and collect results?"
5. "My app is hitting a data race — how do I find and fix it?"
6. "Explain how @MainActor works and when I should use it"
7. "How do I cancel a running Task when the user navigates away?"
8. "I want to stream data from a WebSocket using AsyncSequence"
9. "What's the correct way to make my existing types Sendable?"
10. "Help me understand the difference between Task and TaskGroup"
11. "How do I call async code from a synchronous context safely?"
12. "My Swift 6 migration is showing hundreds of concurrency warnings"
13. "How do I protect shared mutable state without using DispatchQueue?"
14. "What happens to retain cycles when I capture self in a Task?"
15. "How do I use actors with Core Data managed objects?"

### Anti-Examples (Should NOT Trigger)

- "How should I name this async function?" → swift-best-practices (naming, not concurrency)
- "Build a loading spinner in SwiftUI" → swiftui-expert-skill (UI, not concurrency)
- "Write tests for my async service" → swift-testing-expert (testing async, not concurrency itself)
- "Review the architecture of my networking layer" → swift-code-reviewer
- "How do I make a SwiftUI list perform better?" → swiftui-expert-skill (performance is UI-level)

### Semantic Clusters

1. **Async/Await** — syntax, execution model, async let, continuation, bridging from callbacks
2. **Actors & Isolation** — actor types, @MainActor, nonisolated, global actors, isolation boundaries
3. **Sendable & Safety** — Sendable protocol, @unchecked Sendable, region-based isolation, compiler diagnostics
4. **Task Management** — Task lifecycle, cancellation, TaskGroup, detached tasks, priority
5. **Migration & Modernization** — GCD to async/await, Swift 5 to 6 concurrency, incremental adoption

### Capability Matrix

| Capability | Rating (0-3) | Notes |
|---|---|---|
| Async/await patterns | 3 | Core strength — complete async/await guidance |
| Actor isolation | 3 | Full actor model, @MainActor, custom global actors |
| Sendable compliance | 3 | All Sendable patterns and migration strategies |
| Task lifecycle | 3 | Creation, cancellation, groups, detached tasks |
| Swift 6 migration | 3 | Concurrency-specific migration (not general Swift 6) |
| AsyncSequence/Stream | 2 | Patterns and common pitfalls |
| Core Data integration | 2 | NSManagedObject + concurrency patterns |
| Performance profiling | 2 | Instruments, suspension points, thread pool |
| General Swift patterns | 1 | Basics only; defer to swift-best-practices |
| UI integration | 1 | @MainActor only; defer to swiftui-expert-skill |

---

## swift-testing

### Natural Language Description

Covers the foundational concepts of testing in Swift projects: test doubles (mocks, stubs, spies, fakes), test fixtures, test data management, integration testing strategies, and snapshot testing. This skill provides the testing methodology and patterns — how to structure tests, manage dependencies in tests, and apply principles like Arrange-Act-Assert and F.I.R.S.T. It bridges both XCTest and the Swift Testing framework.

### Example Queries

1. "How should I mock this network service dependency in my tests?"
2. "What's the difference between a mock, stub, spy, and fake?"
3. "Help me create reusable test fixtures for my User model"
4. "I need a testing strategy for my app's data layer"
5. "How do I write integration tests that test multiple modules together?"
6. "What's the best way to manage test data across test cases?"
7. "Help me set up snapshot testing for my UI components"
8. "How do I test code that depends on the current date or time?"
9. "Should I use protocol-based mocking or a mocking library?"
10. "How do I structure my test suite for a large module?"
11. "What patterns should I use for testing error handling paths?"
12. "Help me decide between hand-rolled mocks and generated ones"
13. "How do I test a function that writes to the file system?"
14. "What's Arrange-Act-Assert and how do I apply it consistently?"
15. "How do I migrate my test doubles from XCTest to Swift Testing?"

### Anti-Examples (Should NOT Trigger)

- "How do I use @Test and #expect?" → swift-testing-expert (framework-specific syntax)
- "Help me parameterize this test with multiple inputs" → swift-testing-expert
- "How do I run tests in parallel with .serialized?" → swift-testing-expert
- "Fix this flaky test that passes sometimes" → swift-testing-expert (test reliability)
- "Review this code for quality issues" → swift-code-reviewer

### Semantic Clusters

1. **Test Doubles** — mocks, stubs, spies, fakes, dummy objects, dependency injection for testing
2. **Test Fixtures** — test data builders, factory patterns, shared setup, database seeding
3. **Testing Strategy** — unit vs integration vs snapshot, testing pyramid, what to test
4. **Test Organization** — suite structure, naming, grouping, tags, shared state management
5. **XCTest Bridge** — XCTest patterns, migration path, coexistence with Swift Testing

### Capability Matrix

| Capability | Rating (0-3) | Notes |
|---|---|---|
| Test double patterns | 3 | Core strength — mock/stub/spy/fake taxonomy |
| Test fixture design | 3 | Builder patterns, factories, shared data |
| Integration testing | 3 | Module interaction, database testing |
| Snapshot testing | 2 | UI regression testing patterns |
| Test organization | 2 | Suite structure, naming conventions |
| XCTest patterns | 2 | Traditional XCTest knowledge |
| Swift Testing syntax | 1 | Basics only; defer to swift-testing-expert |
| Parameterized testing | 1 | Concept only; defer to swift-testing-expert |
| Async testing | 1 | Patterns only; defer to swift-testing-expert for details |
| Code review | 0 | Not applicable — defer to swift-code-reviewer |

---

## swift-testing-expert

### Natural Language Description

Expert-level knowledge of the Swift Testing framework (`import Testing`): the `@Test` macro, `#expect` and `#require` assertions, traits and tags, parameterized testing with `@Test(arguments:)`, parallel execution control, and migration from XCTest. This skill handles the framework-specific syntax, advanced features like custom traits, Xcode test navigator integration, and best practices for deterministic, fast-running test suites.

### Example Queries

1. "How do I write a parameterized test that runs with multiple input combinations?"
2. "What's the difference between #expect and #require in Swift Testing?"
3. "Help me migrate my XCTest test case to the new Swift Testing framework"
4. "How do I tag tests so I can run subsets from the command line?"
5. "My tests are flaky when running in parallel — how do I fix that?"
6. "How do I wait for an async event in a Swift Testing test?"
7. "Show me how to use custom traits to add metadata to my tests"
8. "How do I force certain tests to run serially instead of in parallel?"
9. "What's the best way to organize a large test suite with @Suite?"
10. "How do I test that a function throws a specific error type?"
11. "Help me convert my setUp/tearDown methods to Swift Testing patterns"
12. "How do I use confirmation() to test async callbacks?"
13. "What are the best practices for keeping Swift Testing tests fast?"
14. "How do I see test results in Xcode's test navigator with Swift Testing?"
15. "Can I mix XCTest and Swift Testing in the same target?"

### Anti-Examples (Should NOT Trigger)

- "How do I create a mock for my service?" → swift-testing (test doubles, not framework syntax)
- "What's the best testing strategy for my app?" → swift-testing (strategy, not framework)
- "Help me set up snapshot testing" → swift-testing (snapshot, not Swift Testing framework)
- "Build a settings screen" → swiftui-expert-skill (creation, not testing)
- "Is this code concurrent-safe?" → swift-concurrency

### Semantic Clusters

1. **Framework Syntax** — @Test, #expect, #require, @Suite, assertions, expected failures
2. **Parameterized Testing** — @Test(arguments:), combinations, custom argument sources
3. **Traits & Tags** — .tags(), custom traits, .enabled(if:), .bug(), .disabled()
4. **Parallel Execution** — default parallelism, .serialized, isolation patterns, shared state
5. **Migration** — XCTest to Swift Testing, coexistence, incremental adoption

### Capability Matrix

| Capability | Rating (0-3) | Notes |
|---|---|---|
| @Test and assertions | 3 | Core strength — full framework syntax |
| Parameterized testing | 3 | @Test(arguments:), combinations, custom sources |
| Traits and tags | 3 | Built-in and custom traits, filtering |
| Parallel execution | 3 | Serialization, isolation, determinism |
| XCTest migration | 3 | Complete migration guide with coexistence |
| Async testing patterns | 2 | confirmation(), async expectations |
| Xcode integration | 2 | Test navigator, diagnostics, test plans |
| Test doubles | 1 | Conceptual only; defer to swift-testing |
| Integration testing | 1 | Framework support; defer to swift-testing for patterns |
| General Swift patterns | 0 | Not applicable — defer to swift-best-practices |

---

## swiftui-expert-skill

### Natural Language Description

Comprehensive SwiftUI expertise covering view composition, state management with `@Observable` and property wrappers, layout systems, navigation (NavigationStack, sheets, deep links), performance optimization (view update reduction, lazy loading, list identity), accessibility, and platform-specific patterns. Covers the full lifecycle from iOS 14 through iOS 26 Liquid Glass. This skill is the go-to for anything related to building user interfaces in SwiftUI.

### Example Queries

1. "Help me build a profile screen with an editable form and photo picker"
2. "My SwiftUI list is laggy — how do I improve scroll performance?"
3. "What's the correct way to manage state in a complex multi-screen flow?"
4. "How do I implement programmatic navigation with NavigationStack?"
5. "I want to replace my @StateObject with @Observable — walk me through it"
6. "Help me create a reusable card component with customizable content"
7. "How do I show a sheet that passes data back to the parent view?"
8. "My view is re-rendering too often — how do I optimize update cycles?"
9. "What's the best way to load and display remote images efficiently?"
10. "Help me implement pull-to-refresh with an async data source"
11. "How do I support Dynamic Type and accessibility in my custom views?"
12. "I want to add the new iOS 26 Liquid Glass effect to my tab bar"
13. "How should I structure a complex view — when to extract subviews?"
14. "Help me implement a custom scroll behavior with ScrollView"
15. "What's the modern replacement for the deprecated onChange(of:perform:)?"

### Anti-Examples (Should NOT Trigger)

- "Fix this Sendable warning in my view model" → swift-concurrency (compiler warning, not UI)
- "Write tests for my SwiftUI view" → swift-testing-expert (testing, not building UI)
- "Review this PR that changes the settings screen" → swift-code-reviewer (review, not building)
- "How should I name the properties in my view?" → swift-best-practices (naming conventions)
- "How do I call an API endpoint from my view model?" → swift-concurrency (networking, not UI)

### Semantic Clusters

1. **State Management** — @State, @Binding, @Observable, @Environment, data flow patterns
2. **View Composition** — extraction, reusable components, ViewBuilder, generics, preferences
3. **Navigation** — NavigationStack, NavigationPath, sheets, alerts, deep linking, coordinators
4. **Performance** — view identity, equatable views, lazy containers, profiling with Instruments
5. **Platform & Modernization** — deprecated API replacements, iOS version support, Liquid Glass

### Capability Matrix

| Capability | Rating (0-3) | Notes |
|---|---|---|
| State management | 3 | Core strength — all property wrappers and @Observable |
| View composition | 3 | Extraction patterns, generic views, ViewBuilder |
| Navigation patterns | 3 | NavigationStack, sheets, deep links |
| Performance optimization | 3 | View updates, identity, lazy loading |
| Layout system | 3 | GeometryReader, custom layouts, alignment |
| Accessibility | 2 | VoiceOver, Dynamic Type, semantic views |
| Animations | 2 | Implicit/explicit animations, transitions |
| Platform-specific | 2 | iOS 26 Liquid Glass, visionOS, watchOS |
| Concurrency integration | 1 | @MainActor basics; defer to swift-concurrency |
| Testing views | 0 | Not applicable — defer to swift-testing |

---

## swift-code-reviewer

### Natural Language Description

Structured code review methodology for Swift projects: step-by-step review workflows, quality checklists for Swift code and SwiftUI views, performance audits, security reviews, and architecture pattern validation. This skill operates in review/audit mode — it evaluates existing code against best practices, project conventions (CLAUDE.md), and known pitfalls. It loads the appropriate checklist per file type and produces actionable feedback with severity ratings.

### Example Queries

1. "Review this pull request for quality and correctness"
2. "Audit my codebase for security vulnerabilities"
3. "Check if this code follows our project's CLAUDE.md conventions"
4. "Look at this diff and tell me what could be improved"
5. "Review my error handling — is it robust enough?"
6. "Do a performance review of my SwiftUI view hierarchy"
7. "Check this code for common Swift anti-patterns"
8. "Audit the architecture of my networking layer"
9. "Review my dependency injection setup for testability"
10. "Is this code safe from force-unwrap crashes?"
11. "Give me feedback on the overall code quality of this module"
12. "Check if my concurrency code is free of data races"
13. "Review this against the OWASP mobile security checklist"
14. "Are there any retain cycles or memory leaks in this code?"
15. "Evaluate whether this module follows clean architecture principles"

### Anti-Examples (Should NOT Trigger)

- "Build a new settings screen" → swiftui-expert-skill (creation, not review)
- "Help me write async/await code" → swift-concurrency (creation, not review)
- "Write tests for UserService" → swift-testing-expert (creation, not review)
- "How should I name this function?" → swift-best-practices (guidance, not review)
- "Explain how actors work" → swift-concurrency (explanation, not review)

### Semantic Clusters

1. **Review Workflow** — step-by-step process, PR review, diff analysis, comment templates
2. **Quality Checklist** — Swift idioms, optionals, error handling, concurrency correctness
3. **Security Audit** — input validation, keychain usage, credential handling, OWASP
4. **Performance Review** — view updates, memory management, retain cycles, profiling
5. **Architecture Validation** — MVVM, DI, modularity, testability, SOLID principles

### Capability Matrix

| Capability | Rating (0-3) | Notes |
|---|---|---|
| PR/code review workflow | 3 | Core strength — structured review process |
| Swift quality checklist | 3 | Comprehensive idiom and pattern checking |
| Security auditing | 3 | OWASP, keychain, input validation, credentials |
| Architecture review | 3 | MVVM, DI, clean architecture, SOLID |
| SwiftUI review | 2 | View-specific checklist; defers to swiftui-expert for depth |
| Performance review | 2 | Memory, retain cycles, view updates |
| Concurrency review | 2 | Race condition detection; defers to swift-concurrency |
| Test quality review | 2 | Coverage, determinism; defers to swift-testing for patterns |
| Code creation | 0 | Review-only — does not create new code |
| API design guidance | 0 | Not applicable — defer to swift-best-practices |
