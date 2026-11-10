# BGA reference library — index

Read-only snapshots of real, working Board Game Arena games, kept here as **grep
substrate** for implementing features in your game.

- These are **other people's code** (see each repo's `LICENCE*`). Read, learn, and
  **cite** — do **not** paste verbatim into a published game without checking the license.
- Fetch them with `scripts/fetch-references.sh` (into the gitignored `reference/`). Paths below are relative to `reference/`.
- The durable, distilled knowledge lives in
  `docs/framework/`. When a pattern here proves
  useful, extract it there with a citation back to the file below. This folder is the
  raw source; framework-notes is the memory.

## The repos

| Folder | Game | Template style | Best for |
|---|---|---|---|
| `bga-heartsla/` | Hearts (elaskavaia tutorial) | **Modern** — `modules/php/Game.php` + per-state classes in `modules/php/States/` | Canonical idiomatic structure; closest to the modern skeleton |
| `bga-santorini/` | Santorini (AntonioSoler) | **Classic** — root `santorini.game.php` + `modules/*.class.php` | Mid-complexity logic; **one-class-per-ability** pattern (~80 `powers/*.class.php`) — the fit for a game with many bespoke card effects |
| `bga-sharedcode/` | elaskavaia demo/util game | Classic | Reusable utilities, animations, and a kitchen-sink demo of components |

## API signature ground truth (read these to avoid hallucinated methods)

- `bga-heartsla/_ide_helper.php` — PHP stubs for the framework `Table`/`APP_*` classes.
- `bga-heartsla/bga-framework.d.ts` — TypeScript/JS stubs for the client framework.
- `bga-sharedcode/_ide_helper.php` — second copy of the PHP stubs.

If a framework method's signature is in doubt, grep these first; they are more reliable
than my training data.

## Feature → where to look

**State machine / game flow**
- Modern style: `bga-heartsla/modules/php/Game.php` (the `machinestates` wiring) +
  `bga-heartsla/modules/php/States/{NewHand,PlayerTurn,NextPlayer,EndHand}.php`
  (discrete state classes — the newest BGA pattern).
- Classic style: `bga-santorini/states.inc.php` + the `st*` / `arg*` / action methods in
  `bga-santorini/santorini.game.php`.

**Per-card / per-ability logic (many bespoke effects)**
- `bga-santorini/modules/powers/*.class.php` + `bga-santorini/modules/PowerManager.class.php`
  — one class per power, dispatched by a manager. This is the model to study before
  Reckoners' card abilities.

**Player management**
- `bga-santorini/modules/PlayerManager.class.php`.

**DB schema & queries**
- `*/dbmodel.sql` for table design; grep `DbQuery` / `getCollectionFromDB` /
  `getObjectFromDB` across `*.game.php` and `modules/` for query idioms.

**Client JS (setup, notifications, animations, UI events)**
- `bga-santorini/santorini.js` (64K, full-featured) and `bga-heartsla/heartslav.js`.
- Animations / token movement helpers: grep `bga-sharedcode` (the community animation
  utilities live here).

**Game config / options / stats**
- `*/gameinfos.inc.php`, `*/gameoptions.*`, `*/stats.*`.

## Maintenance

These are snapshots, not tracked clones. To refresh, re-clone with `--depth 1`, then
re-strip `img/`, `_assets/`, and `.git/`. Add new repos here only when they uniquely
demonstrate a feature we actually need (e.g. deck-building → bga-hardback,
PHPUnit setup → bga-innovation, modern OOP framework → bga-bang).
