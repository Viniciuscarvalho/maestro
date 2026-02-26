# Project Scanner

Detailed procedures for scanning and understanding project context. The orchestrator runs this on every new project or when context seems stale.

---

## Scan Procedure

### Step 1: Project Rules (CLAUDE.md)

Check these paths in order, read the first one found:

```
.claude/CLAUDE.md
CLAUDE.md
.cursor/rules
.github/copilot-instructions.md
```

**What to extract from CLAUDE.md:**

```yaml
architecture:
  pattern: ""          # MVVM, TCA, Clean Architecture, MVI, etc.
  layers: []           # View, ViewModel, Repository, UseCase, etc.
  di_approach: ""      # Constructor injection, Container, etc.

conventions:
  naming: ""           # Custom naming rules
  file_structure: ""   # How files should be organized
  error_handling: ""   # Custom error types, patterns
  logging: ""          # Logging framework, rules

ui:
  design_system: ""    # Custom colors, fonts, spacing tokens
  navigation: ""       # Coordinator, NavigationStack, Router
  component_lib: ""    # Custom component library

testing:
  framework: ""        # Swift Testing, XCTest, both
  coverage_min: 0      # Minimum coverage percentage
  patterns: []         # Required test patterns
  mocking: ""          # Mocking approach

dependencies:
  forbidden: []        # Libraries not allowed
  preferred: []        # Preferred libraries for common tasks
  
platform:
  min_ios: ""          # Minimum iOS version
  min_macos: ""        # Minimum macOS version
  swift_version: ""    # Swift language version
```

### Step 2: Tech Stack Detection

#### Swift / Apple Platforms

**Package.swift** (SwiftPM):
```bash
# Read for:
# - swift-tools-version (determines available features)
# - .macOS/.iOS deployment targets
# - Dependencies (third-party libraries)
# - Targets and their types
# - Swift settings (strict concurrency, upcoming features)

# Key patterns to look for:
grep -i "swift-tools-version" Package.swift
grep -i "swiftLanguageMode" Package.swift
grep -i "StrictConcurrency" Package.swift
grep -i "enableUpcomingFeature" Package.swift
grep -i "defaultIsolation" Package.swift
```

**Xcode Project** (.xcodeproj):
```bash
# Search for build settings:
grep -r "SWIFT_STRICT_CONCURRENCY" *.xcodeproj
grep -r "SWIFT_DEFAULT_ACTOR_ISOLATION" *.xcodeproj
grep -r "IPHONEOS_DEPLOYMENT_TARGET" *.xcodeproj
grep -r "MACOSX_DEPLOYMENT_TARGET" *.xcodeproj
grep -r "SWIFT_VERSION" *.xcodeproj
```

**SwiftLint** (.swiftlint.yml):
```bash
# Read for custom rules, disabled rules, opt-in rules
cat .swiftlint.yml 2>/dev/null
```

#### JavaScript / TypeScript

```bash
# package.json for framework, deps, scripts
cat package.json | jq '.dependencies, .devDependencies'

# tsconfig.json for TS configuration
cat tsconfig.json 2>/dev/null

# Framework detection:
# - "next" in deps → Next.js
# - "react" in deps → React
# - "vue" in deps → Vue
# - "angular" in deps → Angular
# - "svelte" in deps → Svelte
```

#### Python

```bash
# pyproject.toml for modern Python projects
cat pyproject.toml 2>/dev/null

# requirements.txt for dependencies
cat requirements.txt 2>/dev/null

# Framework detection:
# - "django" → Django
# - "fastapi" → FastAPI
# - "flask" → Flask
```

#### Rust

```bash
# Cargo.toml for dependencies, edition, features
cat Cargo.toml 2>/dev/null
```

#### Go

```bash
# go.mod for module path, Go version, dependencies
cat go.mod 2>/dev/null
```

### Step 3: Skill Discovery

Scan for installed skills:

```bash
# Project-local skills
if [ -d ".claude/skills" ]; then
  find .claude/skills -name "SKILL.md" -exec echo "LOCAL: {}" \;
fi

# User-global skills
if [ -d "$HOME/.claude/skills" ]; then
  find "$HOME/.claude/skills" -name "SKILL.md" -exec echo "USER: {}" \;
fi

# For each SKILL.md found, extract:
# 1. name (from YAML frontmatter)
# 2. description (from YAML frontmatter)  
# 3. List references/ directory
```

### Step 4: Dependency Analysis

For each dependency found, note its patterns:

```yaml
# Common Swift dependencies and their implications:

# Alamofire → networking patterns, request/response models
# Kingfisher → image caching, async image loading
# SnapKit → programmatic UI constraints
# Realm → local database, @Persisted properties
# Firebase → auth, analytics, cloud functions
# Combine → reactive patterns (may conflict with async/await advice)
# RxSwift → reactive patterns (suggest migration path)
# TCA (ComposableArchitecture) → specific architecture, Reducers, Effects
# GRDB → SQLite patterns, async database access
# SwiftProtobuf → protobuf models, gRPC patterns
```

### Step 5: Architecture Inference

If CLAUDE.md doesn't specify architecture, infer from code:

```
Signal → Inferred Architecture:

*ViewModel* files with @Observable  → MVVM
*Reducer* files with State/Action   → TCA
*Interactor* + *Presenter* files    → VIPER
*UseCase* files                     → Clean Architecture
*Store* files with ObservableObject → Flux/Redux-like
*Coordinator* files                 → Coordinator pattern
*Router* files                      → Router pattern
```

---

## Scan Output Format

After scanning, the orchestrator should hold this mental model:

```yaml
project:
  name: "MyApp"
  language: "swift"
  swift_version: "6.0"
  min_ios: "17.0"
  min_macos: "14.0"
  
  architecture:
    pattern: "MVVM"
    has_coordinators: true
    di_approach: "constructor"
    
  concurrency:
    strict_checking: "complete"
    default_isolation: "MainActor"  # or "nonisolated"
    upcoming_features: ["NonisolatedNonsendingByDefault"]
    
  ui:
    framework: "SwiftUI"
    design_system: "AppColors, AppFonts, AppSpacing"
    navigation: "NavigationStack + Coordinator"
    
  testing:
    framework: "Swift Testing"
    coverage_min: 80
    patterns: ["Arrange-Act-Assert", "fixtures near models"]
    
  dependencies:
    - name: "Alamofire"
      domain: "networking"
    - name: "Kingfisher"
      domain: "image-loading"
      
  skills_available:
    - swift-best-practices (5 references)
    - swift-concurrency (12 references)
    - swift-testing (8 references)
    - swift-testing-expert (9 references)
    - swiftui-expert-skill (11 references)
    - swift-code-reviewer (8 references)
    
  skill_gaps:
    - "No skill for Alamofire networking patterns"
    - "No skill for Coordinator navigation pattern"
```

---

## Incremental Scanning

After the initial full scan, subsequent tasks only need incremental updates:

```
On each new task:
1. Check if CLAUDE.md has been modified → rescan rules
2. Check if Package.swift has changed → rescan dependencies
3. Check if new skills were added → rescan skill paths
4. Otherwise → use cached project model
```

---

## Multi-Project Support

If working in a monorepo or workspace with multiple projects:

```
workspace/
├── Package.swift          ← Root package
├── CLAUDE.md              ← Workspace-wide rules
├── App/
│   ├── CLAUDE.md          ← App-specific overrides
│   └── Sources/
├── Core/
│   ├── CLAUDE.md          ← Core-specific rules
│   └── Sources/
└── Tests/
    └── Sources/
```

**Rule**: More specific CLAUDE.md files override less specific ones. Workspace rules apply as defaults, project rules override.
