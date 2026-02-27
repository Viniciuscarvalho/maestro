"""
maestro setup — configures the entire system automatically.

What it does:
    1. Creates ~/.maestro/skills/ directory
    2. Copies/moves existing skills from ~/.claude/skills/ to ~/.maestro/skills/
    3. Installs the Gateway SKILL.md in .claude/skills/maestro/
    4. Configures MCP in .claude/mcp.json
    5. Runs initial indexation

Usage:
    maestro-setup                  # full setup
    maestro-setup --claude-ai-only # for Claude.ai (no MCP, manual context)
    maestro-setup --dry-run        # show what would happen
    maestro-setup --keep-originals # copy skills instead of moving
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()

MAESTRO_HOME   = Path.home() / ".maestro"
MAESTRO_SKILLS = MAESTRO_HOME / "skills"
CLAUDE_SKILLS  = Path.home() / ".claude" / "skills"
GATEWAY_DIR    = Path(".claude") / "skills" / "maestro"
MCP_CONFIG     = Path(".claude") / "mcp.json"

GATEWAY_CONTENT = """\
---
name: maestro
description: >
  Skill knowledge gateway. MUST call search_skills MCP tool before any coding
  task to retrieve expert knowledge from the indexed skill base.
---

# Maestro — Skill Knowledge Gateway

## Critical Rule

**BEFORE writing, reviewing, or modifying any code, ALWAYS call the `search_skills`
MCP tool.**

```
EVERY task → search_skills("what you need to know") → apply knowledge → respond
```

## How to Search

```
search_skills("Sendable conformance warning in actor class")
search_skills("SwiftUI @Observable state management pattern")
search_skills("unit tests Swift Testing #expect mock")
```

For compound tasks, call multiple times with focused queries.

## Tools available

| Tool | Purpose |
|------|---------|
| `search_skills` | Search indexed knowledge base (auto-indexes on first call) |
| `reindex_skills` | Force re-index when skills are added/updated |
| `skill_status` | Show what is indexed and chunk counts |

## Without MCP

Ask the user to run:
```bash
maestro context "task description"
```
and paste the output here.
"""


@click.command()
@click.option("--dry-run", is_flag=True, help="Show what would happen without making changes")
@click.option("--claude-ai-only", is_flag=True, help="Skip MCP config (for Claude.ai users)")
@click.option("--keep-originals", is_flag=True, help="Copy skills instead of moving them")
def setup(dry_run: bool, claude_ai_only: bool, keep_originals: bool) -> None:
    """Set up Maestro: move skills, install gateway, configure MCP."""
    console.print(Panel.fit("[bold]✦ Maestro Setup[/bold]", style="cyan"))
    steps: list[str] = []

    # Step 1: Create ~/.maestro/skills/
    if not MAESTRO_SKILLS.exists():
        steps.append(f"  Create {MAESTRO_SKILLS}")
        if not dry_run:
            MAESTRO_SKILLS.mkdir(parents=True, exist_ok=True)

    # Step 2: Move/copy skills from ~/.claude/skills/
    if CLAUDE_SKILLS.exists():
        for skill_dir in CLAUDE_SKILLS.iterdir():
            if not skill_dir.is_dir() or skill_dir.name == "maestro":
                continue
            dest = MAESTRO_SKILLS / skill_dir.name
            if dest.exists():
                steps.append(f"  Skip {skill_dir.name} (already in ~/.maestro/skills/)")
                continue
            verb = "Copy" if keep_originals else "Move"
            steps.append(f"  {verb} {skill_dir.name} → ~/.maestro/skills/")
            if not dry_run:
                if keep_originals:
                    shutil.copytree(skill_dir, dest)
                else:
                    shutil.move(str(skill_dir), str(dest))

    # Step 3: Install Gateway SKILL.md
    if not GATEWAY_DIR.exists():
        steps.append(f"  Install Gateway → {GATEWAY_DIR}/SKILL.md")
        if not dry_run:
            GATEWAY_DIR.mkdir(parents=True, exist_ok=True)
            (GATEWAY_DIR / "SKILL.md").write_text(GATEWAY_CONTENT)
    elif not (GATEWAY_DIR / "SKILL.md").exists():
        steps.append("  Install Gateway SKILL.md")
        if not dry_run:
            (GATEWAY_DIR / "SKILL.md").write_text(GATEWAY_CONTENT)
    else:
        steps.append("  ✓ Gateway already installed")

    # Step 4: Configure MCP
    if not claude_ai_only:
        if MCP_CONFIG.exists():
            mcp = json.loads(MCP_CONFIG.read_text())
        else:
            mcp = {"mcpServers": {}}
        MCP_CONFIG.parent.mkdir(parents=True, exist_ok=True)

        if "maestro" not in mcp.get("mcpServers", {}):
            steps.append(f"  Add maestro to {MCP_CONFIG}")
            if not dry_run:
                mcp.setdefault("mcpServers", {})
                mcp["mcpServers"]["maestro"] = {"command": "maestro-mcp", "args": []}
                MCP_CONFIG.write_text(json.dumps(mcp, indent=2))
        else:
            steps.append("  ✓ MCP already configured")

    # Step 5: Initial index
    steps.append("  Index skills...")
    if not dry_run:
        from .engine import MaestroEngine, Config
        engine = MaestroEngine(Config.load())
        stats = engine.index()
        steps.append(
            f"  ✓ {stats['skills']} skills, {stats['chunks']} chunks "
            f"in {stats['duration_s']}s"
        )

    # Display
    console.print()
    for step in steps:
        console.print(f"  {step}")
    console.print()

    if dry_run:
        console.print("[yellow]Dry run — no changes made. Remove --dry-run to execute.[/]")
    else:
        console.print(Panel.fit(
            "[bold green]Done![/]\n\n"
            f"Skills moved to:    ~/.maestro/skills/\n"
            f"Gateway installed:  .claude/skills/maestro/SKILL.md\n"
            + (f"MCP configured:     .claude/mcp.json\n" if not claude_ai_only else "")
            + "\nClaude now loads ONLY the gateway (~750 tokens).\n"
            "Knowledge is retrieved via RAG on demand.",
            title="Setup Complete",
        ))


if __name__ == "__main__":
    setup()
