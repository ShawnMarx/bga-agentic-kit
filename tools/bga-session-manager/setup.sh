#!/usr/bin/env bash
# One-time setup of the local runtime (venv + Playwright Chromium). Safe to re-run.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
source "$here/_config.sh"
rt="$BGA_SM_RUNTIME"
mkdir -p "$rt"
[ -x "$rt/venv/bin/python" ] || python3 -m venv "$rt/venv"
"$rt/venv/bin/python" -m pip install -q -r "$here/requirements.txt"
"$rt/venv/bin/python" -m playwright install chromium
echo "Runtime ready at $rt. Next: $here/bga.sh login.py  (and login_main.py if you need bug reports/replays)"
