"""Drive a BGA Studio table: click through the game, dump state, take screenshots.

The companion to capture.py, which only *observes*. drive.py runs a list of steps
against the live game frame, so a state can actually be reached and photographed.

Run:
  ./bga.sh drive.py "<table url>" --steps steps.json [--enter-game] [--clear-cache]
                    [--headed] [--wait N] [--out DIR] [--keep-open]
  ./bga.sh drive.py "<table url>" --step 'click=#button_roll' --step 'wait=2' \
                    --step 'shot=#game_play_area'

A steps file is a JSON list; each step is one {verb: value, ...} object:

  [ {"note":  "roll and keep everything"},
    {"click": "#button_roll"},
    {"wait_for": "#button_keep_all"},
    {"click_text": "Keep all"},
    {"wait":  2},
    {"dump":  "#pagemaintitletext, .action-button"},
    {"expect": "#pagemaintitletext", "text": "Use your dice"},
    {"shot":  "#game_play_area", "name": "board-after-roll"},
    {"eval":  "() => window.gameui.gamedatas.gamestate.name"} ]

Verbs
  note       — log a line (structure the transcript)
  click      — CSS selector, clicked in the game frame
  click_text — visible text, clicked in the game frame (BGA action buttons)
  wait       — seconds
  wait_for   — CSS selector, waits until visible
  dump       — CSS selector; prints every match's tag/class/text (all frames)
  expect     — CSS selector (+ optional "text"); records PASS/FAIL, aborts on FAIL
               unless --continue-on-fail
  shot       — CSS selector for a per-element PNG, or "" / omit for the viewport
  eval       — JS expression evaluated in the game frame; result logged (JSON, truncated
               at 2000 chars — raise it with "max_chars": N on the step)
  drive_until— state-driven loop, for games whose turn cycle branches. Pairs with "on":
               {"drive_until": {"state": "gameEnd", "max_iters": 60},
                "on": {"PurchaseEquipment": [{"click_text": "Done buying"}],
                       "RollDice":          [{"click_text": "Keep all & finish"}]}}
               Each iteration reads gamedatas.gamestate.name, runs the steps mapped to it,
               and settles. Unmapped states are waited out (useful for automatic GAME states).
               "state" may be a list. A failing sub-step ends that iteration unless it carries
               "required": false. Returns failure if max_iters is exhausted.

Every step also accepts "frame": "page" to act on the top-level page instead of the
game frame, and "timeout": seconds to override the 15s default.

Console messages and uncaught JS errors are collected for the whole run and printed
at the end, the same as capture.py.
"""
import argparse
import datetime
import json
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
import bga_session as S

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_TIMEOUT = 15.0

# A frame is the game frame if it contains one of these — BGA's own chrome, present
# in every game — so this stays game-agnostic.
GAME_FRAME_MARKERS = ["#pagemaintitletext", "#game_play_area", "#page-title"]


def clear_http_cache():
    """Drop the profile's HTTP caches (keeps cookies) so fresh game JS/CSS is fetched."""
    prof = S.profile_dir()
    for sub in ["Default/Cache", "Default/Code Cache", "Default/GPUCache",
                "GPUCache", "ShaderCache", "GrShaderCache"]:
        p = prof / sub
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def game_frame(page):
    """The frame the game actually renders in — the main page in most Studio views,
    an iframe in others. Falls back to the main frame so a step never silently no-ops."""
    for fr in page.frames:
        for marker in GAME_FRAME_MARKERS:
            try:
                if fr.query_selector(marker):
                    return fr
            except Exception:
                pass
    return page.main_frame


def enter_game(ctx, page, wait_s):
    """Studio ?table= URLs land on the lobby; follow 'Go to game' into the game view."""
    link = page.get_by_text("Go to game", exact=False)
    if link.count() == 0:
        return page
    try:
        with ctx.expect_page(timeout=8000) as pop:
            link.first.click()
        page = pop.value
    except Exception:
        link.first.click()
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=wait_s * 1000)
    except Exception:
        pass
    time.sleep(wait_s)
    return page


def game_state(page):
    """The BGA state machine's current state name, or None if the client isn't up yet.
    This is what makes a branching game loop drivable — see the drive_until verb."""
    try:
        return game_frame(page).evaluate(
            "() => (window.gameui && gameui.gamedatas && gameui.gamedatas.gamestate "
            "&& gameui.gamedatas.gamestate.name) || null")
    except Exception:
        return None


def describe(el):
    try:
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        cls = el.get_attribute("class") or ""
        eid = el.get_attribute("id") or ""
        txt = (el.inner_text() or "").strip().replace("\n", " ")[:120]
        return f"<{tag}{'#' + eid if eid else ''} class='{cls}'> {txt}"
    except Exception as e:
        return f"(unreadable element: {e})"


def load_steps(args):
    steps = []
    if args.steps:
        steps += json.loads(Path(args.steps).read_text(encoding="utf-8"))
    for raw in args.step or []:
        verb, _, val = raw.partition("=")
        verb = verb.strip()
        steps.append({verb: val if verb not in ("wait",) else float(val or 1)})
    return steps


def run_step(i, step, page, ctx, out_dir, log):
    """Execute one step. Returns (ok, page) — page can change if a click opens a tab."""
    target = page if step.get("frame") == "page" else game_frame(page)
    timeout = float(step.get("timeout", DEFAULT_TIMEOUT)) * 1000
    tag = f"[{i:02d}]" if isinstance(i, int) else f"[{i}]"

    if "note" in step:
        log(f"{tag} -- {step['note']}")
        return True, page

    if "wait" in step:
        secs = float(step["wait"])
        log(f"{tag} wait {secs}s")
        time.sleep(secs)
        return True, page

    if "wait_for" in step:
        sel = step["wait_for"]
        try:
            target.wait_for_selector(sel, state="visible", timeout=timeout)
            log(f"{tag} wait_for {sel} -> visible")
            return True, page
        except Exception as e:
            log(f"{tag} wait_for {sel} -> TIMEOUT ({e.__class__.__name__})")
            return False, page

    if "click" in step or "click_text" in step:
        if "click" in step:
            sel, loc = step["click"], target.locator(step["click"])
        else:
            sel, loc = f"text={step['click_text']}", target.get_by_text(step["click_text"], exact=False)
        try:
            loc.first.wait_for(state="visible", timeout=timeout)
            loc.first.click(timeout=timeout)
            log(f"{tag} click {sel} -> ok")
            time.sleep(float(step.get("settle", 1.0)))
            return True, page
        except Exception as e:
            log(f"{tag} click {sel} -> FAILED ({e.__class__.__name__}: {str(e).splitlines()[0]})")
            return False, page

    if "dump" in step:
        sel = step["dump"]
        hits = []
        for fr in page.frames:
            try:
                hits += [describe(el) for el in fr.query_selector_all(sel)]
            except Exception:
                pass
        log(f"{tag} dump {sel} -> {len(hits)} match(es)")
        for h in hits:
            log(f"       {h}")
        return True, page

    if "expect" in step:
        sel, want = step["expect"], step.get("text")
        try:
            el = target.wait_for_selector(sel, state="visible", timeout=timeout)
            got = (el.inner_text() or "").strip()
        except Exception:
            log(f"{tag} expect {sel} -> FAIL (not visible)")
            return False, page
        if want is not None and want.lower() not in got.lower():
            log(f"{tag} expect {sel} ~ {want!r} -> FAIL (got {got[:120]!r})")
            return False, page
        log(f"{tag} expect {sel}{' ~ ' + repr(want) if want else ''} -> PASS")
        return True, page

    if "shot" in step:
        sel = step.get("shot") or ""
        name = step.get("name") or (f"step{i:02d}" if isinstance(i, int) else f"step{i}")
        path = out_dir / f"{name}.png"
        try:
            if sel:
                target.locator(sel).first.screenshot(path=str(path), timeout=timeout)
            else:
                page.screenshot(path=str(path), full_page=bool(step.get("full_page")))
            log(f"{tag} shot {sel or '(viewport)'} -> {path}")
            return True, page
        except Exception as e:
            log(f"{tag} shot {sel or '(viewport)'} -> FAILED ({e.__class__.__name__})")
            return False, page

    if "eval" in step:
        try:
            res = target.evaluate(step["eval"])
            log(f"{tag} eval -> {json.dumps(res, default=str)[:int(step.get('max_chars', 2000))]}")
            return True, page
        except Exception as e:
            log(f"{tag} eval -> FAILED ({e.__class__.__name__}: {str(e).splitlines()[0]})")
            return False, page

    if "drive_until" in step:
        # State-driven loop: read the game state, run the sub-steps mapped to it, repeat.
        # A flat step list cannot drive a game whose turn cycle branches; this can.
        cfg = step["drive_until"]
        stop = cfg.get("state")
        stop_set = {stop} if isinstance(stop, str) else set(stop or [])
        max_iters = int(cfg.get("max_iters", 40))
        settle = float(cfg.get("settle", 2.0))
        on = step.get("on") or {}
        seen_unmapped = set()
        last_state, stuck = None, 0
        for it in range(1, max_iters + 1):
            st = game_state(page)
            # A state that never advances means the mapped steps are clicking the wrong thing.
            # Say so once, with the buttons actually on screen, instead of silently burning
            # every remaining iteration.
            stuck = stuck + 1 if st == last_state else 0
            last_state = st
            if stuck == 5:
                try:
                    btns = game_frame(page).eval_on_selector_all(
                        ".action-button", "els => els.filter(e => e.offsetParent).map(e => e.innerText.trim())")
                except Exception:
                    btns = []
                log(f"{tag}   STALLED in {st!r} for 5 iterations — visible action buttons: {btns}")
            if st is None:
                log(f"{tag}   iter {it}: no game state yet, waiting")
                time.sleep(settle)
                continue
            if st in stop_set:
                log(f"{tag} drive_until reached {st!r} after {it - 1} iteration(s)")
                return True, page
            sub = on.get(st)
            if sub is None:
                if st not in seen_unmapped:
                    log(f"{tag}   iter {it}: state {st!r} has no mapped steps — waiting it out")
                    seen_unmapped.add(st)
                time.sleep(settle)
                continue
            log(f"{tag}   iter {it}: {st}")
            for j, sub_step in enumerate(sub, 1):
                ok, page = run_step(f"{i}.{it}.{j}", sub_step, page, ctx, out_dir, log)
                if not ok and sub_step.get("required", True):
                    break
            time.sleep(settle)
        log(f"{tag} drive_until gave up after {max_iters} iteration(s) in state {game_state(page)!r}")
        return False, page

    log(f"{tag} UNKNOWN STEP {step!r}")
    return False, page


def main():
    ap = argparse.ArgumentParser(description="Drive a BGA Studio table with Playwright.")
    ap.add_argument("url")
    ap.add_argument("--steps", help="JSON file: a list of step objects")
    ap.add_argument("--step", action="append", help="inline step, e.g. 'click=#button_roll'")
    ap.add_argument("--enter-game", action="store_true", help="follow the lobby's 'Go to game'")
    ap.add_argument("--clear-cache", action="store_true", help="drop cached JS/CSS first")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--wait", type=int, default=8, help="seconds to let the app settle on load")
    ap.add_argument("--out", help="directory for screenshots (default: <runtime>/logs/drive-<ts>)")
    ap.add_argument("--continue-on-fail", action="store_true")
    ap.add_argument("--keep-open", action="store_true", help="pause before closing (with --headed)")
    args = ap.parse_args()

    steps = load_steps(args)
    if not steps:
        ap.error("no steps given — use --steps FILE or one or more --step 'verb=value'")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out) if args.out else S.logs_dir() / f"drive-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    lines, console_msgs, page_errors = [], [], []

    def log(msg):
        print(msg, flush=True)
        lines.append(msg)

    def watch(pg):
        pg.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text}"))
        pg.on("pageerror", lambda e: page_errors.append(str(e)))

    if args.clear_cache:
        clear_http_cache()

    failures = 0
    with sync_playwright() as p:
        ctx = S.launch_context(p, headless=not args.headed)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        watch(page)
        ctx.on("page", watch)

        log(f"URL: {args.url}")
        page.goto(args.url, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=args.wait * 1000)
        except Exception:
            pass
        time.sleep(args.wait)

        if args.enter_game:
            page = enter_game(ctx, page, args.wait)
        log(f"TITLE: {page.title()}")
        log(f"OUT:   {out_dir}")

        for i, step in enumerate(steps, 1):
            ok, page = run_step(i, step, page, ctx, out_dir, log)
            if not ok:
                failures += 1
                if not args.continue_on_fail:
                    log("ABORTING (use --continue-on-fail to push through)")
                    break

        if args.keep_open and args.headed:
            input("Press Enter to close the browser...")
        try:
            ctx.close()
        except Exception:
            pass

    lines.append("\n== PAGE ERRORS (uncaught JS) ==")
    lines += page_errors or ["(none)"]
    lines.append("\n== CONSOLE ==")
    lines += console_msgs or ["(none)"]
    for err in page_errors:
        print(f"JS ERROR: {err.splitlines()[0]}")
    transcript = out_dir / "transcript.txt"
    transcript.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{len(steps)} step(s), {failures} failure(s). Transcript: {transcript}")
    print(f"{len(page_errors)} uncaught JS error(s), {len(console_msgs)} console message(s) "
          f"(full text in the transcript).")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
