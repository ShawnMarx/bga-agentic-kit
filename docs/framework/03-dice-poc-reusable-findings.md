# 03 — Reusable findings from the dice POC

Game-agnostic BGA framework lessons learned while building the Reckoners simultaneous
roll/keep/reroll POC inside the tutorial game. (Reckoners-specific design lives in
`_reckoners/docs/reckoners-bga-spec.md`, not here.)

> Status: written from implementation; items marked **(confirm on table)** are still to
> be verified on a live Studio run.

## 1. Chaining multiactive → multiactive (no GAME bridge needed)

Note 02 needed a GAME bridge (`StartPlay`) only because it transitioned multiactive →
**ACTIVE_PLAYER** (which requires a single active player). When the next state is itself
**MULTIPLE_ACTIVE_PLAYER**, you can transition straight there: each player's
`setPlayerNonMultiactive($pid, NextMultiactive::class)` and the next state's
`onEnteringState` just calls `setAllPlayersMultiactive()` again. So:
`ChooseColor (multiactive) → RollDice (multiactive)` with no bridge.

**VERIFIED:** this works — the table reached RollDice and `onEnteringState` ran (rolled
all dice) via a direct multiactive→multiactive transition. (A bug that initially looked
like a broken transition turned out to be an unrelated client API error — see §5.)

## 2. Passing a LIST argument from client → server: use a delimited string

BGA action-arg encoding over the wire is fussy with arrays. The robust pattern that
avoids it entirely:
- **Client:** `performAction('actKeep', { keep: ids.join(',') })`
- **Server:** `#[PossibleAction] public function actKeep(string $keep = '') { $ids = $keep === '' ? [] : array_map('intval', explode(',', $keep)); ... }`

Scalar args (`int`, `string`) inject reliably (as in the skeleton's `actPlayCard(int $card_id)`);
a comma-joined string sidesteps any array-encoding uncertainty. **(confirm on table)**

## 3. getAllDatas auto-enriches `players` with name + color

`getAllDatas` only needs to SELECT your *custom* player columns. The framework merges
the standard `name` and `color` into each `gamedatas.players[id]` entry automatically —
so the JS can use `player.name` / `player.color` even though your SQL never selected
them. (Verified earlier: the hello-world test showed player names with a getAllDatas
that selected only `id, score`.) Key your collection by `player_id AS id`.

## 4. Status-bar buttons: rebuild, don't accumulate

Action buttons added with `this.bga.statusBar.addActionButton(...)` persist and stack.
When a player's in-state situation changes (e.g. their roll number advances) you must
**rebuild**: call `this.bga.statusBar.removeActionButtons()` first, then re-add. Trigger
this from the relevant notification handler (when the notif targets the current player)
as well as from `onPlayerActivationChange`. Starting every "refresh controls" helper with
`removeActionButtons()` makes it idempotent (also neutralizes the duplicate-call issue
from note 02).

## 5. Useful confirmed client API — and a sharp gotcha about WHERE methods live

⚠️ **Current-player / active-player methods live on `this.bga.players`, NOT on
`this.bga`.** This bit us: `this.bga.getCurrentPlayerId()` threw *"is not a function"*
at runtime even though `bga-framework.d.ts` shows `getCurrentPlayerId()` — because the
stub lists it on the `GameGui` / `Players` classes, not on the `Bga` object passed to
your `Game` constructor. Correct calls:
- `this.bga.players.getCurrentPlayerId(): number` — "my" player id.
- `this.bga.players.isCurrentPlayerActive(): boolean` — am I active right now.
- `this.bga.players.isPlayerActive(playerId): boolean` — is a given player active.
- (also `this.bga.gameui.player_id` is the current player id via the GameGui backref.)

**Lesson:** when reading `bga-framework.d.ts`, check which *class* a method is declared
on. The `Bga` interface exposes sub-objects: `players`, `statusBar`, `gameArea`,
`playerPanels`, `actions`, `notifications`, `states`, `dialogs`, `images`, `sounds`,
`userPreferences`, `gameui`. Methods are reached through the right sub-object.

Confirmed-working bits used in the POC:
- `this.bga.statusBar.setTitle(text)`, `.addActionButton(label, cb, {color})`, `.removeActionButtons()`.
- `this.bga.actions.performAction(name, args)`, `this.bga.gameArea.getElement()`,
  `this.bga.playerPanels.getElement(playerId)`.
- In a (multi)active state's `onPlayerActivationChange(args, isCurrentPlayerActive)`,
  the `isCurrentPlayerActive` **parameter** is the simplest active check — no API call
  needed. (ChooseColor used only this and worked; RollDice's `myId()` call is what hit
  the gotcha above.)
- Event delegation (one listener on a parent container, `e.target.closest('.my-item')`)
  is cleaner than per-element handlers when re-rendering item lists like dice.

**How we found it:** the Playwright session manager (`tools/bga-session-manager`) loaded
the table and captured the uncaught page error directly — far faster than screenshot
relay. Worth reaching for whenever a Studio symptom is "nothing happens / no error banner".

## 6. Per-player sub-state during a multiactive phase

A multiactive state often needs per-player progress (here: which roll a player is on,
which dice are locked). BGA multiactive itself only tracks active/inactive, so store the
rest yourself — a per-player column (`player_roll_no`) and per-entity flags (`die.kept_on_roll`).
Drive the transition off `setPlayerNonMultiactive` (phase ends when all are inactive),
and read your own columns for everything finer-grained.

## 6b. ⚠️ Never debug on an EXPIRED Studio table

A long-expired table (clock deep negative, e.g. -3h37) has a **dead realtime
WebSocket**. Symptoms that look like bugs but aren't: actions stick on *"Move recorded,
waiting for update…"*, other players' views don't update / desync, dice render
partially. Confirmed via capture (console shows `WebSocket connection … failed`). The
roll logic that "broke" on the old table worked perfectly on a **fresh** table. Rule:
reproduce/verify gameplay only on a freshly-started, in-time table.

## 7. Randomness

Use `bga_rand($min, $max)` for dice/shuffles (BGA's reproducible RNG), not PHP `rand`/`mt_rand`.

## 8. ⚠️ Deleting a state file locally does NOT delete it on the Studio server

WinSCP "Keep Remote Directory up to Date" **uploads** changes but does **not** delete
remote files when you delete them locally (default behavior). An orphaned state class
left on the server still gets discovered by the framework — and if its `id:` now clashes
with a new state's id, game creation dies with:
`Fatal error during setup: Invalid id for state class ...X (already used by another state)`.

**Fix:** delete the orphan file(s) in WinSCP's *remote* pane (e.g. `modules/php/States/`),
then create a new table. (Hit this when SimultaneousReady/StartPlay were replaced by
ChooseColor/RollDice and SimultaneousReady's id 20 collided with ChooseColor's id 20.)
Consider enabling WinSCP's "delete files" option for the keep-up-to-date task, or just
remember to remove orphans by hand after renaming/removing state classes.

**Same cause, second flavor — stray nested directories.** The framework scans
`modules/php/States/` **recursively**, so ANY stray `.php` in a wrong subfolder there
is treated as a state class and validated against a namespace derived from its path.
A leftover misplaced file (seen: `modules/php/States/modules/php/Game.php` from an old
bad sync) fails with:
`State class .../States/modules/php/Game.php should be of namespace ...States\modules\php (found ...)`.
Fix: delete the orphan folder/file in WinSCP's remote pane. Lesson: keep
`modules/php/States/` containing *only* real state classes; periodically eyeball the
remote tree for junk the local→remote sync never cleaned up.
