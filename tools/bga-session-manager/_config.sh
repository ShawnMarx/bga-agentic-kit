# Sourced by bga.sh / deploy.sh / preflight.sh. Loads the gitignored per-machine config.
#
# Lookup order (first found wins; env vars already set always win over the file):
#   1. $BGA_ENV_FILE                       (point at a per-game file when you have several games)
#   2. <game repo>/.bga.env                (the repo you are standing in, if it has one)
#   3. <kit root>/bga.local.env            (the kit's own machine-wide default)
_kit_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
_here_repo="$(git rev-parse --show-toplevel 2>/dev/null || true)"
for _f in "${BGA_ENV_FILE:-}" "${_here_repo:+$_here_repo/.bga.env}" "$_kit_root/bga.local.env"; do
  if [ -n "$_f" ] && [ -f "$_f" ]; then
    # Only set variables not already exported, so `BGA_PROJECT=x ./deploy.sh …` still overrides.
    while IFS='=' read -r _k _v; do
      case "$_k" in ''|\#*) continue ;; esac
      _k="${_k//[[:space:]]/}"
      _v="${_v%\"}"; _v="${_v#\"}"
      [ -z "${!_k:-}" ] && export "$_k=${_v/#\~/$HOME}"
    done < "$_f"
    export BGA_CONFIG_LOADED="$_f"
    break
  fi
done
export BGA_SM_RUNTIME="${BGA_SM_RUNTIME:-$HOME/.bga-session-manager}"
export BGA_GAME_REPO="${BGA_GAME_REPO:-$_here_repo}"
export BGA_REMOTE_ROOT="${BGA_REMOTE_ROOT:-/${BGA_PROJECT:-}}"
export BGA_SFTP_HOST_ALIAS="${BGA_SFTP_HOST_ALIAS:-bga-studio}"
