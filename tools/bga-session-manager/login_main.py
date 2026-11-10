"""One-time (occasional) interactive login to the MAIN BGA site (boardgamearena.com).

Studio and the main site are SEPARATE logins. The Studio session (login.py / cookies.json) drives
tables on studio.boardgamearena.com; the main site is where bug REPORTS and the tables players
actually play -- including private-alpha tables and their replays -- live. Reading a bug report or
a replay with only the Studio session gets "Unable to load this report".

Opens a real browser window. Log in by hand, then CLOSE it (login is also auto-detected). The
main-site cookies are saved to cookies-main.json, which launch_context() injects alongside the
Studio ones. No password is ever read or stored by this script.

Run:  ./bga.sh login_main.py
"""
import sys
import time
from playwright.sync_api import sync_playwright
import bga_session as S


def main_cookies(context):
    """Every cookie belonging to the main site (studio's own domain excluded)."""
    out = []
    for c in context.cookies():
        dom = (c.get("domain") or "").lstrip(".")
        if dom == "boardgamearena.com" or (dom.endswith(".boardgamearena.com") and not dom.startswith("studio.")):
            out.append(c)
    return out


def logged_in(context) -> bool:
    return any("sso_user" in (c.get("name") or "") and c.get("value") for c in main_cookies(context))


def main():
    with sync_playwright() as p:
        ctx = S.launch_context(p, headless=False)
        closed = {"v": False}
        ctx.on("close", lambda: closed.__setitem__("v", True))

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(f"{S.MAIN_BASE}/account", wait_until="domcontentloaded")
        print("A browser window opened.", flush=True)
        print(">>> Log in to boardgamearena.com (the MAIN site), then CLOSE the window. <<<", flush=True)
        print("(Waiting up to 15 minutes; also auto-detects login.)", flush=True)

        deadline = time.time() + 900
        ok = False
        while time.time() < deadline:
            if closed["v"]:
                print("Window closed before a login cookie appeared — NOT logged in.", flush=True)
                break
            try:
                if logged_in(ctx):
                    ok = True
                    break
            except Exception:
                break  # context/window gone before login was seen
            time.sleep(2)

        if ok:
            try:
                import json
                time.sleep(4)  # let the post-login redirect finish setting cookies
                ck = main_cookies(ctx)
                (S.runtime_dir() / "cookies-main.json").write_text(json.dumps(ck), encoding="utf-8")
                print(f"saved {len(ck)} main-site cookies to cookies-main.json", flush=True)
            except Exception as e:
                print(f"cookie snapshot failed: {e}", flush=True)

        try:
            ctx.close()
        except Exception:
            pass

        print("LOGIN OK — main-site session saved." if ok else "LOGIN TIMEOUT.")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
