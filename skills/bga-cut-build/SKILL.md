---
name: bga-cut-build
description: Cut a new alpha/beta build of a BGA Studio game and record it in git — check Studio matches the working branch and debug flags are off, Dry run build, write the 250-char player-facing release note, Commit & build, Deploy to production from the studiogame page via Playwright, then merge staging→main (--no-ff, message from a FILE), tag alpha-<build id>, and push. Use when the user says "cut a build", "deploy to alpha/beta", "ship it to testers", "set a new build", or asks what testers have not got yet.
---

# Cutting a build

Testers on alpha/beta (and later, production) play a **build** — a snapshot of the Studio project —
not the live Studio files. Deploying to Studio does not change what testers have; cutting a build
does. This is scriptable end to end: **do it, don't hand it back.**

## The branch model this assumes

- **`staging`** — where work lands; what `deploy.sh` pushes to Studio. Studio should match it almost
  all the time; if they drift, `staging` is wrong and needs the commit.
- **`main`** — **what is live in the build.** It moves only when a build is set: merge
  `staging` → `main` `--no-ff` and tag. So `git diff main...staging` always answers "what have
  testers not got yet?".
- **Tags, not branches.** Each build gets an **annotated** tag `alpha-<build id>` (build ids look
  like `YYMMDD-HHMM`, e.g. `alpha-261109-1917`; use `beta-…` once you're in beta). There is never an
  `alpha/…` branch — `main` *is* the alpha.
- Other branches are for experiments only; delete them once merged.

## Step 0 — preconditions (stop if any fail)

```bash
git switch staging && git status --short          # clean, or only unrelated untracked files
git fetch origin && git status -sb                 # staging not behind origin
grep -nE 'const DEBUG_[A-Z_]+ *= *(true|[1-9])' modules/php/Game.php   # must print NOTHING
```

- **Debug flags off** — every `DEBUG_*` constant at `0`/`false` (see `bga-playtest`'s testing aids).
  If one is on: turn it off, run the preflight gate, deploy, commit to `staging`.
- **Studio matches `staging`.** Pull the deployed files over SFTP (`sftp $BGA_SFTP_HOST_ALIAS`,
  `get` under `/$BGA_PROJECT/`) and diff with line endings normalised:
  `diff <(tr -d '\r' < remote/file) file`. Any difference: deploy the `staging` version (with the
  preflight gate from `bga-studio-loop`) before building. **The build is made from Studio, not
  from git** — whatever is on Studio is what ships.
- `git log main..staging --oneline` — this list is what the build delivers; it feeds the release note
  and the merge message.

## Steps 1–4 — the studiogame page (Playwright, Studio login)

Page: `https://studio.boardgamearena.com/studiogame?game=$BGA_PROJECT`, opened with the harness's
`S.launch_context(pw)` (run via `$KIT/tools/bga-session-manager/bga.sh`). If it says not logged in,
`bga.sh login.py` first.

1. **Dry run.** Click **"⇨ Dry run build"**, wait, and read the *Command results* panel. Every line
   must be ✅. A failure here is free; a failure at the real build is after commit and tag.
   CSS failing here (or at step 3) is almost always a selector cssnano rejects — run the cssnano check
   from `bga-studio-loop` locally, it reproduces the error with line and column.
2. **Write the release note — max 250 characters.** It is the note testers actually read, so it is a
   **player-facing changelog line, not a commit summary**: symptom-first plain English, leading with
   the fix a tester would recognise ("Buying a card could purchase the wrong one…"); spend leftover
   characters preempting the obvious question ("No need to start a new table."). Count it:
   `printf %s "$NOTE" | wc -m`.
3. **Commit & build.** Fill the `<textarea maxlength=250>` just before **"⇨ Commit & build a new
   version now"** with the note, click it, wait. The panel ends `Build game <project> ✅ /
   Deploy <id> ✅`. **`<id>` is the build id** — record it.
4. **Deploy to production.** Under *Versions available for production*, click **Deploy to
   production** on that version's block. It then reads *(Current PRODUCTION version)* — that is what
   testers get. The "Online version" label elsewhere can lag; trust the version block.

Lost the build id? It's the **Online version** on the same page.

Side effect: setting a build can take your open Studio tables with it ("Unable to find table
database"). Rebuild test tables afterwards rather than resuming.

## Step 5 — merge, verify, tag, push (separate commands)

Write the merge message to a **file**. Long-form is fine here — this is where the full account lives
(the release note is the 250-char version):

```
Merge staging into main for alpha build <id>

Built and deployed to production <date time> from Studio, which matched
staging (<short sha>). Dry run and build both clean.

Release note (<n>/250):
  <the note, verbatim>

- <change> (<sha>). <what a tester saw, what changed, how it was verified>
- …

Verified on Studio: <what was driven on a real table>
```

```bash
# message already written to .git/BUILD_MERGE_MSG (inside .git, so never committed)
git switch main && git pull --ff-only origin main
git merge --no-ff staging -F .git/BUILD_MERGE_MSG
```

```bash
git log -1 --format='%H %s' main      # MUST show "Merge staging into main for alpha build <id>"
```

Only when that reads right:

```bash
git tag -a "alpha-<id>" -m "Alpha build <id>" main \
  && git push origin main staging --follow-tags \
  && git switch staging
```

**Never `git merge -F - <<'EOF'`.** `-F -` does not read stdin (`error: could not read file '-'`,
exit 129), and a heredoc **ends the `&&` chain at its terminator** — so a `git tag … && git push` on
the following line runs anyway, tagging the *previous* build and pushing a wrong public tag. Merge;
check `git log -1 main`; then tag and push as a separate command.

**`--follow-tags`** pushes annotated tags reachable from what you push. It does not backfill: if older
tags look missing on the remote, `git push origin --tags` once.

## Report

One short block to the user: build id, the release note as shipped, the tag, and `main` == `staging`
at `<sha>`. Then, if your project records builds anywhere else (a changelog, an alpha log, your notes
location as configured in your CLAUDE.md), update it.
