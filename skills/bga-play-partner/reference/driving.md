# Driving Claude's seat

Only what differs from `bga-playtest`. Harness, login, lifecycle, the button-vs-title trap, and where
client state lives are there.

## Setting up a two-seat table

- **`Express start` on a 2+ seat table seats Studio test accounts** in the empty seats — the fast
  path for a two-driver table. Nothing drives them, so walk every seat through setup.
- **Verify configuration from the game state**, not the setup page: if an option changes the first
  state, one read of `gamestate.name` settles what the options did.
- Two Claude sessions (e.g. player + scribe, or two Claude seats) cannot share the persistent
  profile. The second copies `$BGA_SM_RUNTIME/profile` to its own scratch dir and launches from that.

## Taking Claude's seat

The seat switcher is inside the **game iframe**, in the player panel: `a.expressswitch`, href
`/tableview?table=<id>&as=<playerId>`. Navigate straight to that URL — more reliable than clicking.

Player ids are per account; read them off the switcher hrefs (or your client's player data) and record
the pair in `log.md` for the game you're on.

**Confirm the seat before the first click, and after every reload:**

```js
() => {
    const G = window.g_sitecore && window.g_sitecore.GameModule;
    if (!G) return {error: 'no GameModule'};
    const me = G.bga.players.getCurrentPlayerId();
    return {me, active: G.bga.players.isCurrentPlayerActive()};
}
```

`me` must be **Claude's** player id. If it reads the user's, do not click anything.

## Polling loop

```python
prev, same = None, 0
while True:
    st = frame.evaluate(STATE_JS)          # from bga-playtest/scripts/playtest_lib.py
    if st == prev:
        same += 1
        if same > STALL_LIMIT:              # print buttons on screen and say so
            break
    else:
        prev, same = st, 0
        # act / narrate on the new state
    page.wait_for_timeout(6000)
```

~6s while a phase is live; back off in `GAME` states. **Never reload between polls.**

## Two pages for simultaneous phases

When both seats act at once, use **two pages in one context** — each seat's half-made selection lives
in that page's JS, and navigating to switch seats destroys it. The client's action lock is per
session, so a second send while the first is in flight is refused client-side; that's an artifact of
one login, not a real-player bug.

## Traps that cost resources, not just time

- **Never click a market/shop slot by index.** The other seat buys concurrently and the slot
  refills; a remembered index points at a different card. Re-read the live market immediately before
  clicking, target by **name**, and **read the confirm text** (card *and* price) before confirming.
  Purchases are usually irreversible.
- **A stuck client refuses everything silently.** If valid clicks do nothing across different routes,
  read `#logs` for *"Please wait, an action is already in progress"*. Reload the tab, re-confirm the
  seat; nothing is lost.
- **Two-step menus:** choosing *what* (a symbol, an effect) and choosing *where* (a target) are often
  separate steps. Enumerate what's lit at the target step; never infer targets from the first
  button's label.
- **Undo boundaries:** learn where your game's undo stops (end of a unit's turn, end of phase). Treat
  that click as the irreversible one.

## Record game-specific mechanics here

As you learn them at the table — how a menu actually behaves, which targets light when, the
tells that a state is waiting on a board click — add them below, dated, with how they were confirmed.

<!-- e.g. ## Spend menus — learned YYYY-MM-DD -->
