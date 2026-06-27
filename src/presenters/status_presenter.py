import os

from app_info import APP_NAME, APP_VERSION


class StatusPresenter:
    """Format MainWindow title and status strings without changing behavior."""

    def format_window_title(self, file_path: str, dirty: bool) -> str:
        prefix = "* " if dirty else ""
        base = f"{APP_NAME} {APP_VERSION}"
        if file_path:
            name = os.path.basename(file_path)
            return f"{prefix}{base} — {name}"
        return f"{prefix}{base}"

    def format_dirty_marker(self, dirty: bool) -> str:
        return " [已修改]" if dirty else ""

    def format_status_text(self, file_path: str, dirty: bool, count: int) -> str:
        name = os.path.basename(file_path) if file_path else "（未開啟）"
        dirty_marker = self.format_dirty_marker(dirty)
        return f"{name}{dirty_marker}  ·  {count} 條規則"
