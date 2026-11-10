---
name: bga-studio-loop
description: The edit → preflight → deploy → verify loop for a Board Game Arena Studio game. Use when pushing changed game files (JS, CSS, PHP, JSONC, SQL, images) to Studio, before any deploy (to run the syntax/lint/cssnano gate), when a deployed change "does nothing", when a game page says "Not logged in (studio)", when a table 500s with "Gameserver is locked by configuration", or when deciding whether a load failure is your code or BGA's.
---

# The BGA Studio loop: edit → preflight → deploy → verify

A BGA game runs only on Studio's servers. There is no local runtime, so "does it work" means: the
files passed the gate, they landed on Studio, and a **fresh** page load of a table shows the change.
Every step below exists because skipping it has shipped something broken.

## Setup this skill assumes

- `$KIT` is your `bga-agentic-kit` checkout. Config comes from the gitignored `$KIT/bga.local.env`
  (or a per-game `<game repo>/.bga.env`, or `$BGA_ENV_FILE`; already-exported env vars win):
  `BGA_PROJECT`, `BGA_GAME_REPO`, `BGA_SFTP_HOST_ALIAS`, `BGA_SM_RUNTIME`, `BGA_GAME_ID`.
- An `~/.ssh/config` Host block named by `BGA_SFTP_HOST_ALIAS`, using a **dedicated** key (no
  passphrase if you want non-interactive deploys) registered at
  `https://studio.boardgamearena.com/controlpanel`. One key per machine; never reuse keys across
  services. The block template is in the header of `$KIT/tools/bga-session-manager/deploy.sh`.
- The harness is set up once with `$KIT/tools/bga-session-manager/setup.sh`, then logged in with
  `bga.sh login.py` (a human at the keyboard, once per machine/session expiry).
- Optional in the game repo: `eslint.config.mjs` (`scripts/new-game.sh` copies the kit's template;
  `preflight.sh` falls back to the kit's copy). Add any extra globals your client uses there.

## 1. Preflight gate — every check, chained with `&&`

Run from the game repo root:

```bash
"$KIT/scripts/preflight.sh" && "$KIT/tools/bga-session-manager/deploy.sh" modules/js/Game.js "$BGA_PROJECT.css"
```

`preflight.sh` runs every check below, skips any whose files are absent, lints only changed PHP
(`PHP_ALL=1` for all), and takes `JS=` / `CSS=` overrides. Spelled out, it is:

```bash
node --check modules/js/Game.js \
  && npx --yes eslint@9 --no-config-lookup -c eslint.config.mjs modules/js/Game.js \
  && python3 "$KIT/scripts/check_state_scope.py" modules/js/Game.js \
  && php -l modules/php/Game.php && php -l modules/php/States/SomeState.php \
  && npx --yes -p postcss-cli@11 -p cssnano@7 -p postcss@8 \
       postcss "$BGA_PROJECT.css" --use cssnano --no-map -o /dev/null \
  && "$KIT/tools/bga-session-manager/deploy.sh" modules/js/Game.js "$BGA_PROJECT.css"
```

**`&&`, never `;`.** A `;` runs the upload even when the check just failed — that is exactly how a
file with a syntax error reaches a live table.

What each check catches, and why none is optional:

| check | catches | misses |
|---|---|---|
| `node --check` | JS parse errors | every name-resolution error |
| eslint `no-undef` | a variable used outside the scope that defines it (`Uncaught ReferenceError` in the browser = a red banner over the table) | property access on `this` |
| `check_state_scope.py` | modern-skeleton clients with state classes (`constructor(game, bga)`, game is `this.game`) **and** a Game class (helpers are `this.helper()`): a line copied from one into the other parses, lints, then throws. The client wedges on "Updating…" while the server advances — looks like a hung table | anything outside that pattern |
| `php -l` | PHP parse errors. Worse than a JS one: a server class that fails to construct takes the table down before your code runs, which looks like an infrastructure fault | runtime errors |
| **cssnano** | what the **BGA build** runs. Browsers silently skip a broken selector; cssnano hard-fails, and it fails at *Build game* — after the build is committed and tagged. It reports the server's error verbatim, line and column | a valid selector that matches nothing |

- `csstree-validator` is **not** a substitute: it validates declarations, not selectors, so a
  selector made of runaway prose passes it.
- **Never write the comment-close character pair inside a CSS comment** — not even while quoting it
  in an explanation. The comment closes early and the rest of the prose becomes a selector. Write
  "comment-close" in words.
- If the client isn't organised as state classes + Game class, drop `check_state_scope.py` rather
  than trusting its silence.

## 2. Deploy

```bash
D="$KIT/tools/bga-session-manager/deploy.sh"
"$D" modules/js/Game.js modules/php/Game.php          # paths are game-repo-relative
"$D" --mkdir img/newfolder                             # `put` does NOT create remote dirs
"$D" --delete modules/php/States/OldState.php          # remove a remote orphan
```

- **Orphans break the state scanner.** `modules/php/States/` on the server must contain only real
  state classes; a stray `.php` there fails game creation ("Invalid id … / should be of namespace
  …"). When you delete or rename a state locally, `--delete` it remotely too.
- **Not every file takes effect on upload:**
  - `gameinfos.jsonc` → control panel **"Reload game informations"**.
  - `gameoptions.jsonc` / `gamepreferences.jsonc` → **"Reload game options & player preferences
    configuration"**.
  - `dbmodel.sql` → only a **new table** gets the new schema. Use only full-line `-- comments` in
    it: a trailing inline comment after a column definition makes the loader silently skip the
    column ("Unknown column" at runtime).
- **Line endings:** a file last deployed from Windows is CRLF. Compare with
  `diff <(tr -d '\r' < remote) local` before concluding Studio has drifted.

## 3. Verify on a fresh page load

**BGA caches `.js`/`.css` aggressively.** A deploy you verify without busting the cache is a deploy
you didn't verify. Hard-refresh (Cmd/Ctrl+Shift+R) in a browser, or from the harness:

```bash
B="$KIT/tools/bga-session-manager/bga.sh"
"$B" find_table.py                                     # candidate table URLs
"$B" capture.py "<table url>" --enter-game --clear-cache --wait 12 \
     --dump "#pagemaintitletext, #generalactions .bgabutton" --screenshot --studio-logs
```

Green = empty `== PAGE ERRORS ==`, your expected title/elements in the dump, and nothing in the
Studio logs. To step a table through states rather than just observe it, use the `bga-playtest`
skill (`drive.py`).

### False green lights

- **The file didn't land.** Add a temporary `console.log('[marker-N]')`, deploy, capture; no marker
  in the console = stale code. Remove it after.
- **The table is expired/idle.** An old table's realtime socket is dead: actions hang on "Move
  recorded, waiting for update…". Verify on a fresh, in-time table.
- **The table was built before the change.** Schema and setup-time seeding only apply at table
  start.
- **A CSS rule that parses and matches nothing.** Measure it on the table
  (`getComputedStyle(el).width`), don't assume it applied.
- **A reconnect shows the game advanced** — which can mean the *client* threw and the server moved
  on without it. Read PAGE ERRORS, not just the state.
- **Clicked a title, not a button.** See `bga-playtest` ("click the button, not the prompt").

## When the table won't load

**"Not logged in (studio)"**, the page renders but `window.gameui` never appears: Studio's SSO
cookies are session-only and the game-server frame needs them. Run `bga.sh login.py` again; it
snapshots cookies to `$BGA_SM_RUNTIME/cookies.json` and every launch re-injects them. Main-site
pages (alpha tables, bug reports, replays on `boardgamearena.com`) are a **separate** login:
`bga.sh login_main.py` (saved to `cookies-main.json`). "Unable to load this report" on a bug link is
usually just that login missing.

**"Gameserver is locked by configuration"** (a 500 from BGA's own `webActionCore`, thrown before your
`Game.php` is constructed) and you can't create a table because one is "already in progress" — yet
the stuck table appears on no listing:

1. Open `https://studio.boardgamearena.com/lobby?game=$BGA_GAME_ID`.
2. Try to **create** a game. The "already in progress" error **links to the stuck table** — the only
   place it shows.
3. Follow the link, then **Express stop**.

Do not script this against `/table/table/quitgame.html` or `createnew.html`: they reject a synthetic
call at `setAjaxMode()` (feException 806, "Invalid session information") even with
`bgaConfig.requestToken`, GET or POST. The UI path is the working one.

**Is it my code?** `https://studio.boardgamearena.com/studioissues?game=$BGA_PROJECT` lists the
week's PHP and JS errors. "No errors!" there is good evidence a load failure is not yours. If
`php -l` was clean and the table still won't start, it is not a parse error — check there and try the
lock recovery above.

## What "deployed" means

Studio files are what Studio tables run. Alpha/beta players run a **build** snapshot, which a deploy
does not touch — see `bga-cut-build`. After any deploy, the deployed files should match your working
branch; if they drift, the branch is what needs the commit.
