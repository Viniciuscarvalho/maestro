# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-06

### Added

- **Claude Code Plugin format** — one-command install via `/plugin install maestro`
  - `.claude-plugin/plugin.json` manifest
  - `.mcp.json` plugin MCP config with `${CLAUDE_PLUGIN_ROOT}` support
  - `scripts/maestro-mcp.sh` wrapper that auto-creates venv at `~/.maestro/.venv/`
  - `skills/maestro/SKILL.md` gateway skill (plugin-provided)
  - `hooks/hooks.json` SessionStart hook for auto-setup
- **Fingerprint persistence** — skill fingerprints saved to `index_meta.json` and reloaded on restart, avoiding re-indexation

### Changed

- `setup.py` simplified — removed MCP config writing and gateway SKILL.md installation (now handled by the plugin system)
- Removed `--claude-ai-only` flag from `maestro-setup` (standalone MCP config is now manual per README)
- Updated README with plugin install instructions and new file structure
- Cleared project-level `.claude/mcp.json` (plugin provides MCP config)

### Fixed

- Skill fingerprints now persist across MCP server restarts (previously lost, causing degraded T2 filtering)

## [0.1.0] - 2025-12-01

### Added

- Initial release: Python RAG engine with 5 quality techniques (T1-T5)
- ChromaDB vector search + BM25 hybrid with RRF fusion
- Concept graph expansion for Swift/SwiftUI domains
- Cross-encoder reranking
- MCP server (`maestro-mcp`) for Claude Code integration
- CLI tools: `maestro index`, `search`, `context`, `explain`, `status`, `clear`
- Gateway SKILL.md for automatic skill routing
- One-command setup via `maestro-setup`
