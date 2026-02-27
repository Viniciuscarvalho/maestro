"""
Maestro CLI — index and search your skill knowledge.

Commands:
    maestro index  [PATH...]   Index skill directories
    maestro search  QUERY      Search with full pipeline
    maestro context QUERY      Get LLM-ready context block
    maestro status             Show index stats
    maestro explain QUERY      Show HOW the search worked (debug)
    maestro clear              Clear the index
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .engine import MaestroEngine, Config, SearchResponse

console = Console()


@click.group()
@click.version_option("1.0.0", prog_name="maestro")
def main() -> None:
    """Maestro — one-shot skill knowledge retrieval."""
    pass


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
def index(paths: tuple[str, ...]) -> None:
    """Index skill directories."""
    config = Config.load()
    if paths:
        config.skill_paths = [Path(p) for p in paths]
    with console.status("[bold green]Indexing skills..."):
        engine = MaestroEngine(config)
        stats = engine.index()
    console.print(Panel.fit(
        f"[bold green]Done![/]\n\n"
        f"Skills:        {stats['skills']}\n"
        f"Files:         {stats['files']}\n"
        f"Chunks:        {stats['chunks']}\n"
        f"Fingerprints:  {stats['fingerprints']}\n"
        f"Duration:      {stats['duration_s']}s",
        title="✦ Maestro Index",
    ))
    if stats.get("errors"):
        for e in stats["errors"]:
            console.print(f"  [yellow]⚠ {e}[/]")


@main.command()
@click.argument("query")
@click.option("--top-k", "-k", default=7, help="Number of results")
def search(query: str, top_k: int) -> None:
    """Search indexed skills with full pipeline."""
    engine = MaestroEngine(Config.load())
    status = engine.status()
    if not status["indexed"]:
        console.print("[red]No index found. Run `maestro index` first.[/]")
        sys.exit(1)
    response = engine.search(query, top_k=top_k)
    _display_results(response)


@main.command()
@click.argument("query")
@click.option("--max-tokens", "-t", default=3000, help="Context budget")
def context(query: str, max_tokens: int) -> None:
    """Get LLM-ready context block (for Claude.ai copy-paste)."""
    engine = MaestroEngine(Config.load())
    click.echo(engine.get_context(query, max_tokens))


@main.command()
@click.argument("query")
def explain(query: str) -> None:
    """Show HOW the search pipeline worked (debug mode)."""
    engine = MaestroEngine(Config.load())
    console.print(f"\n[bold]Query:[/] {query}\n")

    # Step 1: Concept expansion
    from .concept_graph import get_swift_concept_graph
    graph = get_swift_concept_graph()
    expanded = graph.expand(query)
    console.print("[bold cyan]1. Concept Expansion:[/]")
    if expanded:
        console.print(f"   Added: {', '.join(expanded)}")
    else:
        console.print("   No expansions (query already specific)")

    # Step 2: Skill fingerprinting
    query_emb = engine._embedder.embed_query(query)
    console.print("\n[bold cyan]2. Skill Fingerprinting:[/]")
    matched = engine._match_skills(query_emb)
    if matched:
        console.print(f"   Matched: {', '.join(matched)}")
        total = engine._collection.count() if engine._collection else 0
        matched_chunks = sum(
            engine._fingerprints[s].chunk_count
            for s in matched if s in engine._fingerprints
        )
        pct = 100 * matched_chunks // total if total else 0
        console.print(f"   Searching {matched_chunks}/{total} chunks ({pct}%)")
    else:
        console.print("   Searching all skills (ambiguous query)")

    # Step 3-5: Full search
    response = engine.search(query)
    console.print("\n[bold cyan]3. Hybrid Search + RRF + Reranking:[/]")
    for r in response.results:
        sem = f"sem={r.semantic_rank}" if r.semantic_rank is not None else "sem=∅"
        bm = f"bm25={r.bm25_rank}" if r.bm25_rank is not None else "bm25=∅"
        rr = f"rerank={r.rerank_score:.3f}" if r.rerank_score is not None else ""
        console.print(
            f"   [{r.chunk.skill}/{r.chunk.file}] "
            f"{r.chunk.section[:40]:40s} "
            f"score={r.final_score:.3f} {sem} {bm} {rr}"
        )

    console.print("\n[bold cyan]4. Summary:[/]")
    console.print(f"   Skills used: {', '.join(response.skills_used)}")
    console.print(f"   Time:        {response.time_ms:.0f}ms")
    console.print(f"   Cache:       {'HIT' if response.from_cache else 'MISS'}")
    if response.expanded_terms:
        console.print(f"   Expanded:    +{', '.join(response.expanded_terms)}")


@main.command()
def status() -> None:
    """Show index statistics."""
    engine = MaestroEngine(Config.load())
    stats = engine.status()

    table = Table(title="✦ Maestro Index")
    table.add_column("Skill", style="cyan")
    table.add_column("Chunks", justify="right")
    table.add_column("Domains")
    for name, info in stats["skills"].items():
        table.add_row(name, str(info["chunks"]), ", ".join(info["domains"][:4]))

    console.print(table)
    console.print(
        f"\nTotal chunks: {stats['total_chunks']} | "
        f"Indexed: {'✓' if stats['indexed'] else '✗ — run maestro index'}"
    )


@main.command()
@click.confirmation_option(prompt="Delete all indexed data?")
def clear() -> None:
    """Clear the index."""
    import shutil
    p = Config.load().vectordb_path
    if p.exists():
        shutil.rmtree(p)
        console.print("[green]Index cleared.[/]")
    else:
        console.print("[yellow]No index found.[/]")


def _display_results(response: SearchResponse) -> None:
    if not response.results:
        console.print("[yellow]No results.[/]")
        return

    console.print(f"\n[bold]Results for:[/] {response.query}")
    if response.expanded_terms:
        console.print(f"[dim]Expanded: +{', '.join(response.expanded_terms)}[/]")
    console.print(
        f"[dim]Skills: {', '.join(response.skills_used)} | "
        f"{response.time_ms:.0f}ms | "
        f"{'cached' if response.from_cache else 'fresh'}[/]\n"
    )

    for i, r in enumerate(response.results, 1):
        bar_filled = int(r.final_score * 20)
        score_bar = "█" * bar_filled + "░" * (20 - bar_filled)
        console.print(
            f"[bold]{i}.[/] [{r.chunk.skill}] [cyan]{r.chunk.file}[/] — "
            f"{r.chunk.section}"
        )
        console.print(f"   [green]{score_bar}[/] {r.final_score:.3f}")
        preview = r.chunk.text[:200].replace("\n", " ")
        console.print(f"   [dim]{preview}...[/]\n")


if __name__ == "__main__":
    main()
