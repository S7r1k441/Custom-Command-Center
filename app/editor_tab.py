"""A general-purpose editor tab: HTML, CSS, JS, JSON, Markdown, plain text and more."""
import os

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from app import settings_store
from app.code_editor import CodeEditor
from app.file_explorer_widget import first_root_or_default
from app.file_io import DiskSyncMixin, NotTextFileError, prompt_save_changes, read_text_file, write_text_file
from app.highlighter import create_highlighter
from app.languages import LANGUAGE_LABELS, PREVIEW_LANGUAGES, detect_language
from app.themes import CODE_THEMES, DEFAULT_CODE_THEME


class EditorTabWidget(DiskSyncMixin, QWidget):
    state_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        settings = settings_store.load_settings()
        self.current_file: str | None = None
        self.default_title = "Untitled"
        self.crlf = True
        self.language = "text"
        self.code_theme_name = settings.get("code_theme", DEFAULT_CODE_THEME)
        self.highlighter = None

        self.save_btn = QPushButton("Save")
        self.save_as_btn = QPushButton("Save As...")
        self.preview_btn = QPushButton("Preview in Browser (F5)")
        self.language_label = QLabel()

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.save_btn)
        toolbar.addWidget(self.save_as_btn)
        toolbar.addWidget(self.preview_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.language_label)

        self.editor = CodeEditor()
        self.editor.setFont(QFont(settings["font_family"], settings["font_size"]))
        self.editor.set_autocorrect_enabled(settings.get("autocorrect_enabled", True))
        self.editor.set_emmet_enabled(settings.get("emmet_enabled", True))
        self.editor.set_code_theme(self._code_theme())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(toolbar)
        layout.addWidget(self.editor)

        self.save_btn.clicked.connect(self.save)
        self.save_as_btn.clicked.connect(self.save_as)
        self.preview_btn.clicked.connect(self.preview_in_browser)
        self.editor.document().modificationChanged.connect(lambda _: self.state_changed.emit())
        QShortcut(QKeySequence("F5"), self, activated=self.preview_in_browser,
                  context=Qt.WidgetWithChildrenShortcut)

        self._apply_language()

    # ---- language / appearance ----
    def _apply_language(self):
        self.language = detect_language(self.current_file)
        self.editor.set_language(self.language)
        if self.highlighter is not None:
            self.highlighter.setDocument(None)
            self.highlighter.deleteLater()
            self.highlighter = None
        self.highlighter = create_highlighter(self.editor.document(), self.language, self._code_theme())
        self.language_label.setText(LANGUAGE_LABELS.get(self.language, "Plain text"))
        self.preview_btn.setVisible(self.language in PREVIEW_LANGUAGES)
        self.editor.base_dir = os.path.dirname(self.current_file) if self.current_file else None

    def set_font(self, family: str, size: int):
        self.editor.setFont(QFont(family, size))

    def _code_theme(self) -> dict:
        return CODE_THEMES.get(self.code_theme_name, CODE_THEMES[DEFAULT_CODE_THEME])

    def set_code_theme(self, theme_name: str):
        self.code_theme_name = theme_name
        self.editor.set_code_theme(self._code_theme())
        if self.highlighter is not None:
            self.highlighter.set_palette(self._code_theme())

    def set_autocorrect(self, enabled: bool):
        self.editor.set_autocorrect_enabled(enabled)

    def set_emmet(self, enabled: bool):
        self.editor.set_emmet_enabled(enabled)

    # ---- file operations ----
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
        self._apply_language()
        self.editor.document().setModified(False)
        self.record_disk_stamp()
        self.state_changed.emit()
        return True

    def _start_dir(self) -> str:
        if self.current_file:
            return os.path.dirname(self.current_file)
        return first_root_or_default()

    def _write(self, path: str) -> bool:
        if not self.confirm_overwrite_newer(path):
            return False
        try:
            write_text_file(path, self.editor.toPlainText(), self.crlf)
        except OSError as e:
            QMessageBox.warning(self, "Save File", f"Could not save file:\n{e}")
            return False
        self.current_file = path
        self._apply_language()
        self.editor.document().setModified(False)
        self.record_disk_stamp()
        self.state_changed.emit()
        return True

    def save(self) -> bool:
        if self.current_file:
            return self._write(self.current_file)
        return self.save_as()

    def save_as(self) -> bool:
        suggested = self.current_file or os.path.join(self._start_dir(), "untitled.txt")
        path, _ = QFileDialog.getSaveFileName(self, "Save File As", suggested, "All Files (*)")
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

    # ---- preview ----
    def preview_in_browser(self):
        if self.language not in PREVIEW_LANGUAGES:
            return
        if (not self.current_file or self.is_modified()) and not self.save():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_file))

    def shutdown(self):
        pass
