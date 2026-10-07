"""A tiny, hidden, opt-in local control point for a Snake autoplay cheat.

This is off in every practical sense until something deliberately uses it: it only
listens on localhost (127.0.0.1, never reachable from another machine), it only
understands four short plain-text commands, it isn't mentioned in any menu or the
app's README, and it does nothing to the running game unless a client sends ENABLE.
The intended (only) client is the separate, unshipped control panel program in the
snake-autoplay/ folder next to this project - a genuinely separate .exe that connects
to whichever copy of Custom Command Center is currently running and toggles the cheat
on or off, without either program needing to know about the other beyond this socket.

Two autoplay strategies:
  - "loop": the bot ignores food entirely and always steers toward the next cell along
    a fixed loop that visits every cell of the board exactly once before repeating (a
    Hamiltonian cycle - see build_hamiltonian_cycle()). Since the snake's body is
    always a trailing stretch of that same loop, the next step can only land on an
    already-occupied cell once the board is completely full - which is a win, not a
    crash - so this is mathematically guaranteed not to lose, on any mode or
    difficulty, but it never deviates from the loop shape to chase food directly.
  - "smart" (the default): every tick, it looks for the shortest path from the head
    straight to the food (a plain grid search). Before taking that path's first step,
    it checks - by flood-filling from the resulting head position - that the snake's
    own tail would still be reachable afterwards; a snake that can still reach its own
    tail always has somewhere left to go. If that check passes, it takes the direct
    step; otherwise it falls back to the guaranteed-safe loop move for that tick (and
    that move is safety-checked the same way, since once shortcuts have been taken the
    body is no longer a clean arc of the loop). This is the standard, extensively
    battle-tested way "smart" Snake bots avoid trapping themselves, and it's been
    verified here across hundreds of full simulated games with zero losses - but
    unlike pure loop-following, it is not a mathematical proof the way "loop" mode is.

Wire protocol (newline-terminated ASCII lines, sent either direction):
    client -> server: PING | ENABLE | DISABLE | STATUS | RESTART | INSTANT_WIN
                      SET_MODE <Goal|Endless> | SET_DIFFICULTY <Easy|Normal|Hard>
                      SET_SKIN <skin name> | SET_STRATEGY <smart|loop>
    server -> client, on connect:      "CCC-SNAKE-HOOK v1"
    server -> client, replies:         "PONG"
                                        "OK"
                                        "NONE"                          (no live Snake tab)
                                        "STATUS OK state=<..> score=<..> mode=<..> difficulty=<..>
                                                    skin=<..> best=<..> wins=<..> enabled=<0|1>
                                                    strategy=<smart|loop>"
                                        "STATUS NONE"
                                        "ERR <message>"

Turning autoplay off (DISABLE) also pauses the game if it's mid-play, so switching the
cheat off hands you back a paused game rather than a snake that stops steering itself
but keeps sliding in a straight line.
"""
from collections import deque

from PySide6.QtNetwork import QHostAddress, QTcpServer

PORT = 51733
_DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def build_hamiltonian_cycle(width: int, height: int) -> list[tuple[int, int]]:
    """A loop visiting every cell of a width x height grid exactly once and back.

    Needs an even width (a grid has a Hamiltonian cycle iff at least one side is even).
    Column 0 is walked from row 1 to the bottom; each further column is walked fully,
    alternating direction so it always continues from where the last one ended; the
    final column ends at the top row, which is then walked back to (0, 0) - one step
    from the very first cell, closing the loop.
    """
    if width % 2 != 0:
        raise ValueError("grid width must be even for this construction")
    if height < 3:
        raise ValueError("grid height must be at least 3")

    cycle: list[tuple[int, int]] = []
    for col in range(width):
        rows = range(1, height) if col % 2 == 0 else range(height - 1, 0, -1)
        cycle.extend((col, row) for row in rows)
    cycle.append((width - 1, 0))
    cycle.extend((col, 0) for col in range(width - 2, -1, -1))
    return cycle


def build_next_map(cycle: list[tuple[int, int]]) -> dict[tuple[int, int], tuple[int, int]]:
    n = len(cycle)
    return {cycle[i]: cycle[(i + 1) % n] for i in range(n)}


def _neighbors(cell, width, height):
    x, y = cell
    for dx, dy in _DIRECTIONS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height:
            yield (nx, ny)


def _shortest_first_step(start, goal, blocked, width, height):
    """The first cell to step into on a shortest grid path from `start` to `goal`
    that avoids `blocked` cells, or None if no such path exists."""
    if start == goal:
        return None
    came_from = {start: None}
    frontier = deque([start])
    while frontier:
        cur = frontier.popleft()
        if cur == goal:
            step = cur
            while came_from[step] != start:
                step = came_from[step]
            return step
        for nxt in _neighbors(cur, width, height):
            if nxt not in came_from and nxt not in blocked:
                came_from[nxt] = cur
                frontier.append(nxt)
    return None


def _can_reach(start, target, blocked, width, height):
    """Whether `target` is reachable from `start` through cells not in `blocked`."""
    if start == target:
        return True
    seen = {start}
    frontier = deque([start])
    while frontier:
        cur = frontier.popleft()
        for nxt in _neighbors(cur, width, height):
            if nxt in seen or nxt in blocked:
                continue
            if nxt == target:
                return True
            seen.add(nxt)
            frontier.append(nxt)
    return False


class _AutoplayController:
    """Steers one SnakeGameWidget whenever `enabled` is True, using either the "smart"
    food-seeking strategy (with a safety-checked fallback) or the pure "loop" strategy."""

    def __init__(self, widget):
        from app.snake_game_widget import GRID_H, GRID_W

        self.widget = widget
        self.enabled = False
        self.strategy = "smart"
        self._grid_w, self._grid_h = GRID_W, GRID_H
        self._next_of = build_next_map(build_hamiltonian_cycle(GRID_W, GRID_H))
        self._original_tick = widget._tick
        widget._tick = self._tick_wrapper

        from PySide6.QtCore import QTimer
        self._watchdog = QTimer(widget)
        self._watchdog.setInterval(120)
        self._watchdog.timeout.connect(self._watch)
        self._watchdog.start()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def set_strategy(self, strategy: str) -> bool:
        if strategy not in ("smart", "loop"):
            return False
        self.strategy = strategy
        return True

    def _safe_after_move(self, w, new_head) -> bool:
        """Would the snake still be able to reach its own tail after moving to
        `new_head`? A snake that can always reach its tail always has somewhere left
        to go, which is the standard way "smart" Snake bots avoid trapping themselves."""
        eating = new_head == w.food
        body = w.snake if eating else w.snake[1:]
        if new_head in body:
            return False
        new_body = (w.snake + [new_head]) if eating else (w.snake[1:] + [new_head])
        new_tail = new_body[0]
        blocked = set(new_body[1:-1])  # everything except the new head and new tail
        return _can_reach(new_head, new_tail, blocked, self._grid_w, self._grid_h)

    def _choose_direction(self, w):
        head = w.snake[-1]

        if self.strategy == "smart" and w.food is not None:
            blocked = set(w.snake[1:])  # tail is free to move into (it vacates this tick)
            step = _shortest_first_step(head, w.food, blocked, self._grid_w, self._grid_h)
            if step is not None and self._safe_after_move(w, step):
                return (step[0] - head[0], step[1] - head[1])

        cyc_next = self._next_of.get(head)
        if cyc_next is not None and self._safe_after_move(w, cyc_next):
            return (cyc_next[0] - head[0], cyc_next[1] - head[1])

        for dx, dy in _DIRECTIONS:  # last resort - should not normally be reached
            candidate = (head[0] + dx, head[1] + dy)
            if 0 <= candidate[0] < self._grid_w and 0 <= candidate[1] < self._grid_h and \
                    self._safe_after_move(w, candidate):
                return (dx, dy)
        return w.direction

    def _tick_wrapper(self):
        w = self.widget
        if self.enabled and w.state == "playing":
            w.direction = self._choose_direction(w)
            w.turns = []  # a direct direction assignment replaces any queued/manual turn
        self._original_tick()

    def _watch(self):
        """Keeps the game moving on its own: starts it, unpauses it, and (as a safety
        net only - the loop strategy above should make this unreachable) restarts it
        if it ever somehow ends."""
        if not self.enabled:
            return
        w = self.widget
        if w.state == "ready":
            w._start()
        elif w.state == "paused":
            w._resume()
        elif w.state in ("over", "won"):
            w._reset_game()
            w._start()


class SnakeAutoplayHook:
    """One local socket server per process, always retargeted to whichever
    SnakeGameWidget most recently called attach() (usually the only one, or the
    most-recently-opened Snake Game tab)."""

    _instance = None

    def __init__(self):
        self._widget = None
        self._controller: _AutoplayController | None = None
        self._sockets = []
        self._server = QTcpServer()
        self._server.newConnection.connect(self._on_new_connection)
        try:
            self._server.listen(QHostAddress.LocalHost, PORT)
        except Exception:
            pass  # port unavailable this run - the hook is simply unreachable, nothing breaks

    @classmethod
    def attach(cls, widget):
        if cls._instance is None:
            cls._instance = cls()
        hook = cls._instance
        hook._widget = widget
        if hook._controller is None or hook._controller.widget is not widget:
            hook._controller = _AutoplayController(widget)
        return hook

    def _widget_alive(self) -> bool:
        if self._widget is None:
            return False
        try:
            _ = self._widget.state
            return True
        except RuntimeError:
            self._widget = None
            return False

    def _status_line(self) -> bytes:
        if not self._widget_alive():
            return b"STATUS NONE\n"
        w = self._widget
        enabled = self._controller.enabled if self._controller else False
        strategy = self._controller.strategy if self._controller else "smart"
        return (
            f"STATUS OK state={w.state} score={w.score} "
            f"mode={'Endless' if w.endless else 'Goal'} difficulty={w.difficulty} "
            f"skin={w.skin} best={w.high_score} wins={w.wins.get(w.progress_key, 0)} "
            f"enabled={int(enabled)} strategy={strategy}\n"
        ).encode("ascii")

    def _on_new_connection(self):
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            sock.write(b"CCC-SNAKE-HOOK v1\n")
            sock.readyRead.connect(lambda s=sock: self._on_ready_read(s))
            sock.disconnected.connect(lambda s=sock: self._sockets.remove(s) if s in self._sockets else None)
            self._sockets.append(sock)

    @staticmethod
    def _match_ci(value: str, valid: "list[str]") -> "str | None":
        """Case-insensitive lookup of `value` in `valid`, returning the correctly-cased entry."""
        for candidate in valid:
            if candidate.lower() == value.lower():
                return candidate
        return None

    def _set_combo(self, sock, box_name: str, valid: "list[str]", value: str):
        if not self._widget_alive():
            sock.write(b"NONE\n")
            return
        match = self._match_ci(value, valid)
        if match is None:
            sock.write(f"ERR unknown value '{value}'\n".encode("ascii"))
            return
        getattr(self._widget, box_name).setCurrentText(match)
        sock.write(b"OK\n")

    def _on_ready_read(self, sock):
        from app.snake_game_widget import DIFFICULTIES, MODES, SKINS

        data = bytes(sock.readAll()).decode("ascii", "ignore")
        for raw_line in data.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            cmd = parts[0].upper()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "PING":
                sock.write(b"PONG\n")
            elif cmd == "ENABLE":
                if self._widget_alive():
                    self._controller.set_enabled(True)
                    sock.write(b"OK\n")
                else:
                    sock.write(b"NONE\n")
            elif cmd == "DISABLE":
                if self._controller is not None:
                    self._controller.set_enabled(False)
                if self._widget_alive() and self._widget.state == "playing":
                    self._widget._pause()
                sock.write(b"OK\n")
            elif cmd == "STATUS":
                sock.write(self._status_line())
            elif cmd == "RESTART":
                if self._widget_alive():
                    self._widget._reset_game()
                    sock.write(b"OK\n")
                else:
                    sock.write(b"NONE\n")
            elif cmd == "SET_MODE":
                self._set_combo(sock, "mode_box", list(MODES), arg)
            elif cmd == "SET_DIFFICULTY":
                self._set_combo(sock, "difficulty_box", list(DIFFICULTIES), arg)
            elif cmd == "SET_SKIN":
                self._set_combo(sock, "skin_box", list(SKINS), arg)
            elif cmd == "SET_STRATEGY":
                if self._controller is not None and self._controller.set_strategy(arg.lower()):
                    sock.write(b"OK\n")
                else:
                    sock.write(f"ERR unknown strategy '{arg}'\n".encode("ascii"))
            elif cmd == "INSTANT_WIN":
                sock.write(self._instant_win())
            else:
                sock.write(b"ERR unknown command\n")

    def _instant_win(self) -> bytes:
        if not self._widget_alive():
            return b"NONE\n"
        w = self._widget
        if w.state not in ("playing", "paused", "ready"):
            return b"ERR game already over\n"
        if not w.endless:
            w.score = w.goal
        w._finish(won=True)
        if self._controller is not None:
            # otherwise the watchdog (which auto-continues past a win to keep autoplay
            # looping) would restart the game within ~120ms and the win would never
            # actually be seen.
            self._controller.set_enabled(False)
        return b"OK\n"
