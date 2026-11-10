"""Load a BGA Studio URL with the saved session and capture diagnostics:
console messages, uncaught page errors, visible error banners, and (optionally)
the Studio dev-log popups ("BGA unexpected exceptions logs", "BGA request&SQL logs").

Run:
  <venv>\\Scripts\\python.exe capture.py "<url>" [--headed] [--wait N] [--studio-logs]

Writes a timestamped file under <runtime>/logs and prints a summary to stdout.
"""
import sys
import time
import shutil
import datetime
from playwright.sync_api import sync_playwright
import bga_session as S

# Windows consoles default to cp1252 and choke on game glyphs; print UTF-8 safely.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def clear_http_cache():
    """Delete the persistent profile's HTTP caches (keeps cookies/login) so we always
    fetch fresh game JS/CSS. BGA caches aggressively; stale JS hides code changes."""
    prof = S.profile_dir()
    for sub in ["Default/Cache", "Default/Code Cache", "Default/GPUCache",
                "GPUCache", "ShaderCache", "GrShaderCache"]:
        p = prof / sub
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

STUDIO_LOG_BUTTONS = [
    "BGA unexpected exceptions logs",
    "BGA request&SQL logs",
]


def grab_studio_log(ctx, page, label):
    """Click a Studio dev-log button and return its text (handles popup or same-tab)."""
    try:
        loc = page.get_by_text(label, exact=False)
        if loc.count() == 0:
            return "(button not found on page)"
        try:
            with ctx.expect_page(timeout=4000) as pop_info:
                loc.first.click()
            pop = pop_info.value
            pop.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            txt = pop.evaluate("() => document.body ? document.body.innerText.slice(0, 6000) : ''")
            pop.close()
            return txt
        except Exception:
            # Maybe it navigated in the same tab instead of opening a popup.
            time.sleep(2)
            txt = page.evaluate("() => document.body ? document.body.innerText.slice(0, 6000) : ''")
            try:
                page.go_back()
            except Exception:
                pass
            return txt
    except Exception as e:
        return f"(could not capture: {e})"


def main():
    if len(sys.argv) < 2:
        print('usage: capture.py "<url>" [--headed] [--wait N] [--studio-logs]')
        sys.exit(2)

    url = sys.argv[1]
    headed = "--headed" in sys.argv
    studio_logs = "--studio-logs" in sys.argv
    wait_s = 8
    if "--wait" in sys.argv:
        wait_s = int(sys.argv[sys.argv.index("--wait") + 1])

    if "--clear-cache" in sys.argv:
        clear_http_cache()

    console_msgs = []
    page_errors = []

    def on_console(msg):
        try:
            console_msgs.append(f"[{msg.type}] {msg.text}")
        except Exception:
            pass

    def on_pageerror(err):
        page_errors.append(str(err))

    with sync_playwright() as p:
        ctx = S.launch_context(p, headless=not headed)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("console", on_console)
        page.on("pageerror", on_pageerror)
        ctx.on("page", lambda pg: (pg.on("console", on_console), pg.on("pageerror", on_pageerror)))

        page.goto(url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=wait_s * 1000)
        except Exception:
            pass
        time.sleep(wait_s)

        # Studio table?table= URLs land on the lobby; follow "Go to game" into the
        # actual game view (where the dev-log buttons + game console live).
        if "--enter-game" in sys.argv:
            try:
                link = page.get_by_text("Go to game", exact=False)
                if link.count() > 0:
                    try:
                        with ctx.expect_page(timeout=8000) as pop_info:
                            link.first.click()
                        page = pop_info.value  # game opened in a new tab
                    except Exception:
                        link.first.click()  # same-tab navigation
                    page.wait_for_load_state("domcontentloaded")
                    try:
                        page.wait_for_load_state("networkidle", timeout=wait_s * 1000)
                    except Exception:
                        pass
                    time.sleep(wait_s)
            except Exception:
                pass

        banners = []
        for sel in [".bga-banner", "[class*='error' i]", "#connection_status", ".gamestate_alert", ".banner"]:
            try:
                for el in page.query_selector_all(sel):
                    t = (el.inner_text() or "").strip()
                    if t and t not in banners:
                        banners.append(f"({sel}) {t}")
            except Exception:
                pass

        title = page.title()
        body_snippet = page.evaluate("() => document.body ? document.body.innerText.slice(0, 1500) : ''")

        dev_logs = {}
        if studio_logs:
            for label in STUDIO_LOG_BUTTONS:
                dev_logs[label] = grab_studio_log(ctx, page, label)

        # --dump "<css selector>": print matching elements (tag/class/text) — handy for
        # verifying UI state (status bar title, action buttons, game pieces).
        dumps = []
        if "--dump" in sys.argv:
            sel = sys.argv[sys.argv.index("--dump") + 1]
            # BGA renders the game inside an iframe, so search ALL frames, not just top.
            for fr in page.frames:
                try:
                    for el in fr.query_selector_all(sel):
                        try:
                            cls = el.get_attribute("class") or ""
                            tag = el.evaluate("e => e.tagName.toLowerCase()")
                            txt = (el.inner_text() or "").strip().replace("\n", " ")[:100]
                            dumps.append(f"<{tag} class='{cls}'> {txt}")
                        except Exception:
                            pass
                except Exception:
                    pass

        shot_path = None
        if "--screenshot" in sys.argv:
            shot_path = S.logs_dir() / f"shot-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
            try:
                page.screenshot(path=str(shot_path), full_page=True)
            except Exception as e:
                shot_path = f"(screenshot failed: {e})"

        ctx.close()

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = S.logs_dir() / f"capture-{ts}.txt"
    lines = [f"URL: {url}", f"TITLE: {title}"]
    lines.append("\n== PAGE ERRORS (uncaught JS) ==")
    lines += page_errors or ["(none)"]
    lines.append("\n== CONSOLE ==")
    lines += console_msgs or ["(none)"]
    lines.append("\n== ERROR BANNERS ==")
    lines += banners or ["(none)"]
    for label, txt in dev_logs.items():
        lines.append(f"\n== STUDIO LOG: {label} ==")
        lines.append(txt or "(empty)")
    if "--dump" in sys.argv:
        lines.append(f"\n== DUMP ({sys.argv[sys.argv.index('--dump') + 1]}) ==")
        lines += dumps or ["(no matches)"]
    lines.append("\n== BODY (first 1500 chars) ==")
    lines.append(body_snippet)

    text = "\n".join(lines)
    out.write_text(text, encoding="utf-8")
    print(text[:5000])
    print(f"\n[full output saved to {out}]")
    if "--screenshot" in sys.argv:
        print(f"[screenshot: {shot_path}]")


if __name__ == "__main__":
    main()
