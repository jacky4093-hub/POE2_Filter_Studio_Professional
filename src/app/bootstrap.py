import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from services.settings_service import WorkspaceSettings


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("POE2 Filter Studio")
    app.setOrganizationName("POE2FS")

    settings = WorkspaceSettings()
    window = MainWindow(settings)
    window.show()

    # If a file path was passed on the command line, open it immediately
    if len(sys.argv) > 1:
        window.load_file(sys.argv[1])

    sys.exit(app.exec())
