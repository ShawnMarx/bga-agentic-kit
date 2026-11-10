# <Game> primer — the numbers

<!-- TEMPLATE. Arithmetic on the game's own data tables: what the board IS. What to DO about it goes
     in heuristics.md.

     Strongly recommended: GENERATE this file rather than writing it. Your server code already holds
     the data tables (component stats, dice faces, track lookups, card costs). A small script in this
     skill's scripts/ (e.g. scripts/build_primer.py) can text-extract those constants from
     modules/php/Game.php, compute the tables below, and write this file with a
     "GENERATED — do not hand-edit" header. Re-run it after any balance/data change, so the primer
     can never drift from the code. (Reckoners did exactly this.)

     Optional second script: a FORECAST (e.g. scripts/forecast.py) for any automatic phase that is
     mostly deterministic. Feed it a small JSON of the live board; it outputs exactly what the phase
     will cost, and flags (never silently drops) what it doesn't model. Forecast before the phase,
     score against the log after. In Reckoners this was the single biggest improvement in play. -->

## Randomness: what you can and can't count on

<!-- Probabilities for the random elements: dice faces, deck draws, shuffles. "Chance of at least N
     of X", "expected count of X". The headline should be the counter-intuitive one (e.g. "one roll
     of six dice expects ONE of the symbol you need"). Then 2–4 bullets on what that implies. -->

## The clock — how you lose

<!-- What ends the game against you, how fast, and through which channels. If loss comes through
     more than one channel, separate them: they usually need different answers. -->

## The win condition — what it costs

<!-- What has to happen to win, in units of the game's resources, and what pays it down
     indirectly. -->

## Component threat / value table

<!-- One row per enemy / card / location type: stats, what it does over its lifetime, and a
     "cost to deal with" figure. Sort by whatever decides priority. -->

## Economy

<!-- Costs and income: what a unit of currency buys, by price band. -->

## Caveats

<!-- What these averages are NOT good for (e.g. "averages are not a forecast — use the forecast
     script for a specific board"). -->
