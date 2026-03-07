#!/usr/bin/env bash
set -euo pipefail
MAESTRO_VENV="$HOME/.maestro/.venv"
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$MAESTRO_VENV/bin/maestro-mcp" ]; then
  python3 -m venv "$MAESTRO_VENV"
  "$MAESTRO_VENV/bin/pip" install -q "$PLUGIN_ROOT"
fi

exec "$MAESTRO_VENV/bin/maestro-mcp" "$@"
