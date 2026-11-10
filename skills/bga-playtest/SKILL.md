---
name: bga-playtest
description: Drive a real BGA Studio table with Playwright to reproduce or verify a bug — create or resume a (solo or multi-seat) table, step it through the game by state machine, read the status bar and gamestate, and force-quit a stuck or finished table. Use when asked to playtest, verify a fix in-game, reproduce a report from a live table, reach a specific game state, or when a Studio table is stuck / "already in progress".
---

# Playtesting on BGA Studio

There is no local way to run a BGA game. Verifying anything in-game means driving a real Studio
table. This skill is the procedure that works, plus the traps that cost time. Examples labelled
*(Reckoners)* come from the game this kit was built on — substitute your own state and selector
names.

**Before driving:** deploy and pass the preflight gate (`bga-studio-loop`). A Studio table runs the
files on Studio **now**; alpha/beta players run a frozen build that a deploy does not change, so a fix
verified here is not yet a fix for testers.

## The runtime

`$KIT` is your kit checkout; config comes from `$KIT/bga.local.env` (see `bga-studio-loop`).

```bash
B="$KIT/tools/bga-session-manager/bga.sh"
"$B" login.py              # once, a human at the keyboard; nothing runs until this is done
"$B" find_table.py         # candidate table URLs on the account
"$B" drive.py "<table url>" --enter-game --clear-cache --steps steps.json
"$B" "$PWD/my_script.py"   # your own script: ABSOLUTE path (bga.sh cds into the harness dir)
```

Scripts import `bga_session.py` as a sibling (`bga.sh` `cd`s there), or add
`$KIT/tools/bga-session-manager` to `sys.path` — `scripts/playtest_lib.py` in this skill does that
and gives `gameframe()`, a state probe, and an exact-text button click. `S.launch_context(pw)` is a
**persistent** profile: one script at a time can hold it.

## The loop: branch on `gamestate.name`

A flat step list cannot drive a branching turn cycle — click a button that isn't on screen and the
run burns its budget on nothing. Drive by state:

```json
[{"drive_until": {"state": "gameEnd", "max_iters": 120},
  "on": {"PurchaseEquipment": [{"click_text": "Done buying"}],
         "RollDice":          [{"click_text": "Keep all & finish"}]}}]
```
*(state names: Reckoners)*

Each iteration reads `gameui.gamedatas.gamestate.name`, runs the mapped steps, and waits out
unmapped states (automatic `GAME` states). It reports a state that has not advanced in 5
iterations, listing the buttons actually on screen. Sub-steps take `"required": false`. Full verb
list: the docstring at the top of `drive.py`.

Writing your own loop instead, keep the same discipline:

- **Act, wait, re-read.** Track the previous state; **abort after N identical iterations, printing
  the buttons on screen.** A stall must be diagnosable, not a silent hang.
- **Stop on `gameEnd`**, or the loop spins on a finished table with no seat active. A driver that
  never makes real moves often *loses* within a few rounds — plan for it.
- **Keep one browser alive for the whole run.** Reloading `tableview` costs ~15s and discards any
  client-side staging (a half-built selection, a cost basket).
- **Probing a transition:** read the client's fields several times at ~0.7s intervals right after
  the triggering click. One read after a fixed wait hides a transient; one read before the state
  lands looks like a bug.

## The five traps that look like game bugs

1. **Clicking the prompt, not the button.** Playwright `text=Foo` also matches the status-bar
   title, and prompts routinely contain their own button's words (*"Finish rolling now?"* vs the
   `Finish rolling` button). Match action buttons by **exact** `innerText` (`click_button()` in
   `playtest_lib.py`). Labels can carry glyphs (`Start Next Round ▶`) — read the real text first.
2. **Evaluating in the wrong frame.** `#generalactions`, the player boards and the board live in the
   **game iframe**. Evaluating on the top page returns nothing, which reads like a missing element.
   Find the frame exposing `window.gameui`.
3. **Reading your client off `window.gameui`.** On the modern skeleton, `gameui` is the framework's
   Gamegui: fine for `gamedatas.gamestate`, but your game's own fields and helpers live on
   **`window.g_sitecore.GameModule`**. Off `gameui` they read as empty arrays and `null` — a client
   that looks like it lost its data. And `gamedatas` is the **page-load** snapshot; read live values
   off `GameModule`.
4. **An empty button list is not a stall** in a board-first game — the answer is a click on the
   board. Know which states wait on board clicks.
5. **A preselected option plus an always-visible Confirm.** A loop that clicks Confirm whenever
   present takes the default, not the choice you wanted. Click the choice until the title reflects
   it, then Confirm.

## Table lifecycle (summary)

Create from `https://studio.boardgamearena.com/lobby?game=$BGA_GAME_ID` → `Express start` →
`Go to game` → reuse `tableview?table=<id>` for every later run. Quit with **Express stop** on
`table?table=<id>&nr=true`. Stuck table ("Gameserver is locked by configuration"): try to Create in
the lobby and follow the "already in progress" error's link, then Express stop.

The lobby is stateful and full of traps — remembered seat counts, unstarted tables that silently
disable Create, asynchronously-saved options, decoy hrefs. **Read
[`reference/table-lifecycle.md`](reference/table-lifecycle.md) before creating a table**, and for
multi-seat driving from one login.

## Reading the table

[`reference/reading-the-table.md`](reference/reading-the-table.md): the state probe, button colour
audits, zoom-scaled measurements, the per-session action lock, reading the main-site table record,
and phone emulation.

## Testing without the right roll

[`reference/testing-aids.md`](reference/testing-aids.md): debug constants and debug actions to reach
a state cheaply, stubbing `performAction` to verify a client flow without sending it, and staging
client state — and how to report what was staged vs. proven in play.

## Hygiene

- **Tables do not wait.** An idle Studio table can end itself or vanish (*"Unable to find table
  database"*), and **cutting a build can take open tables with it**. Verify in the run that reached
  the state; expect to rebuild after a break.
- **A table you did not create may be someone else's** (a teammate testing the same deploy). Read the
  log (`#logs`) before attributing server-side changes to your run; ask before stopping a table you
  didn't start, unless your project has said Studio tables are disposable.
- **Kill your headless browsers.** A timed-out run leaves Chromium behind; two sets can exhaust
  memory. Check `ps -axo pid,rss,command | grep ms-playwright`. Keep to one context, two pages.
- **Report what you verified, precisely:** "driven on a real table", "staged client-side", or
  "server guard called directly" are different claims.
