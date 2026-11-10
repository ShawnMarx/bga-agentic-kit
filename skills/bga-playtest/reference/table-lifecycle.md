# Table lifecycle on Studio

Everything here was verified on a live Studio project. URLs use `$BGA_GAME_ID` (numeric Studio game
id) and `$BGA_PROJECT` (project name) from your kit config.

## The happy path

1. **Create** — `https://studio.boardgamearena.com/lobby?game=$BGA_GAME_ID`, click **Create**. You
   land on `table?table=<id>&nr=true`.
   - The Create control is an element with id `joingame_create_$BGA_GAME_ID`. Its `href`
     (`table?table=create_<gameid>&nr=true`) is a **decoy** — navigating there throws *"Bad
     argument type: table should be a Number"*. Click the element; don't follow the href.
2. **Check the table page before starting.** The lobby remembers the last table's seat count and
   options, so Create can hand you a 2-seat table when you expected solo. Read `Number of players`.
3. **Start** — `Express start` fills empty seats with Studio **test accounts** (it does *not* drop
   a 2-seat table to solo); plain `Start game` (`#startgame`) starts with the seats present. The page
   then reads "Game in progress" with a `Go to game` link.
4. **Enter** — `Go to game` → `tableview?table=<id>`, the URL to reuse. If a bare `tableview` loads
   no game iframe, enter from the table page via `#access_game_normal`.

## Configuring a table

- Order the edits: **seat count first** (`#wanted_plus` / `#wanted_minus` — JS-click them), then
  mode, then speed — reloading and re-reading after each.
- Solo tables on Studio are **Training mode only** for many games ("Solo mode … can only be played in
  Training mode"); Training forces "No time limit". A 1-seat Normal table can be made via hidden range
  controls (`#wanted_min_min` …) but Start may refuse it.
- **Game options save asynchronously.** Each option is a hidden `<select>`
  (`#gameoption_<id>_input`) behind a styled control, so Playwright's `select_option` refuses it.
  Setting `el.value` plus a bubbling `change` works, but the save is a background request and
  `Express start` can outrun it. **Set → reload `table?table=<id>&nr=true` → re-read → retry, then
  start.** Sometimes it will not commit from a script at all; don't fight it — drive around it.
- **Verify the configuration from the game, not from the setup page.** If option X routes setup to a
  different first state, one read of `gamestate.name` settles what the options actually did. Better
  still, cross-check an independent invariant the option controls (a starting value that differs per
  difficulty).

## Traps that block Create

- **An UNSTARTED table silently disables Create.** The lobby's Create then opens a wizard that renders
  no game-option `<select>` at all, so option-setting finds nothing and the run proceeds at whatever
  the last table used. Reach the pending table directly at `table?table=<id>&nr=true` (it carries
  the options *and* `Express start`), or quit it (`#quit_game`).
- The lobby may show `Open / Configure / Quit` with `Configure` present in the DOM but **not
  visible** — a click times out. Go straight to the table URL; collect ids from the lobby's
  `a[href*="table="]` links.
- **Table ids are not monotonic.** Never pick "the newest-looking" one.

## Quitting

- Table page: **`Express stop`** (fast) or `Quit game`. In game: `ingame_menu_quit` →
  `#quitgame_confirm`.
- **Stuck table** ("Gameserver is locked by configuration", listed nowhere): lobby → try Create → the
  "already in progress" error links to it → Express stop. Do not script `/table/table/quitgame.html`
  or `createnew.html` — they reject synthetic calls (feException 806) even with
  `bgaConfig.requestToken`.
- A finished table's page (`table?table=<id>`) shows **end-of-game stats** — the cheapest way to see a
  stat change without playing a game out.

## Multiple seats from one login

A real multiplayer table is drivable from one Studio login. Behaviours that only exist between
players (hand-offs, "waiting for other players" strings, one player's action waking another) are
testable — don't write them off as "needs two humans".

- Each seat has an `a.expressswitch` link in the player boards (inside the **game iframe**) pointing
  at `tableview?table=<id>&as=<playerId>`. Navigating straight to that URL is the reliable route.
- **Player ids are per account** — read them off the switcher hrefs or your client's player data;
  never hard-code them across tables.
- Confirm the seat after landing and after every reload: `GameModule` (or `gameui`)
  `player_id` / `this.bga.players.getCurrentPlayerId()`.
- **Step every seat in one loop**, acting only on the seat `bga.players.isPlayerActive(id)` says is
  active.
- **Use two PAGES in one context, not navigation, for simultaneous states.** Each seat's half-made
  client selection lives in that page's JS; navigating away to switch seats destroys it.
- **The client action lock is per session, not per seat.** Two seats in one browser share it, so the
  second seat's send is refused client-side (*"Please wait, an action is already in progress"*,
  `performAction` returns `undefined`) before it reaches the server. That is an artifact of one
  login. To test a real race, send the second request after the first completes — BGA serialises
  actions per table anyway.
- **Test the server guard separately from the UI.** A good client guard clears a stale selection
  before you can click, so the UI path never exercises the server check. Call the action directly
  with stale args and assert on **state** (resources, market, ownership unchanged), not just the
  thrown error:
  ```js
  await G.bga.actions.performAction('actBuyCard', {slot: 0, cardId: STALE_ID})
  ```
- **Two drivers at once** (two sessions): the persistent profile can be held by only one. The second
  session copies `$BGA_SM_RUNTIME/profile` into its own scratch dir and launches from the copy — the
  login comes across intact.
- Watch memory: two seats plus a reload pass can exhaust a laptop. One context, two pages.

*(Reckoners)* A multi-handed setup state staged the count on click and only committed on a separate
`Confirm`; a loop that re-clicked the number stalled forever looking busy. Expect two-step choices.
