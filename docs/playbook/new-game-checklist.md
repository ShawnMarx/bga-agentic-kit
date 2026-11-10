# New-game checklist

The order to do things in on a new BGA game, so the expensive lessons from The Reckoners
([retrospective](../lessons/reckoners-retrospective.md)) are paid for once, not twice. Each item
links to where the detail lives. Items marked ★ are ones Reckoners did late and paid for.

## Week 0 — before the Studio project exists

- [ ] **Licence / publisher permission** in writing, with scope (base game only? expansions?) and
      who supplies art. BGA won't publish without it.
- [ ] ★ **Choose the Studio project name — it can never be changed.** Make it the published title
      in CamelCase (`TheReckoners`, not `reckoners`), so `gameinfos.jsonc` `game_name` slugifies to
      it and the release validator is happy. [release-path §0](release-path.md)
- [ ] Read the **BGA Studio Guidelines** and the **pre-release checklist** end to end, and copy the
      UI rules into the game's `CLAUDE.md` as a one-page checklist (button colour = direction,
      no blocking popups, solo shows no multiplayer chrome, greyed-out actions say why). ★ Both of
      Reckoners' review rounds were items already in those documents.
- [ ] Ask BGA which deliverables are actually **required** for alpha and beta (tutorial? sprites?)
      before scoping them. ★ Reckoners planned 90KB of tutorial nobody required.
- [ ] Decide where confidential assets live: a private store that is **not one machine** and is not
      git (publisher PDFs, raw art). ★ "Local-only" meant salvaging art off a retiring laptop.

## Day 1 — the loop, before any game code

- [ ] Studio project created; skeleton downloaded over SFTP into a new local repo.
- [ ] `scripts/new-game.sh <dir> <project> <game id>` — templates, `.bga.env`, skills linked.
- [ ] Dedicated SFTP key registered; `bga-studio` host alias; `deploy.sh` of one file works.
- [ ] `setup.sh`, `bga.sh login.py`, `bga.sh login_main.py`; `find_table.py` sees a table.
- [ ] ★ **Pre-deploy gate wired and used from the first commit:** `preflight.sh && deploy.sh …`.
      Every check in it was added after a live break.
- [ ] ★ **Client build decision recorded in `CLAUDE.md`:** keep the TS/SCSS build *and never edit
      its output*, or delete `src/` and hand-edit `Game.js`/`.css`. Never a disabled build that can
      overwrite the real client.
- [ ] Add `.gitattributes` (`* text=auto eol=lf`) if more than one OS will ever touch the repo.
- [ ] `staging` and `main` branches, push-every-commit, one tag scheme (`alpha-YYMMDD-HHMM`).

## Week 1 — prove the risky part, and the harness with it

- [ ] Spike the mechanic the game lives or dies on (Reckoners: simultaneous dice → multiactive;
      see [framework 02](../framework/02-multiactive-simultaneous-play.md)).
- [ ] ★ **Drive it on a table with `drive.py` / the `bga-playtest` skill** — state→steps map,
      read the game log, screenshot. "Driven on a table" is the definition of done from now on.
      Reckoners stood this up in month 3, and its first finding was that the driven games had never
      spent a die.
- [ ] Add Studio-only `debug_*` actions for reaching deep states quickly.
- [ ] Solo-with-N seats as the rules test bed if the game has solo (Studio can't switch seats).

## Before the second mechanic — design once

- [ ] ★ **Interaction model decided and spiked on the hardest action:** board-first (click the
      thing on the table), one staged-selection primitive ("pick sources → pick targets → confirm"),
      one highlight colour grammar, one Cancel. Reckoners designed dice-spending three times.
- [ ] Multiactive invariants written down: parked ≠ done ≠ owes-an-answer.
- [ ] Notifications send **patches, not board snapshots** (128KB per-action cap).
- [ ] Everything on screen rebuildable from `getAllDatas()` (notifications don't replay on reload).
- [ ] Schema: an `ext` JSON column on each major table is cheap insurance against `db_upgrade`.
- [ ] Client structure: state classes and Game class clearly separated (or split into modules if
      the skeleton allows); `check_state_scope.py` in the gate.

## Month 1 — rules fidelity

- [ ] ★ **Rules holder (publisher/designer) playing on a Studio table.** Checklists and BGA review
      find zero rules bugs; one publisher playtest found five.
- [ ] Server authoritative for every rule — a rule enforced only in the client is a bug.
- [ ] A rules-audit list: illegal moves that must be refused, re-tried after server changes.
- [ ] ★ Test at **maximum player count on a full board** from the first full round.

## Pre-alpha → alpha → beta

Follow [release-path.md](release-path.md): pre-release checklist, stats/progression/zombie mode,
media assets ([framework 05](../framework/05-studio-media-and-metagame.md)), alpha request, review
rounds, cutting builds (`bga-cut-build` skill), display name, beta request.

## Every session

- [ ] Read `misc/claude-handoff.md` (short!) and `TODO.md`'s "deployed but not played" list.
- [ ] End by rewriting the handoff — current state and next steps, not history.
- [ ] Game-agnostic lesson learned? Add it to the kit's `docs/lessons/field-notes.md`.
