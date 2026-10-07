import sys
import time
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from app import settings_store
from app.main_window import MainWindow
from app.themes import THEMES, DEFAULT_THEME


def _install_error_reporter():
    """This is a windowed app with no console, so uncaught errors in button handlers
    would otherwise vanish silently. Log them and tell the user."""
    showing = []

    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            log = settings_store.get_app_data_dir() / "error.log"
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n{text}\n")
        except OSError:
            log = "(could not write log)"
        if showing or QApplication.instance() is None:
            return
        showing.append(True)
        try:
            box = QMessageBox(QMessageBox.Warning, "Something went wrong",
                              f"{exc_type.__name__}: {exc}\n\nDetails were saved to:\n{log}")
            box.setDetailedText(text)
            box.exec()
        finally:
            showing.clear()

    sys.excepthook = hook


def main():
    app = QApplication(sys.argv)
    _install_error_reporter()
    app.setApplicationName("Custom Command Center")

    settings = settings_store.load_settings()
    app.setStyleSheet(THEMES.get(settings.get("theme", DEFAULT_THEME), THEMES[DEFAULT_THEME]))

    window = MainWindow(settings)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
