"""SettingsManager — v2.6.0

JSON-based persistent settings for POE2 Filter Studio.
Stores recent files, last open directory, window geometry (base64),
and splitter sizes.  Injectable path for testing.

Default storage: %APPDATA%/POE2 Filter Studio/settings.json  (Windows)
               : ~/POE2 Filter Studio/settings.json           (fallback)
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class SettingsManager:
    """JSON-based settings store."""

    MAX_RECENT = 10

    def __init__(self, settings_path: str | Path | None = None) -> None:
        if settings_path is not None:
            self._path = Path(settings_path)
        else:
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
            self._path = Path(base) / "POE2 Filter Studio" / "settings.json"
        self._data: dict = {}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load settings from disk.  Silently resets to empty on error."""
        try:
            raw = self._path.read_text(encoding="utf-8")
            loaded = json.loads(raw)
            self._data = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            self._data = {}

    def save(self) -> None:
        """Write settings to disk.  Creates parent directories as needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Generic key/value
    # ------------------------------------------------------------------

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value

    # ------------------------------------------------------------------
    # Recent files
    # ------------------------------------------------------------------

    def recent_files(self) -> list[str]:
        """Return a copy of the recent-files list (MRU order, max MAX_RECENT)."""
        return list(self._data.get("recent_files", []))

    def add_recent_file(self, path: str) -> None:
        """Prepend *path* (dedup case-insensitive on Windows).  Max MAX_RECENT kept."""
        path = str(path)
        norm_new = os.path.normcase(os.path.normpath(path))
        files = [
            f for f in self.recent_files()
            if os.path.normcase(os.path.normpath(f)) != norm_new
        ]
        files.insert(0, path)
        self._data["recent_files"] = files[: self.MAX_RECENT]

    def clear_recent_files(self) -> None:
        self._data["recent_files"] = []

    # ------------------------------------------------------------------
    # Last-used open directory
    # ------------------------------------------------------------------

    @property
    def last_open_dir(self) -> str:
        return str(self._data.get("last_open_dir", ""))

    @last_open_dir.setter
    def last_open_dir(self, value: str) -> None:
        self._data["last_open_dir"] = str(value)

    # ------------------------------------------------------------------
    # Window geometry (stored as a base64-encoded string)
    # ------------------------------------------------------------------

    @property
    def window_geometry(self) -> str:
        return str(self._data.get("window_geometry", ""))

    @window_geometry.setter
    def window_geometry(self, value: str) -> None:
        self._data["window_geometry"] = str(value)

    # ------------------------------------------------------------------
    # Splitter sizes
    # ------------------------------------------------------------------

    def get_splitter_sizes(self, key: str = "main") -> list[int]:
        """Return stored sizes for *key*, or [] if invalid/missing."""
        raw = self._data.get(f"splitter_{key}", [])
        if (
            isinstance(raw, list)
            and len(raw) > 0
            and all(isinstance(x, int) and x >= 0 for x in raw)
        ):
            return list(raw)
        return []

    def set_splitter_sizes(self, sizes: list[int] | tuple[int, ...], key: str = "main") -> None:
        """Store sizes for *key*.  Clamps negative values to 0."""
        if not isinstance(sizes, (list, tuple)):
            return
        if not all(isinstance(x, int) for x in sizes):
            return
        self._data[f"splitter_{key}"] = [max(0, x) for x in sizes]

    # ------------------------------------------------------------------
    # Last-opened file (for startup restore)
    # ------------------------------------------------------------------

    def set_last_open_file(self, path: str) -> None:
        self._data["last_open_file"] = str(path)

    def get_last_open_file(self) -> str:
        return str(self._data.get("last_open_file", ""))

    # ------------------------------------------------------------------
    # Startup restore preference
    # ------------------------------------------------------------------

    def set_restore_last_file_on_startup(self, value: bool) -> None:
        self._data["restore_last_file_on_startup"] = bool(value)

    def get_restore_last_file_on_startup(self) -> bool:
        return bool(self._data.get("restore_last_file_on_startup", False))
