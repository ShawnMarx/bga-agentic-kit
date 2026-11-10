# bga-agentic-kit

A starter kit and playbook for building **Board Game Arena** games with an AI coding agent
(Claude Code), distilled from taking *The Reckoners* from an empty Studio project to private
alpha and a beta request in about five months, with an agent doing most of the typing.

It is three things:

1. **Tooling that gives the agent a full loop with no human relay** — SFTP deploy, a pre-deploy
   gate that catches the classes of breakage that actually reached live tables, and a Playwright
   harness that logs in, loads a Studio table, drives it through the state machine, and reads back
   console errors, game state and screenshots.
2. **Claude Code skills** that encode how to use that loop: deploy-and-verify, playtest a bug,
   play a game *with* you from a second seat, and cut an alpha/beta build.
3. **Written-down knowledge** — framework notes, symptom-first field notes, a release-path
   how-to, and an honest retrospective of what worked and what didn't.

The game-specific parts of Reckoners (rules, art, publisher material) are not here and never will
be. Reckoners appears only as the case study the lessons came from.

## Layout

```
docs/
  framework/      How the modern (2024+) BGA framework works — skeleton, state machine,
                  multiactive play, ability dispatch, Studio media, driving a table.
  playbook/       How to work: new-game checklist, working with an agent, release path.
  lessons/        field-notes.md (gotchas, symptom → fix) and reckoners-retrospective.md.
skills/           Claude Code skills — symlink into a game repo with scripts/install-skills.sh.
tools/bga-session-manager/
                  deploy.sh, bga.sh (launcher), setup.sh, login.py, login_main.py,
                  find_table.py, capture.py (observe), drive.py (drive by state machine).
scripts/          preflight.sh (pre-deploy gate), check_state_scope.py, new-game.sh,
                  install-skills.sh, fetch-references.sh.
templates/game-repo/
                  CLAUDE.md, .gitignore, TODO.md, handoff and eslint config for a new game.
```

## Quick start

```bash
git clone <this repo> ~/repos/bga-agentic-kit && cd ~/repos/bga-agentic-kit
cp bga.local.env.example bga.local.env          # machine defaults (gitignored)
tools/bga-session-manager/setup.sh              # venv + Playwright Chromium, outside the repo
tools/bga-session-manager/bga.sh login.py       # log in to Studio once, by hand
scripts/fetch-references.sh                     # optional: three real BGA games to grep

# Studio SFTP: generate a dedicated key, register it at studio.boardgamearena.com/controlpanel,
# and add a `bga-studio` Host block to ~/.ssh/config (template in deploy.sh's header).

scripts/new-game.sh ~/repos/bga-mygame mygame <studio game id>
```

Then work from the game repo. Its `CLAUDE.md` (from the template) tells the agent the loop:

```bash
$KIT/scripts/preflight.sh && $KIT/tools/bga-session-manager/deploy.sh modules/js/Game.js mygame.css
```

Read [`docs/playbook/new-game-checklist.md`](docs/playbook/new-game-checklist.md) before writing
any game code.

## Configuration

Everything machine- or game-specific comes from plain `KEY=value` files, never from the code:

| Where | What |
|---|---|
| `<game repo>/.bga.env` | per-game: `BGA_PROJECT`, `BGA_GAME_ID`, `BGA_GAME_REPO` |
| `bga.local.env` (kit root) | machine defaults: `BGA_SFTP_HOST_ALIAS`, `BGA_SM_RUNTIME` |
| `BGA_ENV_FILE=…` | point at any other file explicitly |

Environment variables win over files. Both files are gitignored. Login cookies and the browser
profile live in `BGA_SM_RUNTIME` (default `~/.bga-session-manager`), which should never sit inside a
synced or versioned folder.

Keep a **private note** somewhere of your own for the things that are about *you* — which machine
deploys, key names, where your notes and task list live, publisher contacts. The game repo's
`CLAUDE.md` can point to it; this kit should not contain it.

## Requirements

macOS or Linux (bash), `sftp`, Python 3.10+, Node (for `npx` eslint/cssnano), PHP CLI (`php -l`),
a BGA Studio account with a project. Windows works through WSL.

## Status and licence

Built for one developer's next game, published in case it helps someone else's. The framework
notes describe BGA as observed in 2026 — BGA changes, so verify against the reference games and
the official docs when something disagrees. MIT licensed (see `LICENSE`). Reference games fetched
by `fetch-references.sh` keep their own licences.

Not affiliated with Board Game Arena.
