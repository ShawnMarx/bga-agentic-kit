#!/usr/bin/env bash
# Launcher for the session-manager Python scripts.
#
# Loads config (see _config.sh), points BGA_SM_RUNTIME at the local, never-synced runtime
# (venv, browser profile, cookies, logs) and runs the script with that runtime's venv python,
# from this folder so the scripts can import bga_session.py as a sibling.
#
#   ./bga.sh login.py
#   ./bga.sh find_table.py
#   ./bga.sh capture.py "<table url>" --enter-game --clear-cache --dump "<css>"
#   ./bga.sh drive.py   "<table url>" --enter-game --steps steps.json
#
# One-time setup: ./setup.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_config.sh
source "$here/_config.sh"
PY="$BGA_SM_RUNTIME/venv/bin/python"
[ -x "$PY" ] || { echo "No venv at $PY — run $here/setup.sh first" >&2; exit 1; }
cd "$here"
exec "$PY" "$@"
