"""A playable, cute Snake game tab drawn with QPainter and scaled to fill the available space.

The game logic runs on a fixed timestep (one move every `interval` ms, set by the difficulty),
while the picture is redrawn at the monitor's refresh rate with the snake sliding smoothly
between cells.
"""
import math
import random
import time

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QKeyEvent, QPainter, QPainterPath, QPen,
                           QPixmap)
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from app import settings_store
from app.themes import DEFAULT_THEME, GAME_PALETTES

_now = time.perf_counter          # patched in tests

GRID_W = 32
GRID_H = 18

# In Goal mode every level can be won by reaching its goal length.
DIFFICULTIES = {
    "Easy": {"start_ms": 200, "min_ms": 130, "step_ms": 2, "goal": 15, "wrap": True,
             "tip": "Walls wrap around, slow speed. Eat 15 to win."},
    "Normal": {"start_ms": 170, "min_ms": 100, "step_ms": 2, "goal": 25, "wrap": False,
               "tip": "Walls are deadly, medium speed. Eat 25 to win."},
    "Hard": {"start_ms": 140, "min_ms": 60, "step_ms": 3, "goal": 40, "wrap": False,
             "tip": "Walls are deadly and it gets fast. Eat 40 to win."},
}
DEFAULT_DIFFICULTY = "Easy"

MODES = {
    "Goal": "Reach the goal length to win.",
    "Endless": "No goal - play as long as you can and chase a high score.",
}
DEFAULT_MODE = "Goal"

SKINS = {
    "Mint": {"body": "#7be0a7", "belly": "#d9ffe9", "spot": "#4fbf85", "head": "#69d69b"},
    "Bubblegum": {"body": "#ff9ecb", "belly": "#ffe3f0", "spot": "#ff7ab6", "head": "#ff8bc0"},
    "Lemon": {"body": "#ffd75e", "belly": "#fff4c9", "spot": "#f5b83d", "head": "#ffcb45"},
    "Ocean": {"body": "#6ec6ff", "belly": "#ddf3ff", "spot": "#3fa6f0", "head": "#58b9fb"},
    "Grape": {"body": "#b79cff", "belly": "#ebe2ff", "spot": "#8f70f0", "head": "#a687fb"},
    "Rainbow": None,
    "Classic": None,      # uses the app theme's snake colors
}
DEFAULT_SKIN = "Mint"

MAX_QUEUED_TURNS = 3
FRAME_CAP_DT = 0.1        # a stall (window drag, etc.) never fast-forwards more than this
POP_DURATION = 0.5        # seconds the sparkle burst lasts
TAPER_CELLS = 6.0         # the tail thins out over this many cells

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

KEY_TO_DIR = {
    Qt.Key_Up: UP, Qt.Key_W: UP,
    Qt.Key_Down: DOWN, Qt.Key_S: DOWN,
    Qt.Key_Left: LEFT, Qt.Key_A: LEFT,
    Qt.Key_Right: RIGHT, Qt.Key_D: RIGHT,
}
KEY_TO_DIFFICULTY = {Qt.Key_1: "Easy", Qt.Key_2: "Normal", Qt.Key_3: "Hard"}

EYE_DARK = QColor("#2b2340")
CHEEK = QColor("#ff6f9f")
TONGUE = QColor("#ff4d6d")


def board_layout(width, height):
    """Cell size and top-left offset that fit the whole grid inside width x height."""
    cell = max(1.0, min(width / GRID_W, height / GRID_H))
    return cell, (width - cell * GRID_W) / 2, (height - cell * GRID_H) / 2


def _mix(a, b, t):
    a, b = QColor(a), QColor(b)
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


def _alpha(color, alpha):
    c = QColor(color)
    c.setAlpha(alpha)
    return c


def _pen(color, width):
    return QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def _step(a, b):
    """The real one-cell move from cell a to the adjacent cell b, even across a wrap-around edge."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx > 1:
        dx -= GRID_W
    elif dx < -1:
        dx += GRID_W
    if dy > 1:
        dy -= GRID_H
    elif dy < -1:
        dy += GRID_H
    return dx, dy


class _BoardWidget(QWidget):
    """Canvas that grows with the window; painting is delegated to the owning game."""

    def __init__(self, owner: "SnakeGameWidget"):
        super().__init__(owner)
        self.owner = owner
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(GRID_W * 10, GRID_H * 10)
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        self.owner._paint_board(event)

    def mousePressEvent(self, event):
        self.owner.setFocus()
        super().mousePressEvent(event)


class SnakeGameWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

        settings = settings_store.load_settings()
        self.high_scores = dict(settings.get("snake_high_scores") or {})
        legacy = settings.get("snake_high_score", 0)
        if legacy and "Hard" not in self.high_scores:
            self.high_scores["Hard"] = legacy
        self.wins = dict(settings.get("snake_wins") or {})
        difficulty = settings.get("snake_difficulty")
        self.difficulty = difficulty if difficulty in DIFFICULTIES else DEFAULT_DIFFICULTY
        self.endless = settings.get("snake_mode", DEFAULT_MODE) == "Endless"
        skin = settings.get("snake_skin")
        self.skin = skin if skin in SKINS else DEFAULT_SKIN
        self.palette = GAME_PALETTES.get(settings.get("theme", DEFAULT_THEME), GAME_PALETTES[DEFAULT_THEME])

        self.state = "ready"          # ready | playing | paused | over | won
        self.new_high_score = False
        self.snake = []
        self.turns = []
        self.direction = RIGHT
        self.score = 0
        self.food = (0, 0)
        self.prev_tail = None         # tail cell before the last move (for the sliding tail)
        self.grew = False             # did the last move eat food?
        self.accum = 0.0              # seconds since the last move
        self.game_time = 0.0          # seconds of actual play, drives animations
        self._last_frame = 0.0
        self.pops = []                # [x, y, born game_time] sparkle bursts where food was eaten
        self._cache_key = None
        self._bg_layer = None
        self._solid_colors = None
        self._rainbow_cache = {}
        self._pen_cache = {}
        self._last_dirty = None       # region painted by the previous frame

        font = QFont(settings["font_family"], settings["font_size"])
        self.info_label = QLabel()
        self.info_label.setFont(font)
        self.info_label.setWordWrap(True)

        self.mode_box = self._make_combo(list(MODES), "Endless" if self.endless else "Goal")
        self.difficulty_box = self._make_combo(list(DIFFICULTIES), self.difficulty)
        self.skin_box = self._make_combo(list(SKINS), self.skin)
        self.mode_box.currentTextChanged.connect(self._on_mode_changed)
        self.difficulty_box.currentTextChanged.connect(self._on_difficulty_changed)
        self.skin_box.currentTextChanged.connect(self._on_skin_changed)
        for i, (name, cfg) in enumerate(DIFFICULTIES.items()):
            self.difficulty_box.setItemData(i, cfg["tip"], Qt.ToolTipRole)
        for i, (name, tip) in enumerate(MODES.items()):
            self.mode_box.setItemData(i, tip, Qt.ToolTipRole)

        controls = QHBoxLayout()
        controls.addStretch(1)
        for text, box in (("Mode:", self.mode_box), ("Difficulty:", self.difficulty_box),
                          ("Snake:", self.skin_box)):
            controls.addWidget(QLabel(text))
            controls.addWidget(box)

        self.board = _BoardWidget(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.addLayout(controls)
        layout.addWidget(self.board, 1)

        # One timer drives everything: it redraws at the screen's refresh rate and
        # advances the game on a fixed timestep.
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._frame)

        self._reset_game()

        from app.snake_autoplay_hook import SnakeAutoplayHook
        SnakeAutoplayHook.attach(self)

    @staticmethod
    def _make_combo(items, current):
        box = QComboBox()
        box.setFocusPolicy(Qt.NoFocus)
        box.addItems(items)
        box.setCurrentText(current)
        return box

    # ---- configuration ----
    @property
    def config(self):
        return DIFFICULTIES[self.difficulty]

    @property
    def goal(self):
        return None if self.endless else self.config["goal"]

    @property
    def progress_key(self):
        return f"{self.difficulty} Endless" if self.endless else self.difficulty

    @property
    def high_score(self):
        return self.high_scores.get(self.progress_key, 0)

    def _on_difficulty_changed(self, name):
        if name in DIFFICULTIES and name != self.difficulty:
            self.difficulty = name
            self._save_progress()
            self._reset_game()

    def _on_mode_changed(self, name):
        endless = name == "Endless"
        if endless != self.endless:
            self.endless = endless
            self._save_progress()
            self._reset_game()

    def _on_skin_changed(self, name):
        if name in SKINS and name != self.skin:
            self.skin = name
            self._solid_colors = None
            self._save_progress()
            self.board.update()

    def _save_progress(self):
        settings = settings_store.load_settings()
        settings["snake_difficulty"] = self.difficulty
        settings["snake_mode"] = "Endless" if self.endless else "Goal"
        settings["snake_skin"] = self.skin
        settings["snake_high_scores"] = dict(self.high_scores)
        settings["snake_wins"] = dict(self.wins)
        settings_store.save_settings(settings)

    # ---- game state ----
    def _frame_interval_ms(self):
        screen = self.screen()
        hz = screen.refreshRate() if screen is not None else 60.0
        if not hz or hz < 30:
            hz = 60.0
        return max(4, int(round(1000.0 / hz)))

    def _reset_game(self):
        cx, cy = GRID_W // 2, GRID_H // 2
        self.snake = [(cx - 2, cy), (cx - 1, cy), (cx, cy)]
        self.direction = RIGHT
        self.turns = []
        self.score = 0
        self.accum = 0.0
        self.game_time = 0.0
        self.prev_tail = None
        self.grew = False
        self.pops = []
        self.new_high_score = False
        self.state = "ready"
        self._last_dirty = None
        self.timer.stop()
        self.food = self._random_food()
        self._update_info_label()
        self.board.update()

    def _start(self):
        first_move = self.state == "ready"
        self.state = "playing"
        self._last_frame = _now()
        self.timer.start(self._frame_interval_ms())
        if first_move:
            self._tick()          # start moving right away instead of after a pause
        self._update_info_label()

    def _pause(self):
        if self.state == "playing":
            self.state = "paused"
            self._last_dirty = None
            self.timer.stop()
            self._update_info_label()
            self.board.update()

    def _resume(self):
        if self.state == "paused":
            self._start()
            self.board.update()

    def _random_food(self):
        occupied = set(self.snake)
        choices = [(x, y) for x in range(GRID_W) for y in range(GRID_H) if (x, y) not in occupied]
        return random.choice(choices) if choices else None

    def _interval_for_score(self):
        cfg = self.config
        return max(cfg["min_ms"], cfg["start_ms"] - self.score * cfg["step_ms"])

    def _finish(self, won):
        self.state = "won" if won else "over"
        self._last_dirty = None
        self.timer.stop()
        self.accum = self._interval_for_score() / 1000.0     # the snake rests fully in its cell
        changed = False
        if self.score > self.high_score:
            self.high_scores[self.progress_key] = self.score
            self.new_high_score = True
            changed = True
        if won:
            self.wins[self.progress_key] = self.wins.get(self.progress_key, 0) + 1
            changed = True
        if changed:
            self._save_progress()
        self._update_info_label()
        self.board.update()

    def _update_info_label(self):
        hints = {
            "ready": "Press an arrow key or Space to start",
            "playing": "Arrows/WASD to move - Space pauses",
            "paused": "PAUSED - press Space or an arrow key to continue",
            "over": "GAME OVER" + (" - new best!" if self.new_high_score else "") + " - press Space to try again",
            "won": ("YOU WIN!" if not self.endless else "PERFECT - the board is full!") +
                   " - press Space to play again",
        }
        goal = f"/{self.goal}" if self.goal else ""
        wins = self.wins.get(self.progress_key, 0)
        self.info_label.setText(
            f"Snake ({self.progress_key})  |  Score: {self.score}{goal}  |  Best: {self.high_score}"
            f"  |  Wins: {wins}  |  {hints[self.state]}"
        )

    def _frame(self):
        """One display frame: advance the game clock, make any moves that are due, redraw."""
        now = _now()
        dt = min(max(now - self._last_frame, 0.0), FRAME_CAP_DT)
        self._last_frame = now
        if self.state == "playing":
            self.game_time += dt
            self.accum += dt
            interval = self._interval_for_score() / 1000.0
            while self.state == "playing" and self.accum >= interval:
                self.accum -= interval
                self._tick()
                interval = self._interval_for_score() / 1000.0
        self.pops = [p for p in self.pops if self.game_time - p[2] < POP_DURATION]
        self._update_board()

    def _dirty_rect(self):
        """Pixels that can differ between frames while playing, or None when a full repaint is needed."""
        board = self.board
        cell, ox, oy = board_layout(board.width(), board.height())
        verts = self._snake_vertices()
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        if min(xs) < -0.4 or max(xs) > GRID_W - 0.6 or min(ys) < -0.4 or max(ys) > GRID_H - 0.6:
            return None            # part of the snake is wrapping around the board edge
        margin = 1.7
        rect = QRectF(ox + (min(xs) + 0.5 - margin) * cell, oy + (min(ys) + 0.5 - margin) * cell,
                      (max(xs) - min(xs) + 2 * margin) * cell, (max(ys) - min(ys) + 2 * margin) * cell)
        if self.food is not None:
            fx, fy = self.food
            rect = rect.united(QRectF(ox + (fx - 0.9) * cell, oy + (fy - 1.3) * cell, 2.8 * cell, 2.8 * cell))
        for x, y, _born in self.pops:
            rect = rect.united(QRectF(ox + (x - 1.4) * cell, oy + (y - 1.4) * cell, 3.8 * cell, 3.8 * cell))
        return rect.toAlignedRect().intersected(board.rect())

    def _update_board(self):
        """Repaint only what moved (the union of where the snake was and is now)."""
        current = self._dirty_rect() if self.state == "playing" else None
        previous = self._last_dirty
        self._last_dirty = current
        if current is None or previous is None:
            self.board.update()
        else:
            self.board.update(current.united(previous))

    def _tick(self):
        """Make one move."""
        if self.state != "playing":
            return

        while self.turns:
            turn = self.turns.pop(0)
            if turn != OPPOSITE[self.direction]:
                self.direction = turn
                break

        head_x, head_y = self.snake[-1]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        if self.config["wrap"]:
            new_head = (new_head[0] % GRID_W, new_head[1] % GRID_H)
        elif not (0 <= new_head[0] < GRID_W and 0 <= new_head[1] < GRID_H):
            self._finish(won=False)
            return

        eating = new_head == self.food
        # The tail moves out of the way on the same tick, so stepping onto it is safe.
        body = self.snake if eating else self.snake[1:]
        if new_head in body:
            self._finish(won=False)
            return

        self.prev_tail = self.snake[0]
        self.grew = eating
        self.snake.append(new_head)
        if not eating:
            self.snake.pop(0)
        else:
            self.score += 1
            self.pops.append([new_head[0], new_head[1], self.game_time])
            if self.goal is not None and self.score >= self.goal:
                self._finish(won=True)
                return
            self.food = self._random_food()
            if self.food is None:
                self._finish(won=True)
                return

        self._update_info_label()

    # ---- input ----
    def _queue_turn(self, direction):
        last = self.turns[-1] if self.turns else self.direction
        if direction in (last, OPPOSITE[last]) or len(self.turns) >= MAX_QUEUED_TURNS:
            return
        self.turns.append(direction)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key_Space, Qt.Key_P):
            if self.state in ("over", "won"):
                self._reset_game()
                self._start()
            elif self.state == "ready":
                self._start()
            elif self.state == "playing":
                self._pause()
            elif self.state == "paused":
                self._resume()
            return
        if key in KEY_TO_DIFFICULTY and self.state != "playing":
            self.difficulty_box.setCurrentText(KEY_TO_DIFFICULTY[key])
            return
        if key == Qt.Key_E and self.state != "playing":
            self.mode_box.setCurrentText("Goal" if self.endless else "Endless")
            return
        if key == Qt.Key_C:
            names = list(SKINS)
            self.skin_box.setCurrentText(names[(names.index(self.skin) + 1) % len(names)])
            return
        direction = KEY_TO_DIR.get(key)
        if direction is not None:
            if self.state in ("over", "won"):
                return
            if self.state == "ready":
                if direction == OPPOSITE[self.direction]:
                    return
                self.direction = direction
                self._start()
                return
            if self.state == "paused":
                self._resume()
            self._queue_turn(direction)
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        self._pause()
        super().focusOutEvent(event)

    def hideEvent(self, event):
        self._pause()
        super().hideEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    # ---- geometry: where the snake really is between two moves ----
    def _progress(self):
        """0..1 - how far the snake has slid from its previous cell toward its current one."""
        if self.state in ("playing", "paused"):
            interval = self._interval_for_score() / 1000.0
            return max(0.0, min(1.0, self.accum / interval))
        return 1.0

    def _snake_vertices(self):
        """Path of the snake from tail to head in (unwrapped) cell units, with the head and tail
        part-way between cells. Wrap-around moves are unrolled so the path is continuous."""
        cells = self.snake
        n = len(cells)
        t = self._progress()
        pos = [None] * n
        pos[-1] = (float(cells[-1][0]), float(cells[-1][1]))
        for i in range(n - 2, -1, -1):
            dx, dy = _step(cells[i], cells[i + 1])
            pos[i] = (pos[i + 1][0] - dx, pos[i + 1][1] - dy)
        head = pos[-1]
        if t < 1.0:
            dx, dy = _step(cells[-2], cells[-1])
            head = (pos[-1][0] - (1 - t) * dx, pos[-1][1] - (1 - t) * dy)
        tail = pos[0]
        if self.prev_tail is not None and not self.grew and t < 1.0:
            dx, dy = _step(self.prev_tail, cells[0])
            tail = (pos[0][0] - (1 - t) * dx, pos[0][1] - (1 - t) * dy)
        return [tail] + pos[:-1] + [head]

    # ---- skins ----
    def _skin_colors(self, distance_from_head):
        """(body, belly, spot, head, outline, belly stripe) colors at a point of the body (cached)."""
        if self.skin == "Rainbow":
            hue = int(distance_from_head * 22) % 360
            colors = self._rainbow_cache.get(hue)
            if colors is None:
                body = QColor.fromHsv(hue, 130, 255)
                belly = _mix(body, "#ffffff", 0.55)
                colors = (body, belly, _mix(body, "#000000", 0.18), QColor.fromHsv(0, 150, 255),
                          _mix(body, "#000000", 0.55), _mix(belly, body, 0.2))
                self._rainbow_cache[hue] = colors
            return colors
        if self._solid_colors is None:
            if self.skin == "Classic":
                body, head = QColor(self.palette["snake_body"]), QColor(self.palette["snake_head"])
                belly, spot = _mix(body, "#ffffff", 0.35), _mix(body, "#000000", 0.2)
            else:
                sk = SKINS[self.skin]
                body, head, belly, spot = (QColor(sk["body"]), QColor(sk["head"]),
                                           QColor(sk["belly"]), QColor(sk["spot"]))
            self._solid_colors = (body, belly, spot, head, _mix(body, "#000000", 0.55), _mix(belly, body, 0.2))
        return self._solid_colors

    def _cached_pen(self, color, width):
        key = (color.rgba(), round(width, 1))
        pen = self._pen_cache.get(key)
        if pen is None:
            if len(self._pen_cache) > 600:
                self._pen_cache.clear()
            pen = self._pen_cache[key] = _pen(color, key[1])
        return pen

    # ---- drawing ----
    def _static_layer(self, w, h, dpr, cell, ox, oy):
        """The checkerboard never changes between moves, so it is drawn once and reused."""
        pal = self.palette
        key = (w, h, dpr, pal["background"], pal["grid"], pal["text"])
        if key == self._cache_key:
            return self._bg_layer
        area = QRectF(ox, oy, cell * GRID_W, cell * GRID_H)
        bg = QPixmap(max(1, int(w * dpr)), max(1, int(h * dpr)))
        bg.setDevicePixelRatio(dpr)
        p = QPainter(bg)
        p.setRenderHints(QPainter.Antialiasing)
        p.fillRect(QRectF(0, 0, w, h), QColor(pal["grid"]))
        clip = QPainterPath()
        clip.addRoundedRect(area, cell * 0.45, cell * 0.45)
        p.setClipPath(clip)
        dark = QColor(pal["background"])
        light = _mix(dark, QColor(pal["text"]), 0.05)
        for gy in range(GRID_H):
            for gx in range(GRID_W):
                p.fillRect(QRectF(ox + gx * cell, oy + gy * cell, cell + 0.6, cell + 0.6),
                           light if (gx + gy) % 2 else dark)
        p.end()
        self._cache_key, self._bg_layer = key, bg
        return bg

    def _draw_border(self, p, area, cell):
        pal = self.palette
        wrap = self.config["wrap"]
        width = max(2.0, cell * (0.10 if wrap else 0.14))
        pen = QPen(_alpha(pal["snake_head"], 150) if wrap else _alpha(pal["food"], 210), width)
        if wrap:
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(area.adjusted(width / 2, width / 2, -width / 2, -width / 2), cell * 0.45, cell * 0.45)

    def _paint_board(self, event):
        board = self.board
        if board.width() <= 0 or board.height() <= 0:
            return
        p = QPainter(board)
        self._render(p, board.width(), board.height(), board.devicePixelRatioF())

    def _render(self, p, w, h, dpr):
        """Draw the whole board onto painter p (also used to render frames off-screen in tests)."""
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        cell, ox, oy = board_layout(w, h)
        area = QRectF(ox, oy, cell * GRID_W, cell * GRID_H)
        p.drawPixmap(0, 0, self._static_layer(w, h, dpr, cell, ox, oy))

        clip = QPainterPath()
        clip.addRoundedRect(area, cell * 0.45, cell * 0.45)
        p.save()
        p.setClipPath(clip)
        self._draw_pops(p, cell, ox, oy)
        self._draw_food(p, cell, ox, oy)
        self._draw_snake(p, cell, ox, oy)
        p.restore()

        self._draw_border(p, area, cell)
        self._draw_overlay(p, area, cell)

    def _center(self, cell_xy, cell, ox, oy):
        return QPointF(ox + (cell_xy[0] + 0.5) * cell, oy + (cell_xy[1] + 0.5) * cell)

    def _draw_food(self, p, cell, ox, oy):
        if self.food is None:
            return
        c = self._center(self.food, cell, ox, oy)
        r = cell * 0.40 * (1 + 0.05 * math.sin(self.game_time * 6))
        color = QColor(self.palette["food"])
        p.setPen(Qt.NoPen)
        p.setBrush(_alpha("#000000", 55))
        p.drawEllipse(QPointF(c.x(), c.y() + r * 0.95), r * 0.85, r * 0.26)
        p.setBrush(_mix(color, "#000000", 0.35))
        p.drawEllipse(c, r + cell * 0.04, r + cell * 0.04)
        p.setBrush(color)
        p.drawEllipse(c, r, r)
        p.setBrush(_alpha("#ffffff", 150))
        p.drawEllipse(QPointF(c.x() - r * 0.4, c.y() - r * 0.4), r * 0.22, r * 0.16)
        p.setPen(_pen("#7a4a21", max(1.5, cell * 0.07)))
        p.drawLine(QPointF(c.x(), c.y() - r * 0.85), QPointF(c.x() + r * 0.15, c.y() - r * 1.4))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#5fcf6b"))
        p.save()
        p.translate(c.x() + r * 0.45, c.y() - r * 1.15)
        p.rotate(-28)
        p.drawEllipse(QPointF(0, 0), r * 0.5, r * 0.22)
        p.restore()

    def _draw_pops(self, p, cell, ox, oy):
        for x, y, born in self.pops:
            t = min(1.0, max(0.0, (self.game_time - born) / POP_DURATION))
            c = self._center((x, y), cell, ox, oy)
            fade = max(0, int(230 * (1 - t)))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(_alpha(self.palette["food"], fade), max(1.0, cell * 0.09 * (1 - t) + 1)))
            ring = cell * (0.4 + 0.6 * t)
            p.drawEllipse(c, ring, ring)
            p.setPen(Qt.NoPen)
            p.setBrush(_alpha("#ffe066", fade))
            for k in range(6):
                a = math.radians(k * 60 + 20)
                d = cell * (0.35 + 0.7 * t)
                dot = cell * 0.07 * (1 - t) + 0.8
                p.drawEllipse(QPointF(c.x() + math.cos(a) * d, c.y() + math.sin(a) * d), dot, dot)

    @staticmethod
    def _width_at(distance_from_tail, cell):
        return cell * (0.36 + 0.48 * min(1.0, distance_from_tail / TAPER_CELLS))

    def _body_pieces(self, verts):
        """Short straight pieces of the body: (x1, y1, x2, y2, distance from tail, distance from head)."""
        lengths = [math.hypot(verts[i + 1][0] - verts[i][0], verts[i + 1][1] - verts[i][1])
                   for i in range(len(verts) - 1)]
        total = sum(lengths)
        pieces = []
        walked = 0.0
        for i, seg in enumerate(lengths):
            if seg < 1e-6:
                continue
            (x1, y1), (x2, y2) = verts[i], verts[i + 1]
            parts = 3 if walked < TAPER_CELLS else 1     # thin tail: split so it tapers smoothly
            for k in range(parts):
                a, b = k / parts, (k + 1) / parts
                mid = walked + seg * (a + b) / 2
                pieces.append((x1 + (x2 - x1) * a, y1 + (y2 - y1) * a, x1 + (x2 - x1) * b,
                               y1 + (y2 - y1) * b, mid, total - mid))
            walked += seg
        return pieces, total

    @staticmethod
    def _point_from_head(verts, distance):
        remaining = distance
        for i in range(len(verts) - 1, 0, -1):
            (x2, y2), (x1, y1) = verts[i], verts[i - 1]
            seg = math.hypot(x2 - x1, y2 - y1)
            if seg >= remaining:
                f = remaining / seg if seg else 0
                return x2 + (x1 - x2) * f, y2 + (y1 - y2) * f
            remaining -= seg
        return verts[0]

    def _draw_snake(self, p, cell, ox, oy):
        verts = self._snake_vertices()
        pieces, total = self._body_pieces(verts)
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        if self.config["wrap"]:
            offsets = [(kx, ky) for kx in (-1, 0, 1) for ky in (-1, 0, 1)
                       if max(xs) + kx * GRID_W >= -1 and min(xs) + kx * GRID_W <= GRID_W
                       and max(ys) + ky * GRID_H >= -1 and min(ys) + ky * GRID_H <= GRID_H]
        else:
            offsets = [(0, 0)]
        spots = []
        if self.skin != "Rainbow":
            d = 2.4
            while d < total - 0.8:
                x, y = self._point_from_head(verts, d)
                spots.append((x, y, self._width_at(total - d, cell) * 0.14, d))
                d += 3.0
        outline_w = max(2.0, cell * 0.08)

        solid = self.skin != "Rainbow"
        individual = []     # pieces drawn as separate lines (thin tail, or every piece for Rainbow)
        run = []            # fixed-width body: stroked as one polyline per pass
        for x1, y1, x2, y2, d_tail, d_head in pieces:
            if solid and d_tail >= TAPER_CELLS:
                run.append((x1, y1, x2, y2))
                continue
            body, _belly, _spot, _head, outline, stripe = self._skin_colors(d_head)
            width = self._width_at(d_tail, cell)
            individual.append((x1, y1, x2, y2,
                               self._cached_pen(outline, width + 2 * outline_w),
                               self._cached_pen(body, width),
                               self._cached_pen(stripe, width * 0.27)))
        run_pens = None
        if run:
            body, _belly, _spot, _head, outline, stripe = self._skin_colors(0)
            width = self._width_at(TAPER_CELLS, cell)
            run_pens = (self._cached_pen(outline, width + 2 * outline_w),
                        self._cached_pen(body, width),
                        self._cached_pen(stripe, width * 0.27))
        spot_brushes = [(x, y, r, _alpha(self._skin_colors(d)[2], 200)) for x, y, r, d in spots]

        for kx, ky in offsets:
            ax = ox + (kx * GRID_W + 0.5) * cell
            ay = oy + (ky * GRID_H + 0.5) * cell
            run_path = None
            if run:
                run_path = QPainterPath(QPointF(ax + run[0][0] * cell, ay + run[0][1] * cell))
                for _x1, _y1, x2, y2 in run:
                    run_path.lineTo(QPointF(ax + x2 * cell, ay + y2 * cell))
            for pass_index in range(3):
                p.setBrush(Qt.NoBrush)
                if run_path is not None:
                    p.setPen(run_pens[pass_index])
                    p.drawPath(run_path)
                for piece in individual:
                    p.setPen(piece[4 + pass_index])
                    p.drawLine(QPointF(ax + piece[0] * cell, ay + piece[1] * cell),
                               QPointF(ax + piece[2] * cell, ay + piece[3] * cell))
            p.setPen(Qt.NoPen)
            for x, y, r, brush in spot_brushes:
                p.setBrush(brush)
                p.drawEllipse(QPointF(ax + x * cell, ay + y * cell), r, r)
            self._draw_head(p, cell, QPointF(ax + verts[-1][0] * cell, ay + verts[-1][1] * cell))

    def _draw_head(self, p, cell, c):
        head_color, outline = self._skin_colors(0)[3], self._skin_colors(0)[4]
        dx, dy = self.direction
        px, py = -dy, dx
        clock = self.game_time

        def pt(forward, side):
            return QPointF(c.x() + (dx * forward + px * side) * cell, c.y() + (dy * forward + py * side) * cell)

        radius = cell * 0.57
        outline_w = max(2.0, cell * 0.08)
        p.setPen(Qt.NoPen)
        p.setBrush(outline)
        p.drawEllipse(pt(0.04, 0), radius + outline_w, radius + outline_w)
        p.setBrush(head_color)
        p.drawEllipse(pt(0.04, 0), radius, radius)

        playing = self.state == "playing"
        if self.state == "over" or (playing and clock % 1.3 < 0.36):
            base, tip = pt(0.5, 0), pt(0.86, 0)
            p.setPen(_pen(TONGUE, max(1.5, cell * 0.07)))
            p.drawLine(base, tip)
            p.drawLine(tip, pt(1.0, 0.11))
            p.drawLine(tip, pt(1.0, -0.11))

        p.setPen(Qt.NoPen)
        p.setBrush(_alpha(CHEEK, 200))
        for side in (-1, 1):
            p.drawEllipse(pt(-0.06, side * 0.42), cell * 0.125, cell * 0.09)

        closed = self.state == "paused" or (playing and clock % 3.4 < 0.13)
        for side in (-1, 1):
            e = 0.23 * side
            if self.state == "over":
                p.setPen(_pen(EYE_DARK, max(1.5, cell * 0.07)))
                h = 0.085
                p.drawLine(pt(0.12 - h, e - h), pt(0.12 + h, e + h))
                p.drawLine(pt(0.12 - h, e + h), pt(0.12 + h, e - h))
            elif self.state == "won":
                path = QPainterPath(pt(0.07, e - 0.12))
                path.quadTo(pt(0.27, e), pt(0.07, e + 0.12))
                p.setPen(_pen(EYE_DARK, max(1.5, cell * 0.07)))
                p.setBrush(Qt.NoBrush)
                p.drawPath(path)
            elif closed:
                p.setPen(_pen(EYE_DARK, max(1.5, cell * 0.065)))
                p.drawLine(pt(0.12, e - 0.11), pt(0.12, e + 0.11))
            else:
                p.setPen(Qt.NoPen)
                center = pt(0.12, e)
                p.setBrush(_alpha(EYE_DARK, 210))
                p.drawEllipse(center, cell * 0.205, cell * 0.205)
                p.setBrush(QColor("#ffffff"))
                p.drawEllipse(center, cell * 0.185, cell * 0.185)
                pupil = pt(0.17, e)
                p.setBrush(EYE_DARK)
                p.drawEllipse(pupil, cell * 0.105, cell * 0.105)
                p.setBrush(QColor("#ffffff"))
                p.drawEllipse(QPointF(pupil.x() - cell * 0.035, pupil.y() - cell * 0.04), cell * 0.038, cell * 0.038)

        if self.state == "won":
            p.setPen(_pen("#ffe066", max(1.2, cell * 0.05)))
            for k in range(6):
                a = math.radians(k * 60 + 15)
                sx, sy = c.x() + math.cos(a) * cell * 0.95, c.y() + math.sin(a) * cell * 0.95
                s = cell * 0.11
                p.drawLine(QPointF(sx - s, sy), QPointF(sx + s, sy))
                p.drawLine(QPointF(sx, sy - s), QPointF(sx, sy + s))
        if self.state == "paused":
            p.setPen(_alpha(self.palette["text"], 230))
            p.setFont(QFont(self.info_label.font().family(), max(8, int(cell * 0.5)), QFont.Bold))
            p.drawText(QPointF(c.x() + cell * 0.55, c.y() - cell * 0.5), "z")
            p.setFont(QFont(self.info_label.font().family(), max(10, int(cell * 0.75)), QFont.Bold))
            p.drawText(QPointF(c.x() + cell * 0.85, c.y() - cell * 0.95), "Z")

    def _draw_overlay(self, p, area, cell):
        goal_line = "Endless - beat your best!" if self.endless else f"Eat {self.config['goal']} to win"
        best = "New best!" if self.new_high_score else ""
        messages = {
            "ready": ("Ready?", [goal_line, "Press an arrow key or Space"]),
            "paused": ("Paused", ["Press Space to continue"]),
            "over": ("Oh no!", [f"Score {self.score}", best, "Press Space to try again"]),
            "won": ("You win!" if not self.endless else "Perfect!",
                    [f"Score {self.score}", best, "Press Space to play again"]),
        }
        if self.state not in messages:
            return
        title, lines = messages[self.state]
        lines = [l for l in lines if l]
        family = self.info_label.font().family()
        title_font = QFont(family, max(14, int(cell * 0.95)), QFont.Bold)
        line_font = QFont(family, max(9, int(cell * 0.5)))
        tm, lm = QFontMetrics(title_font), QFontMetrics(line_font)
        width = max([tm.horizontalAdvance(title)] + [lm.horizontalAdvance(l) for l in lines]) + cell * 1.6
        height = tm.height() + lm.height() * len(lines) + cell * 1.2
        card = QRectF(area.center().x() - width / 2, area.center().y() - height / 2, width, height)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawRoundedRect(area, cell * 0.45, cell * 0.45)
        p.setPen(QPen(_alpha(self.palette["snake_head"], 200), max(2.0, cell * 0.08)))
        p.setBrush(_alpha(self.palette["background"], 235))
        p.drawRoundedRect(card, cell * 0.5, cell * 0.5)
        y = card.top() + cell * 0.45
        p.setFont(title_font)
        p.setPen(QColor(self.palette["snake_head"] if self.state != "over" else self.palette["food"]))
        p.drawText(QRectF(card.left(), y, card.width(), tm.height()), Qt.AlignHCenter | Qt.AlignVCenter, title)
        y += tm.height()
        p.setFont(line_font)
        p.setPen(QColor(self.palette["text"]))
        for line in lines:
            p.drawText(QRectF(card.left(), y, card.width(), lm.height()), Qt.AlignHCenter | Qt.AlignVCenter, line)
            y += lm.height()

    # ---- shared widget interface used by MainWindow ----
    def set_font(self, family: str, size: int):
        self.info_label.setFont(QFont(family, size))

    def set_theme(self, theme_name: str):
        self.palette = GAME_PALETTES.get(theme_name, GAME_PALETTES[DEFAULT_THEME])
        self._solid_colors = None
        self.board.update()

    def shutdown(self):
        self.timer.stop()
