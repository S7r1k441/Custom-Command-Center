"""A tab for writing and running Python: editor + live REPL console.

Code runs in-process using the same interpreter that powers this app
(via exec/code.InteractiveInterpreter), so it works even when packaged
as a single .exe with no separate Python installation on the machine.
"""
import codeop
import code as code_module
import os
import sys
import threading
import traceback

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from app import settings_store
from app.code_editor import CodeEditor
from app.file_explorer_widget import first_root_or_default
from app.file_io import DiskSyncMixin, NotTextFileError, prompt_save_changes, read_text_file, write_text_file
from app.highlighter import PythonHighlighter
from app.terminal_widget import HistoryLineEdit
from app.themes import CODE_THEMES, DEFAULT_CODE_THEME

# Only one snippet of user code runs at a time, process-wide, because
# stdout/stderr redirection below is a global swap.
_EXEC_LOCK = threading.Lock()


class _StreamRedirector(QObject):
    text_written = Signal(str)

    def write(self, s):
        if s:
            self.text_written.emit(s)

    def flush(self):
        pass


class _ExecWorker(QThread):
    def __init__(self, target, redirector, parent=None):
        super().__init__(parent)
        self.target = target
        self.redirector = redirector

    def run(self):
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = self.redirector
        try:
            self.target()
        finally:
            sys.stdout, sys.stderr = old_out, old_err


class PythonLabWidget(DiskSyncMixin, QWidget):
    state_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        settings = settings_store.load_settings()
        self.default_title = "Python Lab"
        self.crlf = True
        self.namespace = {"__name__": "__console__", "__doc__": None}
        self.interpreter = code_module.InteractiveInterpreter(self.namespace)
        self.repl_buffer: list[str] = []
        self.redirector = _StreamRedirector()
        self.redirector.text_written.connect(self._append_output)
        self.worker: _ExecWorker | None = None
        self.current_file: str | None = None

        font = QFont(settings["font_family"], settings["font_size"])

        # --- left: editor ---
        toolbar = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run (F5)")
        self.open_btn = QPushButton("Open...")
        self.save_btn = QPushButton("Save")
        self.save_as_btn = QPushButton("Save As...")
        self.restart_btn = QPushButton("Restart")
        for b in (self.run_btn, self.open_btn, self.save_btn, self.save_as_btn, self.restart_btn):
            toolbar.addWidget(b)
        toolbar.addStretch(1)

        self.editor = CodeEditor()
        self.editor.setFont(font)
        self.editor.set_autocorrect_enabled(settings.get("autocorrect_enabled", True))
        self.editor.set_language("python")
        self.editor.document().modificationChanged.connect(lambda _: self.state_changed.emit())
        self.editor.setPlaceholderText(
            "# Write Python here, then click Run (or press F5)\n"
            "print('Hello, world!')\n"
        )
        code_theme = CODE_THEMES.get(settings.get("code_theme"), CODE_THEMES[DEFAULT_CODE_THEME])
        self.editor.set_code_theme(code_theme)
        self.highlighter = PythonHighlighter(self.editor.document(), code_theme)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addLayout(toolbar)
        left_layout.addWidget(self.editor)

        # --- right: console ---
        self.output = QPlainTextEdit(readOnly=True)
        self.output.setFont(font)
        self.output.setMaximumBlockCount(10000)
        self.output.appendPlainText(">>> Python console ready. Try typing: 2 + 2")

        history = settings_store.load_history("python")
        self.prompt_label = QLabel(">>>")
        self.repl_input = HistoryLineEdit(history)
        self.repl_input.setFont(font)
        self.repl_input.setPlaceholderText("Type Python here and press Enter...")
        self.repl_input.history_submit.connect(self.submit_repl_line)

        input_row = QHBoxLayout()
        input_row.addWidget(self.prompt_label)
        input_row.addWidget(self.repl_input)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.addWidget(QLabel("Console"))
        right_layout.addWidget(self.output)
        right_layout.addLayout(input_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([500, 500])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self.run_btn.clicked.connect(self.run_script)
        self.open_btn.clicked.connect(self.open_file)
        self.save_btn.clicked.connect(self.save)
        self.save_as_btn.clicked.connect(self.save_as)
        self.restart_btn.clicked.connect(self.restart_console)

        QShortcut(QKeySequence("F5"), self, activated=self.run_script,
                  context=Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.run_script,
                  context=Qt.WidgetWithChildrenShortcut)

    def set_font(self, family: str, size: int):
        font = QFont(family, size)
        self.editor.setFont(font)
        self.output.setFont(font)
        self.repl_input.setFont(font)

    def set_code_theme(self, theme_name: str):
        theme = CODE_THEMES.get(theme_name, CODE_THEMES[DEFAULT_CODE_THEME])
        self.editor.set_code_theme(theme)
        self.highlighter.set_palette(theme)

    def set_autocorrect(self, enabled: bool):
        self.editor.set_autocorrect_enabled(enabled)

    def set_emmet(self, enabled: bool):
        self.editor.set_emmet_enabled(enabled)

    def _append_output(self, text: str):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _set_busy(self, busy: bool):
        self.run_btn.setEnabled(not busy)
        self.repl_input.setEnabled(not busy)
        self.restart_btn.setEnabled(not busy)

    def _start_worker(self, target):
        if not _EXEC_LOCK.acquire(blocking=False):
            self._append_output("\n[Another tab is currently running code - please wait for it to finish]\n")
            return
        self._set_busy(True)
        self.worker = _ExecWorker(target, self.redirector)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self):
        _EXEC_LOCK.release()
        self._set_busy(False)
        self.worker = None

    # ---- REPL ----
    def submit_repl_line(self, line: str):
        prompt = "... " if self.repl_buffer else ">>> "
        self._append_output(f"\n{prompt}{line}")
        self.repl_buffer.append(line)
        source = "\n".join(self.repl_buffer)

        try:
            needs_more = codeop.compile_command(source, "<console>") is None
        except (OverflowError, SyntaxError, ValueError):
            needs_more = False

        if needs_more:
            self.prompt_label.setText("...")
            return

        self.repl_buffer = []
        self.prompt_label.setText(">>>")
        self._append_output("\n")
        self._start_worker(lambda: self.interpreter.runsource(source, "<console>"))

    # ---- script run ----
    def run_script(self):
        source = self.editor.toPlainText()
        if not source.strip():
            return
        self._append_output("\n----- Running script -----\n")

        def target():
            try:
                code_obj = compile(source, self.current_file or "<script>", "exec")
                exec(code_obj, self.namespace)
                self.redirector.write("----- Finished -----\n")
            except SystemExit:
                self.redirector.write("----- Finished -----\n")
            except BaseException:
                traceback.print_exc()
                self.redirector.write("----- Finished with an error -----\n")

        self._start_worker(target)

    def restart_console(self):
        self.namespace = {"__name__": "__console__", "__doc__": None}
        self.interpreter = code_module.InteractiveInterpreter(self.namespace)
        self.repl_buffer = []
        self.prompt_label.setText(">>>")
        self.output.clear()
        self.output.appendPlainText(">>> Console restarted. Variables have been cleared.")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Python File", "", "Python Files (*.py);;All Files (*)")
        if not path or not self.confirm_close():
            return
        self.load_file(path)

    def load_file(self, path: str) -> bool:
        try:
            text, crlf = read_text_file(path)
        except NotTextFileError as e:
            QMessageBox.warning(self, "Open File", f"Could not open {os.path.basename(path)}:\n{e}")
            return False
        except OSError as e:
            QMessageBox.warning(self, "Open File", f"Could not open file:\n{e}")
            return False
        self.editor.setPlainText(text)
        self.crlf = crlf
        self.current_file = path
        self.editor.document().setModified(False)
        self.record_disk_stamp()
        self.state_changed.emit()
        return True

    def _write(self, path: str) -> bool:
        if not self.confirm_overwrite_newer(path):
            return False
        try:
            write_text_file(path, self.editor.toPlainText(), self.crlf)
        except OSError as e:
            QMessageBox.warning(self, "Save File", f"Could not save file:\n{e}")
            return False
        self.current_file = path
        self.editor.document().setModified(False)
        self.record_disk_stamp()
        self.state_changed.emit()
        return True

    def save(self) -> bool:
        if self.current_file:
            return self._write(self.current_file)
        return self.save_as()

    def save_as(self) -> bool:
        start_dir = os.path.dirname(self.current_file) if self.current_file else first_root_or_default()
        suggested = self.current_file or os.path.join(start_dir, "script.py")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Python File", suggested, "Python Files (*.py);;All Files (*)")
        if not path:
            return False
        return self._write(path)

    def is_modified(self) -> bool:
        return self.editor.document().isModified()

    def display_name(self) -> str:
        return os.path.basename(self.current_file) if self.current_file else self.default_title

    def confirm_close(self) -> bool:
        if not self.is_modified():
            return True
        choice = prompt_save_changes(self, self.display_name())
        if choice == "save":
            return self.save()
        return choice == "discard"

    def shutdown(self):
        settings_store.save_history("python", self.repl_input.history)
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(2000)
