# 01 — Skeleton anatomy & the state machine

Source: the freshly-generated `tutorialdumahatreides` skeleton (modern 2024+ BGA
framework). This is the baseline every new game starts from.

---

## 1. The files and what each is *for*

BGA enforces a strong separation of concerns. Each file has one job:

| File | Side | Job |
|---|---|---|
| `gameinfos.jsonc` | meta | Game metadata: name, player counts, durations, colors, tie-breaker text, interface width. **No logic.** |
| `gameoptions.jsonc` / `gamepreferences.jsonc` | meta | Player-selectable setup options & UI preferences. |
| `stats.jsonc` | meta | Declares the statistics the game tracks (must be declared here before `init()` works in PHP). |
| `dbmodel.sql` | server | Schema for **game-specific** tables. The standard tables (`player`, `global`, `stats`, `gamelog`) already exist — do **not** recreate them. Schema is (re)built from this file each time a game *starts*. |
| `modules/php/Game.php` | server | Core game logic: one-time `setupNewGame`, the `getAllDatas` snapshot, progression, DB migration, debug helpers, shared state (e.g. card-type tables, Component handles). |
| `modules/php/States/*.php` | server | **The state machine** — one PHP class per state. This is the heart of the game. |
| `modules/js/Game.js` | client | UI logic: `setup()`, one JS class per state, notification handlers. (TS version lives in `src-disabled/ts/`; rename to `src` to enable.) |
| `<project>.css` | client | Styling. |
| `bga-framework.d.ts`, `_ide_helper.php` | tooling | Type/stub files for editor autocomplete only — not shipped logic. |

---

## 2. The mental model: a BGA game is a finite state machine (FSM)

Everything a game does is modeled as moving between **states**. At any moment the
game sits in exactly one state. A state either:

- **waits for a player to act** (a *player* state), or
- **runs server code automatically and immediately transitions** (a *game* state).

Each state class is constructed with:
- `id` — a stable integer identifier (used by `jumpToState`, debug, etc.).
- `type` — a `StateType` (see below).
- optional flags like `updateGameProgression: true`.

### State types seen so far
- `StateType::ACTIVE_PLAYER` — one player is active; game waits for their action.
  (`PlayerTurn`, id 10)
- `StateType::GAME` — automatic/server state, no player input. Runs
  `onEnteringState()` then returns the next state. (`NextPlayer` id 90, `EndScore`
  id 98)
- `StateType::MULTIPLE_ACTIVE_PLAYER` — *(not in skeleton yet)* several players
  active simultaneously. **This is the one the Reckoners dice POC (B3) needs.**
  Hooks: client `onPlayerActivationChange` fires as each player becomes (in)active.

### Transitions are return values, not a config table
In the modern framework you **return the next state's class** (or a terminal id)
from a state method, e.g. `return NextPlayer::class;`. This replaces the old
`states.inc.php` giant array of numeric `transitions`. Concepts map 1:1; the
mechanism is just "return the destination."

---

## 3. The skeleton's actual game loop

```
setupNewGame()  ──returns──▶  PlayerTurn (10, ACTIVE_PLAYER)
                                  │  player clicks a card or Pass
                                  │  → server action runs
                                  ▼
                              NextPlayer (90, GAME)
                                  │  onEnteringState: giveExtraTime,
                                  │  activeNextPlayer, check game end
                            ┌─────┴─────┐
                       not over       game over
                            │             │
                            ▼             ▼
                        PlayerTurn     EndScore (98, GAME)
                                          │  onEnteringState
                                          ▼
                                       ST_END_GAME (99)  ← built-in terminal state
```

Walking each node:

**`Game::setupNewGame($players, $options)`** — runs once at game creation.
- Seeds per-player data (here: `playerEnergy->initDb(..., initialValue: 2)`).
- Inserts players into the `player` table with assigned colors.
- `reattributeColorsBasedOnPreferences` + `reloadPlayersBasicInfos` apply favorite-color prefs.
- `activeNextPlayer()` picks the first active player.
- **Returns `PlayerTurn::class`** = the starting state.

**`PlayerTurn` (ACTIVE_PLAYER)** — `modules/php/States/PlayerTurn.php`
- `getArgs()` returns per-state data sent to the client (here `playableCardsIds`).
  Client reads it as `args` in `onEnteringState`.
- `#[PossibleAction] actPlayCard(int $card_id, int $activePlayerId, array $args)`
  — a player action. (see §4 for how it's wired.)
  Validates input, notifies all players, increments score, **returns `NextPlayer::class`**.
- `#[PossibleAction] actPass($activePlayerId)` — notifies, grants energy, returns `NextPlayer::class`.
- `zombie(int $playerId)` — what to do when an active player has quit. **Never** use
  `getCurrentPlayerId()` here; use the passed `$playerId`. Can return a transition or
  delegate to an action method.

**`NextPlayer` (GAME)** — `modules/php/States/NextPlayer.php`
- `onEnteringState(int $activePlayerId)` runs automatically.
- `giveExtraTime()` tops up the player's clock after a completed action.
- `activeNextPlayer()` advances the active player.
- Decides game-over → returns `EndScore::class` or loops back to `PlayerTurn::class`.
- `updateGameProgression: true` → framework calls `Game::getGameProgression()` on entry.

**`EndScore` (GAME)** — `modules/php/States/EndScore.php`
- `onEnteringState()` is where final scores/stats are computed.
- Returns the constant `ST_END_GAME = 99` — the framework's built-in terminal state
  that actually ends the game.

---

## 4. How a player action is wired (client ↔ server)

The modern framework auto-wires actions; there is no manual ajax plumbing.

1. **Client** (`Game.js`, inside a state class) calls
   `this.bga.actions.performAction("actPlayCard", { card_id })`.
2. **Server** routes it to the method named `actPlayCard` on the *current* state
   class, **only because it carries the `#[PossibleAction]` attribute**. Without that
   attribute the method is not callable from the client.
3. **Parameters are injected by name:**
   - `$card_id` ← matches the key in the client's payload.
   - `$activePlayerId`, `$args` ← injected by the framework (current active player,
     and the result of this state's `getArgs()`).
4. The method does its work and **returns the next state class** to transition.
5. Validation failures throw `UserException('...')` — surfaced to the player as a
   red error message, action rejected.

Key idiom: **action method name = the string passed to `performAction`**, and it
must live on the state class that's currently active and be marked `#[PossibleAction]`.

---

## 5. The three client↔server data channels

There are exactly three ways server data reaches the client. Don't confuse them:

| Channel | Server source | Client sink | When |
|---|---|---|---|
| **Full snapshot** | `Game::getAllDatas($currentPlayerId)` → `players`, counters via `fillResult`, etc. | `Game.setup(gamedatas)` | On game load and every F5 refresh. **Must filter to what `$currentPlayerId` is allowed to see** (hidden-info safety). |
| **Per-state args** | `<State>::getArgs()` | state class `onEnteringState(args, ...)` | Each time that state is entered. |
| **Notifications** | `$this->bga->notify->all("name", msg, [args])` | `notif_<name>(args)` handlers | Incremental updates *during* play (a move happened). |

Notification handlers are auto-subscribed: name a client method `notif_cardPlayed`
and `setupPromiseNotifications()` wires it to the `"cardPlayed"` notify call. The
log message string (`'${player_name} plays ${card_name}'`) also shows in the game log.

### ⚠️ Notifications are ONE-SHOT — a reload replays nothing

The three channels are not interchangeable, and this is the way that bites. **A client that
reloads, or a player who joins late, receives `getAllDatas()` and nothing else.** Past
notifications are never re-delivered; their *log message* survives in the game log panel, but
their `args` — and therefore anything the handler built out of them — are gone.

So: **any client state assembled from a notification, and expected to still be on screen later,
must ALSO be reachable from `getAllDatas()`.** The failure is silent and looks like a rendering
bug — the board is correct (it came from `getAllDatas`), only the narrative around it is missing.

It bites hardest wherever a state's whole purpose is to hold something on screen for the player
to read. Reckoners hit it on 2026-09-07: Epic/Steelheart activation is choreographed client-side
from one notification per phase, and the review-gate state that follows exists purely so everyone
can read what happened — so an F5 landed the player on a gate with nothing to review.

Two fixes, and the choice is a real one:

- **Persist the lines** (a static recap) — cheap, small, but the player reads a transcript.
- **Persist the notification PAYLOAD verbatim** and have the client re-dispatch it through the
  same `notif_*` handler on load — the player watches the actual sequence, and there is no second
  choreography to drift out of step with the first. Costs storage, and needs a budget guard if the
  column is `TEXT` (64KB).

If the payload carries per-beat *patches* rather than full snapshots, replaying is still exact
**provided the first beat carries a full snapshot** — patch chains are self-anchoring from there,
so store and replay whole sequences in order rather than individual beats.

---

## 6. Recurring idioms / gotchas

- **Translation:** `clienttranslate('...')` marks server strings for extraction;
  `_('...')` does it client-side. `${placeholder}` tokens are filled from notify
  args. The `i18n` array (e.g. `"i18n" => ['card_name']`) marks which *arg values*
  must themselves be translated (because they're game terms, not player-typed text).
- **Notification decorator** (commented example in `Game.php`): lets you auto-fill
  common args (`player_name`, `card_name`) once instead of on every `notify->all`
  call. If enabled, you delete the per-call duplicate args.
- **Components** (framework helpers that replace hand-rolled SQL):
  - `PlayerCounter` — a typed per-player integer (here `energy`). Created via
    `$this->bga->counterFactory->createPlayerCounter('energy')`. API: `initDb()`,
    `inc()`, `fillResult()` (push into getAllDatas). Client mirrors it with
    `new ebg.counter()` + `{ playerCounter: 'energy', playerId }` for auto-sync.
  - "Deck" component (referenced, not used) — standard card table tooling; needs the
    `card` table shape shown commented in `dbmodel.sql`.
- **Two notify handles appear:** `$this->bga->notify->all(...)` and
  `$this->notify->all(...)` are both used in `PlayerTurn`. They reach the same
  system; `$this->bga->...` is the explicit path. *(TODO: confirm whether
  `$this->notify` is a convenience alias on GameState.)*
- **Globals:** integer game globals use IDs 10–99 via
  `getGameStateValue`/`setGameStateValue`; for non-int use `$this->globals`.
- **Debug helpers** in `Game.php` (`debug_goToState`, `debug_playOneMove`) are
  triggerable from the Studio Debug button — handy for jumping the FSM during testing.
- **Schema changes require restarting a game** to take effect (dbmodel.sql is applied
  at game start, not hot-reloaded).
- **BGA's stylesheet stretches a bare `<button>` inside the game area** to its
  container's width. Custom controls of your own (an icon button in a panel you
  drew yourself, not a `.bgabutton` in the status bar) therefore need an explicit
  `width`/`max-width`, or they render as full-width bars. Reckoners shipped a pair
  of thumb icons as two coloured bars this way (2026-09-22) — it looks like a flex
  mistake in your own CSS, and it is not.

---

## Open questions to resolve later
- `$this->notify` vs `$this->bga->notify` — alias or two things?
- Exact lifecycle hooks available on a state class (`onEnteringState`,
  `onLeavingState`, `getArgs`, `zombie` seen; is there `onEnteringState` arg
  injection beyond `$activePlayerId`?).
- How `MULTIPLE_ACTIVE_PLAYER` activation/transition differs (the B3-critical one).
