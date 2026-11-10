"""One-time (occasional) interactive login to BGA Studio.

Opens a real browser window. You log in by hand, then CLOSE the window (or it
auto-detects a logged-in cookie). The session is persisted to the local runtime
profile and reused by capture.py. No password is ever read or stored by this script.

Run:  ./bga.sh login.py
"""
import sys
import time
from playwright.sync_api import sync_playwright
import bga_session as S


LOBBY = S.lobby_url()   # set BGA_GAME_ID so this is your game's lobby
LOBBY_PATH = LOBBY.split("boardgamearena.com", 1)[1].split("?", 1)[0]   # "/lobby" or "/studio"


def logged_in(page) -> bool:
    # Studio's own answer, read off the user's window: a logged-out Studio sends the lobby to
    # /account?warn (from JavaScript, seconds after load) and the header names you "Visitor-NNN".
    # Every cookie-based test failed on 2026-09-19 — "any *sso_user" matched the persistent MAIN-site
    # cookie, launch_context() re-injects the last Studio pair from cookies.json, and a real login
    # came back with the SAME sso_id, so neither presence nor change of a cookie means anything.
    u = page.url
    if "/account" in u:
        return False
    if LOBBY_PATH not in u:
        page.goto(LOBBY, wait_until="domcontentloaded")   # the post-login redirect went elsewhere
        return False
    name = page.evaluate("() => (document.querySelector('#connected_username, #topbar_user_name')||{}).innerText || ''")
    return "Visitor" not in name


def main():
    with sync_playwright() as p:
        ctx = S.launch_context(p, headless=False)
        closed = {"v": False}
        ctx.on("close", lambda: closed.__setitem__("v", True))

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(LOBBY, wait_until="domcontentloaded")
        print("A browser window opened.", flush=True)
        print(">>> The window opens on your game's Studio lobby. If it asks you to log in, do; it closes itself once the lobby loads. <<<", flush=True)
        print("(Waiting up to 15 minutes; also auto-detects login.)", flush=True)

        deadline = time.time() + 900
        ok = False
        streak = 0
        while time.time() < deadline:
            if closed["v"]:
                # The window closed without the sso cookie ever appearing: NOT a login. (Until
                # 2026-09-17 this counted as success and printed LOGIN OK over an empty profile.)
                print("Window closed before a login cookie appeared — NOT logged in.", flush=True)
                break
            try:
                # Four in a row, 3s apart: the logged-out redirect can land 5-9s after load.
                if logged_in(page):
                    streak += 1
                    if streak >= 4:
                        ok = True
                        break
                else:
                    streak = 0
            except Exception:
                break  # context/window gone before login was seen
            time.sleep(3)

        if ok:
            # Snapshot EVERY BGA cookie. The *_sso_user / *_sso_id pair is session-only and the game
            # server needs it; launch_context() re-injects this file on every launch (2026-09-17).
            try:
                import json
                time.sleep(4)  # let the post-login redirect finish setting cookies
                ck = [c for c in ctx.cookies() if "boardgamearena" in c.get("domain", "")]
                (S.runtime_dir() / "cookies.json").write_text(json.dumps(ck), encoding="utf-8")
                print(f"saved {len(ck)} cookies to cookies.json", flush=True)
            except Exception as e:
                print(f"cookie snapshot failed: {e}", flush=True)

        # Best-effort: dump cookie names (to tune detection) and close cleanly.
        try:
            names = sorted({c.get("name", "") for c in ctx.cookies()})
            (S.logs_dir() / "cookies-after-login.txt").write_text("\n".join(names), encoding="utf-8")
        except Exception:
            pass
        try:
            ctx.close()
        except Exception:
            pass

        print("LOGIN OK — session saved." if ok else "LOGIN TIMEOUT.")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
