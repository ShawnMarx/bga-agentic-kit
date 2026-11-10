# CLAUDE.md

<!-- Template from bga-agentic-kit. Fill in every <…>; delete guidance comments as you go.
     Everything NOT in angle brackets is a rule that was paid for on a previous game — keep it
     unless you have a reason, and if you drop one, say why in a comment so the next session
     doesn't reintroduce it. -->

## What this is

Board Game Arena implementation of **<Game Title>** (<Publisher>), on the modern (2024+) BGA
Studio skeleton: PHP state classes + JSONC config + a plain-JS client. <Co-op / competitive,
player counts, solo mode, anything that shapes the state machine.>

> **<PRIVATE REPO ONLY / public OK>.** Publisher art, rulebooks and print files are confidential
> (BGA T&C art. 6.b). They are gitignored and kept local-only — never commit anything under
> `img/official/`, `**/references/`, or `*.publisher.psd`. <Adjust the paths in .gitignore.>
> "Local-only" means one copy on one machine: keep a synced backup somewhere that is not git.

## Kit and machine config

Tooling comes from **bga-agentic-kit** (`<path to kit>`), configured by this repo's gitignored
`.bga.env` (copy the kit's `bga.local.env.example`). Machine-specific facts — SFTP user, key
name, where notes go — live in the developer's private setup note, not here.

Shorthand below: `$KIT` = the kit checkout.

## Edit → check → deploy → verify (IMPORTANT)

There is **no local way to run the game** — it runs on BGA Studio's servers. You see a change
by deploying the files and loading a Studio table.

```bash
$KIT/scripts/preflight.sh && $KIT/tools/bga-session-manager/deploy.sh modules/js/Game.js <project>.css
$KIT/tools/bga-session-manager/deploy.sh --mkdir img/newfolder    # put does NOT create remote dirs
$KIT/tools/bga-session-manager/deploy.sh --delete modules/php/States/OldState.php
```

- **Chain checks to the deploy with `&&`, never `;`.** A `;` uploads even when the check failed.
- `preflight.sh` runs: `node --check` → eslint `no-undef` → `check_state_scope.py` → `php -l` on
  changed PHP → **cssnano** (what the BGA build itself runs). Each one exists because the one
  before it let a broken file reach a live table. Details: `$KIT/skills/bga-studio-loop/`.
- After deploying, **hard-refresh** (Cmd/Ctrl+Shift+R) or use `capture.py --clear-cache`. BGA
  caches `.js`/`.css` hard; a "fix that did nothing" is usually stale code.
- **Verify on a table, not by reading the code.** A deploy that succeeded and a page that loaded
  are two false green lights; the behaviour itself is the only real one.
- `"Not logged in (studio)"` with no `window.gameui` → `$KIT/tools/bga-session-manager/bga.sh login.py`.
  Bug reports, replays and alpha tables live on the **main site** → `login_main.py`.
- Studio tables are disposable. Stop any of them when a test needs the slot.

### Locked-up / unstartable table

Symptom: game page 500s with **"Gameserver is locked by configuration"**, and a new table cannot be
created because one is "already in progress" — and the stuck table is not listed anywhere.
Go to `https://studio.boardgamearena.com/lobby?game=<game id>`, try to **create a game**; the
"already in progress" error links to the stuck table; follow it and **express stop**. Don't try to
script `quitgame.html`/`createnew.html` — they reject synthetic calls (feException 806).

`/studioissues?game=<project>` lists the week's PHP and JS errors — "No errors!" is good evidence
a load failure is not your code.

## Branches: `staging` is where work lands, `main` is what players have

<!-- Adopt this from the first alpha build. Before alpha, `main` alone is fine. -->

BGA serves alpha/beta players a **build** — a snapshot cut from the Studio project — so a deploy
to Studio does *not* change what testers play.

- **`staging`** — the working branch, and what `deploy.sh` pushes. Studio should match `staging`
  almost all the time; if they drift, `staging` needs the commit.
- **`main`** — what is live in the current build. Moves only when a build is cut: merge
  `staging` → `main` with `--no-ff`, tag annotated `alpha-YYMMDD-HHMM`. Then
  `git diff main...staging` answers "what have testers not got yet?". No `alpha/…` branches, ever.
- Cutting the build is scriptable — `$KIT/skills/bga-cut-build/`.
- **Write the merge message to a FILE and pass `-F <path>`** — never `-F - <<'EOF'` (git doesn't
  read stdin there, and the heredoc ends the `&&` chain, so the tag lands on the previous build).
- **The BGA release note is capped at 250 characters** and is what testers read: symptom-first,
  player-facing. The long account goes in the merge commit.
- **Push every commit as you make it** (`git push origin staging --follow-tags`).

## Client build: <choose one on day one and record it here>

<!-- Option A (what Reckoners ended up with): no build. Hand-edit modules/js/Game.js and
     <project>.css directly; delete the skeleton's src/ + rollup/sass config so nobody runs a
     build that overwrites them from a stale tree.
     Option B: keep the TypeScript/SCSS build, but then the BUILD OUTPUT is never edited by hand,
     and preflight runs on the output. Don't end up in between. -->

Client JS has two kinds of object and one `this`: **state classes** (`constructor(game, bga)`,
where the game is `this.game`) and the **Game class** (helpers are `this.helper()`). A line
copied between them parses and lints, then throws in the browser — `check_state_scope.py` is the
only check that catches it.

## Server

- `php -l` every PHP file you touch before deploying. A parse error in `Game.php` takes the table
  down before your code runs and looks exactly like an infrastructure fault.
- **`dbmodel.sql`: full-line `-- comments` only.** A trailing inline comment after a column
  silently drops the column → "Unknown column" at runtime. Schema changes need a **fresh table**.
- **Notifications are capped at 128KB per action.** Never attach a whole-board snapshot per
  animation beat — send patches. Test payload-heavy sequences at max player count on a full board.
- **Notifications are one-shot; a reload replays nothing.** Everything the client shows must be
  rebuildable from `getAllDatas()`.
- `gameinfos.jsonc` / `gameoptions.jsonc` changes need a control-panel click ("Reload game
  informations" / "Reload game options…") — the SFTP push alone does nothing.
- `gameinfos.jsonc` `game_name` must slugify (lowercase, alphanumerics only) to the Studio project
  name or the release validator complains. The *displayed* name is set in the translation centre.
  The Studio project name can never be changed — choose it carefully.

## Architecture

<Server: Game.php responsibilities; state classes and their numeric ids/types; what setupNewGame
returns. Client: where getAllDatas lands, the render entry points. Config: options and their ids.>

## Source of truth & references

- `docs/<game>-bga-spec.md` — the implementation spec.
- `misc/claude-handoff.md` — live per-session status. Keep it SHORT: current state + next steps;
  move finished history into `docs/plans/LOG_*.md`.
- `TODO.md` — deferred work.
- Framework knowledge: `$KIT/docs/framework/`; production gotchas: `$KIT/docs/lessons/field-notes.md`.
  Learn something game-agnostic here? Add it to the kit, not this file.
