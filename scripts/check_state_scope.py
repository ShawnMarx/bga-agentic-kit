#!/usr/bin/env python3
"""Catch `this.<GameMethod>()` called from inside a STATE class in modules/js/Game.js.

Assumes the modern-skeleton client layout: state classes as top-level `class X {` blocks first,
then the Game class body. Written for The Reckoners (the examples below); adjust if your
Game.js is laid out differently — the script refuses to run rather than guess.

Why this exists
---------------
The client has two kinds of object and one `this`:

  * the **state classes** at the top of the file (`ChooseCharacter`, `RollDice`, `UseDice`, …),
    each built as `constructor(game, bga)` -- inside them, the game is `this.game`;
  * the **Game class** below them, which owns ~400 helpers -- inside it, they are `this.helper()`.

Copying a line from one into the other compiles, lints, and then dies in the browser. On
2026-09-08 a solo-wording edit put `this.waitTitle(...)` into `ChooseCharacter.render()`. It threw
"this.waitTitle is not a function" at the exact moment the last character was confirmed, so the
client wedged on "Updating..." while the server advanced without it -- a table that looked hung
but was fine after a reload, which is a genuinely expensive thing to diagnose.

Neither existing check sees it:

  * `node --check` only parses.
  * the eslint `no-undef` pass resolves *identifiers*; `this.waitTitle` is a property access on an
    object, which is legal until it runs.

So this is a third check, and it belongs in the same `&&` chain before every deploy:

    node --check modules/js/Game.js \\
      && npx --yes eslint@9 --no-config-lookup -c eslint.config.mjs modules/js/Game.js \\
      && python3 scripts/check_state_scope.py modules/js/Game.js \\
      && ./deploy.sh ...

Exit code 1 with the offending lines if it finds any, 0 otherwise.

It is deliberately conservative: it only flags a name that is NOT defined on the state class
itself and IS defined on Game, so a genuine same-named method on both is never reported.
"""
import re
import sys
from pathlib import Path

# Usage: check_state_scope.py [path/to/Game.js]   (default: modules/js/Game.js under the cwd)
GAME_JS = Path(sys.argv[1] if len(sys.argv) > 1 else "modules/js/Game.js")

# `this.foo` is fine for these regardless of where it appears.
ALWAYS_OK = {"game", "bga"}


def method_names(lines):
    """Method names declared at one level of indentation inside a class body."""
    out = set()
    for ln in lines:
        m = re.match(r"^    (?:static\s+)?(?:async\s+)?(\w+)\s*\(", ln)
        if m and m.group(1) not in ("if", "for", "while", "switch", "catch", "return"):
            out.add(m.group(1))
    return out


def main():
    lines = GAME_JS.read_text(encoding="utf-8").split("\n")

    # The state classes are the top-level `class X {` blocks; the Game class body is everything
    # after the last of them. Game is not declared as a bare top-level `class Game`, so it is
    # found by exclusion rather than by name.
    starts = [i for i, ln in enumerate(lines) if re.match(r"^class\s+\w+", ln)]
    if not starts:
        print("check_state_scope: no `class` declarations found -- has Game.js been restructured?")
        return 1

    # End of the last state class = its closing brace at column 0.
    state_end = None
    for i in range(starts[-1], len(lines)):
        if lines[i] == "}":
            state_end = i + 1
            break
    if state_end is None:
        print("check_state_scope: could not find the end of the state classes")
        return 1

    game_own = method_names(lines[state_end:])
    if len(game_own) < 10:
        print(f"check_state_scope: only {len(game_own)} Game methods found -- layout changed, "
              "this check needs updating rather than trusting")
        return 1

    bad = []
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else state_end
        cls = re.match(r"^class\s+(\w+)", lines[i]).group(1)
        own = method_names(lines[i:end])
        for off, ln in enumerate(lines[i:end]):
            code = ln.split("//")[0]          # ignore anything in a trailing comment
            for m in re.finditer(r"\bthis\.(\w+)\s*\(", code):
                name = m.group(1)
                if name in own or name in ALWAYS_OK:
                    continue
                if name in game_own:
                    bad.append((i + off + 1, cls, name, ln.strip()))

    if not bad:
        print(f"check_state_scope: OK ({len(starts)} state classes, {len(game_own)} Game methods)")
        return 0

    print("check_state_scope: FAIL -- a state class is calling a Game method on itself.")
    print("Inside a state class the game is `this.game`, not `this`.\n")
    for ln, cls, name, txt in bad:
        print(f"  modules/js/Game.js:{ln}  [{cls}]  this.{name}()  ->  this.game.{name}()")
        print(f"      {txt[:120]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
