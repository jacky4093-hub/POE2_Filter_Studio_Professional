import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app_info import APP_NAME, APP_VERSION
from ui.main_window import MainWindow
from services.settings_service import WorkspaceSettings


def _assets_dir() -> Path:
    """Resolve assets path for dev and PyInstaller frozen builds."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def apply_theme(app: QApplication) -> None:
    """Load v2 dark-theme QSS stylesheets onto the application."""
    styles_dir = _assets_dir() / "styles"
    if not styles_dir.is_dir():
        return

    qss_parts: list[str] = []
    for qss_file in sorted(styles_dir.glob("*.qss")):
        qss_parts.append(qss_file.read_text(encoding="utf-8"))

    if qss_parts:
        app.setStyleSheet("\n".join(qss_parts))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("POE2FS")

    apply_theme(app)

    settings = WorkspaceSettings()
    window = MainWindow(settings)
    window.show()

    # If a file path was passed on the command line, open it immediately
    if len(sys.argv) > 1:
        window.load_file(sys.argv[1])

    sys.exit(app.exec())
