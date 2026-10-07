"""QSS stylesheets and syntax-highlight palettes for the app's themes."""

DARK_MODERN = """
QMainWindow, QWidget { background-color: #1e1f26; color: #e6e6e6; }
QMenuBar { background-color: #23242e; color: #e6e6e6; }
QMenuBar::item:selected { background-color: #3a7bd5; color: #ffffff; }
QMenu { background-color: #23242e; color: #e6e6e6; border: 1px solid #3a3b46; }
QMenu::item:selected { background-color: #3a7bd5; }
QTabWidget::pane { border: 1px solid #3a3b46; background-color: #1e1f26; }
QTabBar::tab { background-color: #23242e; color: #c7c7c7; padding: 6px 14px; border: 1px solid #3a3b46; border-bottom: none; }
QTabBar::tab:selected { background-color: #2d2f3a; color: #ffffff; }
QTabBar::tab:hover { background-color: #2a2c37; }
QPlainTextEdit, QTextEdit { background-color: #14151b; color: #e6e6e6; border: 1px solid #3a3b46; selection-background-color: #3a7bd5; }
QLineEdit { background-color: #14151b; color: #e6e6e6; border: 1px solid #3a3b46; padding: 4px; border-radius: 3px; }
QPushButton { background-color: #2d2f3a; color: #e6e6e6; border: 1px solid #3a3b46; padding: 5px 12px; border-radius: 4px; }
QPushButton:hover { background-color: #3a7bd5; color: #ffffff; }
QPushButton:disabled { color: #6b6c75; }
QToolButton { background-color: #2d2f3a; color: #e6e6e6; border: 1px solid #3a3b46; border-radius: 4px; padding: 4px; }
QToolButton:hover { background-color: #3a7bd5; }
QLabel { color: #c7c7c7; }
QStatusBar { background-color: #23242e; color: #9fa0a8; }
QSplitter::handle { background-color: #3a3b46; }
QComboBox, QSpinBox, QFontComboBox { background-color: #14151b; color: #e6e6e6; border: 1px solid #3a3b46; padding: 3px; }
QScrollBar:vertical { background: #1e1f26; width: 12px; }
QScrollBar::handle:vertical { background: #3a3b46; min-height: 20px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

RETRO_GREEN = """
QMainWindow, QWidget { background-color: #000000; color: #33ff66; }
QMenuBar { background-color: #001a00; color: #33ff66; }
QMenuBar::item:selected { background-color: #144d14; }
QMenu { background-color: #001a00; color: #33ff66; border: 1px solid #1f5c1f; }
QMenu::item:selected { background-color: #144d14; }
QTabWidget::pane { border: 1px solid #1f5c1f; background-color: #000000; }
QTabBar::tab { background-color: #001a00; color: #2c9c4c; padding: 6px 14px; border: 1px solid #1f5c1f; border-bottom: none; }
QTabBar::tab:selected { background-color: #072607; color: #33ff66; }
QPlainTextEdit, QTextEdit { background-color: #000000; color: #33ff66; border: 1px solid #1f5c1f; selection-background-color: #1f5c1f; font-family: Consolas, 'Cascadia Mono', monospace; }
QLineEdit { background-color: #000000; color: #33ff66; border: 1px solid #1f5c1f; padding: 4px; }
QPushButton { background-color: #001a00; color: #33ff66; border: 1px solid #1f5c1f; padding: 5px 12px; }
QPushButton:hover { background-color: #144d14; }
QToolButton { background-color: #001a00; color: #33ff66; border: 1px solid #1f5c1f; }
QToolButton:hover { background-color: #144d14; }
QLabel { color: #2c9c4c; }
QStatusBar { background-color: #001a00; color: #2c9c4c; }
QSplitter::handle { background-color: #1f5c1f; }
QComboBox, QSpinBox, QFontComboBox { background-color: #000000; color: #33ff66; border: 1px solid #1f5c1f; }
QScrollBar:vertical { background: #000000; width: 12px; }
QScrollBar::handle:vertical { background: #1f5c1f; min-height: 20px; }
"""

LIGHT_CLEAN = """
QMainWindow, QWidget { background-color: #fafafa; color: #202020; }
QMenuBar { background-color: #f0f0f0; color: #202020; }
QMenuBar::item:selected { background-color: #d6e4ff; }
QMenu { background-color: #ffffff; color: #202020; border: 1px solid #d0d0d0; }
QMenu::item:selected { background-color: #d6e4ff; }
QTabWidget::pane { border: 1px solid #d0d0d0; background-color: #fafafa; }
QTabBar::tab { background-color: #eeeeee; color: #404040; padding: 6px 14px; border: 1px solid #d0d0d0; border-bottom: none; }
QTabBar::tab:selected { background-color: #ffffff; color: #000000; }
QPlainTextEdit, QTextEdit { background-color: #ffffff; color: #1a1a1a; border: 1px solid #d0d0d0; selection-background-color: #b8d4ff; }
QLineEdit { background-color: #ffffff; color: #1a1a1a; border: 1px solid #c0c0c0; padding: 4px; border-radius: 3px; }
QPushButton { background-color: #eeeeee; color: #1a1a1a; border: 1px solid #c0c0c0; padding: 5px 12px; border-radius: 4px; }
QPushButton:hover { background-color: #d6e4ff; }
QToolButton { background-color: #eeeeee; color: #1a1a1a; border: 1px solid #c0c0c0; border-radius: 4px; }
QToolButton:hover { background-color: #d6e4ff; }
QLabel { color: #404040; }
QStatusBar { background-color: #f0f0f0; color: #505050; }
QSplitter::handle { background-color: #d0d0d0; }
QComboBox, QSpinBox, QFontComboBox { background-color: #ffffff; color: #1a1a1a; border: 1px solid #c0c0c0; }
QScrollBar:vertical { background: #fafafa; width: 12px; }
QScrollBar::handle:vertical { background: #cccccc; min-height: 20px; border-radius: 5px; }
"""

THEMES = {
    "Dark Modern": DARK_MODERN,
    "Retro Green": RETRO_GREEN,
    "Light Clean": LIGHT_CLEAN,
}

# Colors for the code editor, chosen separately from the app theme.
# Editor keys: background, foreground, selection, line_highlight, gutter_bg, gutter_fg.
# Syntax keys: keyword, tag (optional, defaults to keyword), builtin, string, comment,
# number, def_name, decorator, self.
CODE_THEMES = {
    "Dark+": {
        "background": "#1e1e1e", "foreground": "#d4d4d4", "selection": "#264f78",
        "line_highlight": "#2a2d2e", "gutter_bg": "#1e1e1e", "gutter_fg": "#858585",
        "keyword": "#c586c0", "tag": "#569cd6", "builtin": "#4ec9b0", "string": "#ce9178",
        "comment": "#6a9955", "number": "#b5cea8", "def_name": "#dcdcaa",
        "decorator": "#dcdcaa", "self": "#9cdcfe",
    },
    "Monokai": {
        "background": "#272822", "foreground": "#f8f8f2", "selection": "#49483e",
        "line_highlight": "#3e3d32", "gutter_bg": "#272822", "gutter_fg": "#90908a",
        "keyword": "#ff6b9d", "builtin": "#66d9ef", "string": "#e6db74",
        "comment": "#8f8f7a", "number": "#ae81ff", "def_name": "#a6e22e",
        "decorator": "#a6e22e", "self": "#fd971f",
    },
    "Dracula": {
        "background": "#282a36", "foreground": "#f8f8f2", "selection": "#44475a",
        "line_highlight": "#313442", "gutter_bg": "#282a36", "gutter_fg": "#8a9bd0",
        "keyword": "#ff79c6", "builtin": "#8be9fd", "string": "#f1fa8c",
        "comment": "#8897cf", "number": "#bd93f9", "def_name": "#50fa7b",
        "decorator": "#50fa7b", "self": "#ffb86c",
    },
    "One Dark": {
        "background": "#282c34", "foreground": "#abb2bf", "selection": "#3b4252",
        "line_highlight": "#2c313a", "gutter_bg": "#282c34", "gutter_fg": "#8790a6",
        "keyword": "#c678dd", "tag": "#ea7a84", "builtin": "#56b6c2", "string": "#98c379",
        "comment": "#8b94a5", "number": "#d19a66", "def_name": "#61afef",
        "decorator": "#e5c07b", "self": "#ea7a84",
    },
    "Solarized Dark": {
        "background": "#002b36", "foreground": "#9fb0b0", "selection": "#0a3d4a",
        "line_highlight": "#073642", "gutter_bg": "#002b36", "gutter_fg": "#7a9198",
        "keyword": "#859900", "tag": "#3f9de6", "builtin": "#3f9de6", "string": "#2aa198",
        "comment": "#7e969c", "number": "#ea66a8", "def_name": "#b58900",
        "decorator": "#e06a3c", "self": "#8a8fdc",
    },
    "Solarized Light": {
        "background": "#fdf6e3", "foreground": "#48606a", "selection": "#e6dfc4",
        "line_highlight": "#f5eed8", "gutter_bg": "#eee8d5", "gutter_fg": "#5c6f74",
        "keyword": "#5f7000", "tag": "#1f6fb0", "builtin": "#1f6fb0", "string": "#16766e",
        "comment": "#5c6f74", "number": "#b02a6c", "def_name": "#8a6600",
        "decorator": "#b03e0c", "self": "#5a5fb0",
    },
    "GitHub Light": {
        "background": "#ffffff", "foreground": "#24292f", "selection": "#b6d7ff",
        "line_highlight": "#f3f6fa", "gutter_bg": "#f6f8fa", "gutter_fg": "#636b74",
        "keyword": "#cf222e", "tag": "#116329", "builtin": "#0550ae", "string": "#0a3069",
        "comment": "#6e7781", "number": "#0550ae", "def_name": "#8250df",
        "decorator": "#953800", "self": "#953800",
    },
    "High Contrast": {
        "background": "#000000", "foreground": "#ffffff", "selection": "#264f78",
        "line_highlight": "#1c1c1c", "gutter_bg": "#000000", "gutter_fg": "#cfcfcf",
        "keyword": "#ffb454", "tag": "#6cb6ff", "builtin": "#00ffff", "string": "#7fff7f",
        "comment": "#b8b8b8", "number": "#ff9d9d", "def_name": "#ffff66",
        "decorator": "#ff8cff", "self": "#66ccff",
    },
    "Retro Green": {
        "background": "#000000", "foreground": "#33ff66", "selection": "#1f5c1f",
        "line_highlight": "#071f0e", "gutter_bg": "#000000", "gutter_fg": "#2c9c4c",
        "keyword": "#7dffb3", "builtin": "#66ffcc", "string": "#a8ffb0",
        "comment": "#1f8f3a", "number": "#c9ffcf", "def_name": "#ffffff",
        "decorator": "#99ff99", "self": "#33cc88",
    },
}

DEFAULT_CODE_THEME = "Dark+"

# Snake game colors per theme, keyed the same as THEMES.
GAME_PALETTES = {
    "Dark Modern": {
        "background": "#14151b",
        "grid": "#1e1f26",
        "snake_head": "#3a7bd5",
        "snake_body": "#5b9bf0",
        "food": "#e05561",
        "text": "#e6e6e6",
    },
    "Retro Green": {
        "background": "#000000",
        "grid": "#071f0e",
        "snake_head": "#33ff66",
        "snake_body": "#1f8f3a",
        "food": "#ffee33",
        "text": "#33ff66",
    },
    "Light Clean": {
        "background": "#ffffff",
        "grid": "#eeeeee",
        "snake_head": "#3a7bd5",
        "snake_body": "#7fb0ec",
        "food": "#e05561",
        "text": "#202020",
    },
}

DEFAULT_THEME = "Dark Modern"
