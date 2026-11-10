# 02 — MULTIPLE_ACTIVE_PLAYER (simultaneous play)

The pattern where **several players are active at once** and each must act, rather
than strict turn order. This is the direct prerequisite for the Reckoners dice POC
(B3), where players act simultaneously. The generated skeleton does **not** include
it; this note comes from the modern-framework docs + a prototype state we built into
the `tutorialdumahatreides` game (`SimultaneousReady` + `StartPlay`).

> Status: verified end-to-end on a live 4-player Studio table. The JS
> activation-timing detail in §4 is CONFIRMED, not speculative. The automatic
> "wait for everyone" transition fired correctly on the last player's deactivation.
>
> **Studio testing tip:** the **Input/Output** panel at the bottom of a Studio table
> prints each `gameStateChange` with the state `id` and `type`. We watched the chain
> `{"id":25,...,"type":"game"}` → `{"id":10,...,"type":"activeplayer"}` — i.e. the
> multiactive state → StartPlay (GAME bridge) → PlayerTurn (ACTIVE_PLAYER). This panel
> is the fastest way to confirm state-machine flow during testing. Switch player views
> with the **little red ▶ arrow** next to each player's name (opens that player's
> perspective in a new tab).

---

## 1. Declaring a multiactive state (PHP)

Same state-class shape as any other state; only the `type` changes:

```php
class SimultaneousReady extends GameState {
    function __construct(protected Game $game) {
        parent::__construct($game,
            id: 20,
            type: StateType::MULTIPLE_ACTIVE_PLAYER,   // <-- the whole difference
        );
    }
}
```

## 2. Activating everyone (on entry)

Activate players **inside `onEnteringState`**, not before. Do not pre-set a single
active player in `setupNewGame` when the first state is multiactive.

```php
function onEnteringState() {
    $this->gamestate->setAllPlayersMultiactive();
    // (or setPlayersMultiactive([...ids], $nextState, $bExclusive) for a subset)
}
```

- `setAllPlayersMultiactive()` — all players become active simultaneously.
- `setPlayersMultiactive($players, $next_state, $bExclusive=false)` — activate a
  specific subset. `$bExclusive=true` deactivates everyone not in `$players`.

## 3. Each player acts, then removes *themselves*

A `#[PossibleAction]` runs **once per player, per click**. The relevant player is the
*current* player (the one whose browser sent the request) — NOT a single "active
player". Read it explicitly:

```php
#[PossibleAction]
public function actReady() {
    $playerId = (int) $this->game->getCurrentPlayerId();   // the player who clicked
    $this->notify->all("playerReady", clienttranslate('${player_name} is ready'), [
        "player_id"   => $playerId,
        "player_name" => $this->game->getPlayerNameById($playerId),
    ]);
    // Remove THIS player from the active set:
    $this->gamestate->setPlayerNonMultiactive($playerId, StartPlay::class);
}
```

- `setPlayerNonMultiactive($playerId, $nextState)` — deactivate one player.
- **The framework auto-fires the transition to `$nextState` when the LAST active
  player is removed.** "Wait for everyone, then move on" is free — you don't count
  players yourself. (Every `setPlayerNonMultiactive` call passes the same target;
  only the final one triggers the move.)
- `zombie(int $playerId)` for a multiactive state should just
  `setPlayerNonMultiactive($playerId, $nextState)` so a quitter doesn't block others.

## 4. Client side (JS) — the timing gotcha

Buttons are driven from **`onPlayerActivationChange`**, NOT `onEnteringState`.

**CONFIRMED behavior in this framework version (and it contradicts the skeleton's
generated comment):** the framework **calls `onPlayerActivationChange` itself when a
player becomes active, including on initial entry** to the state. `isCurrentPlayerActive`
is already correct there. So do all button rendering in `onPlayerActivationChange`, and
do **NOT** call it manually from `onEnteringState`.

> The skeleton's `Game.js` comment suggests calling
> `this.onPlayerActivationChange(args, isCurrentPlayerActive)` at the end of
> `onEnteringState`. **Don't** — in this version it produces a **DUPLICATE button**
> (we saw two "Ready!" buttons), because the framework already fired the callback.
> Leave `onEnteringState` empty for a multiactive state.

```js
class SimultaneousReady {
    onEnteringState(args, isCurrentPlayerActive) {
        // empty — framework calls onPlayerActivationChange itself on entry
    }
    onPlayerActivationChange(args, isCurrentPlayerActive) {
        if (isCurrentPlayerActive) {
            this.bga.statusBar.setTitle(_('${you} must get ready'));
            this.bga.statusBar.addActionButton(_('Ready!'),
                () => this.bga.actions.performAction('actReady'));
        } else {
            this.bga.statusBar.setTitle(_('Waiting for other players to be ready…'));
        }
    }
}
```
Register it like any state class: `this.bga.states.register('SimultaneousReady', instance)`.

## 5. Transitioning OUT of a multiactive state — gotcha

A multiactive state ends with **no single active player set**. A turn-based
`ACTIVE_PLAYER` state needs exactly one. So don't transition multiactive →
`ACTIVE_PLAYER` directly; go through a small **`GAME`** bridge state that picks the
first active player:

```php
class StartPlay extends GameState {            // type: StateType::GAME
    function onEnteringState() {
        $this->game->activeNextPlayer();        // establish the single active player
        return PlayerTurn::class;               // now safe to enter an ACTIVE_PLAYER state
    }
}
```

## 6. Reusable mental model for Reckoners (B3)

- Players rolling/acting at once = `MULTIPLE_ACTIVE_PLAYER` + `setAllPlayersMultiactive`.
- Each player resolves independently and calls `setPlayerNonMultiactive` when done.
- The "all players finished this phase" gate is automatic via the last-deactivation
  transition — no manual readiness counting.
- Sequence simultaneous phases by chaining multiactive → GAME bridge → next phase.

## 7. ⚠️ There is no "active but not my turn" — so a soft pass costs you the turn flag

BGA tracks exactly one bit per player: **multiactive or not.** There is no third state, and
**multiactive *is* "your turn"** everywhere the framework speaks for itself — the
games-in-progress list, the turn indicator, turn-based reminder mail, and the reflection clock.

This matters the moment you want an **interruptible pass**: "I'm done, but keep me in so I can
jump back if something changes." The obvious implementation — keep the passed player multiactive
so their "Continue" button stays clickable — silently tells the whole platform it is still their
turn. Reckoners shipped exactly that and a player reported the symptom directly: *"I passed but
BGA still shows it as my turn."*

`giveExtraTime` does not help: it moves the clock, not the flag.

**The pattern that works** is to make coming back the SERVER's job:

1. Keep your own per-player pass state in your schema — a tri-state, not a boolean:
   *still playing* / *done, final* / *waiting, re-openable*.
2. **Both** kinds of done call `setPlayerNonMultiactive`. The player leaves the active set, so
   the platform stops claiming it is their turn and (on realtime) the clock stops.
3. When something happens that a *waiting* player would want to react to, the acting player's
   own action re-activates them:
   `setPlayersMultiactive([$pid], $nextState, false)` — the `false` matters, it adds to the
   active set instead of replacing it. Give them a fresh clock at the same time.
4. Your phase-end gate reads YOUR column, not the active set: the phase ends when nobody is
   *still playing*, which waiting players satisfy.

A "waiting" player therefore cannot click their own way back in — by design. That is the price
of not lying to the turn system, and it is the right trade.

**Related trap — an undo that restores your pass column.** If undo snapshots the table holding
that column, restoring can hand a player back into the phase while the framework has already
dropped them (the phase then waits forever on someone who cannot act), or park a player who is
still active. Passing is usually *not* snapshotted, so the two drift. Re-sync the active set
against the column after any restore.

## 8. ⚠️ The state ends the moment the LAST player leaves — even mid-promise

`setPlayerNonMultiactive` fires the transition as soon as the active set empties. A multiactive
state that is holding something unfinished — a vote, a claim, anything one player owes another —
therefore has to keep somebody active itself. Nothing in the framework knows the obligation
exists.

Reckoners lost a live alpha table to this on **2026-09-24**. Its Purchase step lets a player
SUGGEST a purchase that every other player must confirm. Two players had finished buying; the
third suggested a card and pressed the step's own Wait button. That emptied the active set, the
step advanced, and the suggestion — which no longer had anyone able to answer it — silently
vanished.

Two distinct mistakes, and the second is the subtle one:

- **The obligation did not defend itself.** Every path that stands a player down (a "done"
  button, a "wait" pass, `zombie()`) must first ask *"is anything still owed?"* and re-activate
  whoever owes it. Do it in ONE place that every such path funnels through, not in each handler
  — the one you forget is the one a player finds.
- **"Parked by my bookkeeping" is not "out of the active set."** The fix for the pass pattern in
  §7 keeps your own *waiting* column, and it is tempting to write `wake()` as "re-activate
  everyone in my waiting column". But a player who pressed **Done** is not in that column — they
  are simply non-multiactive. Waking the parked players therefore does not bring back the
  finished ones, and an obligation addressed to a finished player can never be discharged.
  `setPlayersMultiactive([...], $next, false)` reaches only who you name;
  `setAllPlayersMultiactive()` is what brings the finished back too.

Cheap belt-and-braces once the above is right: refuse the stand-down actions outright while
something is addressed to that player ("answer it, or wait"), so the re-activation path is a
floor rather than the only guard. And clear the obligation's storage on the way OUT of the step,
because a table that ended the step under the bug still carries it in its saved state.

## Open questions
- Is there a built-in "some players may have nothing to do" helper, or do we
  `setPlayerNonMultiactive` them immediately in `onEnteringState`?
- Private per-player state (`initializePrivateStateForAllActivePlayers` /
  `nextPrivateState`) — seen in docs; explore when a phase has per-player sub-steps.
