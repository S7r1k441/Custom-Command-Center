"""Reading/writing text files without mangling encoding or line endings."""
import os

from PySide6.QtWidgets import QMessageBox


class NotTextFileError(Exception):
    pass


def read_text_file(path: str) -> tuple[str, bool]:
    """Return (text with \\n line endings, whether the file used \\r\\n)."""
    with open(path, "rb") as f:
        data = f.read()
    if b"\x00" in data:
        raise NotTextFileError("This looks like a binary file, not text.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise NotTextFileError("This file isn't UTF-8 text, so it can't be edited safely here.")
    crlf = "\r\n" in text
    return text.replace("\r\n", "\n"), crlf


def write_text_file(path: str, text: str, crlf: bool) -> None:
    with open(path, "w", encoding="utf-8", newline="\r\n" if crlf else "\n") as f:
        f.write(text)


def _disk_stamp(path: str):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


class DiskSyncMixin:
    """Keeps an editing tab in step with its file on disk (external edits, renames).

    Host needs: current_file, editor, crlf, is_modified(), load_file(), state_changed.
    """
    _disk_stamp_value = None

    def record_disk_stamp(self):
        self._disk_stamp_value = _disk_stamp(self.current_file) if self.current_file else None

    def _changed_on_disk(self) -> bool:
        if not self.current_file or self._disk_stamp_value is None:
            return False
        now = _disk_stamp(self.current_file)
        return now is not None and now != self._disk_stamp_value

    def confirm_overwrite_newer(self, path: str) -> bool:
        """Before saving: don't silently clobber a version that changed outside the app."""
        if path != self.current_file or not self._changed_on_disk():
            return True
        reply = QMessageBox.warning(
            self, "File changed on disk",
            f"{os.path.basename(path)} was changed outside this editor since you opened it.\n\n"
            "Overwrite it with what's in this tab?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def check_disk_changes(self) -> bool:
        """Pull in outside changes. Returns True if the tab was reloaded."""
        if not self._changed_on_disk():
            return False
        if self.is_modified():
            reply = QMessageBox.question(
                self, "File changed on disk",
                f"{os.path.basename(self.current_file)} was changed outside this editor, "
                "and you also have unsaved edits here.\n\nReload from disk and lose your edits?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                self.record_disk_stamp()  # keep my version; the next save overwrites
                return False
        position = self.editor.textCursor().position()
        try:
            text, crlf = read_text_file(self.current_file)
        except (OSError, NotTextFileError):
            return False
        self.editor.setPlainText(text)
        self.crlf = crlf
        cursor = self.editor.textCursor()
        cursor.setPosition(min(position, len(text)))
        self.editor.setTextCursor(cursor)
        self.editor.document().setModified(False)
        self.record_disk_stamp()
        self.state_changed.emit()
        return True


def prompt_save_changes(parent, name: str) -> str:
    """Ask what to do with unsaved changes: 'save', 'discard' or 'cancel'."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Unsaved changes")
    box.setText(f"Do you want to save changes to {name}?")
    save = box.addButton("Save", QMessageBox.AcceptRole)
    discard = box.addButton("Don't Save", QMessageBox.DestructiveRole)
    box.addButton("Cancel", QMessageBox.RejectRole)
    box.setDefaultButton(save)
    box.exec()
    clicked = box.clickedButton()
    if clicked is save:
        return "save"
    if clicked is discard:
        return "discard"
    return "cancel"
