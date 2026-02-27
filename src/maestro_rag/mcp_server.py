"""
MCP Server with auto-indexing.

When Claude Code calls search_skills for the first time, the engine
automatically indexes all skills in ~/.maestro/skills/.
No manual `maestro index` step needed.

Setup:
    .claude/mcp.json → { "mcpServers": { "maestro": { "command": "maestro-mcp" } } }
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .engine import MaestroEngine, Config

TOOLS = [
    {
        "name": "search_skills",
        "description": (
            "Search the indexed skill knowledge base. Returns relevant chunks "
            "about Swift, SwiftUI, concurrency, testing, architecture, performance, "
            "security, and any other domain covered by installed skills. "
            "Auto-indexes on first call if no index exists. "
            "Use this BEFORE writing or reviewing code to get expert knowledge."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Describe what you need. Be specific: "
                        "'Sendable conformance for actor classes' not just 'concurrency'. "
                        "Include context: 'SwiftUI @Observable state in view model'. "
                        "For compound tasks, call multiple times with focused queries."
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results (default: 7, max: 15)",
                    "default": 7,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "reindex_skills",
        "description": (
            "Force re-indexation of all skills. Use when skills are added, removed, "
            "or updated."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Override skill directories to index",
                },
            },
        },
    },
    {
        "name": "skill_status",
        "description": (
            "Show indexed skills, chunk counts, domains, and whether the index "
            "needs a refresh."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def run_mcp_server() -> None:
    """Stdio JSON-RPC MCP server with auto-indexing."""
    config = Config.load()
    engine = MaestroEngine(config)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        rid = req.get("id")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "maestro-rag", "version": "1.0.0"},
                },
            }
        elif method == "notifications/initialized":
            resp = {"jsonrpc": "2.0", "id": rid, "result": {}}
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            text = _handle(engine, config, name, args)
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {"content": [{"type": "text", "text": text}]},
            }
        else:
            resp = {"jsonrpc": "2.0", "id": rid, "result": {}}

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


def _handle(engine: MaestroEngine, config: Config, name: str, args: dict) -> str:
    if name == "search_skills":
        query = args.get("query", "")
        top_k = min(args.get("top_k", 7), 15)
        response = engine.search(query, top_k=top_k)

        if not response.results:
            status = engine.status()
            if not status["indexed"]:
                return (
                    "No skills indexed yet. Make sure skills are in ~/.maestro/skills/ "
                    "or ~/.claude/skills/ and try again."
                )
            skills_list = list(status["skills"].keys())
            return f"No results for: {query}. Indexed skills: {skills_list}"

        context = response.as_context(max_tokens=4000)
        meta = (
            f"Found {len(response.results)} results from "
            f"{', '.join(response.skills_used)} "
            f"({response.time_ms:.0f}ms"
            f"{', cached' if response.from_cache else ''})"
        )
        if response.expanded_terms:
            meta += f"\nConcepts added: {', '.join(response.expanded_terms)}"
        return f"{meta}\n\n{context}"

    elif name == "reindex_skills":
        paths = [Path(p) for p in args.get("paths", [])] or None
        stats = engine.index(paths, force=True)
        lines = [
            f"Indexed {stats['skills']} skills, {stats['chunks']} chunks "
            f"in {stats['duration_s']}s"
        ]
        for err in stats.get("errors", []):
            lines.append(f"  ⚠ {err}")
        return "\n".join(lines)

    elif name == "skill_status":
        s = engine.status()
        lines = [
            f"Indexed: {'yes' if s['indexed'] else 'NO — will auto-index on first search'}",
            f"Total chunks: {s['total_chunks']}",
            "",
        ]
        for skill_name, info in s["skills"].items():
            domains_str = ", ".join(info["domains"][:3])
            lines.append(f"  {skill_name}: {info['chunks']} chunks ({domains_str})")
        return "\n".join(lines)

    return f"Unknown tool: {name}"


def main() -> None:
    run_mcp_server()


if __name__ == "__main__":
    main()
