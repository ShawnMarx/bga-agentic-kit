"""Find active Studio table(s) using the saved session. Scans a few Studio pages
for links containing `table=` and prints candidate table URLs. Throwaway helper."""
import re
import sys
from playwright.sync_api import sync_playwright
import bga_session as S

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PAGES = [
    "https://studio.boardgamearena.com/",
    "https://studio.boardgamearena.com/studio",
    "https://studio.boardgamearena.com/controlpanel",
]

with sync_playwright() as p:
    ctx = S.launch_context(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    found = {}
    for url in PAGES:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2500)
        except Exception as e:
            print(f"(skip {url}: {e})")
            continue
        # collect hrefs and any table ids in page content
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        for h in hrefs:
            if "table=" in h:
                m = re.search(r"table=(\d+)", h)
                if m:
                    found.setdefault(m.group(1), h)
        # also scan raw html for table=NNN
        try:
            html = page.content()
            for m in re.finditer(r"table=(\d+)", html):
                found.setdefault(m.group(1), f"https://studio.boardgamearena.com/table?table={m.group(1)}")
        except Exception:
            pass
    ctx.close()

if not found:
    print("NO TABLES FOUND")
else:
    print("CANDIDATE TABLES:")
    for tid, href in sorted(found.items(), key=lambda kv: -int(kv[0])):
        print(f"  table {tid}: {href}")
