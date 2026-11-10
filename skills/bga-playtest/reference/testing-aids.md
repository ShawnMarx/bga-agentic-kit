# Testing aids: reaching a state without playing to it

Most game states are behind irreversible actions and luck. These are the cheap ways in, roughly in
order of how much they prove.

## 1. Debug constants in `Game.php` (proves server + client)

Build flags into your game class, default `0`, and document each in your repo's `CLAUDE.md`.
*(Reckoners)* examples:

- `DEBUG_REWARDS = N` — every reward step banks N extra of each assignable reward, so the reward UI
  is reachable without first earning rewards.
- `DEBUG_TEST` — front-loads cards under test into the market and grants extra starting money.

Rules:

- **Setup-time flags only matter at table START** (anything read in `setupNewGame` / board seeding):
  flip on → deploy → create and start a table → flip off → redeploy.
- **Check it took** — read the seeded value on the table. A table started immediately after a deploy
  has been seen to seed the old values.
- **Every debug flag must be off before a build.** `bga-cut-build` checks this; name your flags
  consistently (`DEBUG_*`) so the check is a grep.

## 2. Debug actions (proves server + client, targeted)

BGA Studio exposes `debug_*` methods on the game class (e.g. "give this player card X", "move this
piece to the discard"). Call them from the game frame:

```js
gameui.ajaxcall('/$BGA_PROJECT/$BGA_PROJECT/debug_giveCard.html',
                {cardId: 12, lock: true}, gameui, () => {}, () => {})
```

then reload. Substitute your project name. Good for states several rounds away (a captured piece, a
depleted deck).

## 3. Know what your randomness CAN produce

Before burning rerolls or redeals hoping for an outcome, check the data tables. *(Reckoners)* each die
colour has exactly one doubled face, so one colour could never roll a doubled *action* — the test
needed a card that grants an extra die, or a staged face.

## 4. Stub the send (proves the client only)

Answer "what lights, what the bar offers, what a click would send" without a server round-trip:

```js
const G = window.g_sitecore.GameModule; window.__sent = [];
G.bga.actions.performAction = (a, b) => { window.__sent.push([a, b]); return Promise.resolve(); };
```

Then drive the UI and read `window.__sent` for the exact action name and args. The client does NOT
advance after a stubbed send (no notification comes back), so Cancel or reload between cases — a
half-finished walk spoils every case after it.

## 5. Stage client state (proves the client only)

Set the fields you need on `GameModule` objects (a die's faces, a player's tokens, a piece's location)
and call your own re-render helpers. Only the re-rendered part changes.

**Report it as "staged client-side, unverified in play"**, and drive at least one real action through
the server before calling a flow done.

## Scale tests to the worst case

Limits that scale with board size won't show on a small table. BGA caps **one action's notifications
at 128KB total** ("generated notifications are larger than 128k"), aborting the transition with a red
banner. Anything that emits a payload per step (a step-through animation sequence, a per-beat board
snapshot) needs checking at max players on a full board, not at 2. Send patches, not whole-board
snapshots, per beat.
