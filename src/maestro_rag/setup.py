"""
maestro setup — configures the entire system automatically.

What it does:
    1. Creates ~/.maestro/skills/ directory
    2. Copies/moves existing skills from ~/.claude/skills/ to ~/.maestro/skills/
    3. Runs initial indexation

Note: Gateway SKILL.md and MCP config are handled by the plugin system
when installed via `/plugin install`. For standalone users, those are
configured manually.

Usage:
    maestro-setup                  # full setup
    maestro-setup --dry-run        # show what would happen
    maestro-setup --keep-originals # copy skills instead of moving
"""
from __future__ import annotations

import shutil
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()

MAESTRO_HOME   = Path.home() / ".maestro"
MAESTRO_SKILLS = MAESTRO_HOME / "skills"
CLAUDE_SKILLS  = Path.home() / ".claude" / "skills"


@click.command()
@click.option("--dry-run", is_flag=True, help="Show what would happen without making changes")
@click.option("--keep-originals", is_flag=True, help="Copy skills instead of moving them")
def setup(dry_run: bool, keep_originals: bool) -> None:
    """Set up Maestro: migrate skills and run initial indexation."""
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

    # Step 3: Initial index + Skill Index generation
    steps.append("  Index skills...")
    if not dry_run:
        from .engine import MaestroEngine, Config
        from .cli import _refresh_skill_index
        engine = MaestroEngine(Config.load())
        stats = engine.index()
        steps.append(
            f"  ✓ {stats['skills']} skills, {stats['chunks']} chunks "
            f"in {stats['duration_s']}s"
        )
        # Update SKILL_INDEX table in gateway SKILL.md files
        status_data = engine.status()
        updated = _refresh_skill_index(status_data["skills"])
        for f in updated:
            steps.append(f"  ✓ Skill Index updated in {f}")

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
            "\nClaude now loads ONLY the gateway (~750 tokens).\n"
            "Knowledge is retrieved via RAG on demand.\n\n"
            "Plugin users: Gateway SKILL.md and MCP are configured automatically.\n"
            "Standalone users: see README.md for manual MCP configuration.",
            title="Setup Complete",
        ))


if __name__ == "__main__":
    setup()
