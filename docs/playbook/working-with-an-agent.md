# Working with an agent on a BGA game

How the work was actually organised on The Reckoners. One developer and Claude Code took it from
an empty Studio project to a beta request in about five months. The agent wrote most of the code.
The developer decided, played and talked to the publisher. Evidence for each point is in the
[retrospective](../lessons/reckoners-retrospective.md) and the
[field notes](../lessons/field-notes.md#10-working-with-an-agent).

## The core idea: give the agent the whole loop

An agent that can only edit files hands every check back to you, and you become a screenshot
relay. The kit exists so the agent can **edit → gate → deploy → load a real table → read the
result** on its own:

| Step | Tool |
|---|---|
| gate | `scripts/preflight.sh` |
| deploy | `tools/bga-session-manager/deploy.sh` |
| observe | `capture.py` (console, JS errors, DOM, Studio server logs) |
| drive | `drive.py` / `skills/bga-playtest` (state→steps, reads `gamestate.name` and the log) |
| play with you | `skills/bga-play-partner` (a second seat, driven from a seat-switcher tab) |
| ship | `skills/bga-cut-build` (Studio build page → production → merge + tag) |

Reckoners got the driving part in month three. Before that, "fixed" meant "deployed and the human
said it looked fine", and the first driven game showed that a core action had never been exercised.
**Stand the loop up in week one and make "driven on a table" the definition of done.**

## Instructions the agent always loads

- **The game repo's `CLAUDE.md` is where rules go to be obeyed.** A lesson kept in a personal note
  didn't stop a fresh session repeating a mistake. The same lesson as a line in `CLAUDE.md` did.
  So did a check script, which is even better. Write the *incident* next to each rule: the date,
  the symptom and the error text. That is what lets a later session recognise the failure when it
  happens again.
- **Prefer a script over a rule** whenever the failure can be detected mechanically. Three of
  Reckoners' worst client breaks passed every check that existed at the time.
  `check_state_scope.py` and the cssnano step exist because a rule in prose was not enough.
- **Date every number and claim in instructions and skills.** "A 2-player table needs a second
  login" sat in a skill for weeks and every session obeyed it. It was wrong. "Game.js is ~3.6k
  lines" was true once; the file is now 11k lines.
- **Keep game-agnostic knowledge in the kit,** not the game repo. That way the next game starts
  with it.

## Memory across sessions

Context resets are constant. What survived them:

- **`PLAN_<topic>.md` + `LOG_<topic>.md` pairs** for any effort spanning sessions. The plan holds
  the scoped items. The log holds `[x]` steps, deviations and, most valuable of all, corrections
  ("the revert was a misdiagnosis: root cause found"). Move both to `docs/complete/` when done.
- **A short, overwritten handoff** (`misc/claude-handoff.md`, under ~5KB) holding current state,
  next steps and live traps. Reckoners let this grow to 127KB of history, at which point no session
  read it properly. History belongs in git and the LOG files.
- **`TODO.md`'s "deployed but not played" list.** It names exactly what is unverified. The goal is
  to keep it empty.

## Verification discipline

- **Name your evidence.** "I verified X by running Y" and "the other session told me X" are
  different statements. Never upgrade a relayed claim by repeating it.
- **Two false green lights:** the deploy succeeded, and the page loaded. Neither shows the change
  works. Hard-refresh or use `--clear-cache`, then watch the behaviour itself.
- **Reproduce before reading the code.** Several Reckoners bugs were found in minutes on a driven
  table after hours of reading the code had missed them.
- **The log is authoritative, not `gamedatas`.** `gamedatas` is a load-time snapshot.
- **Test at maximum player count on a full board.** Payload caps and layout overflows only show
  there.
- **A reviewer agent reasoning from memory is worse than none.** If a session's job is to check,
  it must read live state.

## What the human is for

The agent can't do these, and Reckoners lost time whenever they were left late:

- **Rules fidelity.** Neither BGA review nor any checklist finds rules bugs. The rules holder
  (publisher/designer) playing on a Studio table found five in one session. Get them playing in
  month one.
- **Design calls with a publisher.** Reckoners used a Suggest/Confirm/Reject flow for one contested
  interaction and agreed it with the publisher before building it.
- **Taste on interaction.** Settle the interaction model once, early, and spike it on the hardest
  action. Reckoners' dice-spending flow was designed three times.
- **Logins.** Studio and main-site logins are interactive. After that the harness reuses the cookies.

## Cost

Measured on Reckoners: a full driven game with one agent seat cost about $125, and two agent seats
about $252. Cost was linear in seats, and roughly 83% of it was cache reads of the session's own
context. The lever is **context length**: short skills, deterministic scripts in place of
re-derived arithmetic, and one seat unless a second agent buys something a human teammate can't.
Long prompt-cache TTLs matter when sessions sit waiting on each other.

## Standing authorisations worth writing down

Decide these once, put them in `CLAUDE.md`, and the agent stops asking:

- Studio tables are disposable. Stop any of them when a test needs the slot.
- Push every commit to `origin` as it is made.
- Cutting and deploying a build is the agent's job once the human says "ship it".
