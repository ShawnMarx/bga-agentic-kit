# 04 — The ability-dispatch pattern (one class per card/power)

*How to structure a game where many cards/powers/abilities each tweak the standard
flow at specific moments. Distilled from Santorini in the reference library
(`reference/bga-santorini/`, see `scripts/fetch-references.sh`). The pattern is pure PHP OOP — it works the
same in the modern skeleton or the classic layout, so it's reusable for Reckoners
(many epics + dice with bespoke effects).*

> **When this pattern earns its weight:** only when you have *many* bespoke effects
> (Santorini has ~70) that hook the *same* lifecycle points. For a handful of cards,
> a `switch` is simpler. Reckoners qualifies (epics, hero abilities, die faces) — but
> don't build the machinery until the dice POC is done and the repeated hook points
> are real, not guessed. See [[03-dice-poc-reusable-findings]].

## The shape (three parts)

1. **An abstract base** (`SantoriniPower.class.php`) declaring *every* lifecycle hook
   as a **no-op** (empty body, or `return null`). A concrete ability overrides only
   the few hooks it cares about and inherits do-nothing for the rest. This is the key
   that keeps each ability class tiny — Apollo is 72 lines and overrides just two
   methods (`Apollo.class.php`).
2. **One concrete class per ability** (`modules/powers/*.class.php`). Its constructor
   sets metadata (`id`, `name`, `title`, `text`, `playerCount`, `implemented`, …); its
   body overrides the relevant hooks. `implemented = false` lets you ship the class
   stub before the logic exists.
3. **A manager** (`PowerManager.class.php`) that owns:
   - a static **`$classes` map: `ID => 'ClassName'`** (the registry — the one place you
     edit to add an ability), and a `getPower($id)` **factory** (`new self::$classes[$id](...)`).
   - the **dispatch loop** `applyPower($methods, $args)` that calls a hook on every
     relevant active ability, in a fixed order.
   - lifecycle/CRUD for the cards (deal, move, discard, duplicate) and UI data.

## The hook taxonomy (the reusable idea)

Santorini's hooks fall into a few categories — copy the *categories*, rename to your
game. For each, there's usually a **player / teammate / opponent** variant so an
ability can react to its owner's turn *or* someone else's:

| Category | Example hooks | Purpose | Convention |
|---|---|---|---|
| **arg-modifiers** | `argPlayerMove(&$arg)`, `argUsePower(&$arg)` | mutate the set of *legal choices* offered to the UI | take `&$arg` **by reference**, add/remove options |
| **action overrides** | `playerMove($worker,$work)`, `playerBuild(...)` | replace/augment the default action | **return `true` to bypass** the default, `false`/array to keep it (`SantoriniPower.class.php:309-314`) |
| **after-hooks** | `afterPlayerBuild(...)`, `afterOpponentMove(...)` | react once an action has happened | side effects only |
| **state redirects** | `stateAfterMove()`, `stateStartOfTurn()` | send the FSM somewhere non-standard | **return a transition name or `null`**; manager errors if two abilities disagree (`PowerManager.class.php:997-1000`) |
| **win modifiers** | `checkPlayerWinning(&$arg)`, `checkOpponentWinning(&$arg)` | add/deny/steal a win condition | mutate `&$arg` |
| **lifecycle** | `setup()`, `startPlayerTurn()`, `endPlayerTurn()` | per-turn / on-acquire bookkeeping | |

## The dispatch loop (the heart)

`PowerManager::applyPower($methods, $arg)` (`PowerManager.class.php:684`) is the engine:

- It takes a **list of method names** — typically `[ownerHook, teammateHook, opponentHook]` —
  and fans them out **in order: active player's abilities → teammates' → opponents'**.
- It calls each via `call_user_func_array([$power, $method], $arg)`, so `$arg` passed
  **by reference** accumulates contributions from every ability. That's how multiple
  powers compose on one decision (e.g. one adds moves, an opponent removes some).
- Only abilities the player *currently has* are invoked (`hasPower` guard, line 704) —
  matters when an effect removes a power mid-resolution.

For FSM redirects, `getNewState($method)` (line 976) collects each ability's returned
transition, returns the single non-null one, and **throws if two abilities return
different states** — a built-in conflict detector worth copying.

## Two more reusable bits

- **Notification + logging live in base-class helpers**, not in each ability.
  `placeWorker`, `moveToken`, `removePiece` (`SantoriniPower.class.php:148-221`) each
  mutate state, write the game log, and `notifyAllPlayers` in one call — so ability
  classes read like rules text, not plumbing. Build the equivalent helpers (e.g.
  `rollDie`, `keepDie`, `spendDie`) for Reckoners early.
- **Combination validity as data**: `$bannedMatchups` (line 85) is a flat list of
  `[idA, idB]` pairs, and `computeBannedIds()` derives the banned set from the current
  offer. Reckoners' "which epics/heroes can coexist" rules can be the same flat table
  rather than scattered `if`s.

## Translating to Reckoners

| Santorini | Reckoners analogue |
|---|---|
| Power class per god | class per **epic / hero ability / special die face** |
| `argPlayerMove` (offer legal moves) | `argRollOptions`, `argSpendOptions` (what can I do with my dice?) |
| `playerMove` override | a die face / ability that **changes how a roll or spend resolves** |
| `afterPlayerBuild` | "after you roll" / "after damage dealt" reactive triggers |
| `stateAfterMove` redirect | abilities that insert an extra step into the turn FSM |
| `$bannedMatchups` | incompatible epic/hero combos |
| base-class `placeWorker`/notify helpers | `rollDie` / `applyDamage` helpers that notify+log |

## Caveats / gotchas

- **The `$classes` registry is the single source of truth** and must be hand-kept in
  sync with the files in `powers/`. Easy to forget when adding an ability.
- Reflection-style dispatch (`call_user_func_array`, `$power->$method()`) means typos
  in hook names fail at runtime, not compile time — the `_ide_helper.php` stubs help,
  but write a smoke test that instantiates every registered class.
- `&$arg` by-reference is load-bearing across the whole pattern; a hook that takes
  `$arg` by value silently does nothing.
- This is **heavyweight**. It pays off past ~10+ effects sharing hook points; below
  that it's over-engineering (see the warning at top).

## Source pointers (reference library, not our code)

- `bga-santorini/modules/SantoriniPower.class.php` — the abstract base + every hook.
- `bga-santorini/modules/powers/Apollo.class.php` — a minimal two-hook example.
- `bga-santorini/modules/PowerManager.class.php` — registry, factory, `applyPower`
  dispatch (684), `getNewState` conflict detection (976), `$bannedMatchups` (85).
- `bga-santorini/modules/PlayerManager.class.php` — `getOpponents`/`getTeammates`
  used by the fan-out.

> License: Santorini is third-party code (`bga-santorini/LICENCE_BGA`). Learn and
> cite; do not paste verbatim into a published game.
