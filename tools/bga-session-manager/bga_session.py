"""Shared helpers for the BGA Studio session manager.

Reusable across BGA games. The heavy/secret RUNTIME (venv, persisted login session,
cookie snapshots, logs) lives OUTSIDE the repo and outside any synced folder — by default
~/.bga-session-manager (Windows: %LOCALAPPDATA%\\bga-session-manager). Override with
env BGA_SM_RUNTIME. bga.sh loads bga.local.env / .bga.env into the environment first.
"""
import os
from pathlib import Path

STUDIO_BASE = "https://studio.boardgamearena.com"
MAIN_BASE = "https://boardgamearena.com"


def runtime_dir() -> Path:
    rt = os.environ.get("BGA_SM_RUNTIME")
    if rt:
        return Path(rt).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "bga-session-manager"
    return Path.home() / ".bga-session-manager"


def project() -> str:
    """Studio project name (BGA_PROJECT), e.g. 'mygame'."""
    return os.environ.get("BGA_PROJECT", "")


def lobby_url() -> str:
    """The game's Studio lobby (needs BGA_GAME_ID); falls back to the Studio home page."""
    gid = os.environ.get("BGA_GAME_ID", "").strip()
    return f"{STUDIO_BASE}/lobby?game={gid}" if gid else f"{STUDIO_BASE}/studio"


def profile_dir() -> Path:
    p = runtime_dir() / "profile"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = runtime_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def launch_context(playwright, headless: bool = True):
    """Persistent context => the login session is stored on disk and reused."""
    ctx = playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir()),
        headless=headless,
        viewport={"width": 1500, "height": 950},
        args=["--disable-blink-features=AutomationControlled"],
    )
    # Studio's *_sso_user / *_sso_id cookies are session-only (2026-09-17): the remember-me token keeps
    # the SITE logged in across launches, but the GAME SERVER frame needs the sso pair and answers
    # "Not logged in (studio)" without them. login.py snapshots every BGA cookie to cookies.json;
    # re-inject them here so each launch starts with the full set.
    # cookies-main.json is the MAIN SITE (boardgamearena.com) login, saved by login_main.py. It is a
    # SEPARATE account session from Studio's and lives in its own file so neither login can clobber
    # the other's snapshot; the domains do not overlap, so both sets can be injected together.
    for name in ("cookies.json", "cookies-main.json"):
        cj = runtime_dir() / name
        if not cj.exists():
            continue
        try:
            import json, time
            saved = json.loads(cj.read_text())
            for c in saved:
                if c.get("expires", -1) in (-1, None) or c["expires"] < 0:
                    c["expires"] = time.time() + 30 * 86400
            ctx.add_cookies(saved)
        except Exception as e:  # never block a run on the cookie cache
            print(f"({name} not applied: {e})")
    return ctx
