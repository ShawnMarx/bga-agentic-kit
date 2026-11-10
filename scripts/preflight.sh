#!/usr/bin/env bash
# The pre-deploy gate. Run from the game repo root; chain it to the deploy with && (never ;):
#
#   ~/repos/bga-agentic-kit/scripts/preflight.sh && ~/repos/bga-agentic-kit/tools/bga-session-manager/deploy.sh …
#
# Each check exists because the one before it let a broken build reach a live table:
#   node --check        parses only — misses undefined names                     (2026-08-31)
#   eslint no-undef     resolves identifiers — misses this.helper() on the wrong class
#   check_state_scope   state class calling a Game method on itself              (2026-09-08)
#   php -l              server parse error takes the whole table down before your code runs
#   cssnano             a bad selector survives the browser but kills the BGA BUILD (2026-09-12)
#
# Skips any check whose files are absent. Override paths with JS=… CSS=… env vars.
set -euo pipefail
kit="$(cd "$(dirname "$0")/.." && pwd)"
JS="${JS:-modules/js/Game.js}"
CSS="${CSS:-$(ls *.css 2>/dev/null | head -1)}"
ESLINT_CFG="${ESLINT_CFG:-$( [ -f eslint.config.mjs ] && echo eslint.config.mjs || echo "$kit/templates/game-repo/eslint.config.mjs")}"

step() { printf '\n▸ %s\n' "$*"; }

if [ -f "$JS" ]; then
  step "node --check $JS";            node --check "$JS"
  step "eslint no-undef $JS";         npx --yes eslint@9 --no-config-lookup -c "$ESLINT_CFG" "$JS"
  step "state-class scope $JS";       python3 "$kit/scripts/check_state_scope.py" "$JS"
fi
php_files=$(git ls-files -m -o --exclude-standard -- '*.php' 2>/dev/null || true)
[ -n "${PHP_ALL:-}" ] && php_files=$(git ls-files -- '*.php')
if [ -n "$php_files" ]; then
  step "php -l (changed files; PHP_ALL=1 for all)"
  for f in $php_files; do php -l "$f" >/dev/null || { php -l "$f"; exit 1; }; done
  echo "ok"
fi
if [ -n "$CSS" ] && [ -f "$CSS" ]; then
  step "cssnano $CSS (what the BGA build runs)"
  npx --yes -p postcss-cli@11 -p cssnano@7 -p postcss@8 postcss "$CSS" --use cssnano --no-map -o /dev/null
  echo "ok"
fi
printf '\n✔ preflight passed\n'
