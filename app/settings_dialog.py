from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFontComboBox, QFormLayout,
    QPlainTextEdit, QSpinBox,
)

from app.code_editor import CodeEditor
from app.highlighter import PythonHighlighter
from app.themes import CODE_THEMES, DEFAULT_CODE_THEME, THEMES

PREVIEW_CODE = """# Preview: pick colors you can read
import random

def roll(sides=6):
    return random.randint(1, sides)

for turn in range(3):
    print("Turn", turn + 1, "rolled", roll())
"""


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(520)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(settings.get("theme", "Dark Modern"))

        self.code_theme_combo = QComboBox()
        self.code_theme_combo.addItems(list(CODE_THEMES.keys()))
        self.code_theme_combo.setCurrentText(settings.get("code_theme", DEFAULT_CODE_THEME))

        self.font_combo = QFontComboBox()
        self.font_combo.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        self.font_combo.setCurrentFont(self.font_combo.font())
        self.font_combo.setEditText(settings.get("font_family", "Cascadia Mono"))

        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 28)
        self.size_spin.setValue(settings.get("font_size", 11))

        self.autocorrect_check = QCheckBox("Auto-close brackets, quotes && HTML tags; smart indent")
        self.autocorrect_check.setChecked(settings.get("autocorrect_enabled", True))

        self.emmet_check = QCheckBox("Emmet: Tab expands abbreviations (HTML, CSS, JSX...)")
        self.emmet_check.setChecked(settings.get("emmet_enabled", True))

        self.preview = CodeEditor()
        self.preview.setReadOnly(True)
        self.preview.setPlainText(PREVIEW_CODE)
        self.preview.setFixedHeight(190)
        self.preview.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.preview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_highlighter = PythonHighlighter(self.preview.document(), CODE_THEMES[DEFAULT_CODE_THEME])

        form = QFormLayout(self)
        form.addRow("App theme:", self.theme_combo)
        form.addRow("Code colors:", self.code_theme_combo)
        form.addRow("", self.preview)
        form.addRow("Font:", self.font_combo)
        form.addRow("Font size:", self.size_spin)
        form.addRow("Autocorrect:", self.autocorrect_check)
        form.addRow("Emmet:", self.emmet_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.code_theme_combo.currentTextChanged.connect(self._update_preview)
        self.font_combo.currentFontChanged.connect(self._update_preview_font)
        self.size_spin.valueChanged.connect(self._update_preview_font)
        self._update_preview()
        self._update_preview_font()

    def _update_preview(self, *_):
        theme = CODE_THEMES.get(self.code_theme_combo.currentText(), CODE_THEMES[DEFAULT_CODE_THEME])
        self.preview.set_code_theme(theme)
        self.preview_highlighter.set_palette(theme)

    def _update_preview_font(self, *_):
        self.preview.setFont(QFont(self.font_combo.currentFont().family(), self.size_spin.value()))

    def result_settings(self) -> dict:
        return {
            "theme": self.theme_combo.currentText(),
            "code_theme": self.code_theme_combo.currentText(),
            "font_family": self.font_combo.currentText(),
            "font_size": self.size_spin.value(),
            "autocorrect_enabled": self.autocorrect_check.isChecked(),
            "emmet_enabled": self.emmet_check.isChecked(),
        }
