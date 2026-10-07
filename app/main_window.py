import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QDockWidget, QFileDialog, QMainWindow, QMenu, QMessageBox,
    QTabWidget, QToolButton,
)

from app import settings_store
from app.editor_tab import EditorTabWidget
from app.emmet_cheatsheet import EMMET_ACTIONS, EmmetCheatSheet
from app.file_explorer_widget import FileExplorerWidget, first_root_or_default
from app.languages import detect_language, is_binary_file
from app.python_lab_widget import PythonLabWidget
from app.settings_dialog import SettingsDialog
from app.snake_game_widget import SnakeGameWidget
from app.terminal_widget import TerminalWidget
from app.themes import CODE_THEMES, THEMES
from app.version import APP_VERSION

SHELLS = {
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe", "-NoLogo"],
}


class MainWindow(QMainWindow):
    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self._tab_counter = 0
        self._maximized_before_fullscreen = False
        self._dock_hidden_by_fullscreen = False

        self.setWindowTitle(f"Custom Command Center v{APP_VERSION}")
        self.resize(1100, 700)
        self.setAcceptDrops(True)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.explorer = FileExplorerWidget()
        self.explorer.file_activated.connect(self.open_path_in_editor)
        self.explorer.path_renamed.connect(self._on_path_renamed)
        self.explorer_dock = QDockWidget("Explorer", self)
        self.explorer_dock.setObjectName("explorer_dock")
        self.explorer_dock.setWidget(self.explorer)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.explorer_dock)

        self._build_corner_button()
        self._build_menu()
        self.statusBar().showMessage("Ready")
        QApplication.instance().applicationStateChanged.connect(self._on_app_state_changed)

        self.new_terminal_tab()
        self.new_python_tab()

    # ---- tab creation ----
    def _next_title(self, base: str) -> str:
        self._tab_counter += 1
        return f"{base} {self._tab_counter}"

    def new_terminal_tab(self, shell: str = "cmd"):
        args = SHELLS.get(shell, SHELLS["cmd"])
        widget = TerminalWidget(args, shell)
        widget.set_font(self.settings["font_family"], self.settings["font_size"])
        idx = self.tabs.addTab(widget, self._next_title("Terminal" if shell == "cmd" else "PowerShell"))
        self.tabs.setCurrentIndex(idx)

    def _add_editing_tab(self, widget, default_title: str, file_path: str | None):
        """Shared setup for tabs that edit files (Python Lab and the general editor)."""
        widget.set_font(self.settings["font_family"], self.settings["font_size"])
        widget.set_code_theme(self.settings["code_theme"])
        widget.set_autocorrect(self.settings["autocorrect_enabled"])
        widget.set_emmet(self.settings["emmet_enabled"])
        widget.editor.emmet_message.connect(lambda m: self.statusBar().showMessage(m, 5000))
        widget.default_title = default_title
        if file_path and not widget.load_file(file_path):
            widget.shutdown()
            widget.deleteLater()
            return None
        widget.state_changed.connect(lambda w=widget: self._refresh_tab_title(w))
        idx = self.tabs.addTab(widget, widget.display_name())
        self.tabs.setCurrentIndex(idx)
        return widget

    def new_python_tab(self, file_path: str | None = None):
        return self._add_editing_tab(PythonLabWidget(), self._next_title("Python Lab"), file_path)

    def new_editor_tab(self, file_path: str | None = None):
        return self._add_editing_tab(EditorTabWidget(), self._next_title("Untitled"), file_path)

    def _refresh_tab_title(self, widget):
        idx = self.tabs.indexOf(widget)
        if idx < 0:
            return
        name = widget.display_name()
        self.tabs.setTabText(idx, ("*" if widget.is_modified() else "") + name)
        self.tabs.setTabToolTip(idx, widget.current_file or "")

    def open_path_in_editor(self, path: str):
        if is_binary_file(path):
            os.startfile(path)
            return
        norm = os.path.normcase(os.path.normpath(path))
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            current = getattr(widget, "current_file", None)
            if current and os.path.normcase(os.path.normpath(current)) == norm:
                self.tabs.setCurrentIndex(i)
                return
        if detect_language(path) == "python":
            self.new_python_tab(file_path=path)
        else:
            self.new_editor_tab(file_path=path)

    def open_file_dialog(self):
        start = first_root_or_default()
        path, _ = QFileDialog.getOpenFileName(self, "Open File", start, "All Files (*)")
        if path:
            self.open_path_in_editor(path)

    # ---- drag and drop: dropping a folder opens it in the Explorer, a file opens it in a tab ----
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        added_to_explorer = False
        for path in paths:
            if os.path.isdir(path):
                self.explorer.add_root(path)
                added_to_explorer = True
            elif os.path.isfile(path):
                if not self.explorer.is_within_open_root(path) and self.explorer.add_loose_file(path):
                    added_to_explorer = True
                self.open_path_in_editor(path)
        if added_to_explorer:
            self.explorer_dock.show()
            self.explorer_dock.raise_()
        event.acceptProposedAction()

    def save_current(self, save_as: bool = False):
        widget = self.tabs.currentWidget()
        action = getattr(widget, "save_as" if save_as else "save", None)
        if action is not None and action():
            self.statusBar().showMessage(f"Saved {widget.current_file}", 4000)

    def new_snake_tab(self):
        widget = SnakeGameWidget()
        widget.set_font(self.settings["font_family"], self.settings["font_size"])
        widget.set_theme(self.settings["theme"])
        idx = self.tabs.addTab(widget, self._next_title("Snake"))
        self.tabs.setCurrentIndex(idx)
        widget.setFocus()

    def close_tab(self, index: int):
        widget = self.tabs.widget(index)
        if widget is None:
            return
        confirm = getattr(widget, "confirm_close", None)
        if confirm is not None and not confirm():
            return
        widget.shutdown()
        self.tabs.removeTab(index)

    def _on_tab_changed(self, index: int):
        widget = self.tabs.widget(index)
        if isinstance(widget, SnakeGameWidget):
            widget.setFocus()
        self._sync_tab_with_disk(widget)

    def _on_app_state_changed(self, state):
        if state == Qt.ApplicationActive:
            self._sync_tab_with_disk(self.tabs.currentWidget())

    def _sync_tab_with_disk(self, widget):
        check = getattr(widget, "check_disk_changes", None)
        if check is None or getattr(self, "_syncing_disk", False):
            return
        self._syncing_disk = True
        try:
            if check():
                self.statusBar().showMessage(f"Reloaded {widget.current_file} (changed on disk)", 4000)
        finally:
            self._syncing_disk = False

    def _on_path_renamed(self, old_path: str, new_path: str):
        old_norm = os.path.normcase(os.path.normpath(old_path))
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            current = getattr(widget, "current_file", None)
            if not current:
                continue
            cur_norm = os.path.normcase(os.path.normpath(current))
            if cur_norm == old_norm:
                updated = new_path
            elif cur_norm.startswith(old_norm + os.sep):
                updated = os.path.join(new_path, os.path.relpath(current, old_path))
            else:
                continue
            widget.current_file = os.path.normpath(updated)
            if hasattr(widget, "_apply_language"):
                widget._apply_language()
            widget.record_disk_stamp()
            self._refresh_tab_title(widget)

    # ---- menu ----
    def _build_corner_button(self):
        button = QToolButton()
        button.setText("+")
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)
        menu.addAction("New Terminal (Ctrl+N)", lambda: self.new_terminal_tab())
        menu.addAction("New PowerShell Tab", lambda: self.new_terminal_tab("powershell"))
        menu.addAction("New Python Lab (Ctrl+Shift+N)", lambda: self.new_python_tab())
        menu.addAction("New Text/Code File (Ctrl+T)", lambda: self.new_editor_tab())
        menu.addAction("New Snake Game (Ctrl+G)", self.new_snake_tab)
        button.setMenu(menu)
        self.tabs.setCornerWidget(button, Qt.TopRightCorner)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")

        new_terminal_act = QAction("New Terminal Tab", self, shortcut=QKeySequence("Ctrl+N"))
        new_terminal_act.triggered.connect(lambda: self.new_terminal_tab())
        file_menu.addAction(new_terminal_act)

        new_ps_act = QAction("New PowerShell Tab", self)
        new_ps_act.triggered.connect(lambda: self.new_terminal_tab("powershell"))
        file_menu.addAction(new_ps_act)

        new_py_act = QAction("New Python Lab Tab", self, shortcut=QKeySequence("Ctrl+Shift+N"))
        new_py_act.triggered.connect(lambda: self.new_python_tab())
        file_menu.addAction(new_py_act)

        new_editor_act = QAction("New Text/Code File Tab", self, shortcut=QKeySequence("Ctrl+T"))
        new_editor_act.triggered.connect(lambda: self.new_editor_tab())
        file_menu.addAction(new_editor_act)

        new_snake_act = QAction("New Snake Game Tab", self, shortcut=QKeySequence("Ctrl+G"))
        new_snake_act.triggered.connect(self.new_snake_tab)
        file_menu.addAction(new_snake_act)

        file_menu.addSeparator()

        open_act = QAction("Open File...", self, shortcut=QKeySequence("Ctrl+O"))
        open_act.triggered.connect(lambda: self.open_file_dialog())
        file_menu.addAction(open_act)

        save_act = QAction("Save", self, shortcut=QKeySequence("Ctrl+S"))
        save_act.triggered.connect(lambda: self.save_current())
        file_menu.addAction(save_act)

        save_as_act = QAction("Save As...", self, shortcut=QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(lambda: self.save_current(save_as=True))
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        close_tab_act = QAction("Close Tab", self, shortcut=QKeySequence("Ctrl+W"))
        close_tab_act.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        file_menu.addAction(close_tab_act)

        file_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        view_menu = self.menuBar().addMenu("&View")
        explorer_act = self.explorer_dock.toggleViewAction()
        explorer_act.setText("Explorer")
        explorer_act.setShortcut(QKeySequence("Ctrl+B"))
        view_menu.addAction(explorer_act)
        self._fullscreen_action = QAction("Full Screen", self, checkable=True)
        self._fullscreen_action.setShortcut(QKeySequence("F11"))
        self._fullscreen_action.triggered.connect(lambda: self.toggle_fullscreen())
        view_menu.addAction(self._fullscreen_action)
        self._exit_fullscreen_action = QAction("Exit Full Screen", self)
        self._exit_fullscreen_action.setShortcut(QKeySequence("Esc"))
        self._exit_fullscreen_action.setEnabled(False)
        self._exit_fullscreen_action.triggered.connect(lambda: self.toggle_fullscreen())
        self.addAction(self._exit_fullscreen_action)
        view_menu.addSeparator()
        theme_menu = view_menu.addMenu("Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        self._theme_actions = {}
        for name in THEMES:
            act = QAction(name, self, checkable=True)
            act.setChecked(name == self.settings["theme"])
            act.triggered.connect(lambda checked, n=name: self.apply_theme(n))
            theme_group.addAction(act)
            theme_menu.addAction(act)
            self._theme_actions[name] = act

        code_menu = view_menu.addMenu("Code Colors")
        code_group = QActionGroup(self)
        code_group.setExclusive(True)
        self._code_theme_actions = {}
        for name in CODE_THEMES:
            act = QAction(name, self, checkable=True)
            act.setChecked(name == self.settings["code_theme"])
            act.triggered.connect(lambda checked, n=name: self.apply_code_theme(n))
            code_group.addAction(act)
            code_menu.addAction(act)
            self._code_theme_actions[name] = act

        emmet_menu = self.menuBar().addMenu("E&mmet")
        for label, shortcut, name, kwargs in EMMET_ACTIONS:
            act = QAction(label, self)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(lambda checked=False, n=name, k=kwargs: self.run_emmet(n, **k))
            emmet_menu.addAction(act)
        emmet_menu.addSeparator()
        self.emmet_toggle_action = QAction("Tab Expands Abbreviations", self, checkable=True)
        self.emmet_toggle_action.setChecked(self.settings["emmet_enabled"])
        self.emmet_toggle_action.toggled.connect(self.set_emmet_enabled)
        emmet_menu.addAction(self.emmet_toggle_action)
        cheat_act = QAction("Emmet Cheat Sheet...", self)
        cheat_act.setShortcut(QKeySequence("F1"))
        cheat_act.triggered.connect(lambda: EmmetCheatSheet(self).exec())
        emmet_menu.addAction(cheat_act)

        settings_menu = self.menuBar().addMenu("&Settings")
        prefs_act = QAction("Preferences...", self)
        prefs_act.triggered.connect(self.open_preferences)
        settings_menu.addAction(prefs_act)

        help_menu = self.menuBar().addMenu("&Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(self.show_about)
        help_menu.addAction(about_act)

    # ---- full screen ----
    def toggle_fullscreen(self):
        if self.isFullScreen():
            if self._dock_hidden_by_fullscreen:
                self.explorer_dock.show()
                self._dock_hidden_by_fullscreen = False
            self.showMaximized() if self._maximized_before_fullscreen else self.showNormal()
        else:
            self._maximized_before_fullscreen = self.isMaximized()
            if isinstance(self.tabs.currentWidget(), SnakeGameWidget) and self.explorer_dock.isVisible():
                self.explorer_dock.hide()
                self._dock_hidden_by_fullscreen = True
            self.showFullScreen()
        self._fullscreen_action.setChecked(self.isFullScreen())
        self._exit_fullscreen_action.setEnabled(self.isFullScreen())

    # ---- emmet ----
    def current_editor(self):
        return getattr(self.tabs.currentWidget(), "editor", None)

    def run_emmet(self, name: str, **kwargs):
        editor = self.current_editor()
        if editor is None:
            self.statusBar().showMessage("Open a code or text tab to use Emmet.", 4000)
            return
        editor.emmet_action(name, **kwargs)
        editor.setFocus()

    def set_emmet_enabled(self, enabled: bool):
        self.settings["emmet_enabled"] = enabled
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, "set_emmet"):
                widget.set_emmet(enabled)
        settings_store.save_settings(self.settings)

    # ---- settings ----
    def apply_theme(self, name: str):
        self.settings["theme"] = name
        QApplication.instance().setStyleSheet(THEMES[name])
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, "set_theme"):
                widget.set_theme(name)
        if name in self._theme_actions:
            self._theme_actions[name].setChecked(True)
        settings_store.save_settings(self.settings)

    def apply_code_theme(self, name: str):
        self.settings["code_theme"] = name
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, "set_code_theme"):
                widget.set_code_theme(name)
        if name in self._code_theme_actions:
            self._code_theme_actions[name].setChecked(True)
        settings_store.save_settings(self.settings)

    def open_preferences(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            new_settings = dlg.result_settings()
            theme_changed = new_settings["theme"] != self.settings.get("theme")
            code_theme_changed = new_settings["code_theme"] != self.settings.get("code_theme")
            self.settings.update(new_settings)
            settings_store.save_settings(self.settings)
            if theme_changed:
                self.apply_theme(new_settings["theme"])
            if code_theme_changed:
                self.apply_code_theme(new_settings["code_theme"])
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                widget.set_font(self.settings["font_family"], self.settings["font_size"])
                if hasattr(widget, "set_autocorrect"):
                    widget.set_autocorrect(self.settings["autocorrect_enabled"])
                if hasattr(widget, "set_emmet"):
                    widget.set_emmet(self.settings["emmet_enabled"])
            self.emmet_toggle_action.blockSignals(True)
            self.emmet_toggle_action.setChecked(self.settings["emmet_enabled"])
            self.emmet_toggle_action.blockSignals(False)
            self.explorer.set_font(self.settings["font_family"], self.settings["font_size"])

    def show_about(self):
        QMessageBox.information(
            self,
            "About Custom Command Center",
            f"Custom Command Center v{APP_VERSION}\n\n"
            "A custom terminal with tabs for real shell sessions (cmd/PowerShell), "
            "a Python editor + REPL for learning and testing code, a code/text editor "
            "for HTML, CSS, JavaScript, JSON, Markdown and more, a file explorer for "
            "managing your own projects, and a Snake game for a break.\n\n"
            "Shortcuts: Ctrl+N new terminal, Ctrl+Shift+N new Python lab, "
            "Ctrl+T new text/code file, Ctrl+O open, Ctrl+S save, Ctrl+Shift+S save as, "
            "Ctrl+G new Snake game, Ctrl+B toggle Explorer, F11 full screen, "
            "Ctrl+W close tab, F5 run script / preview HTML in browser.",
        )

    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            confirm = getattr(self.tabs.widget(i), "confirm_close", None)
            if confirm is not None:
                self.tabs.setCurrentIndex(i)
                if not confirm():
                    event.ignore()
                    return
        for i in range(self.tabs.count()):
            self.tabs.widget(i).shutdown()
        settings_store.save_settings(self.settings)
        super().closeEvent(event)
