# CLAUDE.md — working on the kit itself

This repo is **public**. It holds game-agnostic tooling, skills and knowledge for building BGA
games with an agent. Game work happens in a separate game repo that *uses* the kit.

## What belongs here, and what never does

- **Belongs:** anything that would be true for the next BGA game — framework behaviour, Studio
  process, tooling, verification technique, release mechanics, agent working patterns.
- **Never:** publisher material (rules text, card content, art, print files, correspondence),
  names of private people (publisher contacts, testers), the developer's account names, key
  names, email, machine paths, table or bug-report ids, or anything about their personal systems.
  Those go in the game repo or in the developer's private setup note.
- Before committing, grep for leaks:
  `git diff --cached | grep -niE '/Users/|@[a-z0-9.-]+\.(com|net)|id_ed25519_|table=[0-9]{5,}'`

## When a game session learns something

A game repo's agent that finds a game-agnostic lesson should add it here — a field note
(`docs/lessons/field-notes.md`: bold rule, symptom, fix, `Seen:` line) or a framework note — rather
than only in the game's own `CLAUDE.md`.

## Conventions

- Scripts are bash + Python; read config via `tools/bga-session-manager/_config.sh`, never
  hard-code a project, path or account.
- Python under `tools/` runs via `bga.sh` (venv lives in `BGA_SM_RUNTIME`, not the repo).
- Test a script change against a real game repo before committing: `scripts/preflight.sh` from the
  game root, `bga.sh find_table.py`, and a `deploy.sh` of one harmless file.
