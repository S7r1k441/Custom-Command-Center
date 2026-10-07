Snake Autoplay Cheat (dev tool - NOT shipped in the release)
==============================================================

A separate, standalone program ("Snake Autoplay Cheat.exe") that remote-controls the
Snake game inside an already-running copy of Custom Command Center - like a game
trainer that attaches to a running process, except the "attach point" is a small,
hidden, off-by-default local connection built into the real app
(app/snake_autoplay_hook.py) that does nothing until this separate program connects
to it. This folder is a sibling of app/ and redist/, so it's never picked up by the
main project's build.ps1 or its release zip - it's a personal/dev tool, not something
meant to be shared with your brother.

How to run it:
1. Build it once (or after editing autoplay_control_panel.py):
       .\build_control_panel.ps1
   This produces "Snake Autoplay Cheat.exe" in this folder, using the main project's
   existing venv.
2. Open Custom Command Center and start a Snake Game tab.
3. Double-click "Snake Autoplay Cheat.exe". It finds and attaches to the running app
   automatically - no need to launch anything in a special way.

What it can do:
- ENABLE AUTOPLAY (F9): the snake plays itself and can't lose - see "Pathing" below.
  Turning it off pauses the game rather than leaving it running unsteered.
- Pathing: "Smart" beelines straight for the apple, checking every single move (with a
  flood-fill reachability check) that it won't trap itself, and falls back to the old
  guaranteed-safe loop pattern for that one move whenever going straight for the apple
  isn't verified safe. "Loop" disables the food-seeking entirely and always follows the
  fixed loop, which is a mathematical guarantee rather than a very-well-tested one (see
  the module docstring in app/snake_autoplay_hook.py for the full reasoning and the
  difference between the two).
- Instant Win: jumps straight to a win.
- Mode / Difficulty / Snake skin / Restart Game: same options as the real game, applied
  live to the running copy.

Nothing here touches your real high scores in a way you wouldn't expect - it's driving
the real game exactly as if you'd clicked those same controls yourself, so wins/scores
save normally, same as manual play.
