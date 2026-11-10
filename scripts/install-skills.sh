#!/usr/bin/env bash
# Symlink the kit's skills into a game repo (default) or your user skills dir.
#   install-skills.sh [<game repo>]      → <game repo>/.claude/skills/<skill> -> kit
#   install-skills.sh --user             → ~/.claude/skills/<skill> -> kit
# Symlinks, so `git pull` in the kit updates every game. Existing non-link dirs are left alone.
set -euo pipefail
kit="$(cd "$(dirname "$0")/.." && pwd)"
if [ "${1:-}" = "--user" ]; then dest="$HOME/.claude/skills"; else dest="${1:-$(git rev-parse --show-toplevel)}/.claude/skills"; fi
mkdir -p "$dest"
for s in "$kit"/skills/*/; do
  name="$(basename "$s")"; target="$dest/$name"
  if [ -e "$target" ] && [ ! -L "$target" ]; then echo "skip $name (a real directory exists at $target)"; continue; fi
  ln -sfn "${s%/}" "$target"; echo "linked $target"
done
