#!/usr/bin/env bash
# Start a new BGA game repo from the kit templates.
#   new-game.sh <dir> <studio project name> [<studio game id>]
#
# Expects <dir> to be empty or to hold the skeleton BGA Studio generated for the project
# (download it over SFTP first — see docs/playbook/new-game-checklist.md). Never overwrites a file.
set -euo pipefail
kit="$(cd "$(dirname "$0")/.." && pwd)"
dir="${1:?usage: new-game.sh <dir> <project> [game id]}"; project="${2:?project name required}"; gid="${3:-}"
mkdir -p "$dir"; cd "$dir"
[ -d .git ] || git init -q -b main
put() { [ -e "$2" ] && echo "keep $2 (exists)" || { mkdir -p "$(dirname "$2")"; cp "$1" "$2"; echo "add  $2"; }; }
t="$kit/templates/game-repo"
put "$t/CLAUDE.md" CLAUDE.md
put "$t/gitignore" .gitignore
put "$t/TODO.md" TODO.md
put "$t/misc/claude-handoff.md" misc/claude-handoff.md
put "$t/eslint.config.mjs" eslint.config.mjs
if [ ! -e .bga.env ]; then
  printf 'BGA_PROJECT=%s\nBGA_GAME_ID=%s\nBGA_GAME_REPO=%s\n' "$project" "$gid" "$(pwd)" > .bga.env; echo "add  .bga.env (gitignored)"
fi
sed -i.bak "s#<path to kit>#$kit#; s#<project>#$project#g; s#<game id>#${gid:-<game id>}#g" CLAUDE.md && rm -f CLAUDE.md.bak
"$kit/scripts/install-skills.sh" "$(pwd)"
echo
echo "Next: fill in the <…> placeholders in CLAUDE.md, then follow $kit/docs/playbook/new-game-checklist.md"
