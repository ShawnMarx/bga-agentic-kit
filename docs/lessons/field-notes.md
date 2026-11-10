# Field notes

Lessons from roughly five months of building *The Reckoners* (a co-op dice game) on Board Game Arena
Studio, almost entirely through Claude Code sessions. Each entry is a rule, the symptom that taught it,
and the fix. Dates are when it was first hit; "Reckoners" is the case-study game.

Paths like `tools/bga-session-manager/` and `scripts/check_state_scope.py` refer to this kit.

---

## 1. Verifying changes, and false green lights

**A check that has never been seen to pass cannot be used to interpret a failure.**
Before bisecting, prove the harness reports PASS on a known-good state. One session bisected backwards
through good commits because every capture used a URL that always 500s (below); reverting everything to
HEAD still "failed", which was read first as "the code is innocent" and then as "the platform is down".
Both wrong, and a real client bug was live the whole time.
Seen: 2026-08-30, Reckoners — an hour lost to a harness that could never succeed.

**`node --check` is a floor, not a verification: it parses, it does not resolve names.**
Two shipped breakages passed it. (1) A regex edit put a `//` comment after a call's last argument and
swallowed its `);` — the file still parsed because parens re-balanced later, as a *different* program;
the browser said `missing ) after argument list` and hung on "Opening the game box...". (2) Code moved
between methods kept a reference to the old method's local; the browser threw
`Uncaught ReferenceError: ap is not defined`, which BGA paints as a red banner over the live table.
Fix: add an ESLint `no-undef` pass with BGA globals declared (`templates/game-repo/eslint.config.mjs`),
and `grep -n "//.*);$"` for swallowed parens. Never put a `//` after a closing paren on an argument line.
Seen: 2026-08-30 and 2026-08-31, Reckoners — both passed the syntax check and broke the live client.

**A linter that resolves names cannot see a wrong receiver; write a project-specific check.**
The modern skeleton's `Game.js` holds state classes (`constructor(game, bga)`, helpers on `this.game`)
and the Game class (helpers on `this`). `this.waitTitle()` pasted into a state class is a legal property
access to both `node --check` and ESLint, and throws `this.waitTitle is not a function` at runtime — here
at the instant the last character was confirmed, wedging the client on "Updating..." while the server
advanced. `scripts/check_state_scope.py` flags any `this.<GameMethod>()` inside a state class; it was
negative-tested by reintroducing the bug.
Seen: 2026-09-08, Reckoners — reported by a tester as "stuck after selecting characters".

**Chain checks to the deploy with `&&`, never `;`.**
A `;` runs the upload even when the check just failed. That put a file with a syntax error on a live
table for about a minute. A script that edits two files and then deploys must also gate on *both* edits
having landed — a half-applied replacement once shipped new JS with old CSS.
Seen: 2026-08-31, Reckoners — failed lint, deployed anyway.

**A driver that reconnects hides the wedge it just caused. Capture `pageerror` and console errors on every run.**
"Server advanced, client stuck" is exactly what a client-render exception looks like: the action lands,
the client dies drawing the result. A reconnect rebuilds correct state from `getAllDatas()` and reads as
success. Treat any stall as a client bug until proven otherwise; a driver that only reads game state
sees only the server's opinion.
```python
page.on("pageerror", lambda e: errs.append(str(e)))
page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
```
Seen: 2026-09-08, Reckoners — a verification run walked past the bug and reported it verified.

**Validating a fix means reproducing the failure on purpose, not re-running the happy path.**
"An ordinary purchase still works" is a regression check. The contention case (two seats racing for one
item) had never been reproduced before or after the fix. When a client guard works, it hides the server
guard: test the server half by calling `performAction` directly with stale arguments. Assert on state
(money, ownership unchanged), not merely that something threw.
Seen: 2026-09-11, Reckoners — "did you validate the fix?" — honestly, no.

**Reproducing on a real table beats reading the code — reading misses compensating layers and runtime values.**
Five rules bugs were diagnosed by reading, then re-checked once a Playwright harness existed. Reading got
three exactly right and two wrong: it missed a guard one layer up (a state-class check covering a helper
that "had no validation"), and it guessed wrong about the values that actually reach the code (data that
"deploys 4" deploys 3 from its real starting position — a question to the publisher dissolved). The real
defect it walked past showed up in the first minute on a table. Build the ability to reproduce before
writing a rules fix.
Seen: 2026-08-28, Reckoners — two of five diagnoses corrected by a table.

**For UI bugs, the missing fact is which look-alike state the user was in. Ask for a screenshot early.**
Two confident code-reading diagnoses in a row were wrong; a screenshot of the status bar showed the
player was in a payment sub-step governed by a different client flag. That fact exists only in the live
client — not in `gamedatas`, the database, or the log. A wrong diagnosis that fits every symptom is the
expensive kind; fitting the symptoms is not evidence.
Seen: 2026-08-30, Reckoners — a highlight cue failed only mid-payment.

**When one input path works and another doesn't, the difference between the paths is the bug.**
"Tooltips don't work at all" — but help-mode tap still worked, and tap was the one path that never read
the tooltip preference. The preference was simply set to Disabled. Ask for the setting before rewriting
the code that reads it.
Seen: 2026-08-29, Reckoners — a correct preference gate nearly got "fixed".

**A mechanism that could cause the symptom is not evidence that it did.**
An iOS layout glitch was blamed on CSS `zoom` (a genuine iOS quirk) and a reflow fix shipped that did
nothing. The user's repro steps, one message later, pointed elsewhere. Ask for a repro before shipping a
speculative fix.
Seen: 2026-08-29, Reckoners — dead space under the board on iPhone.

**Stage client-only state to verify UI without touching the game.**
Opening menus, setting selection/basket fields and calling render methods sends nothing to the server,
so a second headless browser on the same live table can stage a state, screenshot it and discard it
while someone else plays. Stage the state the player is actually in (a mid-walk class, not the finished
one), and read `getComputedStyle` after a wait — same-tick reads return pre-transition values.
Seen: 2026-08-30, Reckoners — a badge passed on a finished walk and was broken mid-walk.

**Confirm the object handle before believing the values. `window.gameui` is not your game.**
`window.gameui` is the framework's Gamegui: right for `gamestate` and `gamedatas`, empty for your own
client fields. In the modern skeleton your instance is `window.g_sitecore.GameModule` (also reachable as
`window.gameui.GameModule` in some builds). `gamedatas` is the page-load snapshot and does not update
live. A uniformly empty dump is more likely the wrong object than a broken client.
Seen: 2026-08-30 and 2026-09-12, Reckoners — "the client lost its data" (it hadn't).

**Match automation clicks on exact button text; well-written prompts contain their button's words.**
`text=Finish rolling` matched the status-bar prompt ("Finish rolling now? You have 2 more rolls...") not
the button. The run stalled in a loop that looked exactly like a game bug.
```js
[...document.querySelectorAll('#generalactions .bgabutton, .action-button')]
  .find(b => (b.innerText || '').trim() === label).click();
```
Also: `#generalactions` and `#player_boards` live in the game frame, not the top-level page.
Seen: 2026-09-03, Reckoners — a false claim that a confirm dialog was broken.

**A readback of your own write proves nothing. Verify against state only the server could produce.**
Setting a hidden table-option `<select>` via `el.value` + `change` read back correctly, yet the table
started at a different difficulty — the background save was still in flight when Express start fired.
Earlier runs happened to win the race, which is worse than always failing. Fix: reload the owning page
and re-read, retry, and skip the run rather than record results at an unknown setting; cross-check with
an invariant the setting implies (a start value that differs by difficulty). Later the same day the
option form would not persist at all; reaching the state another way was faster than fighting it.
Seen: 2026-09-12, Reckoners — a difficulty sweep caught by an invariant assertion.

**Rendering a control proves it exists; only operating it proves it works.**
Operate it, reload, read the value back from the store. A screenshot of a checked box is not a saved
setting.
Seen: 2026-09-13, a sibling web app — checkboxes that posted nothing.

**The default configuration is where bugs hide. Test the configurations that distinguish things.**
Two player-visible bugs were structurally unreachable at "two players, one unit each": a purchase keyed
on a market slot that refills in place (needs two players contending), and a helper named
`getPlayerDice()` that returned one unit's dice (needs one player controlling several). For any game
with multi-unit control, solo variants or shared resources, the representative tests are those, not the
plain 2P table.
Seen: 2026-09-11, Reckoners — both found by the owner's own play, both already shipped to alpha.

**Measure layouts three ways that don't lie.**
CSS `zoom` scales `getBoundingClientRect()` (a 25px rule measured 35px under `zoom: 1.4`) — read
`getComputedStyle(el).width` and walk ancestors for `zoom`. `offsetParent` is always null for
`position: fixed`, so it cannot test visibility. Measure against content, not a wrapping container's box.
Seen: 2026-09-12, Reckoners — a correct size rule "missed" by 10px.

---

## 2. Deploy and tooling

**Four different things make a change take effect, and they are not interchangeable.**
Code: SFTP deploy + hard refresh (BGA caches JS/CSS aggressively). `gameinfos.jsonc` / `gameoptions.jsonc`:
deploy **plus** the control-panel "Reload game informations" / "Reload game options" click (a full
Deploy performs these reloads itself). `stats.jsonc`: reloaded automatically. Media slots (box, icon,
banner): upload only, not in the served tree. Schema (`dbmodel.sql`): a fresh table.
Seen: 2026-08-21, Reckoners — an options change "didn't work" without the reload click.

**There is no Studio API; SFTP plus Playwright is the whole toolchain.**
Host `1.studio.boardgamearena.com`, port 2022, remote root `/<project>/`. `put` does not create remote
directories — `mkdir` a new folder first. Everything else (builds, options, tutorials, bug reports) is
session-cookie web pages, which a logged-in Playwright context can drive.
Seen: 2026-08-13, Reckoners — checked for an API twice; none.

**Studio SSH keys are per-machine and additive; revoke only on decommission.**
The control panel adds keys rather than replacing them. A box demoted to backup should keep its key;
revoking it "because it's no longer primary" just breaks the backup.
Seen: 2026-08-21, Reckoners — revocation advised, then withdrawn.

**Line endings differ per machine and byte-diffs lie.**
A file last deployed from Windows (CRLF) diffs 100% changed against a Mac (LF) checkout with identical
content — reads exactly like a machine full of uncommitted work. Compare with
`diff <(tr -d '\r' < remote) local`. Harmless at runtime.
Seen: 2026-08-21, Reckoners — 4,491 "changed" lines that were 4,491 CRs.

**The deployed Studio tree is a backup of last resort — but only of what you deploy.**
Anything SFTP'd can be fetched back with `get`; that recovered assets whose only local copy was on a
retiring machine. Source material never deployed (print PDFs, extraction scratch) has no such net.
Seen: 2026-08-21, Reckoners — player-aid images recovered from the server.

**"Gitignored and local-only" is not a backup strategy, it is the absence of one.**
Confidentiality and durability are different problems; `.gitignore` solves only the first, and a private
repo already solves it. Decision rule: commit small derived assets (regenerable only with effort); keep
bulk binaries (print PDFs) in cloud storage, because git history is permanent and can't be pruned without
a rewrite. Never nest a tool inside an ignored asset folder — it was found only by searching for the
folder.
Seen: 2026-08-21, Reckoners — 122 MB of irreplaceable source existed on one machine only.

**Studio's game frame needs session-only cookies; persist and re-inject them.**
Studio keeps the *site* logged in on a remember-me token, but the game server needs `..._sso_user` /
`..._sso_id` session cookies that vanish when a persistent Playwright profile closes. Symptom: lobby and
table pages work, the game frame renders "Not logged in (studio)", `window.gameui` never appears. Fix:
snapshot all cookies at login and re-inject them on every launch with a long expiry
(`tools/bga-session-manager/login.py` + `launch_context()`). Read the frame's `document.body.innerText`
before suspecting the game. Related: a login script must not report OK when the window was merely closed,
and `~` in an env var is not expanded — `expanduser()` it or the re-injection silently does nothing.
Seen: 2026-09-17, Reckoners — an hour lost mid-investigation.

**Studio and the main site are two separate logins; alpha tables, bug reports and replays are on the main site.**
Without the main-site login `boardgamearena.com/bug?id=...` says "Unable to load this report", which
reads like a permissions problem. Keep the two cookie jars apart so neither login clobbers the other,
and inject both (`login_main.py`). The doc wiki also uses the main-site login.
Seen: 2026-09-18, Reckoners — first attempt to read a tester's bug report.

**"Gameserver is locked by configuration" on the obvious game URL is not your code.**
`https://studio.boardgamearena.com/<n>/<project>?table=<id>` can 500 with that message, thrown in
`webActionCore.inc.php` before any game PHP runs. Load tables via `table?table=<id>` and click through
("Go to game"). If a table is genuinely stuck and invisible to every listing: go to the lobby for your
game, try to create a table, follow the "already in progress" error's link, and express-stop it. Scripted
`quitgame`/`createnew` calls are rejected (`feException` 806). `/studioissues?game=<project>` reporting
"No errors!" is good evidence a load failure is not yours.
Seen: 2026-08-30, Reckoners — misread as a server fault twice.

**One login can drive every seat of a multiplayer Studio table.**
The arrow beside each player's name is an `a.expressswitch` linking `tableview?table=<id>&as=<playerId>`.
Open one page per seat in the same browser context and act only on the seat the client reports active.
(`testuser=` is ignored on `tableview`, which is how the wrong conclusion "you need a second login" got
written down and sat for weeks — every between-players behaviour was shipped unverified meanwhile.)
Not every switcher seat necessarily has units to play; iterate. A count picker that stages then asks for
Confirm will spin a naive loop forever.
Seen: 2026-09-09, Reckoners — weeks of "unverifiable" multiplayer behaviour that was verifiable.

**Seats driven from one login share one client-side action lock, so you can't race yourself.**
The second seat's send is refused client-side ("Please wait, an action is already in progress") and
looks like a server refusal. It doesn't matter: BGA serialises actions per table, so sending the second
request after the first completes gives the server the identical sequence two real browsers would.
Seen: 2026-09-22, Reckoners — a "simultaneous suggestion" test.

**The Studio lobby remembers its last table configuration.**
Create can hand you a 2-player table when you expected solo; a solo driver then stalls forever in a
multiactive state waiting on an unplayed seat, which looks like a game bug. Check `Number of players`
first (the `#wanted_minus` / `#wanted_plus` widget sits in a hidden container — click via JS). An
unstarted table silently disables Create and hides option controls. Configure seat count, then mode,
then speed. `Express start` fills seats with test accounts; `#startgame` starts with seats present.
Seen: 2026-09-09 and 2026-09-12, Reckoners.

**Emulate the device, don't just narrow the viewport.**
BGA's phone scaling only engages for a real phone UA/DPR, so a narrowed desktop window hides the whole
class of phone layout bugs.
```python
dev = dict(p.devices["iPhone 15 Pro Max"]); dev.pop("default_browser_type")
ctx = p.chromium.launch_persistent_context(user_data_dir=..., headless=True, **dev)
```
Seen: 2026-09-15, Reckoners — narration running off-screen only on a real phone.

**A heredoc ends a shell `&&` chain; the next line runs anyway. And `git merge -F -` does not read stdin.**
`git merge ... -F - <<'MSG'` fails (`error: could not read file '-'`, exit 129); the `git tag ... && git
push` on the line after the terminator is a new statement and runs regardless — tagging the *previous*
build. Happened three times, twice pushing a wrong public tag. Write the message to a file and pass
`-F <path>`; run the merge on its own, check `git log -1`, then tag and push. A note about it did not
prevent repeats; a rule in the repo's `CLAUDE.md` (loaded every session) did. Also: auto-mode permission
classifiers may refuse the recovery (`git tag -d` + delete remote tag), so prevention matters more.
Seen: 2026-09-16 (x2) and 2026-09-17, Reckoners — release tags on the wrong commit.

---

## 3. Client JS and BGA framework quirks

**`await performAction()` resolves before BGA unlocks the interface, and a blocked call returns `undefined`, not a rejection.**
The interface stays locked until the action's notifications finish playing. A loop firing several
actions sends the first; the rest hit `checkAction` ("Please wait, an action is already in progress")
and vanish silently, because `await undefined` sails through. Poll the framework's silent check:
```js
async waitForAction(action, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try { if (this.bga.actions.checkAction(action, true)) return true; } catch (_) { return true; }
    if (Date.now() > deadline) return false;
    await new Promise(r => setTimeout(r, 80));
  }
}
```
Seen: 2026-08-29, Reckoners — confirming three removals at once applied one.

**Make several actions read as one: one undo snapshot, one log line.**
Tag the calls `start | more | end`; only `start` takes `undoSnapshot()`, so one Undo reverts the group.
Intermediate calls `notify->all()` with an **empty message** (updates the board, writes no history) while
accumulating descriptions server-side; `end` emits the joined summary. Clear the accumulator when a group
starts or a refused last call leaks its half-summary into the next. Cheaper than a batch endpoint that
would re-implement per-step prompts.
Seen: 2026-08-29, Reckoners — a three-dice spend showed three log lines and undid piecemeal.

**`bgaFormatText(log, args)` is the only hook into the game log — and it can rewrite args too.**
Log lines are composed server-side and rendered by BGA's formatter; your own text pipeline never touches
them. The framework calls `bgaFormatText` at the start of every `format_string_recursive` and expects
`{ log, args }` back (the old `format_string_recursive` override is deprecated). Mutating a fresh copy of
`args` renders markup, just as `${player_name}` arrives as a coloured span. Pattern: the server writes
`{token}`s, the client swaps them for SVG. Match `{name}` but never `${name}` —
`/(?<!\$)\{([a-z_-]+)\}/g` — since the hook runs before BGA substitutes its own placeholders. Emit
structured parts rather than prose so several costs can merge ("x2") instead of concatenating. Wrap it
all in try/catch: never break a log line over an icon.
Seen: 2026-08-29 (template) and 2026-09-12 (args, measured on a live table), Reckoners.

**A custom tooltip layer must honour BGA's own tooltip preference.**
BGA's `addTooltipHtml` sticks open on touch, so a custom overlay is common — but then global preference
**200** ("Display tooltips": 0 enabled, 1 disabled) no longer covers it. Read
`this.bga.userPreferences.get(200)`. Don't put an SVG `<title>` and a `data-tip` on the same element (two
tooltips from two systems); use `aria-label`. Keep `data-tip` plain text and inject markup at display
time. Wait ~700 ms of hover intent, cancelled on pointer-out/click/touch.
Seen: 2026-08-29, Reckoners — Studio review flagged tooltips; debugging found the preference.

**`onEnteringState` means "the state changed", not "the situation changed". A looping state never redraws its own bar.**
When one state resolves several identical obligations in turn, the framework never re-enters it, so a
Confirm built for obligation #1 is still on screen, wired to a consumed selection, when #2 begins. Next
click: `BadMethodCallException: actX parameter dieId is mandatory` and a red banner. Fix both ways: the
notification that resolves one obligation redraws the controls; and every handler reading live client
state validates it and re-renders instead of sending.
Seen: 2026-08-31, Reckoners — a two-dice surrender step.

**A page-load flag must record which state it loaded into, and be consumed on the first entry either way.**
BGA calls `onEnteringState` right after `setup()`, so clients set `freshLoad = true` to tell "reloaded
mid-phase" from "phase just started". Consumed by only one state, it stayed armed when the page loaded
into another and later misfired on a genuine entry — showing "waiting for other players" in a solo game.
Record `gamedatas.gamestate.name` alongside it. And when one entry hook needs a reload guard, every hook
that clears the same state needs it: grep for the reset, not for the flag.
Seen: 2026-08-31 and 2026-09-03 (the half-fix), Reckoners — a dead end reachable by pressing F5.

**The last action's notification can arrive after the state change it triggered.**
A handler that mutates per-piece state then re-sets flags the new state's entry hook just cleared. Guard
notification handlers with a phase check. Tell client drift from server bugs fast: a fresh page load
showing correct state means the server was right; compare `gamedatas` against the live client object.
Seen: 2026-08-30, Reckoners — roll-phase "done" flags leaking into the next phase.

**Full-state paths stay right while delta paths rot.**
A notification carried one unit's dice where the player owned several; a reload always recovered it
because `getAllDatas()` was correct. If "a refresh fixes it", suspect the incremental notification. Name
helpers for what they actually return.
Seen: 2026-09-11, Reckoners — a bought-back die never reached the client.

**If a container refills in place, its index is not an identity.**
An action that takes a market slot index buys whatever is in that slot when it arrives. When a rival buys
first the slot refills immediately, so an occupancy check passes and the stale Confirm buys the
replacement. Send the id of the thing chosen and have the server refuse when the slot no longer holds it.
The client-side drop is nice; the server check is the one that matters, since two confirms can land in
the same instant.
Seen: 2026-09-11, Reckoners — "I ended up buying the wrong item".

**Give injected SVG primitives literal fallbacks for CSS variables.**
An icon filled `var(--x)` renders black anywhere outside the subtree declaring `--x` — e.g. a status-bar
button. Use `var(--x, #d8452f)`.
Seen: 2026-08-29, Reckoners — black icons in action buttons.

**Guard the first write of a newly added statistic.**
`initStat()` runs only in `setupNewGame()`, so tables already in progress have no row. Rather than find out
whether `getStat`/`setStat` throws inside a GAME-type state on every tester's open table at once, wrap
the first out-of-setup write in try/catch. Stat ids are permanent once a table has run. Stats are scalars
(no series) — pick a pair (average, worst) that answers what the series would have been read for. A driven
table that loses quickly shows the end-of-game stats block on `table?table=<id>`.
Seen: 2026-09-14, Reckoners — two new stats shipped mid-alpha.

**A progress value that takes `max()` of two races stalls. Ask "does every input move it?"**
`getGameProgression()` returning `max(winPct, lossPct)` ignores whichever race is behind, so real
progress doesn't move the bar — and that number is all the games-in-progress list shows. Union blend
`(1 - (1-win)*(1-loss)) * 100` is monotonic in both and still hits 100 when either completes (it runs
ahead; soften with `win + k*loss*(1-win)`). Also call `updateGameProgression` from more than one state.
Seen: 2026-09-03, Reckoners — "no progression % change in the game list".

**The game list's Progression and "It's your turn!" come from a main-site table record, written only on turn events of a clocked table.**
A game can compute perfect progression and the list still reads 0%. Read the stored record via
`table_infos` in a site page, or `GET /table/table/tableinfos.html?id=<table>` with
`X-Request-Token: bgaConfig.requestToken` and `X-Requested-With: XMLHttpRequest`, after leaving the game
page (the game page's own card updates live and lies). Turn-based 2P tables write every step; Training
writes at start and when the active set empties; **1-player tables (always Training) write once at start,
never again** — a known, long-standing platform limitation for solo progression; don't re-investigate.
What *is* yours: the "your turn" flag is recorded from whoever is active at table start. Activating the
player from inside the first state's `onEnteringState` via `changeActivePlayer()` isn't reported without
a transition; call `activeNextPlayer()` in `setupNewGame()`. Use a second Studio project as a control to
separate "Studio does this to everyone" from "our code".
Seen: 2026-09-16/17, Reckoners — two days on solo tables showing no turn flag.

---

## 4. CSS, mobile and iPad layout

**Run cssnano before deploying CSS — it is what the BGA build runs, and browsers hide broken rules.**
A broken rule throws nothing in the browser; it is skipped. BGA's build minifies with cssnano, which
hard-fails at *Build game* — after the checks, the SVN commit and the release tag. A comment that quoted
the comment-close characters literally (while explaining an earlier broken comment) closed itself and
turned prose into a selector. `csstree-validator` missed it (it validates declarations, not selectors).
```bash
npx --yes -p postcss-cli@11 -p cssnano@7 -p postcss@8 postcss game.css --use cssnano --no-map -o /dev/null
```
Never write the comment-close sequence inside a comment; spell it out in words.
Seen: 2026-09-12, Reckoners — build failed at a line:column the browser had happily ignored.

**A valid selector that matches nothing is the CSS bug no tool catches. Measure every CSS change on a table.**
Size rules written for the wrong of two similarly named icon classes deployed clean and changed nothing;
only a probe returning `null` width exposed it. A malformed comment can also silently eat the following
rule.
Seen: 2026-09-12, Reckoners — "the icons ignored the size change".

**BGA lays out at `game_interface_width.min`, not device width — derive zoom from the container, never cap it.**
With a min of 480 on a 430px phone, BGA renders a 480px canvas scaled ~0.896 (`#page-content` gets
`zoom`). Your own chrome eats into that. A fixed phone zoom cap encoded "1.2 fits" for a 340px card and
rotted silently when the card grew to 400px. Compute `floor((panelW - padding) / cardW * 1000) / 1000`,
treat the user's size setting as a ceiling, and re-apply from a `ResizeObserver` on **width only** (zoom
changes height; reacting to that loops).
Seen: 2026-09-15, Reckoners — activation text off the right edge on iPhone.

**Never cut a platform gesture to hide a layout glitch.**
`html, body { overscroll-behavior-y: contain; }` fixed iOS dead space under the board — and killed
pull-to-reload, which is the only reload a BGA page saved to the Home Screen has (no address bar). A tester
reported it; the rule was removed.
Seen: 2026-08-29 (added), 2026-10-28 (removed), Reckoners.

**On iPad Safari, size overlays in percentages of a definite ancestor — nothing intrinsic.**
An SVG with `height: 100%; width: auto` (width from viewBox ratio), shifted by `translateX(-100%)`, kept a
stale width after its container re-rendered; Chrome measured it correctly to 0.01px, so no desktop harness
could reproduce it. Derive the width by hand as a percentage and use `margin-left: -N%` instead of the
transform. Comment the derivation next to the constant.
Seen: 2026-09-12, Reckoners — brackets a few pixels off until reload, iPad only.

**A reflow nudge that restores an equivalent value is a no-op — at the default, where most users are.**
Clearing `zoom` then restoring it does nothing when the setting is `zoom: 1`. Step to a genuinely different
value and back (`* 1.001`) in one synchronous task.
Seen: 2026-09-12, Reckoners — the workaround fired at every size except Medium.

**A layout constant is a measurement someone stopped taking. Get the two numbers before proposing a fix.**
Three layout fixes were shipped and rejected, each a guess about available room. Arithmetic (available
~108px vs required ~124px) showed it was over-constrained by 16px; the problem became a menu and was
settled in one word. For an out-of-flow element, measure it and publish its height as a CSS custom
property — safe only if the measured dimension doesn't depend on the property. Better still, ask first
whether it needs to be out of flow at all. Never measure an element that carries its own `min-height` to
derive that `min-height`.
Seen: 2026-09-02 and 2026-09-15, Reckoners — district card header overlap.

**`flex: 0 0 160px` is a request. A card at its `min-width` shrinks "fixed" columns.**
A 160px column measured 120px because another rule re-enabled shrink; pinning it made the card grow to
content width and collapse a two-across ring to one. Fix: cap the card (`min-width = max-width`) and pin
only the column that must not give. Write down the wrap arithmetic.
Seen: 2026-09-13, Reckoners — adding miniature figures to a card.

**Nothing inside an element with `opacity` or `filter` can render un-faded. Stack a clipped copy instead.**
To keep one region of a faded card readable, move the fade off the container, fade the base image, and
overlay the same image (same file, same box, same `object-fit`) with `clip-path: var(--region)`.
Reproduce old compound opacities by multiplying. `clip-path` also clips hit-testing, so a transparent
element with the same clip is a precisely shaped hover target. Mock it on the live page before building.
Seen: 2026-09-12, Reckoners — a defeated card keeping its rewards banner legible.

**Put state on one element and let siblings read it.**
When a new visual must share an existing element's state classes (toggled from a dozen paths), place the
state owner first in the DOM and style followers with `+`/`~`; use grid to reorder visually. `:has()` for
the reverse direction as progressive enhancement only. Copy the lighting *policy* too, not just colours.
Seen: 2026-09-13, Reckoners — figures that light with the pill under them.

**A dark-mode outline built from stacked `drop-shadow`s erases icons defined by thin gaps.**
Fine for solid silhouettes; a knockout mark at 22px became a white block. Exempt by use (marker class),
not by icon. Check theme-gated rules in the theme that has them — a local page loading the real
stylesheet with the theme class toggled reproduces it without a table.
Seen: 2026-09-13, Reckoners — a blank button icon only in dark mode.

**Chosen must outrank hover in CSS, explicitly.**
With many `:hover` rules more specific than the plain "picked" rule, hovering a chosen target repainted it.
One block at the end of the stylesheet declaring chosen states `!important` is the cleanest hammer; new
target types must be added there.
Seen: 2026-08-31, Reckoners.

---

## 5. State machine, notifications and server rules

**BGA caps one action's notifications at 128KB. Per-beat payloads are a size multiplier.**
"Unexpected error: generated notifications are larger than 128k (256215)" aborts the step with a red
banner and no transition. It only appeared at the largest board (6 units, full ring); 2P tables never got
near it. Fix: per-beat board snapshots are **patches** against the previous snapshot in the same request
(changed sections, changed rows, flagged `patch`; client merges rows by id). A row-count change sends the
whole array (a patch can't express removal). The first beat is complete, so replays stay safe. Test
anything per-beat at the maximum board.
Seen: 2026-09-02, Reckoners — an activation sequence at 6 players.

**A paced animation must apply the board one beat at a time.**
One notification carrying the final board means every counter has already moved before beat one plays,
and narration reads as a recap. Snapshot inside the server loop after each step's write; client applies
each beat's board, renders, then plays that beat. Anything the animation positions by hand must be
re-applied after every re-render or the render undoes it. Fall back to the final board for older payloads.
Seen: 2026-08-31, Reckoners — population dropped before the narration said why.

**A multiactive state ends the instant the active set empties — even with an obligation outstanding.**
`setPlayerNonMultiactive` transitions as soon as nobody is active; the framework knows nothing about your
pending vote/offer/suggestion. A live alpha table lost a teammate suggestion this way. "Parked" (your own
waiting column) is not "finished": `setPlayersMultiactive([...], $next, false)` reaches only who you name;
`setAllPlayersMultiactive()` brings finished players back. Build one funnel for standing a player down
(done, pass, `zombie()`) that re-activates whoever still owes something; refuse stand-down while something
is addressed to that player; clear the obligation's storage on the way out of the step.
Reproduce with three seats, two finished, the third acting last.
Seen: 2026-09-24, Reckoners — a suggestion evaporated as the phase advanced.

**`displaycondition` is a convenience for the create-table screen, never the enforcement.**
A `minplayers 2 / maxplayers 5` condition hid an option on a 2-player table that met both. No error; the
`gamepanel?game=<project>` page still listed it (so "reload the options" checked out clean). A
conditioned-out option silently resolves to its default. Delete the condition and guard in
`setupNewGame()`. Debug: listed in the game panel but absent from Table configuration = the condition.
Seen: 2026-08-30, Reckoners — a multi-handed variant unreachable.

**`dbmodel.sql`: full-line `--` comments only.**
A trailing inline comment after a column definition makes BGA's schema loader silently skip the column;
you find out at runtime as "Unknown column". Schema changes need a fresh table.
Seen: early development, Reckoners.

**Enforce rules server-side; a client-only check is no check.**
A movement restriction enforced only in the client was one of the designer's first findings; the server
had no check at all. Check both ends of a move (origin and destination).
Seen: 2026-08-26, Reckoners.

**`php -l` every server file you touch — a parse error in the main Game class takes the whole table down.**
Unlike a JS error (client loads, shows a banner), a PHP parse error prevents construction and looks like
an infrastructure fault.
Seen: 2026-09-12, Reckoners — PHP linting added after months of none.

---

## 6. Interaction design on BGA (general patterns)

**Match the platform's button semantics — and colour by direction, not consequence.**
Studio guideline: blue = advance/confirm, red = cancel/undo/stop, white = optional/side action, grey =
disabled (a state, via `disabled: true`, not a colour). Two wrong turns, mirror images: "irreversible
means red" (Studio: "Done buying should be blue, even if it ends the phase") and "harmless means white"
(the *no* of a confirm is a cancel — red). Irreversible-but-forward is blue; harmless-but-backward is red.
BGA's `bgabutton_gray` is pale with blue ink and reads as disabled-blue; repaint background *and* colour.
On the board too: if blue means "confirm" in the action bar, it can't mean "hover" three inches above it.
Rewrite the doctrine comment above the button helpers before touching call sites — the prose is what
propagates. Audit colour on a driven table: conditionally rendered confirms never show up in a grep.
Seen: 2026-08-30 and 2026-09-09, Reckoners — two Studio review rounds.

**When two entry points produce "the same" action, make one call the other.**
Target-first and cost-first spends diverged silently: only one path opened the composable basket.
Converge on one primitive, or diff capabilities by hand forever. The same rule absorbed a new source type
and a character with a second location ("a wider target set, not a separate flow").
Seen: 2026-08-31 to 2026-09-16, Reckoners.

**Confirm only compositions. A single selection that completes a chosen action commits on click.**
With Undo available, a Confirm on one undoable choice asks a question with one answer. Keep Confirm where
the player assembled something by hand. Make the open action's Cancel the only exit, so a stray click
can't silently bin a half-built action — and test "is an action open?" against the bar as well as state
fields so a leftover flag can't trap the player.
Seen: 2026-08-30 to 2026-09-15, Reckoners.

**Hover-lit by default; lit outright only once the player has said what they want.**
Lighting every live thing buries meaning. Offer an "always highlight" preference for those who want it.
Seen: 2026-08-30, Reckoners.

**When one player controls several units, require selecting the unit first.**
Inferring the acting unit from whatever was clicked caused misfires; "Done" must finish the selected unit
only, with a separately labelled, confirmed "Done with all".
Seen: 2026-08-30, Reckoners — a single Done ended a whole multi-unit turn.

**A count keyed on an optional field silently counts nothing.**
A per-target "xN" chip keyed on a field written only when there was a choice to make; with one option in
play it was absent and the first unit went unmarked. Fall back to the context value.
Seen: 2026-08-31, Reckoners.

---

## 7. Tutorials, bug reports, replays, rules summary

**BGA tutorials are interactive; the recorded game is the scaffold.**
Each comment's continue mode is either "click Continue" or "Player must DO the next game action";
guideline: never auto-play a current player's move. A DO comment sits one move *before* the action it
asks for. Comments can stack on a move and default to unanchored (anchoring is a drag; not scriptable).
Seen: 2026-09-11, Reckoners — a tutorial half-built as a passive replay.

**The tutorial authoring view is not the player view; nothing can be judged before "Publish as tutorial".**
The replay URL shows Delete/Modify controls, Space does nothing, and game buttons sit on "Updating game
situation...". `#publishtutorial` produces `tutorial?game=<project>&tutorial=<id>` with real gating.
Scriptable: `#archive_next`, `#archive_addcomment` + text + save, and continue mode **on a new comment
before first save**. Not scriptable: continue mode on an existing comment (silently doesn't persist),
`Go to move`, `#archive_end_game`. Verify saves by reading `div[id^=archiveComment_]`, not by whether the
editor is still visible (it always is). Don't edit an official tutorial's text: it wipes community
translations.
Seen: 2026-09-11, Reckoners — 13 comments authored passive; 13 "failed saves" that had saved.

**Studio replay archives are reaped fast. Check `gamereview?table=<id>` the same day, before quitting.**
Next day: "this archive has not been found" / "Unable to find table database" — not a defect. Unfinished
games archive fine; a few turns are enough.
Seen: 2026-09-10, Reckoners.

**Step a replay with `window.gameui.archiveGoToMove(N)` in the game frame, then poll.**
`&step=N` in the URL is ignored; the page's "Go to move" box ignores scripted clicks. `archiveGoToMove`
replays from the start, so poll until the log shows the move — reading early gives a confident answer
about the wrong round. Your client state is on `g_sitecore.GameModule` in replays too.
Seen: 2026-09-18, Reckoners.

**A reporter's explanation of their own bug is a hypothesis. The replay is the evidence.**
A tester theorised an equipment card "doesn't work in the round it's bought". The replay showed the card
was live; the only qualifying symbol was on a die colour the card doesn't apply to. Implementing the theory
would have broken a correct rule. A fresh-table repro proves the mechanic but can't explain *their* table.
Seen: 2026-09-18, Reckoners — a bug report that was correct play.

**The rules summary on the game page is the public wiki page `Gamehelp<projectname>`, rendered very reduced.**
Only one heading level (`== H ==`); deeper levels and bold lines all look like headings — use capitalised
run-ins ("VICTORY CONDITION - ..."). List markers are dropped; write numbers/bullets literally. The game page
caches it (wait, don't re-edit). `index.php?title=Gamehelp<name>&action=raw` returns live source to diff.
Main-site login; a public write an agent may not be permitted to make — plan a manual paste.
Seen: 2026-10-28, Reckoners.

---

## 8. Release, alpha and the metagame

**Name the Studio project after the published title, in CamelCase, on day one.**
The alpha validator slugifies `gameinfos.jsonc` `game_name` and requires it to equal the project name;
"The Reckoners" ≠ project `reckoners` blocked the alpha request. Renames are refused once deployed; the
"Overwrite project" tool is a copy, not a rename (new namespace, SFTP root, panel, re-invite testers). The
escape hatch: the *displayed* name is a translation-center string (module for your game, English → English,
context "Game name", source `<project>_displayed`) — auto-validated for the developer. Ask Studio about that
route before any rename request.
Seen: 2026-08-13 to 2026-10-28, Reckoners — listed as "Reckoners" for two months.

**Studio files are not what alpha players get; a build is.**
SFTP updates the Studio working copy (what Studio tables run). Players get a build cut from it. Keep a
`staging` branch matching Studio and a `main` branch matching the live build, merged and tagged at each
build, so `git diff main...staging` answers "what haven't testers got?".
Seen: 2026-09-03, Reckoners — private alpha granted.

**Cutting and deploying a build is scriptable from `studiogame?game=<project>`.**
No API, but a logged-in Playwright context can: (1) "Dry run build" and read *Command results* (all ✅);
(2) fill the `<textarea maxlength=250>` before "Commit & build a new version now" and click it — ends
`Deploy <YYMMDD-HHMM> ✅`; (3) under "Versions available for production", click that version's **Deploy to
production** — only then do alpha players get it. Buttons are id-less svelte `a.bga-button`s: match
`innerText`, locate by DOM position. The "Online version" label lags. Keep one known-good version for
rollback. The build can still fail at *Build game* after the commit (see cssnano).
Seen: 2026-11-09, Reckoners — first fully scripted build.

**The 250-character release note is a player-facing changelog line.**
It's what testers read. Symptom-first plain English, lead with the fix a tester would recognise, spend
leftovers preempting the obvious question ("No need to start a new table."). The long form goes in the
merge commit.
Seen: 2026-09, Reckoners.

**BGA's pre-release checklist and Studio review do not check rules correctness.**
Both passed with zero rules bugs found; the designer then found four in one evening (three real) and
re-checking them surfaced a fifth. The checklist is framework citizenship; the review is interface
conformance. Get a rules-fluent player on a real table early and repeatedly, as its own gate. Audit code
against your own spec's rules table first — one rule was written correctly in the spec and silently
narrowed in code.
Seen: 2026-08-26, Reckoners — alpha gated on rules feedback.

---

## 9. Assets and art pipeline

**Publisher print PDFs hold genuine vector art; extract it, then render and compare.**
PyMuPDF `page.get_drawings()` filtered by fill colour and bbox, emitted as `<path>`. All three failure
modes render plausible-but-wrong SVG rather than erroring, so raster the same PDF region at high zoom and
compare: hairline (`0.001pt`) die-lines are real geometry you must give a visible stroke; the `even_odd`
flag is untrustworthy (emit `fill-rule="evenodd"` when the print clearly knocks out); a leading full-bounds
rect may be a clip, not ink. Extract in the PDF's own page coordinates so pieces compose in register.
Printed numerals are usually vector too.
Seen: 2026-08-29, Reckoners — a card-back mark rendering as a solid square.

**Flat, shaded token art from a miniature's print STL needs no 3D app.**
Render a face-ID map (each triangle in a colour encoding its index) with Pillow; derive normals (Lambert
shade, posterize), depth edges (silhouettes) and creases from it. Decimate first. Drop small line
components or sculpt stipple becomes noise; `potracer` treats zero as ink (invert first); judge candidates
on a contact sheet at 96/64/48/32/24px, not at full size; `svgo --multipass` halves trace size. Keep the
STL out of git and read it from an env var; commit the derived SVGs.
Seen: 2026-09-13, Reckoners — enforcer miniature to 44px tokens in about two hours.

**When a human rewrites machine-readable strings, validate what comes back.**
A wording-review page displayed `${card.name}` as a pretty chip without braces; the reviewer rewrote what
they saw and the placeholders were gone. Show the literal, seed the input with the real template, and —
the only fix that survives dictation or phone editing — check the returned text contains every placeholder
the original had.
Seen: 2026-10-11, Reckoners — a pre-beta wording pass.

---

## 10. Working with an agent

**Say what kind of statement you're making: "I verified X by running Y" vs "session Z told me X".**
When sessions relay claims, confidence accumulates while evidence doesn't; an echo arrives looking like
corroboration. Never upgrade a received claim by repeating it; verify before telling the user; push back
with measurements, not "are you sure?"; send retractions to the peer too, not just the user.
Seen: 2026-08-21, a sibling web project — a false environment claim relayed as confirmed.

**A general claim from a singular measurement is the subtler failure.**
An honest, real observation ("it works signed out") was true of the one instance measured and false for
yours. Ask what specifically was measured; re-run it against your own case, especially where a cookie, env
var or per-object flag could differ.
Seen: 2026-09-05, a sibling web project.

**If your job is to check, then check. A reviewer reasoning from memory is worse than none.**
A scribe session that read source caught four wrong table-side claims in a row — then, reasoning from a
skill document instead of live state, told a playing session to scrap a correctly configured table. Both
playing sessions refused with live readings, rightly. Being right repeatedly buys deference the next
unverified claim hasn't earned; the front line looking at the running system often has better evidence.
Seen: 2026-09-09, Reckoners — a two-agent playtest with an outside scribe.

**Put rules where every session loads them.**
A personal note about the heredoc trap did not stop a fresh session repeating it; a line in the repo's
`CLAUDE.md` did. Lessons that must prevent a repeat belong in the always-loaded project instructions (or a
check script), not in notes the agent never sees.
Seen: 2026-09-17, Reckoners — third wrong release tag.

**Wrong facts written into a skill propagate as truth.**
"A 2-player table needs a second login" sat in the playtest skill for weeks and every session obeyed it.
Date claims in skills, record how they were established, and re-test the ones that block work.
Seen: 2026-09-09, Reckoners.
