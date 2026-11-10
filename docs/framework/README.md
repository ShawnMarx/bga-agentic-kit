# BGA Framework Notes

Non-game-specific findings about how the Board Game Arena (BGA) Studio framework
works. Built up first in a throwaway Studio sandbox project, then while shipping The
Reckoners to alpha. Keep **game-specific** notes out of here — this is the reusable
knowledge base. When you learn something new about the framework on your game, add it here.

Framework flavor documented here: the **modern (2024+) BGA skeleton** — PHP state
*classes* + JSONC config + TypeScript/JS client. Many online tutorials describe the
older `states.inc.php` / `.view.php` / `.tpl` layout; follow the *concepts* there,
not the file names.

## Reference library (real games to grep)

Run `scripts/fetch-references.sh` to clone three working BGA games into the gitignored
`reference/`. See [reference-index.md](reference-index.md) for a feature → file map. Use it as ground truth when implementing a feature, then distill
the reusable pattern back into a note here with a citation.

- `bga-heartsla/` — **matches the modern skeleton documented here** (PHP state classes);
  the closest reference for our code. Also ships `_ide_helper.php` + `bga-framework.d.ts`
  (framework API signature stubs).
- `bga-santorini/` — classic layout (concepts only, not file names), but the best
  reference for **one-class-per-ability** card logic (`modules/powers/`).
- `bga-sharedcode/` — reusable utilities and animation helpers.

## Index

- [01 — Skeleton anatomy & the state machine](01-skeleton-anatomy-and-state-machine.md)
  — what every file is for, the finite-state-machine model that is the heart of
  a BGA game, and the three client↔server data channels — including that
  **notifications are one-shot and a reload replays nothing**.
- [02 — MULTIPLE_ACTIVE_PLAYER (simultaneous play)](02-multiactive-simultaneous-play.md)
  — activating all players at once, per-player deactivation, the automatic "wait for
  everyone" transition, the GAME-bridge gotcha, and §7: there is **no "active but not my
  turn"**, so an interruptible pass has to deactivate and be re-activated by the server.

- [03 — Reusable findings from the dice POC](03-dice-poc-reusable-findings.md)
  — multiactive→multiactive chaining (no bridge), passing list args as a delimited
  string, getAllDatas player enrichment, rebuilding status-bar buttons, per-player
  sub-state, and confirmed client API bits.
- [04 — The ability-dispatch pattern (one class per card/power)](04-ability-dispatch-pattern.md)
  — abstract base of no-op lifecycle hooks + one tiny subclass per ability + a manager
  that fans hooks out (player→teammate→opponent) by reference. The structure for
  Reckoners' epics/dice effects, distilled from Santorini. *Heavyweight — only past
  ~10+ effects sharing hook points.*
- [05 — Studio media assets & the metagame info panel](05-studio-media-and-metagame.md)
  — per-slot Media dialog rules (box/icon/banner/publisher/display/title: dimensions,
  formats, transparency, no-shadow/no-text), image size budget, PIL recipes for keying
  & building them, and which "Game information" fields are staff-side/community-driven
  vs editable (display_name, developer credit, duration, ratings, zombieModeLevel,
  game_interface_width, Gamehelp wiki).
- [06 — Driving a Studio table with Playwright](06-driving-a-studio-table-with-playwright.md)
  — automating a real table: why `testuser=` can't switch seats (use solo-with-N instead),
  the create/start/abandon lifecycle, `gamedatas` being a load-time snapshot, and driving
  from the state machine rather than a flat click script.
- [Reference library index](reference-index.md) — which reference game to grep for which feature,
  and the framework API stub files (`_ide_helper.php`, `bga-framework.d.ts`) to check signatures
  against before trusting memory.

See also [`../lessons/field-notes.md`](../lessons/field-notes.md) for the shorter, symptom-first
gotchas found in production, and [`../playbook/`](../playbook/) for how to work.
