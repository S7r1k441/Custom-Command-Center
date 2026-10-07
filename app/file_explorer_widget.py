"""A Visual-Studio-style file/project tree: browse, create, rename, delete files.

Supports opening several folders at once (each gets its own labeled section, like
VS Code's multi-root workspaces) and accepts folders/files dropped from Windows Explorer.
"""
import os
import subprocess

from PySide6.QtCore import QDir, QModelIndex, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFileSystemModel, QHBoxLayout, QInputDialog,
    QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QSplitter,
    QToolButton, QTreeView, QVBoxLayout, QWidget,
)

try:
    from send2trash import send2trash
except ImportError:  # pragma: no cover - dependency always installed in this app
    send2trash = None

from app import settings_store

DEFAULT_PROJECTS_DIR_NAME = "CustomCommandCenter Projects"


def _default_root() -> str:
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    root = os.path.join(docs, DEFAULT_PROJECTS_DIR_NAME)
    os.makedirs(root, exist_ok=True)
    return root


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def _shorten(path: str, max_len: int = 42) -> str:
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3):]


def _local_paths(mime_data):
    """Local filesystem paths from dropped/pasted URLs, if any."""
    if not mime_data.hasUrls():
        return []
    return [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]


def first_root_or_default() -> str:
    """The first open folder, for dialogs that need a sensible starting directory."""
    roots = settings_store.load_settings().get("explorer_roots") or []
    return roots[0] if roots else _default_root()


class _RootSection(QWidget):
    """One opened folder: a header bar plus its own tree, sharing the parent's model."""

    def __init__(self, path: str, model: QFileSystemModel, owner: "FileExplorerWidget"):
        super().__init__(owner)
        self.path = path
        self.owner = owner

        name_label = QLabel(os.path.basename(path.rstrip("\\/")) or path)
        name_label.setToolTip(path)
        bold = name_label.font()
        bold.setBold(True)
        name_label.setFont(bold)

        close_btn = QToolButton()
        close_btn.setText("✕")
        close_btn.setToolTip("Remove folder from Explorer")
        close_btn.setAutoRaise(True)
        close_btn.clicked.connect(lambda: owner.remove_root(self))

        header = QHBoxLayout()
        header.setContentsMargins(2, 2, 2, 2)
        header.addWidget(name_label, 1)
        header.addWidget(close_btn)

        self.tree = QTreeView()
        self.tree.setModel(model)
        # setRootPath (not just index()) is what makes QFileSystemModel actually
        # watch and populate this folder - index() alone returns a valid but
        # permanently-empty node.
        self.tree.setRootIndex(model.setRootPath(path))
        for col in (1, 2, 3):
            self.tree.hideColumn(col)
        self.tree.setEditTriggers(QAbstractItemView.EditKeyPressed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(lambda pos: owner._show_context_menu(self, pos))
        self.tree.doubleClicked.connect(owner._on_double_clicked)
        self.tree.selectionModel().selectionChanged.connect(lambda *_: setattr(owner, "_active", self))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(header)
        layout.addWidget(self.tree)

    def current_index(self) -> QModelIndex:
        indexes = self.tree.selectionModel().selectedIndexes()
        return indexes[0] if indexes else QModelIndex()

    def target_dir(self, index: QModelIndex = None) -> str:
        index = self.current_index() if index is None else index
        if index is None or not index.isValid():
            return self.path
        file_path = self.tree.model().filePath(index)
        return file_path if os.path.isdir(file_path) else os.path.dirname(file_path)


class _LooseFilesSection(QWidget):
    """Standalone scripts pinned to the Explorer without opening their whole folder."""

    def __init__(self, owner: "FileExplorerWidget"):
        super().__init__(owner)
        self.owner = owner

        title = QLabel("Loose Files")
        bold = title.font()
        bold.setBold(True)
        title.setFont(bold)
        header = QHBoxLayout()
        header.setContentsMargins(2, 2, 2, 2)
        header.addWidget(title, 1)

        self.list = QListWidget()
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._show_context_menu)
        self.list.itemActivated.connect(self._open_item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(header)
        layout.addWidget(self.list)

    def refresh(self):
        self.list.clear()
        for path in self.owner.loose_files:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self.list.addItem(item)

    def _open_item(self, item: QListWidgetItem):
        self.owner.file_activated.emit(item.data(Qt.UserRole))

    def _show_context_menu(self, pos):
        item = self.list.itemAt(pos)
        if item is None:
            return
        path = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("Open", lambda: self.owner.file_activated.emit(path))
        menu.addSeparator()
        menu.addAction("Rename", lambda: self.owner.rename_loose_file(path))
        menu.addAction("Delete", lambda: self.owner.delete_loose_file(path))
        menu.addSeparator()
        menu.addAction("Reveal in File Explorer",
                        lambda: subprocess.Popen(["explorer", "/select,", os.path.normpath(path)]))
        menu.addAction("Remove from Explorer", lambda: self.owner.remove_loose_file(path))
        menu.exec(self.list.viewport().mapToGlobal(pos))


class FileExplorerWidget(QWidget):
    file_activated = Signal(str)
    path_renamed = Signal(str, str)  # old full path, new full path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.sections: list[_RootSection] = []
        self._active: _RootSection | None = None
        self.loose_files: list[str] = self._initial_loose_files()

        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        self.model.setReadOnly(False)  # default is read-only, which silently disables Rename
        self.model.fileRenamed.connect(
            lambda folder, old, new: self.path_renamed.emit(os.path.join(folder, old), os.path.join(folder, new)))

        add_file_btn = QPushButton("Add File...")
        add_folder_btn = QPushButton("Add Folder...")
        new_file_btn = QPushButton("New File")
        new_folder_btn = QPushButton("New Folder")
        add_file_btn.clicked.connect(self.choose_loose_file)
        add_folder_btn.clicked.connect(self.choose_root)
        new_file_btn.clicked.connect(self.new_file)
        new_folder_btn.clicked.connect(self.new_folder)
        self.new_file_btn = new_file_btn
        self.new_folder_btn = new_folder_btn

        toolbar = QHBoxLayout()
        toolbar.addWidget(new_file_btn)
        toolbar.addWidget(new_folder_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(add_file_btn)
        toolbar.addWidget(add_folder_btn)

        self.empty_label = QLabel(
            "No folders open.\nClick \"Add Folder...\" or drag a folder here.\n"
            "For a standalone script, use \"Add File...\" or drag it here.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)

        self.splitter = QSplitter(Qt.Vertical)
        self.loose_section = _LooseFilesSection(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(toolbar)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.splitter, 1)

        roots = self._initial_roots()
        for path in roots:
            self._add_section(path)
        self._save_roots()
        self.splitter.addWidget(self.loose_section)
        self.loose_section.refresh()
        self._save_loose_files()
        self._update_empty_state()

    @staticmethod
    def _initial_roots() -> list[str]:
        settings = settings_store.load_settings()
        roots = settings.get("explorer_roots")
        if not roots:
            legacy = settings.get("explorer_root")
            roots = [legacy] if legacy else []
        seen, cleaned = set(), []
        for path in roots:
            if path and os.path.isdir(path) and _norm(path) not in seen:
                seen.add(_norm(path))
                cleaned.append(path)
        return cleaned or [_default_root()]

    @staticmethod
    def _initial_loose_files() -> list[str]:
        settings = settings_store.load_settings()
        paths = settings.get("explorer_loose_files") or []
        seen, cleaned = set(), []
        for path in paths:
            if path and os.path.isfile(path) and _norm(path) not in seen:
                seen.add(_norm(path))
                cleaned.append(path)
        return cleaned

    def _update_empty_state(self):
        has_content = bool(self.sections) or bool(self.loose_files)
        self.empty_label.setVisible(not has_content)
        self.splitter.setVisible(has_content)
        self.new_file_btn.setEnabled(bool(self.sections))
        self.new_folder_btn.setEnabled(bool(self.sections))
        self.loose_section.setVisible(bool(self.loose_files))

    def _save_roots(self):
        settings = settings_store.load_settings()
        settings["explorer_roots"] = [s.path for s in self.sections]
        settings.pop("explorer_root", None)
        settings_store.save_settings(settings)

    def _save_loose_files(self):
        settings = settings_store.load_settings()
        settings["explorer_loose_files"] = list(self.loose_files)
        settings_store.save_settings(settings)

    # ---- managing open folders ----
    def add_root(self, path: str) -> bool:
        path = os.path.normpath(path)
        if not os.path.isdir(path):
            return False
        if any(_norm(s.path) == _norm(path) for s in self.sections):
            self._active = next(s for s in self.sections if _norm(s.path) == _norm(path))
            return True
        self._add_section(path)
        self._save_roots()
        self._update_empty_state()
        return True

    def _add_section(self, path: str):
        section = _RootSection(path, self.model, self)
        self.sections.append(section)
        # Keep root sections above the Loose Files section, which is always last.
        self.splitter.insertWidget(len(self.sections) - 1, section)
        self._active = section

    def remove_root(self, section: "_RootSection"):
        self.sections.remove(section)
        section.setParent(None)
        section.deleteLater()
        if self._active is section:
            self._active = self.sections[0] if self.sections else None
        self._save_roots()
        self._update_empty_state()

    def choose_root(self):
        path = QFileDialog.getExistingDirectory(self, "Add Folder to Explorer", first_root_or_default())
        if path:
            self.add_root(path)

    def is_within_open_root(self, path: str) -> bool:
        norm_path = _norm(path)
        return any(norm_path == _norm(s.path) or norm_path.startswith(_norm(s.path) + os.sep)
                   for s in self.sections)

    # ---- managing loose (standalone) files ----
    def add_loose_file(self, path: str) -> bool:
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            return False
        if any(_norm(p) == _norm(path) for p in self.loose_files):
            return True
        self.loose_files.append(path)
        self.loose_section.refresh()
        self._save_loose_files()
        self._update_empty_state()
        return True

    def remove_loose_file(self, path: str):
        self.loose_files = [p for p in self.loose_files if _norm(p) != _norm(path)]
        self.loose_section.refresh()
        self._save_loose_files()
        self._update_empty_state()

    def choose_loose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Add File to Explorer", first_root_or_default(), "All Files (*)")
        if path:
            self.add_loose_file(path)

    def rename_loose_file(self, path: str):
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=os.path.basename(path))
        if not ok or not name.strip():
            return
        new_path = os.path.join(os.path.dirname(path), name.strip())
        if os.path.exists(new_path):
            QMessageBox.warning(self, "Rename", f"'{name}' already exists.")
            return
        try:
            os.rename(path, new_path)
        except OSError as e:
            QMessageBox.warning(self, "Rename", f"Could not rename:\n{e}")
            return
        self.loose_files = [new_path if _norm(p) == _norm(path) else p for p in self.loose_files]
        self.loose_section.refresh()
        self._save_loose_files()
        self.path_renamed.emit(path, new_path)

    def delete_loose_file(self, path: str):
        name = os.path.basename(path)
        reply = QMessageBox.question(
            self, "Delete", f"Send '{name}' to the Recycle Bin?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            if send2trash is not None:
                send2trash(path)
            else:
                os.remove(path)
        except OSError as e:
            QMessageBox.warning(self, "Delete", f"Could not delete '{name}':\n{e}")
            return
        self.remove_loose_file(path)

    def set_font(self, family: str, size: int):
        font = QFont(family, size)
        for section in self.sections:
            section.tree.setFont(font)
        self.loose_section.list.setFont(font)

    def shutdown(self):
        pass

    # ---- drag and drop ----
    def dragEnterEvent(self, event):
        if _local_paths(event.mimeData()):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if _local_paths(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.handle_dropped_paths(_local_paths(event.mimeData()))
        event.acceptProposedAction()

    def handle_dropped_paths(self, paths: list[str]):
        for path in paths:
            if os.path.isdir(path):
                self.add_root(path)
            elif os.path.isfile(path):
                if not self.is_within_open_root(path):
                    self.add_loose_file(path)
                self.file_activated.emit(path)

    # ---- actions ----
    def _active_section(self) -> "_RootSection | None":
        return self._active if self._active in self.sections else (self.sections[0] if self.sections else None)

    def _on_double_clicked(self, index: QModelIndex):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            self.file_activated.emit(path)

    def new_file(self, section: "_RootSection" = None, index: QModelIndex = None):
        section = section or self._active_section()
        if section is None:
            return
        target_dir = section.target_dir(index)
        name, ok = QInputDialog.getText(self, "New File", "File name:", text="new_script.py")
        if not ok or not name.strip():
            return
        path = os.path.join(target_dir, name.strip())
        if os.path.exists(path):
            QMessageBox.warning(self, "New File", f"'{name}' already exists.")
            return
        try:
            open(path, "w", encoding="utf-8").close()
        except OSError as e:
            QMessageBox.warning(self, "New File", f"Could not create file:\n{e}")
            return
        section.tree.setCurrentIndex(self.model.index(path))
        self.file_activated.emit(path)

    def new_folder(self, section: "_RootSection" = None, index: QModelIndex = None):
        section = section or self._active_section()
        if section is None:
            return
        target_dir = section.target_dir(index)
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:", text="New Folder")
        if not ok or not name.strip():
            return
        path = os.path.join(target_dir, name.strip())
        if os.path.exists(path):
            QMessageBox.warning(self, "New Folder", f"'{name}' already exists.")
            return
        try:
            os.makedirs(path)
        except OSError as e:
            QMessageBox.warning(self, "New Folder", f"Could not create folder:\n{e}")
            return
        section.tree.setCurrentIndex(self.model.index(path))

    def rename_selected(self, section: "_RootSection", index: QModelIndex):
        if index.isValid():
            section.tree.edit(index)

    def delete_selected(self, section: "_RootSection", index: QModelIndex):
        if not index.isValid():
            return
        # QFileSystemModel.filePath() returns forward-slash paths on Windows, which
        # send2trash's win32 backend fails to resolve (it builds a \\?\ long path and
        # can't find the file) - normalize before touching the filesystem.
        path = os.path.normpath(self.model.filePath(index))
        name = os.path.basename(path)
        reply = QMessageBox.question(
            self, "Delete",
            f"Send '{name}' to the Recycle Bin?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            if send2trash is not None:
                send2trash(path)
            elif os.path.isdir(path):
                os.rmdir(path)
            else:
                os.remove(path)
        except OSError as e:
            QMessageBox.warning(self, "Delete", f"Could not delete '{name}':\n{e}")

    def reveal_in_explorer(self, section: "_RootSection", index: QModelIndex):
        path = self.model.filePath(index) if index.isValid() else section.path
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])

    def _show_context_menu(self, section: "_RootSection", pos):
        index = section.tree.indexAt(pos)
        self._active = section
        menu = QMenu(self)
        menu.addAction("New File", lambda: self.new_file(section, index))
        menu.addAction("New Folder", lambda: self.new_folder(section, index))
        if index.isValid():
            menu.addSeparator()
            menu.addAction("Rename", lambda: self.rename_selected(section, index))
            menu.addAction("Delete", lambda: self.delete_selected(section, index))
        menu.addSeparator()
        menu.addAction("Reveal in File Explorer", lambda: self.reveal_in_explorer(section, index))
        menu.addAction("Remove Folder from Explorer", lambda: self.remove_root(section))
        menu.exec(section.tree.viewport().mapToGlobal(pos))
