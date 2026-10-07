"""Snake Autoplay Cheat - a genuinely separate program that remote-controls the Snake
game inside an already-running copy of Custom Command Center.

This window does not run any Snake logic itself. It's a remote control: it opens a
plain TCP connection to 127.0.0.1 on the port the real app's Snake game listens on
(a small, hidden, off-by-default hook - see app/snake_autoplay_hook.py in the main
project - that does nothing until a client like this one connects) and sends it short
text commands (ENABLE / DISABLE / STATUS / RESTART / INSTANT_WIN / SET_MODE /
SET_DIFFICULTY / SET_SKIN / SET_STRATEGY). All of the actual steering runs inside
Custom Command Center itself, using the exact same game state - this window just
remote-controls it and shows what's happening.

This file lives outside app/ and redist/, so it is never bundled into the real app's
.exe and never shipped in the release zip. build_control_panel.ps1 in this same folder
packages *this* file into its own separate "Snake Autoplay Cheat.exe".
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QTcpSocket
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

# Must match PORT in app/snake_autoplay_hook.py in the main project - kept as a plain
# constant here (rather than imported) so this program stays fully standalone and never
# needs to bundle any of the main app's code.
PORT = 51733

RECONNECT_MS = 1000
POLL_MS = 500

MODES = ["Goal", "Endless"]
DIFFICULTIES = ["Easy", "Normal", "Hard"]
SKINS = ["Mint", "Bubblegum", "Lemon", "Ocean", "Grape", "Rainbow", "Classic"]
STRATEGIES = ["Smart", "Loop"]

NOT_FOUND_TEXT = (
    "TARGET NOT FOUND\nOpen Custom Command Center and start (or switch to) a Snake "
    "Game tab - this attaches automatically."
)
NO_SNAKE_TAB_TEXT = "ATTACHED, but no Snake Game tab is open there right now."

MONO_FAMILY = "Consolas"

CHEAT_QSS = f"""
QMainWindow, QWidget {{ background-color: #0d1117; color: #c7d0e0; font-family: "{MONO_FAMILY}"; }}
QLabel {{ color: #c7d0e0; }}
QLabel#title {{ color: #39ff6a; font-size: 20px; font-weight: 800; letter-spacing: 1px; }}
QLabel#subtitle {{ color: #5c6b8a; font-size: 11px; }}
QLabel#hint {{ color: #8892b0; }}
QLabel#hint_warn {{ color: #ffb545; font-weight: 600; }}
QGroupBox {{
    border: 1px solid #23293d; border-radius: 8px; margin-top: 14px;
    padding: 10px 8px 8px 8px; font-weight: 700; color: #39ff6a; font-size: 11px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
QComboBox, QPushButton {{
    background-color: #161b28; border: 1px solid #2a3352; border-radius: 5px;
    padding: 6px 10px; color: #d7ddee;
}}
QComboBox:disabled, QPushButton:disabled {{ color: #454f6b; border-color: #1c2136; }}
QComboBox:hover, QPushButton:hover:!disabled {{ border-color: #39ff6a; }}
QPushButton#toggleOff {{
    font-weight: 800; font-size: 15px; padding: 14px; background-color: #161b28;
    border: 2px solid #2a3352; letter-spacing: 1px;
}}
QPushButton#toggleOn {{
    font-weight: 800; font-size: 15px; padding: 14px; background-color: #0f3d24;
    border: 2px solid #39ff6a; color: #b9ffce; letter-spacing: 1px;
}}
QPushButton#winBtn {{
    font-weight: 700; padding: 9px; background-color: #3a2c0b; border: 1px solid #ffb545;
    color: #ffd98a;
}}
QPushButton#winBtn:hover {{ border-color: #ffd54a; }}
QPushButton#restart {{ padding: 8px; }}
QLabel.stat {{ color: #6dd6ff; font-weight: 700; }}
"""


class ControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snake Autoplay Cheat")
        self.resize(440, 640)

        self.socket = QTcpSocket()
        self.socket.readyRead.connect(self._on_ready_read)
        self.socket.disconnected.connect(self._on_disconnected)
        self._recv_buffer = ""
        self._connected = False
        self._syncing = False  # true while controls are set programmatically from STATUS

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        # ---- header ----
        title = QLabel("☠  SNAKE TRAINER")
        title.setObjectName("title")
        subtitle = QLabel("100% survival rate  •  undetectable by the snake")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        conn_row = QHBoxLayout()
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color: #e05555; font-size: 13px;")
        self.conn_label = QLabel("TARGET: searching...")
        mono_bold = QFont(MONO_FAMILY)
        mono_bold.setBold(True)
        self.conn_label.setFont(mono_bold)
        conn_row.addWidget(self.dot)
        conn_row.addWidget(self.conn_label, 1)
        root.addLayout(conn_row)

        self.hint_label = QLabel(NOT_FOUND_TEXT)
        self.hint_label.setObjectName("hint_warn")
        self.hint_label.setWordWrap(True)
        root.addWidget(self.hint_label)

        # ---- live stats ----
        stats_box = QGroupBox("LIVE STATS")
        stats_form = QFormLayout(stats_box)
        self.state_value = self._stat_label()
        self.score_value = self._stat_label()
        self.best_value = self._stat_label()
        self.wins_value = self._stat_label()
        stats_form.addRow("State:", self.state_value)
        stats_form.addRow("Score:", self.score_value)
        stats_form.addRow("Best:", self.best_value)
        stats_form.addRow("Wins:", self.wins_value)
        root.addWidget(stats_box)

        # ---- the cheats ----
        cheats_box = QGroupBox("CHEATS")
        cheats_layout = QVBoxLayout(cheats_box)
        cheats_layout.setSpacing(8)

        self.toggle_btn = QPushButton("[ F9 ]  ENABLE AUTOPLAY")
        self.toggle_btn.setObjectName("toggleOff")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setMinimumHeight(54)
        self.toggle_btn.toggled.connect(self._on_toggle)
        cheats_layout.addWidget(self.toggle_btn)

        strategy_row = QHBoxLayout()
        strategy_row.addWidget(QLabel("Pathing:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(STRATEGIES)
        strategy_row.addWidget(self.strategy_combo, 1)
        cheats_layout.addLayout(strategy_row)

        strategy_hint = QLabel("Smart chases the apple; Loop is the old fixed safe pattern.")
        strategy_hint.setObjectName("hint")
        strategy_hint.setWordWrap(True)
        cheats_layout.addWidget(strategy_hint)

        self.win_btn = QPushButton("⚡  INSTANT WIN")
        self.win_btn.setObjectName("winBtn")
        cheats_layout.addWidget(self.win_btn)

        note = QLabel("Disabling autoplay pauses the game instead of leaving it unsteered.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        cheats_layout.addWidget(note)

        root.addWidget(cheats_box)

        # ---- game settings ----
        settings_box = QGroupBox("GAME SETTINGS")
        settings_form = QFormLayout(settings_box)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODES)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(DIFFICULTIES)
        self.skin_combo = QComboBox()
        self.skin_combo.addItems(SKINS)
        self.restart_btn = QPushButton("Restart Game")
        self.restart_btn.setObjectName("restart")
        settings_form.addRow("Mode:", self.mode_combo)
        settings_form.addRow("Difficulty:", self.difficulty_combo)
        settings_form.addRow("Snake:", self.skin_combo)
        settings_form.addRow(self.restart_btn)
        root.addWidget(settings_box)
        root.addStretch(1)

        self.mode_combo.currentTextChanged.connect(lambda v: self._send_set("SET_MODE", v))
        self.difficulty_combo.currentTextChanged.connect(lambda v: self._send_set("SET_DIFFICULTY", v))
        self.skin_combo.currentTextChanged.connect(lambda v: self._send_set("SET_SKIN", v))
        self.strategy_combo.currentTextChanged.connect(lambda v: self._send_set("SET_STRATEGY", v.lower()))
        self.restart_btn.clicked.connect(lambda: self._send_line("RESTART"))
        self.win_btn.clicked.connect(lambda: self._send_line("INSTANT_WIN"))

        self._set_controls_enabled(False)

        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.setInterval(RECONNECT_MS)
        self.reconnect_timer.timeout.connect(self._try_connect)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(POLL_MS)
        self.poll_timer.timeout.connect(self._poll_status)

        self.reconnect_timer.start()
        self._try_connect()

    @staticmethod
    def _stat_label() -> QLabel:
        label = QLabel("-")
        label.setProperty("class", "stat")
        label.setStyleSheet("color: #6dd6ff; font-weight: 700;")
        return label

    def _set_toggle_style(self, enabled: bool):
        self.toggle_btn.setObjectName("toggleOn" if enabled else "toggleOff")
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)
        self.toggle_btn.setText("[ F9 ]  AUTOPLAY: ON" if enabled else "[ F9 ]  ENABLE AUTOPLAY")

    def _set_controls_enabled(self, enabled: bool):
        widgets = (
            self.mode_combo, self.difficulty_combo, self.skin_combo, self.restart_btn,
            self.toggle_btn, self.strategy_combo, self.win_btn,
        )
        for w in widgets:
            w.setEnabled(enabled)

    # ---- connection lifecycle ----
    def _try_connect(self):
        if self.socket.state() == QAbstractSocket.SocketState.UnconnectedState:
            self.socket.connectToHost(QHostAddress.LocalHost, PORT)

    def _on_disconnected(self):
        self._connected = False
        self.poll_timer.stop()
        self._set_controls_enabled(False)
        self.toggle_btn.blockSignals(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.blockSignals(False)
        self._set_toggle_style(False)
        self.dot.setStyleSheet("color: #e05555; font-size: 13px;")
        self.conn_label.setText("TARGET: searching...")
        self.hint_label.setObjectName("hint_warn")
        self.hint_label.setStyleSheet("")
        self.hint_label.setText(NOT_FOUND_TEXT)
        for label in (self.state_value, self.score_value, self.best_value, self.wins_value):
            label.setText("-")
        if not self.reconnect_timer.isActive():
            self.reconnect_timer.start()

    # ---- wire protocol ----
    def _send_line(self, line: str):
        if self.socket.state() == QAbstractSocket.SocketState.ConnectedState:
            self.socket.write((line + "\n").encode("ascii"))

    def _send_set(self, command: str, value: str):
        if not self._syncing:
            self._send_line(f"{command} {value}")

    def _on_ready_read(self):
        self._recv_buffer += bytes(self.socket.readAll()).decode("ascii", "ignore")
        while "\n" in self._recv_buffer:
            line, self._recv_buffer = self._recv_buffer.split("\n", 1)
            self._handle_line(line.strip())

    def _handle_line(self, line: str):
        if line.startswith("CCC-SNAKE-HOOK"):
            self._connected = True
            self.reconnect_timer.stop()
            self.poll_timer.start()
            self.dot.setStyleSheet("color: #39ff6a; font-size: 13px;")
            self.conn_label.setText("TARGET: Custom Command Center [ATTACHED]")
            self._poll_status()
        elif line == "STATUS NONE":
            self._set_controls_enabled(False)
            self.hint_label.setObjectName("hint")
            self.hint_label.setStyleSheet("color: #8892b0;")
            self.hint_label.setText(NO_SNAKE_TAB_TEXT)
            for label in (self.state_value, self.score_value, self.best_value, self.wins_value):
                label.setText("-")
        elif line.startswith("STATUS OK"):
            self._apply_status(line)

    def _apply_status(self, line: str):
        fields = dict(part.split("=", 1) for part in line.split()[2:] if "=" in part)
        enabled = fields.get("enabled") == "1"

        self._set_controls_enabled(True)
        self.hint_label.setText("")

        self._syncing = True
        self.mode_combo.setCurrentText(fields.get("mode", MODES[0]))
        self.difficulty_combo.setCurrentText(fields.get("difficulty", DIFFICULTIES[0]))
        self.skin_combo.setCurrentText(fields.get("skin", SKINS[0]))
        self.strategy_combo.setCurrentText(fields.get("strategy", "smart").capitalize())
        self._syncing = False

        self.toggle_btn.blockSignals(True)
        self.toggle_btn.setChecked(enabled)
        self.toggle_btn.blockSignals(False)
        self._set_toggle_style(enabled)

        self.state_value.setText(fields.get("state", "?").upper())
        self.score_value.setText(fields.get("score", "?"))
        self.best_value.setText(fields.get("best", "?"))
        self.wins_value.setText(fields.get("wins", "?"))

    def _poll_status(self):
        if self.socket.state() == QAbstractSocket.SocketState.ConnectedState:
            self.socket.write(b"STATUS\n")
        else:
            self._on_disconnected()

    def _on_toggle(self, checked: bool):
        self._send_line("ENABLE" if checked else "DISABLE")
        self._set_toggle_style(checked)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(CHEAT_QSS)
    window = ControlPanel()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
