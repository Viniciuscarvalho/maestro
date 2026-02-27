# RAG Engine

5-phase Retrieval-Augmented Generation protocol for semantic skill routing. This engine activates when keyword-based routing (Phase 3 of SKILL.md) returns zero matches or ambiguous results. It decomposes natural language queries into semantic dimensions, scores skills by similarity, and loads only the references needed for the task.

---

## When RAG Activates

The RAG engine is a fallback path invoked by Phase 3b of the orchestrator. It runs when:

1. **Keyword routing returns 0 matches** — the task doesn't contain any skill trigger words
2. **Keyword routing returns ambiguous results** — multiple skills match equally with no clear winner
3. **Task is phrased in natural language** — longer than 10 words, or contains phrases like "help me", "how do I", "I want to", "what's the best way to", "can you"
4. **Task is conceptual rather than technical** — asks about approaches, strategies, or best practices without naming specific APIs

---

## Phase RAG-1: Query Decomposition

Decompose the user's task into four semantic dimensions:

### Dimensions

| Dimension | What to Extract | Examples |
|---|---|---|
| **Intent** | The action the user wants performed | create, fix, review, explain, migrate, optimize |
| **Domain** | The technical area involved | UI, concurrency, testing, architecture, security |
| **Complexity** | Scope and depth of the task | single-function, module-level, system-wide |
| **Implicit Requirements** | Unstated needs inferred from context | error handling, state management, thread safety |

### Decomposition Process

```
Input: "Help me build a user profile screen that loads data from our API"

Decomposition:
  Intent:     create (inferred from "build")
  Domain:     ui (screen, profile), networking (loads data, API)
  Complexity: module-level (full screen with data loading)
  Implicit:   state management (loading/loaded/error states),
              error handling (API can fail),
              async patterns (network call),
              navigation (screen implies navigation context)
```

### Implicit Requirement Inference Rules

```
Task mentions "screen" or "view"
  → Implies: state management, view composition, navigation context

Task mentions "load", "fetch", "API", "data"
  → Implies: async/await, error handling, loading states

Task mentions "form", "input", "edit"
  → Implies: validation, binding, state management

Task mentions "list", "collection", "scroll"
  → Implies: performance, identity, lazy loading

Task mentions "test" or "verify"
  → Implies: test doubles for dependencies, assertions

Task mentions "review" or "check"
  → Implies: checklists, project conventions (CLAUDE.md)

Task mentions "migrate" or "update" or "modernize"
  → Implies: deprecated API knowledge, version constraints
```

---

## Phase RAG-2: Similarity Scoring

Score each skill in the registry against the decomposed query. Higher scores indicate stronger matches.

### Scoring Rubric

| Factor | Points | Description |
|---|---|---|
| **Exact domain match** | +30 | Skill's `domains` field contains the extracted domain |
| **Intent alignment** | +20 | Skill's `actions` field contains the extracted intent |
| **Framework match** | +15 | Skill covers the detected framework (SwiftUI, Swift Testing, etc.) |
| **Example similarity** | +20 | Task semantically resembles one of the skill's example queries in `semantic-index.md` |
| **Implicit requirement coverage** | +15 | Skill covers inferred implicit needs |
| **Anti-example hit** | -40 | Task matches an anti-example for this skill (strong negative signal) |

### Scoring Process

```
For each skill in registry:
  score = 0

  # Domain matching
  for domain in extracted_domains:
    if domain in skill.domains:
      score += 30

  # Intent matching
  if extracted_intent in skill.actions:
    score += 20

  # Framework matching
  if detected_framework in skill.frameworks:
    score += 15

  # Example similarity (semantic, not keyword)
  best_example_similarity = max(
    semantic_similarity(task, example)
    for example in skill.example_queries
  )
  if best_example_similarity > 0.7:
    score += 20
  elif best_example_similarity > 0.5:
    score += 10

  # Implicit requirement coverage
  covered_implicits = count(
    req for req in implicit_requirements
    if skill.covers(req)
  )
  score += (covered_implicits / total_implicits) * 15

  # Anti-example penalty
  for anti_example in skill.anti_examples:
    if semantic_similarity(task, anti_example.trigger) > 0.7:
      score -= 40
      # Also note the suggested_skill from the anti-example
```

### Output Format

Produce the top-3 skills ranked by score:

```
RAG-2 Results:
  1. swiftui-expert-skill    → 85/100  (domain: +30, intent: +20, framework: +15, example: +20)
  2. swift-concurrency        → 45/100  (implicit: +15, domain: +30)
  3. swift-best-practices     → 25/100  (intent: +20, implicit: +5)
```

---

## Phase RAG-3: Lazy Reference Retrieval

Only load reference files that are relevant to the specific task. Do NOT load all references for matched skills.

### Retrieval Strategy

```
For each matched skill (from RAG-2, score > threshold):

  1. Read the skill's reference file list from skill-registry.md
  2. For each reference file, check if its topic overlaps with:
     - The extracted domains
     - The implicit requirements
     - The specific sub-task being performed
  3. Load ONLY files that pass the relevance check
  4. Cap at 3 reference files per skill, 6 total across all skills
```

### Reference Relevance Rules

```
Reference file → Load when:
  state-management.md      → task involves UI state, forms, data binding
  async-await-basics.md    → task involves network calls, async operations
  actors.md                → task involves shared mutable state, isolation
  sendable.md              → task mentions Sendable, data race, crossing boundaries
  fundamentals.md          → task involves writing new tests
  expectations.md          → task involves assertions, verifying behavior
  test-doubles.md          → task involves mocking, stubbing dependencies
  performance-patterns.md  → task mentions performance, slow, optimization
  review-workflow.md       → task is a code review request
  security-checklist.md    → task involves auth, credentials, user input
  migration.md             → task involves upgrading, modernizing, converting
  modern-apis.md           → task mentions deprecated APIs or needs current patterns
```

### Example

```
Task: "Help me build a profile screen that loads data from our API"

Matched skills:
  1. swiftui-expert-skill (score: 85)
     → Load: state-management.md (UI state), modern-apis.md (current SwiftUI patterns)
  2. swift-concurrency (score: 45)
     → Load: async-await-basics.md (API call)

Total references loaded: 3 (within budget)
Skipped: performance-patterns.md (no perf concern), actors.md (no shared state),
          navigation.md (not the focus), all testing/review references
```

---

## Phase RAG-4: Context Window Optimization

When multiple skills are loaded, merge their guidance to avoid redundancy and stay within the context budget.

### Merge Rules

1. **Deduplicate overlapping advice.** If both `swiftui-expert-skill` and `swift-concurrency` mention `@MainActor`, include it once in the SwiftUI context (it's a UI concern primarily).

2. **Establish a primary voice.** The highest-scoring skill "owns" the response structure. Other skills contribute specific advice where relevant.

3. **Layer knowledge, don't repeat.** Structure merged context as:
   ```
   Primary skill context (full guidance for the main domain)
   └── Supplementary: [secondary skill] — [specific relevant advice only]
   └── Supplementary: [tertiary skill] — [specific relevant advice only]
   ```

4. **Respect the context budget.**
   ```
   Budget allocation:
     CLAUDE.md / project rules:    ~500 tokens (always loaded)
     Primary skill references:     ~2000 tokens (1-3 files)
     Secondary skill references:   ~1500 tokens (1-2 files)
     Tertiary skill references:    ~500 tokens (0-1 files)
     ─────────────────────────────────────────
     Total target:                 < 5000 tokens of skill knowledge
   ```

5. **Trim aggressively.** From each reference file, extract only the sections relevant to the decomposed query. Skip sections about unrelated sub-topics.

### Context Assembly Template

```
## Skill Context for Current Task

### Primary: [skill-name] (score: XX)
[Relevant sections from loaded references]

### Secondary: [skill-name] (score: XX)
[Only the specific advice relevant to implicit requirements]

### Project Overrides
[Relevant rules from CLAUDE.md that apply to this task]
```

---

## Phase RAG-5: Confidence Thresholds

Use the top skill's score from RAG-2 to determine routing confidence:

### Threshold Table

| Score Range | Confidence | Action |
|---|---|---|
| **> 70** | Confident | Route to matched skills. Execute normally via Phase 4. |
| **50–70** | Uncertain | Route to best match but note the uncertainty. Apply broader skill set. Load additional context to compensate. |
| **< 50** | Skill Gap | No skill adequately covers this task. Flag the gap. Apply general programming principles. Suggest a skill that would help. |

### Confident (> 70)

```
Proceed with Phase 4 (Execution) using the matched skills.
Do not mention routing uncertainty to the user.
Apply knowledge assertively.
```

### Uncertain (50–70)

```
Proceed with Phase 4 but:
  1. Load references from both the primary AND secondary skill
  2. Apply conservative patterns (prefer well-established over cutting-edge)
  3. Cross-check output against swift-code-reviewer checklists
  4. If the task is a creation task, add error handling as a safety net
```

### Skill Gap (< 50)

```
1. Apply general best practices (clean code, SOLID, error handling)
2. Check if CLAUDE.md provides project-specific guidance for this domain
3. Surface the gap to the user:
   "This task involves [domain] which isn't covered by a specialized skill.
    I'll apply general best practices. Consider adding a skill for [domain]
    to get deeper guidance."
4. Log the gap in the knowledge graph (skill-gaps.md)
```

---

## Full Pipeline Example

```
User: "I want to make my app handle background refresh properly
       and show the updated data when the user comes back"

Phase RAG-1 — Decomposition:
  Intent:     create / fix
  Domain:     concurrency (background refresh), ui (show updated data)
  Complexity: module-level (background + foreground coordination)
  Implicit:   state management (data freshness), app lifecycle,
              async patterns (background fetch), error handling

Phase RAG-2 — Scoring:
  swift-concurrency:     75 (domain: +30, intent: +20, implicit: +15, example: +10)
  swiftui-expert-skill:  65 (domain: +30, intent: +20, implicit: +15)
  swift-best-practices:  20 (intent: +20)
  swift-testing:          0 (no match)
  swift-code-reviewer:    0 (no match)

  Top-3: swift-concurrency (75), swiftui-expert-skill (65), swift-best-practices (20)

Phase RAG-3 — Reference Loading:
  swift-concurrency:
    → async-await-basics.md (background task coordination)
    → tasks.md (Task lifecycle, background tasks)
  swiftui-expert-skill:
    → state-management.md (data freshness in UI)

  Total: 3 files loaded

Phase RAG-4 — Context Merge:
  Primary: swift-concurrency — background task patterns, async coordination
  Secondary: swiftui-expert-skill — @Observable data flow, view updates on foreground
  Project: CLAUDE.md rules applied

Phase RAG-5 — Confidence:
  Top score: 75 → CONFIDENT
  Action: Execute normally with full skill context
```
