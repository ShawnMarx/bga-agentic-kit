# Retrospective: The Reckoners on BGA (2026-06-01 → 2026-11-10)

A record of five months building *The Reckoners* (a simultaneous co-op dice game with a solo mode)
on Board Game Arena with Claude Code doing most of the typing. The game went from an empty
repository to a full playable round loop in **8 days**, then took **five more months** to reach a
beta request. This document is about the five months.

It is written for one reader: the next BGA game. Wins are kept short. The trouble areas and the
"do differently" list are why the document exists.

Numbers come from `git log` on the private game repo: **415 commits**, of which **276 touch code,
config or assets** and **139 touch only docs**. The client file `modules/js/Game.js` appears in 211
commits, `reckoners.css` in 129, and the server `Game.php` in 75.

---

## 1. Timeline

| Date | Milestone | Notes |
|---|---|---|
| 2026-06-01 | First commit | Ported from a tutorial sandbox onto the modern (2024+) skeleton: PHP state classes, JSONC config, plain-JS client. |
| 06-03 | Use Dice engine | Board, movement, plan tokens, boss, per-symbol targeting, rewards, all in the first 3 days. |
| 06-08 | Full round loop playable | Equipment, characters, Epic phase, real decks. The original plan's go/no-go was "can a beginner build the multiactive dice POC?", and it was answered by about day 2. |
| 06-11 | Solo mode | One human drives 2–6 characters on the same engine. |
| 06-15 | Publisher approval | Base game only. |
| 06-19 | Official art imported | |
| 06-22 → 06-24 | First issue-driven fix cycle | Numbered issues #3–#21, mostly UI. |
| 06-29 → 07-13 | Pre-release checklist pass | Progression, stats, zombie/takeover, dark mode, tooltips, realtime clocks. "Check project" static analysis reached 0 warnings on 07-12. |
| 07-13 → 08-21 | **No commits for 5.5 weeks** | The alpha request went in by hand on 08-13, inside this gap. |
| 08-13 | Alpha requested | The pre-release validator blocked on `game_name` (see §3.7). |
| 08-21 | Dev box moved Windows → Mac | Local-only art had to be salvaged off the old machine. |
| 08-26 | **Two reviews landed on one day** | Studio's pre-alpha review: 7 UI and action-bar items. The publisher's first playtest: 5 rules bugs. |
| 08-28 | Playwright table-driving stood up | Nearly 3 months in. |
| 08-29 → 08-31 | Board-first interaction rehaul | 38 commits on 08-31 alone. |
| 09-02 | 128KB notification cap hit | Only reachable at 6 characters on a full board. |
| 09-03 | **Private alpha granted**, first build | |
| 09-05 | `staging` / `main` split | |
| 09-07 | Studio review round 2 | "Not ready yet": 3 problems, 6 required bullets, all UI. Answered 09-09. |
| 09-09 | Busiest day | 54 commits. |
| 09-12 | A build failed in BGA's minifier | A CSS comment broke cssnano. `php` installed locally the same day, after 3.5 months of unlinted PHP. |
| September | ~30 alpha builds | 31 of the 34 `alpha-*` tags are from September. 242 of the 415 commits. |
| 10-28 | Display name fixed via the translation center | The project rename was refused as "too late". Beta requirements received. |
| 11-09 | 10/10 reviewer approvals; **beta requested** | |

**Plan vs. reality.** The original plan treated the multiactive dice POC as the single risk worth
testing. It assumed the legacy framework (`states.inc.php`, `*.action.php`, `*.view.php`) and a
WinSCP auto-sync loop. Neither survived contact. The modern skeleton made the engine easy, and the
dice turned out not to be the risk at all. The real costs, none of which the plan named, were:

- BGA's UI guidelines and review rounds;
- the interaction design of spending dice;
- rules fidelity, checked only by the rules holder;
- verification without a local runtime;
- release mechanics.

---

## 2. What worked (repeat these)

**A long, opinionated `CLAUDE.md` holding rules that were each paid for.** Every hard rule in it
records a dated incident: the cssnano gate, the `&&`-not-`;` deploy chain, the merge-message trap,
the locked-table recovery, the 128KB cap. That made the second occurrence cheap. Write the
*incident* next to the rule, not just the rule; the date and the symptom are what let a later
session recognise the same failure.

**Plan / LOG pairs for every multi-session effort.** `PLAN_*.md` holds the scoped items and
`LOG_*.md` holds `[x]` steps with deviations noted inline. This survived many context resets. The
best entries record a *correction*, for example "The revert was a MISDIAGNOSIS — root cause
found", rather than a success.

**Driving real tables with Playwright, once it existed.** A `drive.py` with a state→steps map
(`drive_until`) reads `gamestate.name` each iteration and waits out automatic states. It drove a
solo game from setup to natural end, and it turned "deploy and ask the human" into
"deploy and check". It needed two logins: Studio, and the main site for alpha tables, bug reports
and replays. Studio-only `debug_*` actions, such as dropping a die straight into a state that would
otherwise take several rounds to reach, paid for themselves.

**Solo-with-N-characters as the rules test bed.** Studio has no in-page seat switcher, so a real
N-player table needs N logins. Because solo ran the same engine with `playerCount = N`, a 2-character
solo game reproduced the publisher's 2-player board exactly.

**Schema future-proofing up front.** `ext` JSON columns on every major table, plus a generic
"boss" row and a generic held-card table. No alpha build needed a live DB upgrade. Most builds
shipped with "no need to start a new table", which testers notice. Whether the expansion work it
was designed for ever comes is an open question (§5).

**A `staging` / `main` + annotated-tag model at alpha.** `git diff main...staging` always answers
"what have testers not got?". It also made rapid builds safe: ~30 in September with no rollback.

**Release notes written for players.** The 250-character build note is player-facing. Writing it
symptom-first ("buying equipment could purchase the wrong card…") and putting the long form in the
merge commit kept both audiences served.

**Recording gotchas as framework notes outside the game repo.** Game-agnostic lessons were written
to a shared notes folder: multiactive pitfalls, Playwright driving, Studio media. That is the seed of
this kit.

**Agent co-op play as a test, used once and costed honestly.** Two full games with Claude driving
seats found real UX friction and produced a forecasting script. That script decided the next game,
which is good evidence the learning generalised. It cost **~$125 per driven seat per game**, and
83% of that was cache reads. The cost lever is context length, not cleverness.

---

## 3. Trouble areas (where the time went)

### 3.1 Verification had no local loop for three months
There is no local runtime; the game exists only on Studio. Until 08-28, every behavioural check was
"deploy, then the human looks". Changes stacked up untested, and the human became the bottleneck.
When automation arrived, its first finding was that the driven games **never spent a die**. The
setup and the automatic city side were well exercised; the action engine, the heart of the game,
was not. A `TODO.md` section titled **"Shipped but NOT yet played"** still existed in November,
listing paths that went to testers without anyone driving them.

### 3.2 Client breakages that every check at the time passed
At least **four** builds or deploys broke the live client in ways `node --check` could not see:
- **07-13:** a malformed tooltip string crashed client load.
- **08-30:** a regex edit appended a trailing comment that swallowed a call's closing `);` at three
  sites. The parentheses happened to re-balance later in the file, so `node --check` passed and
  `setup()` never ran.
- **08-31:** a `ReferenceError` from a variable in another function's scope, shown as a red banner
  on the live table.
- **09-08:** a line copied from the Game class into a state class called `this.helper()`, where
  `this` is the state object. It parses and lints. The client wedged on "Updating…" while the
  server advanced, so the table *looked* hung but was fine after a reload. That made it slow to
  diagnose.

Each one added a gate: eslint `no-undef` with BGA globals, a state-scope checker script, `php -l`
from 09-12, and cssnano. **All four gates could have existed on day one.**

### 3.3 Misdiagnosis from the harness itself
One bisection went backwards through innocent commits and reverted a correct CSS fix. The cause
was capturing a URL that returns HTTP 500 ("Gameserver is locked by configuration") *regardless of
the deployed code*. Good code looked broken. The correct path was the table page plus the real
"Go to game" link. Lesson: **validate the harness against a known-good build before trusting a
"still broken" reading.**

### 3.4 Rules correctness: nobody checks it but the rules holder
The completed pre-release checklist, Studio's static analysis and Studio's human review together
found **zero rules bugs**. One playtest by the publisher found **five**. One of them was a
**server-authority hole**: a movement restriction enforced only in the client, with no server check
on the destination at all. BGA's process checks framework citizenship and UI, not fidelity to the
rulebook.

### 3.5 The dice-spending interaction was designed three times
The original flow presented choices as lists in the action bar. Studio's pre-alpha review
("simplify the action bar", "move table actions onto the table") forced a **board-first** rehaul:
eleven duplicate-list flows were converted to a shared staged-selection primitive. That rehaul was
then refined for weeks.
- `UseDice.php` was touched in 35 commits: 14 in June, 14 in September.
- 41 commit subjects between 08-29 and 09-17 concern Use Dice sources, targets and baskets.
- The only `git revert` in the history is a Use Dice basket change (09-16).
- On 09-09 a behaviour flipped and flipped back on the same day: "Waiting revives Done'd
  Reckoners", then "Done is final again".

The underlying issue: **the interaction model was invented per action rather than designed once
against BGA's guidelines**.

### 3.6 Two Studio review rounds, both about UI guidelines
- **Round 1 (pre-alpha, 13 days after the request):** seven items. Button colours and naming, greyed
  impossible actions, compact character display, help and settings out of player panels, simplify
  the action bar, move table actions onto the table.
- **Round 2 (4 days after the private-alpha grant):** forward actions must not be red, no popups
  that block game flow, no multiplayer information when playing solo.

Every one of these is in the published BGA Studio Guidelines. None needed a review to discover.

### 3.7 The `game_name` saga: four reversals over eleven weeks
The Studio project was named `reckoners`. The pre-release validator requires `game_name` to slugify
to the project name, so the published title *The Reckoners* (slug `thereckoners`) was blocked.
- `game_name` was shortened (08-13), changed back (09-03), and reverted the same day.
- A support request for an in-place project rename was answered **eight weeks** later: "too late".
- The fix was the translation center's "Game name" string (10-28). The docs needed three
  correction entries along the way, because each reversal left stale text behind.

**This was entirely decided by one keystroke at project creation.**

### 3.8 Platform ceilings found late
- **128KB notification cap per action.** Hit at 6 characters on a full board: 256KB, because a
  per-beat activation sequence carried a full board snapshot on every beat. It was invisible at
  2 characters. Fixed with patch-style snapshots merged by id on the client.
- **cssnano at build time.** Browsers silently skip a broken CSS rule; BGA's build minifier
  hard-fails. That happens *after* the build is committed and tagged. A comment that quoted the
  comment-close sequence closed itself, and the prose after it became a selector.
  `csstree-validator` did not catch it.
- **The build's cache-clear step warned once** that testers might be served stale JS and CSS.
- **Locked tables are invisible.** A stuck table shows up on no listing page. It is found only via
  the error link when you try to create a new table.
- **Solo tables never update the game-list progression %.** This is a known platform issue. Time
  was spent investigating it as our bug before that was established.

### 3.9 The tutorial: about 90KB of planning for something that was not required
There were 28 tutorial commits, a 36KB plan, a 30KB script, and a 22KB log, plus harness work
against the replay-comment editor. In that editor, the continue mode does not persist via script,
"Go to move" cannot be scripted, and the editor-still-visible check gave false failures on every
save. Then it emerged that **tutorials are not a beta requirement** and are usually built by groups
who specialise in them. The tutorial is still unpublished.

### 3.10 Documentation overhead and drift
- One commit in three touched only docs.
- The per-session handoff file grew to **127KB**. That is not a handoff, it is an archive, and a
  fresh session cannot read it at start-up.
- `CLAUDE.md` still describes `Game.js` as "~3.6k lines"; it is **11,335**.
- Several decisions needed explicit CORRECTION entries because an earlier entry was never amended.

Docs worked as institutional memory, but they cost real time and they drift.

### 3.11 One 11k-line client file
`Game.js` holds about a dozen state classes plus a Game class with hundreds of helpers. It shares
one `this` convention that differs between the two kinds of object. That is the root of bug class
3.2 (the 09-08 wedge), and it makes every edit a large-context edit. The TypeScript and Sass build in
`package.json` was disabled early and the compiled files were edited by hand. That was workable,
but it left a stale `src-disabled/` tree that would silently overwrite the real client if anyone
ran `npm run build`.

### 3.12 Environment
- Confidential art lived only, gitignored, on one machine. Retiring that machine required a written
  salvage procedure, and anything not salvaged was gone.
- Moving from Windows to Mac made every file read as 100% changed in a raw diff, because of CRLF vs
  LF line endings.
- Studio login cookies are session-only and had to be snapshotted for the harness.
- In the harness, `gamedatas` is *not* refreshed by notifications. A driven check that reads it
  after a move sees stale state.

### 3.13 Multiactive edge cases shipped to testers
A purchase-suggestion feature stranded an open vote. A player who clicked **Done** is *out of the
active set*, not parked waiting, so "wake the parked players" missed them, and the last player
leaving ended the step over an unanswered suggestion. It was found on a live alpha table. The
general rule: **model "who still owes an answer" explicitly. Never infer it from who is active.**

---

## 4. What I'd do differently from day one (prioritised)

1. **Build to the BGA Studio Guidelines and pre-release checklist before writing UI.** Read the
   Guidelines (C.3 button colours: blue for the one forward action, red only for undo or cancel;
   no blocking popups; solo shows no multiplayer chrome; unavailable actions greyed *with the
   reason*). Turn them into a one-page checklist in `CLAUDE.md`. Both review rounds, roughly three
   weeks of waiting plus a full interaction rehaul, were guideline items.
2. **Stand up Playwright table-driving in week one.** Include a state→steps driver, a log reader
   (the log, not `gamedatas`, is authoritative), Studio *and* main-site logins, and a
   `debug_*`-action convention for reaching deep states. Make "driven on a table" the definition of
   done. Never let a "shipped but not played" list exist.
3. **Wire the full pre-deploy gate on the first commit, chained with `&&`:** `node --check`, eslint
   `no-undef` with BGA globals, a state-scope check, `php -l`, and cssnano. Every one of these was
   added after a live break.
4. **Choose the Studio project name as the CamelCase published title before creating the project.**
   It must slugify to `game_name`, and it cannot be renamed later. Ten seconds of thought would have
   saved eleven weeks of back-and-forth.
5. **Get the rules holder playing in the first month, and make the server authoritative for every
   rule.** BGA review will not find rules bugs. A rule enforced only in the client is a bug. Keep a
   rules-audit test that tries each illegal move against the server.
6. **Design the interaction model once, early.** Board-first: click a thing on the table to act on
   it. Use one staged-selection primitive for every "pick sources, pick targets, confirm" flow, one
   colour grammar for highlights, and one Cancel. Spike it on the hardest action, then build every
   action on it.
7. **Test at maximum player count and board size from the first full round.** The 128KB
   notification cap scales with board size. Send patches, not snapshots, from the start.
8. **Split the client from the start.** Use separate files per concern if the skeleton's module
   loading allows it. At minimum keep state classes and the Game class visibly separated, with a
   lint rule for the `this.game` vs `this` boundary. Either keep the build pipeline alive or delete
   its source tree. Never leave a disabled one that can overwrite the real client.
9. **Make the handoff a short, overwritten status file**, under ~5KB. History lives in git and the
   LOG files. Put a date on any number in `CLAUDE.md` (line counts, file lists) or leave it out.
10. **Ask BGA which deliverables are required before building them.** The tutorial, and arguably
    image spriting, were scoped from assumptions.
11. **Keep confidential assets backed up but private from day one.** Use an encrypted or private
    store that is not tied to one machine, and never git-track them in a public repo. Normalise line
    endings with `.gitattributes`.
12. **Model multiactive state explicitly**: parked, done, and owes-an-answer are three different
    things. Write the invariants down before the first multiactive feature that involves votes or
    waiting.
13. **Adopt `staging` / `main` and one tag naming scheme at the first build.** Reckoners has both
    `alpha-2026-09-03` and `alpha-260903-2147` styles. Script build cutting from the start; it is
    fully drivable from the Studio game page.

---

## 5. Open questions for the next game

- **Does the modern skeleton support splitting the client into ES modules cleanly,** and does it
  survive BGA's minifier? If yes, item 8 is cheap. If no, what is the least bad structure for a
  10k-line single file?
- **Was the expansion-readiness schema worth it?** It cost design time in July and has paid nothing
  yet. Revisit if the expansion is ever built.
- **What does a rules-audit harness look like?** Specifically, a scripted list of "this must be
  refused" moves run against a Studio table after every server change.
- **How much agent self-play is worth buying?** At ~$125 per seat-game, what is the cheapest
  configuration that still finds UX friction? Shorter contexts, scripted forecasting and a single
  seat are candidates.
- **When is the right moment to involve a tutorial group,** and what do they need from the
  developer?
- **How early can a beta-grade wording pass happen?** Prompts and tooltips were the author's largest
  self-assigned pre-beta item. Is there a style sheet for prompt voice that would prevent it?
- **What did the beta request actually require beyond the published list?** Still pending at the
  time of writing. Update this file when BGA answers.
