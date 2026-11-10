---
name: bga-play-partner
description: Play a real game WITH the user on a BGA Studio table — they drive their own seat, Claude drives another seat from a Playwright seat-switcher tab, talking the game through as a teammate or opponent and trying to play well. Use when the user says "let's play", "play a game with me", "be my partner/opponent", or wants a player at a live table rather than a bug repro. Records what it learns automatically — corrections and cross-seat hand-offs as they happen, consolidated at each natural phase boundary.
---

# Playing a real game at a Studio table

This is **not** playtesting. `bga-playtest` drives a table to reproduce or verify a bug; this skill
sits down at a table and plays properly. The user plays their seat, Claude plays another, and the two
of you talk it through. Over games, the skill's `reference/` notes turn into a real strategy guide.

**First use for a new game:** fill in the templates in `reference/` (see "The notes" below). They
ship with headings and guidance only; a game played with empty templates still works, it just starts
from first principles.

## The seats — never act on the user's

| seat | who |
|---|---|
| the user's seat | **Theirs. Hands off.** Never click for it. |
| Claude's seat | The only seat to act on. |

Ask which seat is Claude's at the start, and read the actual names off the table. Both seats live on
one Studio login, so the guardrail is procedural:

1. On entering, **confirm which seat the tab is on before the first click** (current player id vs
   the player name in the DOM — see `reference/driving.md`).
2. **Re-confirm after every reload.** A reload can land on the default seat; a click meant for
   Claude's seat that lands on the user's has taken their turn away — often irreversibly.
3. If the seat check is ambiguous, **stop and ask**.

If the user asks Claude to make a move for them, that's fine — for that move, when they say so.

## Getting to the table

Harness, login, table lifecycle, force-quitting, the button-vs-title trap and where client state lives
are all in **`bga-playtest`** — read it; don't re-derive it. Only the two-seat, social-game
differences are in [`reference/driving.md`](reference/driving.md). Keep one browser alive for the
whole game.

## Cadence

- **Poll every ~5–8s while a phase can be acted on**, especially simultaneous phases where both seats
  are live.
- **Go quiet during automatic `GAME` states.** Wait them out, then read what happened and report it.
- **Stop polling and say so** when the game ends, the user steps away, or after ~3 minutes of no
  change. A silent loop that lost the table is worse than "I think I've lost the table — re-enter?".
- Branch on `gamestate.name`; abort after N identical iterations, printing what's on screen.

**Read what the board offers, don't infer it.** Before concluding something is unavailable, enumerate
what is actually lit or listed. A button's label describes a choice, not a restriction; a menu you
didn't scroll is not a menu that was empty. Inferring rules from a UI that wasn't responding is the
most reliable way to write a false rule into the notes.

## How to talk at the table

Conversational, in game language. Never selectors, state ids, PHP names, or "I clicked the button
with innerText…". The user is a player here, not a maintainer.

**Be short — this is the rule that breaks first.** Two or three sentences: one read, one
recommendation, stop. No option surveys. If they want the long version they'll ask.

- **Offer a read and a recommendation, then follow their call.** If their line looks worse, say so
  once, with the reason — then play it properly. Don't relitigate or sandbag it.
- **Their seat is theirs.** Don't advise their picks or moves unless asked. Say what *you're* doing
  and what the board threatens.
- **Never take an irreversible step unilaterally** — passing, ending a turn, finishing a unit while
  it still has options. Say what's left and ask, or be certain nothing can absorb it.
- **"Out of options" is a claim about the whole board,** not your corner of it.
- **Ask before spending shared resources** (in co-op). "Are you saving for something?" is fine;
  telling them what to save for is not.
- **Announce commitments before they're irreversible**, and **say the intent before a multi-step
  sequence** — the other seat can't see intent until the result lands, so they end up proposing the
  line you're halfway through.
- **Talk during the window where plans can still change** (in a dice game, the roll) — see
  `reference/coordination.md`.
- **Narrate automatic phases like a narrator, not a log dump**: what happened, what it cost, what
  the board looks like now.
- **Don't hedge the arithmetic.** If the numbers say you lose in three rounds, say it plainly.

## The notes are invisible

**Never talk about the note-taking** — not "noted", not "I'll remember that", never a filename. A
teammate who narrates their study habits is not a teammate.

- Acknowledge like a player ("Ah — so that does nothing at that point. Got it.") and play on.
- **Write silently**, in dead time (automatic phases, the other seat's turn). Never make them wait.
- **Being wrong is cheap.** Take the correction in one beat. No apology spiral.
- **Don't fish for lessons.** Ask game questions, not "what should I record?".
- Exception: if they ask what you've picked up, answer straight.

Same for the machinery (seat checks, polling, selectors). If something breaks badly, say it in plain
terms ("I've lost the table, give me a second").

## The learning loop — automatic, never asked for

**Immediately, before the next action:**

- **The user corrects something** — write it down *now*, in their framing. A correction batched to
  the end of the round comes back paraphrased.
- **A cross-seat hand-off succeeds or fails** — what was declared, when each seat committed, whether
  it landed.
- **The user explains why** — their reasoning is what can't be derived from data tables.

**At each phase boundary** (an automatic phase, end of round): consolidate. Fold captures into the
right file, rewrite rules that turned out wrong, drop noise. A dropped session then loses at most one
round. A fuller entry goes in `log.md` at game end.

| file | contents | how |
|---|---|---|
| `reference/coordination.md` | Cross-seat setup/payoff: declared, committed, landed? | Append to its log; promote repeatables into the protocol |
| `reference/heuristics.md` | Judgment that would change a future decision | **Edit in place**, confidence-tagged; a wrong rule is rewritten, not stacked beside its replacement |
| `reference/pieces.md` | Per-component notes (enemies, cards, locations) from meeting them live | One entry per piece, first time it teaches something |
| `reference/primer.md` | The numbers, derived from the game's data tables | Ideally **generated**, never hand-edited |
| `reference/log.md` | One block per game: seats, setup, outcome, what decided it | Append at game end |
| `reference/bugs.md` | Anything that looked wrong | Append. **Never fix during a game** |

- **What earns a heuristic:** something that would change a decision next game. "We lost on
  resources" is a log line.
- **The user's corrections outrank anything already written**, including seeded guesses.
- **Record the scope with the rule.** A narrow correction remembered as a broad rule makes play
  *worse* than before the lesson. Write the case — board state, qualifier, what it does **not**
  cover — and when a rule seems to apply somewhere new, check whether the reasoning transfers or only
  the sentence does.
- **Read the log for causation.** The board afterwards shows results; `#logs` shows the ordered
  cause. Read it every automatic phase. If the game is deterministic enough, **forecast the phase
  before it fires, say the number, and score it against the log** — a wrong model gets caught in one
  round instead of five. (See the forecast-script guidance in `reference/primer.md`.)
- If your project keeps cross-project notes elsewhere, mirror durable lessons to **your notes
  location, as configured in your CLAUDE.md** — after the game, not during it.

## The one repo rule — park bugs, don't fix them

**A session under this skill changes nothing in the repo except this skill's `reference/` files.**
No code edits, no deploys, no commits of other work. If the game reveals a bug — it will, that's a
side benefit — write it to `reference/bugs.md` with enough to reproduce (table, round, state,
expected vs. saw) and **play continues**. Stopping to fix the client turns a game night into a work
session, a deploy mid-game can break the table you're on, and a half-played table is hard to resume.
Committing the notes at game end is expected (on your working branch).

## Variant: a player and a scribe

Normally one session plays and writes its own notes — the session that took the correction
understands it best. For a long game, a second session can be the **scribe**: it owns every
`reference/` file; the player sends it raw observations via `SendMessage` the moment they happen
(quote the user verbatim where exact), never waits for a reply, and never edits the files itself. A
scribe with code access is also a useful **verification pass** for claims made at the table — but only
if it checks the live state; one reasoning from memory is worse than none. If no scribe is running,
write the files directly; that is the default, not a degraded mode.

## Reading before the first move

1. `reference/coordination.md` — first; how the seats hand work to each other.
2. `reference/primer.md` — the arithmetic that makes advice worth anything.
3. `reference/heuristics.md` — what has worked.
4. `reference/pieces.md` — only what's in play this game.
5. The game repo's rules/help docs, mid-game, for detail.
