# 06 — Driving a Studio table with Playwright

Game-agnostic findings from building `drive.py` (the `bga-session-manager` harness) and using it
to reproduce and then verify rules bugs in The Reckoners, 2026-08-28. `capture.py` **observes**;
this note is about actually clicking through a game.

## You cannot drive a second seat — use solo instead

The obvious plan for testing an N-player game is a table with N test accounts and a `testuser=`
switch. **It does not work:**

- `tableview?table=<id>&testuser=<player_id>` **ignores the parameter** — `gameui.player_id` stays
  whoever the persisted profile is logged in as, regardless of the value passed.
- The `/N/<game>?table=…&testuser=…` game path answers **"Not logged in (studio)"** when opened
  directly; the game only loads inside the `tableview` iframe.
- There is **no in-page account switcher**. The player names in the panel are ordinary profile
  links (`/player?id=…`).

Driving a second seat therefore needs a **second browser profile logged in as that test account**,
i.e. its password. Avoid the whole problem: if the game has a **solo / multi-handed mode where one
human drives N pieces**, use it. Board setup that keys off "player count" usually keys off that
same N, so a solo-with-N table reproduces the N-player board exactly from one session.

## The table lifecycle

- **Create** from `gamepanel?game=<name>`. The player-count dropdown is a `.bga-dropdown-button`;
  its options are `.bga-dropdown-option`. **Solo is an option labelled "Solo", not "1"** — a
  `/^[1-6]$/` filter silently drops it.
- **Start.** Multiplayer shows *Start* + **Express start** (fills the seats with test accounts and
  starts immediately). Solo shows **Start now** instead — no Express start.
- The panel **remembers the last configuration server-side**, and while a table is in progress the
  creation controls are replaced by *Go to game*, so a leftover table blocks making another.
- **Abandon.** Tables are free; create and throw away rather than trying to rewind one. Most game
  states cannot be reached without committing irreversible actions, so "cancel and restore" buys
  nothing. Quit is hidden in the in-game menu: click `#ingame_menu_quit`, then `#quitgame_confirm`
  ("Leave game") in the `#popin_quitConfirmContent` dialog. Both need a JS `.click()` — Playwright's
  actionability check refuses them as not visible.
- **Schema or setup changes need a fresh table.** `dbmodel.sql` only rebuilds when a game *starts*,
  and setup code only runs once.

## `gamedatas` is a snapshot, not live state

`gameui.gamedatas` is populated by `getAllDatas()` **at page load and never updated by
notifications** — the game client keeps its own live copy (`this.board` and friends). After a
successful action, `gamedatas` still shows the old world: a Reckoner read as being in her previous
district after a move that had visibly succeeded.

- **Read game state from a fresh page load**, or from the DOM, not from `gamedatas` mid-run.
- The **exception is `gamedatas.gamestate.name`**, which the framework *does* keep current. That is
  what makes state-driven driving possible (below).
- The visible game log (`#logs`) holds authoritative narration but only **recent** moves.

## The client instance is not `gameui` — and its state is drivable, safely

`gameui` is BGA's page object. The **game's own class instance** (the one holding `this.board`,
the open menu, the half-built selection) hangs off it under the module name — for The Reckoners,
`gameui.GameModule`. Find it without guessing by scanning for a field you know it has:

```js
Object.keys(gameui).filter(k => gameui[k] && typeof gameui[k] === 'object' && 'hitAt' in gameui[k])
```

This matters because **UI bugs live in fields that appear nowhere else**: not in `gamedatas` (a
load-time snapshot), not in the DOM until they are rendered, and never on the server. Which of
several look-alike states you are in — "collecting costs for an action" vs "paying for a cost
card" — is a client flag, and no amount of code reading tells you which one the reporter was
looking at.

**Opening menus and baskets sends nothing to the server.** Selecting a piece, opening an action
menu, starting a cost basket: all client-only, until something calls `performAction`. So it is
safe to drive these against a **live table someone else is playing**, including in a second
browser session on the same account — set the state, read it, screenshot it, then cancel. Keep to
the client-only verbs and the game is untouched.

Two habits make it decisive rather than suggestive:

- **Assert on `element.className`, not on the screenshot.** `"rk-plantok rk-plantok-live"` versus
  `"… rk-plantok-cost"` is an exact answer to "is the cue applied?"; a picture of a small pill is
  an argument about pixels.
- **Set the suspect state directly** (`G.hitPayFor = <id>; G.render…()`), rather than clicking a
  path six steps long to reach it. The click-path run is the confirmation afterwards.

You can only drive **your own** seat's UI. If the report comes from another player's hand, you
reproduce the *shape* of their state in yours — or ask for a screenshot, which is often the faster
half: theirs identified the exact flag in one glance after two wrong guesses from the code.

## Drive from the state, not from a script

A flat list of clicks cannot drive a game whose turn cycle branches. A conditional state
(a "surrender a die" step that only fires sometimes) parks the script, which then clicks buttons
that are not on screen — silently, because a missing click looks like any other failed step. One
run burned 100 iterations that way.

The working shape (`drive_until` in `drive.py`): a **state → steps map**. Each iteration reads
`gamedatas.gamestate.name`, runs the steps mapped to it, and **waits out unmapped states** — which
is exactly right for automatic `GAME` states that resolve themselves. Two things matter:

- **Report a stalled state.** If the state has not advanced in N iterations, log it once *with the
  action buttons actually on screen*. That one line is the difference between a diagnosable run
  and a mystery.
- **Select buttons distinctively.** `.action-button` first-match is fragile once the page has been
  live for several rounds; prefer the text, or a class that is specific to the state
  (`.action-button.bgabutton_red`).

## Odds and ends

- **The game frame.** The game runs in an iframe of `tableview`. Resolve it by looking for BGA's own
  chrome — `#pagemaintitletext`, `#game_play_area`, `#page-title` — rather than by index.
- **The Studio dev logs are same-origin fetchable.** The buttons live in the game frame and open
  popups, which is awkward to drive. Their hrefs are
  `/<N>/<game>/<game>/logaccess.html?table=<id>[&err=1]`; `fetch()` them from inside the page and
  the session cookie comes along. The exception log is **global, not per-table** — filter it by
  table id or date, and "no matching lines" is the pass condition.
- **Benign console noise:** `NotAllowedError: play() failed because the user didn't interact with
  the document first` fires on every load in a headless run. Filter it out or it drowns real errors.
- **`--clear-cache`** matters: BGA caches JS/CSS hard, and a stale bundle will hide the change you
  deployed.
