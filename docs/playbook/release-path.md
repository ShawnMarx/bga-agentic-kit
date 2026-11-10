# Release path: Studio project → alpha → beta

The end-to-end path a BGA game takes from an empty Studio project to a beta request. For each stage
it gives what you do, what BGA checks, and the traps. "Seen in Reckoners" asides are what actually
happened on *The Reckoners* (2026). Read the whole page once **before creating the project**,
because the first trap is at step 0.

Rough elapsed times from one game: first commit → alpha request took 10 weeks. Request → private
alpha took 3 weeks, including one review round. Private alpha → beta request took 9.5 weeks.
BGA's own response times ran from 4 days to 8 weeks.

---

## 0. Before you create the Studio project

- **Check the license.** The Studio licensing page lists licensed games and shows "Good to go!"
  with the license date when the publisher has licensed BGA. Beta needs this. Ask for publisher
  approval in writing early; the alpha request needs a **publisher authorization** on record.
- **Choose the project name as the published title in CamelCase**, for example `TheFooBar`.
  The project name becomes your PHP namespace (`Bga\Games\<name>`), your CSS file name and your SFTP
  root. The pre-release validator **lowercases and strips non-alphanumerics on both sides** and
  requires `gameinfos.jsonc` `game_name` to slugify to the project name. **A project cannot be
  renamed later.**

  > *Seen in Reckoners:* the project was created as `reckoners` while the published title is
  > *The Reckoners* (`thereckoners`). The alpha request was blocked, and `game_name` was changed
  > back and forth four times. A support request for an in-place rename was answered eight weeks
  > later with "too late". The eventual fix was cosmetic only (see §8).

- **Decide where confidential art lives.** Publisher art is under BGA's confidentiality terms. Keep
  it out of any public repo, gitignored, *and* backed up somewhere private that does not depend on
  one machine.

## 1. Development setup

- **SFTP to Studio** runs on **port 2022**, with a key registered per machine in the Studio control
  panel. Use one key per machine and revoke a key only when its machine is retired. `put` does
  **not** create remote directories, so create them first.
- **Normalise line endings** (`.gitattributes`). Otherwise a file last deployed from Windows
  byte-diffs as 100% changed against one from a Mac. Compare with `tr -d '\r'` before concluding
  anything has drifted.
- **Hard-refresh after every deploy.** BGA caches JS and CSS aggressively.
- **Two logins for automation:** Studio, and the main site. Alpha tables, bug reports and replays
  live on the main site. A bug report reading "Unable to load this report" usually means logged
  out, not a permissions problem. Studio cookies are session-only, so snapshot them for a
  Playwright harness.
- **Config changes need a control-panel click:**
  - a `gameinfos.jsonc` change needs **"Reload game informations"**;
  - a `gameoptions.jsonc` or `gamepreferences.jsonc` change needs **"Reload game options & player
    preferences configuration"**.

  An SFTP push alone does nothing for either.
- **Schema changes need a fresh table.** In `dbmodel.sql`, use full-line `-- comments` only. An
  inline trailing comment after a column silently drops the column.

### The pre-deploy gate (wire it on day one)

```bash
node --check modules/js/Game.js \
  && npx --yes eslint@9 --no-config-lookup -c eslint.config.mjs modules/js/Game.js \
  && php -l modules/php/Game.php \
  && npx --yes -p postcss-cli@11 -p cssnano@7 -p postcss@8 \
       postcss <game>.css --use cssnano --no-map -o /dev/null \
  && ./deploy.sh …
```

Chain the gate with `&&`, never `;`. A `;` uploads even when a check fails.

- **`node --check`** only parses, so it misses undefined names.
- **The eslint `no-undef` pass**, with BGA globals declared, catches those.
- **cssnano** is what BGA's build runs. Browsers silently skip a bad rule, but cssnano hard-fails
  the build.
- Never write the comment-close sequence inside a CSS comment.

> *Seen in Reckoners:* four client breakages reached a table before the eslint and state-scope
> checks existed. A build died at the minifier on a CSS comment that closed itself. The PHP had
> never been linted locally for 3.5 months.

## 2. Pre-release checklist (before requesting alpha)

Work through BGA's pre-release checklist as a tracked LOG, and **verify each item on a real
table**. Static review does not count. The items that took real work:

| Item | What to check |
|---|---|
| **Check project** (static analysis, on the Studio game page) | Drive warnings to 0. Expect advisories for direct DOM access to framework elements, legacy score APIs, and even a comment that literally contains `@import`. |
| Minified JS and CSS | Play a table under both minify toggles. |
| Spectator | Shows public info only. |
| Replay | An in-game replay from a log line, and a full replay after game end. |
| Browsers | Chrome and Firefox are required; Edge and Safari recommended. Plus a phone-size screen. |
| Realtime mode | Clocks stay alive (`giveExtraTime` / `giveFullTime` at the turn seam). |
| Waiting screen | Every setup route starts cleanly. |
| `exception_on_warning` | A full playthrough to a natural end with no PHP warnings. |
| Dark mode | Verify on BGA's real dark toggle, not just a media query. |
| Tooltips | Honour the "Display tooltips" preference if you use a custom overlay. |
| Zombie / quitter | Every state survives a quit. In co-op, decide whether a quitter's seats are reassigned. |
| Progression and stats | `updateGameProgression` actually fires, and stats appear on a fresh table. |
| i18n | "Display dummy translations" shows every UI string bracketed. Decide deliberately about proper nouns. |
| Hygiene | Copyright headers, no `console.log`, no stray root files, no dead skeleton states. |

**The checklist does not test rules correctness, and neither does Studio's review.** Get the
publisher or designer playing before you request alpha, and make the server authoritative for every
rule.

> *Seen in Reckoners:* the full checklist, static analysis and Studio's review found zero rules
> bugs. One publisher playtest found five, including a movement rule enforced only in the client.

**Also before the request, read the BGA Studio Guidelines and build to them.** Both review rounds
below were guideline items: C.3 button colours, popups, solo chrome, greyed-out actions, layout and
action bar.

## 3. Requesting alpha

1. Run a build from the Studio game page (see §6), with build notes.
2. Submit the alpha request. The **pre-release validator** runs here; the `game_name` slug check is
   the usual blocker. Do not tick "Ignore". It hides the warning from your form, not from the
   reviewer.
3. Make sure the publisher authorization is on record.

## 4. Studio review rounds

Studio replies with required items, sometimes over more than one round. Answer **in prose, item by
item**: state what changed, whether it was verified on a table, and anything you are deliberately
not doing, with the reason. Keep the verbatim review text in the repo and plan against it, not a
paraphrase.

> *Seen in Reckoners:*
> - **Round 1 (13 days after the request):** seven UI items, including button colours and naming,
>   greying impossible actions, a compact character display, help and settings out of player
>   panels, simplifying the action bar, and moving table actions onto the table.
> - **Round 2 (4 days after the private-alpha grant):** forward actions must not be red, remove
>   flow-blocking popups, and hide multiplayer information in solo.
> - Rewriting the action bar into a board-first model took most of a week.

`statusBar.addActionButton(label, cb, { disabled: true, tooltip: '…' })` is the supported way to
grey an action and say why.

## 5. Private alpha → public alpha

- **Private alpha** testers join through the game's **players' group**. Show the **publisher the
  alpha, not the Studio**; BGA asked for exactly this.
- **Public alpha is a separate status.** Check the Manage Game page: a public-alpha request may
  already show as requested. If you want more private time, say so explicitly, and expect the answer
  to take a while.

  > *Seen in Reckoners:* a hold request sent on the day of the private-alpha grant was answered
  > eight weeks later. The status moved between public and private more than once in between.

- Alpha players get a **build** (a snapshot), not the Studio files. Pushing to Studio does not change
  what testers play.

## 6. Branches, builds and deploy to production

### Branch and tag model

- **`staging`** is the working branch and what you deploy to Studio. Studio should match `staging`
  at all times.
- **`main`** is what is live in the alpha build. It moves only when you cut a build.
- At each build, merge `staging` → `main` with `--no-ff` and add an **annotated** tag
  `alpha-<build id>`. Then `git diff main...staging` = "what testers have not got".
- Use **one tag naming scheme** from the first build.
- **Never create an alpha branch.** `main` is the alpha.
- **Push as you go:** `git push origin main staging --follow-tags`. `--follow-tags` pushes only
  annotated tags reachable from what you push, and does not backfill old ones. Run
  `git push origin --tags` once if any are missing.

### The merge-message trap

Write the merge message to a **file** and use `git merge --no-ff -F <file>`. **Never use
`-F - <<'EOF'`.** `git merge -F -` does not read stdin and exits 129. And because a heredoc ends the
`&&` chain at its terminator, a following `git tag … && git push` still runs, which **tags the
previous build**. Merge first, check that `git log -1 main` shows the new merge, then tag and push
as a separate command.

> *Seen in Reckoners:* this happened three times, and twice it pushed a wrong public tag.

### Cutting the build (scriptable with Playwright on the Studio game page)

1. Confirm the Studio files match `staging` and that every debug flag is off.
2. Click **"Dry run build"** and read the *Command results* panel. Every step should show a pass.
3. Fill in the **release note** and click **"Commit & build a new version now"**. The panel ends
   with the build and deploy steps passing and shows the build id.
4. Under *Versions available for production*, click **Deploy to production** on that version. It
   then reads *(Current PRODUCTION version)*. The "Online version" label can lag behind.
5. Merge and tag as above.

**The release note is capped at 250 characters, and it is what testers read.** Write a
player-facing changelog line, not a commit summary. Lead with the symptom a tester would recognise,
for example "buying equipment could purchase the wrong card…". Use any spare characters to
pre-empt the obvious question, for example "No need to start a new table." The long form goes in
the merge commit on `main`.

- **A build failure at the minifier happens after the commit and tag.** That is why cssnano belongs
  in the pre-deploy gate (§1).
- **A cache-clear warning at deploy** means testers may get stale JS and CSS. Tell them to
  hard-refresh, and re-deploy the same version before suspecting the code.
- **Check the BGA server-status page for peak hours** before a production deploy.
- **Prefer builds that need no new table.** JSON `ext` columns let features land without a schema
  change, so testers' tables in progress pick up the build.

## 7. Platform limits to design for, not discover

- **128KB of notifications per action.** Above that, the step aborts with a red banner. The limit
  scales with board size and player count, so test at the **maximum** count on a full board.
  Send diffs and patches, never a whole-board snapshot per beat.

  > *Seen in Reckoners:* 256KB at 6 characters, from a step-through animation. It was invisible at
  > 2 characters.

- **Locked or stuck table.** The game page returns 500 with "Gameserver is locked by
  configuration", and you cannot create a new table. The stuck table is on no listing page. Go to
  the lobby for your game, try to create a table, and **follow the link in the "already in
  progress" error**, then express-stop it. Scripted calls to the quit and create endpoints are
  rejected with code 806. Use the UI.
- **The Studio issues page** (`/studioissues?game=<name>`) lists the week's backend and frontend
  errors. "No errors!" there is good evidence a load failure is not your code.
- **Solo tables never update the game-list progression %.** This is a known platform issue; do
  not debug it. The in-game value and the "your turn" flag *are* yours.
- **Scripting a replay:** `&step=N` is ignored. Use `gameui.archiveGoToMove(N)` and poll the log,
  because it replays from the start.

## 8. Display name

If the shown title must differ from what `game_name` can be, change it in the **translation
center**. Open the game's module, English → English, find the string with context **"Game name"**,
and request a change. For the game's own developer the change is auto-validated, and the main site
picks it up on its own refresh cycle. Leave `game_name` alone so the validator's slug check keeps
passing.

> *Seen in Reckoners:* this is how *The Reckoners* finally displayed correctly, eleven weeks after
> the problem was first seen.

## 9. Beta request

The beta requirements, as Studio stated them:

- **Publisher license** listed as "Good to go" on the licensing page, linked to your project.
- **10 reviewer approvals.** This took about two months of alpha play.
- **"Does a quitter nullify the result?"** Decide it and state it in the request. In co-op with
  seat reassignment the answer can be no.
- **Premium-game contract**, if any. Ask BGA's publisher contact address.
- A link to the publisher approval, plus a healthy bug list and reviews.
- **A tutorial is not required.** Tutorials are usually built by groups who specialise in them. Ask
  before you invest.

  > *Seen in Reckoners:* about 90KB of tutorial planning and scripting before learning this.

Submit with **"Request BETA status"** on the Studio project page.
