#!/usr/bin/env bash
# Deploy files from your game repo to its BGA Studio project over SFTP (key auth).
#
# Needs an ~/.ssh/config Host block (alias from BGA_SFTP_HOST_ALIAS, default `bga-studio`):
#   Host bga-studio
#     HostName 1.studio.boardgamearena.com
#     Port 2022
#     User <your-studio-user>
#     IdentityFile ~/.ssh/id_ed25519_bga        # a DEDICATED key, registered at
#     IdentitiesOnly yes                         # studio.boardgamearena.com/controlpanel
#
# Usage (paths are relative to the game repo root):
#   deploy.sh modules/js/Game.js
#   deploy.sh modules/php/States/RollDice.php modules/php/Game.php
#   deploy.sh --mkdir img/newfolder        # `put` does NOT create remote dirs — do this first
#   deploy.sh --delete modules/php/States/OldState.php
#
# After deploying, hard-refresh the game page (Cmd/Ctrl+Shift+R) — BGA caches .js/.css hard.
# Run the preflight gate first and chain with && (never ;):  preflight.sh && deploy.sh …
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_config.sh"

[ -n "${BGA_PROJECT:-}" ]   || { echo "BGA_PROJECT not set (bga.local.env / .bga.env)" >&2; exit 2; }
[ -d "${BGA_GAME_REPO:-}" ] || { echo "BGA_GAME_REPO not set or missing: '${BGA_GAME_REPO:-}'" >&2; exit 2; }

mode=put; files=()
while [ $# -gt 0 ]; do
  case "$1" in
    --delete) mode=rm ;;
    --mkdir)  mode=mkdir ;;
    -*) echo "Unknown flag: $1" >&2; exit 2 ;;
    *)  files+=("$1") ;;
  esac
  shift
done
[ ${#files[@]} -gt 0 ] || { echo "No files given. Example: deploy.sh modules/js/Game.js" >&2; exit 2; }

batch=""
for f in "${files[@]}"; do
  rel="${f#/}"; rel="${rel#./}"; remote="$BGA_REMOTE_ROOT/$rel"
  case "$mode" in
    rm)    batch+="rm $remote"$'\n' ;;
    mkdir) batch+="-mkdir $remote"$'\n' ;;
    put)   [ -f "$BGA_GAME_REPO/$rel" ] || { echo "Local file not found: $BGA_GAME_REPO/$rel" >&2; exit 1; }
           batch+="put \"$BGA_GAME_REPO/$rel\" $remote"$'\n' ;;
  esac
done
batch+="bye"$'\n'

echo "→ $BGA_SFTP_HOST_ALIAS:$BGA_REMOTE_ROOT ($mode, ${#files[@]} file(s))"
printf '%s' "$batch" | sftp -o BatchMode=yes -o StrictHostKeyChecking=accept-new -b - "$BGA_SFTP_HOST_ALIAS"
