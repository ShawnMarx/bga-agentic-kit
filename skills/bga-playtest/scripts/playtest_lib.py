"""Shared bits for driving a BGA Studio table from your own Playwright script.

Run scripts that import this with the harness venv:

    "$KIT/tools/bga-session-manager/bga.sh" /abs/path/to/my_script.py

and in the script:

    sys.path.insert(0, "<path to this scripts/ dir>")
    from playtest_lib import *
    with sync_playwright() as pw:
        ctx = S.launch_context(pw, headless=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(view_url(TABLE_ID)); page.wait_for_timeout(8000)
        fr = gameframe(page)
        show("start", fr)

Traps this file exists to avoid:

1. A Playwright `text=Foo` selector matches the status-bar TITLE as well as the button, and prompts
   often contain their own button's words. Match buttons by exact innerText.
2. `window.gameui` is the framework's Gamegui. It has `gamedatas` (fine for `gamestate`), but on the
   modern skeleton your client's own state lives on `window.g_sitecore.GameModule`.
3. Everything in-game lives in the game IFRAME, not the top page.
"""
import json
import os
import sys
from pathlib import Path

# Locate the session-manager harness: $BGA_SM_DIR, else the kit layout
# (<kit>/skills/bga-playtest/scripts -> <kit>/tools/bga-session-manager).
_SM = os.environ.get("BGA_SM_DIR") or str(
    Path(__file__).resolve().parents[3] / "tools" / "bga-session-manager")
if _SM not in sys.path:
    sys.path.insert(0, _SM)

from playwright.sync_api import sync_playwright  # noqa: E402,F401
import bga_session as S  # noqa: E402,F401

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = "https://studio.boardgamearena.com"
GAME_ID = os.environ.get("BGA_GAME_ID", "")
TABLE_ID = os.environ.get("BGA_TABLE_ID", "")   # or set in your script


def view_url(table_id, as_player=None):
    u = f"{BASE}/tableview?table={table_id}"
    return u + (f"&as={as_player}" if as_player else "")


def table_url(table_id):
    return f"{BASE}/table?table={table_id}&nr=true"


def lobby_url(game_id=GAME_ID):
    return f"{BASE}/lobby?game={game_id}"


def gameframe(page):
    """The frame exposing window.gameui (the game runs in an iframe)."""
    for f in page.frames:
        try:
            if f.evaluate("() => typeof window.gameui !== 'undefined' && !!window.gameui"):
                return f
        except Exception:
            pass
    return page.main_frame


BUTTONS_SEL = "#generalactions .bgabutton, #generalactions button, .action-button"

STATE_JS = """() => {
    const g = window.gameui && window.gameui.gamedatas;
    const st = (g && g.gamestate) ? g.gamestate : {};
    const btns = Array.from(document.querySelectorAll('%s'))
                      .map(b => (b.innerText || '').trim()).filter(Boolean);
    const title = (document.querySelector('#pagemaintitletext') || {}).innerText || '';
    return {state: st.name, id: st.id, title: title.trim(), buttons: btns};
}""" % BUTTONS_SEL


def state(fr):
    return fr.evaluate(STATE_JS)


def show(label, fr):
    st = state(fr)
    print("[" + label + "] " + json.dumps(st, ensure_ascii=False))
    return st


CLICK_BTN_JS = """(label) => {
    const btns = Array.from(document.querySelectorAll('%s'));
    const hit = btns.find(b => (b.innerText || '').trim() === label);
    if (!hit) return false;
    hit.click();
    return true;
}""" % BUTTONS_SEL


def click_button(fr, label):
    """Click the action button whose text is EXACTLY `label`. Returns True if found."""
    ok = fr.evaluate(CLICK_BTN_JS, label)
    print(("   clicked button: " if ok else "   button not found: ") + label)
    return ok


def click_any(fr, st, labels):
    """Click the first of `labels` that is actually on screen."""
    for label in labels:
        if label in (st.get("buttons") or []):
            if click_button(fr, label):
                return True
    return False


def click_sel(fr, sel, timeout_ms=4000):
    try:
        fr.click(sel, timeout=timeout_ms)
        print("   clicked " + sel)
        return True
    except Exception as e:
        print("   click failed " + sel + ": " + str(e).splitlines()[0])
        return False


def drive(fr, page, handlers, stop=("gameEnd",), poll_ms=2500, stall_limit=8, max_iters=300):
    """State-driven loop. `handlers` maps state name -> fn(fr, st). Unmapped states are waited out.
    Aborts loudly (printing the buttons on screen) after `stall_limit` identical reads."""
    prev, same = None, 0
    for _ in range(max_iters):
        st = state(fr)
        if st.get("state") in stop:
            show("stop", fr)
            return st
        if st == prev:
            same += 1
            if same >= stall_limit:
                print("STALL in", st.get("state"), "- buttons on screen:", st.get("buttons"))
                return st
        else:
            prev, same = st, 0
            show("state", fr)
        fn = handlers.get(st.get("state"))
        if fn:
            fn(fr, st)
        page.wait_for_timeout(poll_ms)
    print("max_iters exhausted")
    return state(fr)
