# Routing Engine

Complete decision trees and routing tables for mapping developer tasks to the right skills. The orchestrator consults this when the SKILL.md's inline routing table isn't sufficient.

---

## Master Decision Tree

```
START: Analyze user message
│
├─ Contains file path / code snippet?
│   ├─ YES → Detect language from extension/syntax
│   │         Route to language-specific skills
│   └─ NO → Continue to intent analysis
│
├─ Is this a review request?
│   ├─ YES → Route: code-review domain
│   │   ├─ PR/MR mentioned? → Load review-workflow.md
│   │   ├─ "uncommitted changes"? → Use git diff
│   │   ├─ Specific file? → Read file + run checklists
│   │   └─ "against standards"? → Load custom-guidelines.md
│   └─ NO → Continue
│
├─ Is this a creation task?
│   ├─ YES → Identify what's being created
│   │   ├─ UI component? → swiftui-expert-skill
│   │   │   └─ Also load: state-management, modern-apis, view-structure
│   │   ├─ Data model? → swift-best-practices
│   │   │   └─ Also load: api-design
│   │   ├─ Network layer? → swift-concurrency + swift-best-practices
│   │   │   └─ Also load: async-await-basics, actors
│   │   ├─ Tests? → swift-testing-expert
│   │   │   └─ Also load: fundamentals, expectations, test-doubles
│   │   ├─ ViewModel? → swiftui-expert-skill + swift-concurrency
│   │   │   └─ Also load: state-management, actors
│   │   └─ Architecture? → swift-best-practices + swift-code-reviewer
│   │       └─ Also load: architecture-patterns
│   └─ NO → Continue
│
├─ Is this a fix/debug task?
│   ├─ YES → Analyze the error
│   │   ├─ Concurrency warning? → swift-concurrency
│   │   │   └─ Load: sendable, actors, threading
│   │   ├─ UI not updating? → swiftui-expert-skill
│   │   │   └─ Load: state-management, performance-patterns
│   │   ├─ Test failing? → swift-testing-expert
│   │   │   └─ Load: expectations, async-testing-and-waiting
│   │   ├─ Crash / force unwrap? → swift-code-reviewer
│   │   │   └─ Load: security-checklist
│   │   └─ Performance issue? → swiftui-expert-skill
│   │       └─ Load: performance-patterns, list-patterns
│   └─ NO → Continue
│
├─ Is this a refactor/modernize task?
│   ├─ YES
│   │   ├─ Swift 5 → 6? → swift-concurrency (migration)
│   │   ├─ XCTest → Swift Testing? → swift-testing-expert (migration)
│   │   ├─ ObservableObject → @Observable? → swiftui-expert-skill
│   │   ├─ Deprecated APIs? → swiftui-expert-skill (modern-apis)
│   │   └─ General cleanup? → swift-best-practices + swift-code-reviewer
│   └─ NO → Continue
│
├─ Is this an explanation request?
│   ├─ YES → Route to the domain skill with highest relevance
│   │   └─ Don't load reference files unless deep detail needed
│   └─ NO → Continue
│
└─ Catch-all: Apply swift-best-practices as baseline
```

---

## Compound Task Routing

Real tasks often span multiple domains. Here are common compound patterns:

### "Build a login screen"
```
Primary:   swiftui-expert-skill
Secondary: swift-concurrency, swift-best-practices
Tertiary:  swift-code-reviewer (security-checklist)

References to load:
  - state-management.md (form state, validation state)
  - modern-apis.md (TextField, SecureField patterns)
  - async-await-basics.md (login request)
  - security-checklist.md (credential handling)

Project check:
  - CLAUDE.md: auth patterns, error handling
  - Design system: colors, typography, spacing
```

### "Review PR #42"
```
Primary:   swift-code-reviewer
Secondary: All relevant skills based on diff content

References to load:
  - review-workflow.md (process)
  - custom-guidelines.md (CLAUDE.md rules)
  
Then based on diff content:
  - SwiftUI files? → swiftui-review-checklist.md
  - Async code? → swift-quality-checklist.md (concurrency section)
  - Tests? → swift-quality-checklist.md (testing section)
  - Security? → security-checklist.md
```

### "Fix: 'Sending value of non-Sendable type risks causing data races'"
```
Primary:   swift-concurrency
Secondary: swift-best-practices

References to load:
  - sendable.md (Sendable conformance patterns)
  - threading.md (isolation boundary identification)
  - actors.md (if actor isolation is involved)
  - migration.md (if Swift 6 migration context)
```

### "Write tests for UserService"
```
Primary:   swift-testing-expert
Secondary: swift-testing

References to load:
  - fundamentals.md (suite structure)
  - expectations.md (#expect, #require)
  - test-doubles.md (mocking UserService dependencies)
  - fixtures.md (test data for User)
  - async-testing-and-waiting.md (if UserService is async)

Project check:
  - CLAUDE.md: testing requirements, coverage thresholds
```

### "Migrate from ObservableObject to @Observable"
```
Primary:   swiftui-expert-skill
Secondary: swift-concurrency

References to load:
  - state-management.md (@Observable patterns, property wrapper changes)
  - modern-apis.md (related API updates)
  - threading.md (default actor isolation changes with @Observable)
```

---

## Priority Resolution

When multiple skills apply, use this priority system:

```
Priority 1 (HIGHEST): Project CLAUDE.md rules
  → These override everything. If CLAUDE.md says "use TCA",
    don't suggest MVVM even if a skill recommends it.

Priority 2: Specialized skill (priority 8-10)
  → Domain-specific expertise wins for domain questions.
    swift-concurrency for concurrency, swiftui-expert for UI.

Priority 3: General skill (priority 5-7)
  → swift-best-practices, swift-code-reviewer for broad guidance.

Priority 4 (LOWEST): General programming principles
  → Clean code, SOLID, DRY — apply when no skill speaks to the topic.
```

### Conflict Examples

**Conflict**: swift-best-practices says "use struct", CLAUDE.md says "ViewModels are classes"
**Resolution**: Follow CLAUDE.md. Note the deviation in review comments if appropriate.

**Conflict**: swift-testing says "use SpyingStub", swift-testing-expert says "prefer state verification"
**Resolution**: Both are complementary. Use SpyingStub pattern with state verification as recommended.

**Conflict**: swiftui-expert says "@Observable", but project targets iOS 16
**Resolution**: Platform constraint wins. Use ObservableObject with @StateObject/@ObservedObject.

---

## Reference Loading Strategy

### Lazy Loading Rules

```
NEVER preload all references at once. 
ALWAYS load on-demand as sub-topics are encountered.

Trigger: User mentions "async" in a SwiftUI context
  Load: swiftui-expert-skill/references/state-management.md
  Then IF async patterns needed: swift-concurrency/references/async-await-basics.md
  Then IF actors mentioned: swift-concurrency/references/actors.md

Trigger: User asks for a code review
  Load: swift-code-reviewer/references/review-workflow.md
  Then based on file types in diff, load relevant checklists
  DO NOT load all 8 reference files upfront
```

### Context Window Budget

```
Budget allocation per task:
  - CLAUDE.md: Always (typically 200-500 tokens)
  - Primary skill SKILL.md: Always (200-400 tokens, already in context)
  - Primary references: 1-3 files max (500-1500 tokens each)
  - Secondary references: Only if directly relevant (500-1000 tokens)
  
Total budget target: < 5000 tokens of skill knowledge per task
```

---

## Language-Agnostic Routing

The routing engine extends to any language by following this pattern:

### Detection → Skill Mapping

```python
# Pseudocode for routing logic

def route_task(task, project_context):
    # 1. Detect language
    language = detect_language(project_context)
    
    # 2. Get available skills for this language
    skills = registry.filter(language=language)
    
    # 3. Classify task domains
    domains = classify_domains(task)
    
    # 4. Match skills to domains
    matched = []
    for domain in domains:
        primary = skills.best_match(domain, priority="highest")
        secondary = skills.other_matches(domain)
        matched.append((domain, primary, secondary))
    
    # 5. Load references based on task specifics
    references = []
    for domain, primary, _ in matched:
        refs = select_references(primary, task, domain)
        references.extend(refs)
    
    # 6. Apply project overrides
    apply_claude_md_overrides(matched, project_context)
    
    return matched, references
```

### Adding a New Language

To extend the orchestrator to a new language:

1. **Create language skills** following the same structure:
   - `SKILL.md` with YAML frontmatter
   - `references/` with deep knowledge files
   
2. **Install in the skill path**:
   - `.claude/skills/<skill-name>/` for project-specific
   - `~/.claude/skills/<skill-name>/` for user-global

3. **The orchestrator auto-discovers** by scanning for SKILL.md files

4. **The routing engine auto-extends** by reading new skill metadata

No changes to the orchestrator itself are needed.
