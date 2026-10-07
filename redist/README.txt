Custom Command Center
======================

How to install:
1. Make sure this whole "redist" folder stays together (don't move just
   the .exe by itself).
2. Double-click "Install.bat".
3. If Windows shows a blue "Windows protected your PC" screen, click
   "More info" then "Run anyway" - this just means the app isn't signed
   with a paid certificate, it's not a virus.
4. That's it. A "Custom Command Center" shortcut will appear on your
   Desktop and in the Start Menu. Nothing else needs to be installed -
   no Python, no extra downloads.

Updating to a newer version later: just run "Install.bat" again from a
newer redist folder. It automatically detects an older version, closes
the app if it's running, and replaces it - no need to uninstall first.
If you're already on the latest version, it tells you and does nothing.

How to use it:
- On the left is the Explorer - a file browser for your own projects. It
  starts pointed at a "CustomCommandCenter Projects" folder in your
  Documents. Right-click (or use the buttons) to make a New File or New
  Folder, then double-click any file to open and edit it. Ctrl+B toggles
  the panel.
- You can have more than one folder open at once. Click "Add Folder..."
  to open another one alongside it - each gets its own labeled section
  with a "x" button to close it. You can also just drag a folder from
  Windows Explorer and drop it onto the app to open it (drop a file the
  same way to open it in an editor tab), anywhere in the window.
- Got a single script that isn't inside any open folder? Click "Add
  File..." (or drag the file in) to pin it under "Loose Files" at the
  bottom of the Explorer, so it's still one click away next time you
  open the app. Right-click it there to rename, delete or unpin it.
- Double-click any file in the Explorer to open it. Python files (.py)
  open in a Python Lab tab (run with F5). Everything else - HTML, CSS,
  JavaScript, JSON, Markdown, plain text - opens in a code editor tab
  with colored syntax, auto-closing tags/brackets and auto-indent.
  Ctrl+S saves, Ctrl+Shift+S saves as, Ctrl+O opens any file, Ctrl+T
  starts a new blank text/code file. A "*" on a tab means unsaved
  changes; you'll be asked before closing it.
  Saving writes straight to the real file in your folder. If the file
  is changed by another program while it's open here, the tab reloads it
  (or asks first if you have unsaved edits), and you're warned before
  saving over a newer version. Rename a file or folder in the Explorer
  (F2 or right-click > Rename) and any open tab follows it.
- Emmet: type a shorthand and press Tab to expand it. For example
  "ul>li*3" in an HTML file becomes a list with three items, "!" gives
  a full HTML page, and "m10-20" in CSS gives "margin: 10px 20px;".
  Tab again jumps between the spots to fill in. Works in HTML, XML,
  XSL, JSX/TSX, Pug, HAML, Slim, CSS/SCSS/Less, Sass and Stylus files
  (and inside <style> blocks in HTML). The Emmet menu has the other
  Emmet actions (wrap with abbreviation, balance tags, remove tag,
  toggle comment, math, number stepping, edit points, ...) with their
  keyboard shortcuts, and "Emmet Cheat Sheet" (F1) lists everything.
  You can turn it off in Preferences or the Emmet menu.
- Code colors are separate from the app theme, so your code stays easy
  to read whichever app theme you use. Pick from 9 code color schemes
  (Dark+, Monokai, Dracula, One Dark, Solarized Dark/Light, GitHub
  Light, High Contrast, Retro Green) in Settings > Preferences (with a
  live preview) or View > Code Colors.
- HTML files have a "Preview in Browser" button (or press F5): it saves
  the file and opens it in your web browser. After editing, save and
  refresh the browser page to see changes.
- It opens with two tabs: a Terminal tab (a real command prompt) and a
  Python Lab tab (for writing and running Python code).
- In the Python Lab tab: type code on the left and click "Run" (or press
  F5) to run it. Use the Console on the right to try quick one-line bits
  of code, like a calculator (try typing 2 + 2 and press Enter).
  tkinter (Python's built-in GUI toolkit) works too - a program that
  opens a window with `import tkinter` will pop up its own window
  while your code runs.
- Click the "+" button (top-right of the tab bar) to open more Terminal,
  Python Lab, or Snake Game tabs.
- Snake Game tab: it waits for you - press an arrow key (or WASD) or
  Space to start, Space/P to pause. Eat enough food to WIN: 15 on Easy
  (walls wrap around, slow), 25 on Normal, 40 on Hard. Pick the level
  with the Difficulty box or keys 1/2/3. Your best score and win count
  are saved for each level. The board grows to fill the window; press
  F11 for full screen (Esc to leave it).
  The snake glides smoothly between squares and the game redraws at
  your monitor's refresh rate (60/120/144 Hz), so it stays smooth on
  any window size.
  Mode: "Endless" removes the goal - keep going for a high score (each
  difficulty keeps its own Endless best; press E to switch modes). The
  Snake box (or the C key) changes the look: Mint, Bubblegum, Lemon,
  Ocean, Grape, Rainbow or Classic. Easy has a dashed border (walls
  wrap); Normal/Hard have a solid red border (walls hurt).
- Settings menu > Preferences lets you change the theme, font, font
  size, and turn Autocorrect on/off. Autocorrect auto-closes brackets
  and quotes as you type (e.g. typing "(" adds the matching ")") and
  auto-indents new lines - handy for learning, but you can switch it
  off in Preferences if you'd rather type everything yourself.
  View menu > Theme is a quicker way to switch themes.

To uninstall: run "Uninstall.bat" in this folder.
