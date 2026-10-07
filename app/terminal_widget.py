"""A tab that runs a real Windows shell (cmd.exe or PowerShell) via QProcess."""
import re

from PySide6.QtCore import Qt, QProcess, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from app import settings_store

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07")


class HistoryLineEdit(QLineEdit):
    """A QLineEdit with Up/Down arrow command history."""

    history_submit = Signal(str)

    def __init__(self, history: list, parent=None):
        super().__init__(parent)
        self.history = list(history)
        self.history_index = len(self.history)
        self.returnPressed.connect(self._on_return)

    def _on_return(self):
        text = self.text()
        if text.strip():
            self.history.append(text)
        self.history_index = len(self.history)
        self.history_submit.emit(text)
        self.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            if self.history and self.history_index > 0:
                self.history_index -= 1
                self.setText(self.history[self.history_index])
            return
        if event.key() == Qt.Key_Down:
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.setText(self.history[self.history_index])
            else:
                self.history_index = len(self.history)
                self.clear()
            return
        super().keyPressEvent(event)


class TerminalWidget(QWidget):
    def __init__(self, shell_args: list[str], label: str, parent=None):
        super().__init__(parent)
        self.shell_args = shell_args
        self.label = label
        self.history_kind = "shell"

        settings = settings_store.load_settings()
        history = settings_store.load_history(self.history_kind)

        self.output = QPlainTextEdit(readOnly=True)
        self.output.setFont(QFont(settings["font_family"], settings["font_size"]))
        self.output.setMaximumBlockCount(10000)

        self.input = HistoryLineEdit(history)
        self.input.setFont(QFont(settings["font_family"], settings["font_size"]))
        self.input.setPlaceholderText(f"Type a {label} command and press Enter...")
        self.input.history_submit.connect(self.submit_command)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.output)
        layout.addWidget(self.input)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.finished.connect(self._on_finished)
        self.process.start(shell_args[0], shell_args[1:])

    def set_font(self, family: str, size: int):
        font = QFont(family, size)
        self.output.setFont(font)
        self.input.setFont(font)

    def _read_output(self):
        data = bytes(self.process.readAllStandardOutput())
        text = data.decode("utf-8", errors="replace")
        text = ANSI_ESCAPE.sub("", text)
        self._append(text)

    def _append(self, text: str):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def submit_command(self, text: str):
        if self.process.state() != self.process.ProcessState.Running:
            self._append("\n[session ended - close this tab]\n")
            return
        self.process.write((text + "\r\n").encode("utf-8"))

    def _on_finished(self, *_):
        self._append("\n[process exited]\n")
        self.input.setEnabled(False)

    def shutdown(self):
        settings_store.save_history(self.history_kind, self.input.history)
        if self.process.state() != self.process.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
