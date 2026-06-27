"""WorkspaceSettings — v1.0.0

Thin wrapper around QSettings (INI format) that persists workspace state.

Storage:
    Windows: %APPDATA%/POE2FS/POE2FilterStudio.ini
    Linux:   ~/.config/POE2FS/POE2FilterStudio.ini

INI layout:
    [Window]
    geometry = <base64>

    [Splitter]
    sizes = 240,720,260

    [Editor/Sections]
    conditions_expanded = true
    appearance_expanded = true
    audio_expanded = false

    [RecentFiles]
    size = 3
    1 = C:/path/to/file.filter
    2 = ...

    [SectionCollapse/<8-char-hash>]
    0   = true      <- first_rule_index of section = expanded state
    42  = false
    132 = true

Public API:
    save_geometry(window)
    restore_geometry(window)
    save_splitter(splitter)
    restore_splitter(splitter)
    save_section_states(states: dict[str, bool])
    restore_section_states() -> dict[str, bool]
    save_section_collapse_states(file_path, states: dict[int, bool])
    restore_section_collapse_states(file_path) -> dict[int, bool]
    add_recent_file(path)
    recent_files() -> list[str]
    clear_recent_files()
"""

from __future__ import annotations

import hashlib

from PySide6.QtCore import QSettings, QByteArray


_MAX_RECENT = 10

_SECTION_DEFAULTS: dict[str, bool] = {
    "conditions": True,
    "appearance": True,
    "audio":      False,
}


class WorkspaceSettings:
    """Typed facade over QSettings (INI, user scope)."""

    def __init__(self) -> None:
        self._qs = QSettings(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            "POE2FS",
            "POE2FilterStudio",
        )

    # ------------------------------------------------------------------
    # Window geometry
    # ------------------------------------------------------------------

    def save_geometry(self, window) -> None:
        """Save QMainWindow geometry bytes to [Window] geometry."""
        self._qs.beginGroup("Window")
        self._qs.setValue("geometry", window.saveGeometry())
        self._qs.endGroup()

    def restore_geometry(self, window) -> None:
        """Restore QMainWindow geometry; silently skips if never saved."""
        self._qs.beginGroup("Window")
        raw = self._qs.value("geometry")
        self._qs.endGroup()
        if isinstance(raw, (bytes, QByteArray)) and raw:
            window.restoreGeometry(raw)

    # ------------------------------------------------------------------
    # Splitter proportions
    # ------------------------------------------------------------------

    def save_splitter(self, splitter) -> None:
        """Save splitter pane sizes as a comma-separated string."""
        sizes_str = ",".join(str(s) for s in splitter.sizes())
        self._qs.beginGroup("Splitter")
        self._qs.setValue("sizes", sizes_str)
        self._qs.endGroup()

    def restore_splitter(self, splitter) -> None:
        """Restore splitter sizes; silently skips if never saved or malformed."""
        self._qs.beginGroup("Splitter")
        raw = self._qs.value("sizes", "")
        self._qs.endGroup()
        if not raw:
            return
        try:
            sizes = [int(x) for x in str(raw).split(",") if x.strip()]
            if len(sizes) == splitter.count():
                splitter.setSizes(sizes)
        except (ValueError, AttributeError):
            pass

    # ------------------------------------------------------------------
    # CollapsibleSection states
    # ------------------------------------------------------------------

    def save_section_states(self, states: dict[str, bool]) -> None:
        """Persist {section_name: expanded} mapping under [Editor/Sections]."""
        self._qs.beginGroup("Editor/Sections")
        for key, expanded in states.items():
            self._qs.setValue(f"{key}_expanded", expanded)
        self._qs.endGroup()

    def restore_section_states(self) -> dict[str, bool]:
        """Return {section_name: expanded} with per-key fallback to defaults."""
        self._qs.beginGroup("Editor/Sections")
        result: dict[str, bool] = {}
        for key, default in _SECTION_DEFAULTS.items():
            raw = self._qs.value(f"{key}_expanded", default)
            # QSettings may return string "true"/"false" when read from INI
            result[key] = _to_bool(raw, default)
        self._qs.endGroup()
        return result

    # ------------------------------------------------------------------
    # Recent files
    # ------------------------------------------------------------------

    def add_recent_file(self, path: str) -> None:
        """Prepend *path* to the recent-files list; dedup + cap at 10."""
        current = self.recent_files()
        # Remove duplicate (case-insensitive on Windows paths)
        normalised = _norm(path)
        current = [p for p in current if _norm(p) != normalised]
        current.insert(0, path)
        current = current[:_MAX_RECENT]
        self._write_recent(current)

    def recent_files(self) -> list[str]:
        """Return up to 10 recent file paths in MRU order."""
        self._qs.beginGroup("RecentFiles")
        size = _to_int(self._qs.value("size", 0), 0)
        paths: list[str] = []
        for i in range(1, size + 1):
            p = self._qs.value(str(i), "")
            if p:
                paths.append(str(p))
        self._qs.endGroup()
        return paths

    def clear_recent_files(self) -> None:
        """Erase all recent file entries."""
        self._write_recent([])

    # ------------------------------------------------------------------
    # Filter section collapse states (keyed by first_rule_index)
    # ------------------------------------------------------------------

    def save_section_collapse_states(
        self, file_path: str, states: dict[int, bool]
    ) -> None:
        """Persist {first_rule_index: expanded} for *file_path*.

        Keyed by first_rule_index (int) to avoid duplicate section-name
        conflicts.  The file_path is hashed to a safe INI group name.
        """
        group = f"SectionCollapse/{_file_key(file_path)}"
        self._qs.beginGroup(group)
        self._qs.remove("")          # clear stale entries
        for idx, expanded in states.items():
            self._qs.setValue(str(idx), expanded)
        self._qs.endGroup()
        self._qs.sync()

    def restore_section_collapse_states(
        self, file_path: str
    ) -> dict[int, bool]:
        """Return {first_rule_index: expanded} for *file_path*.

        Returns an empty dict if nothing was saved (caller defaults to expanded).
        """
        group = f"SectionCollapse/{_file_key(file_path)}"
        self._qs.beginGroup(group)
        result: dict[int, bool] = {}
        for key in self._qs.childKeys():
            try:
                idx = int(key)
                result[idx] = _to_bool(self._qs.value(key), True)
            except ValueError:
                pass
        self._qs.endGroup()
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_recent(self, paths: list[str]) -> None:
        self._qs.beginGroup("RecentFiles")
        # Remove stale keys first
        self._qs.remove("")       # removes all keys inside the group
        self._qs.setValue("size", len(paths))
        for i, p in enumerate(paths, start=1):
            self._qs.setValue(str(i), p)
        self._qs.endGroup()
        self._qs.sync()


# ---------------------------------------------------------------------------
# Module-level helpers — pure, no Qt dependency for easy testing
# ---------------------------------------------------------------------------

def _to_bool(value, default: bool) -> bool:
    """Coerce QSettings value (may be str/bool) to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "no", "off", "")
    return bool(value) if value is not None else default


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm(path: str) -> str:
    """Normalise path for deduplication (lowercase, forward slashes)."""
    return path.replace("\\", "/").lower()


def _file_key(file_path: str) -> str:
    """Return an 8-char hex key derived from a normalised file path.

    Used as an INI group suffix so that special path characters (colons,
    backslashes, spaces) do not appear in the group name.
    """
    normalised = file_path.replace("\\", "/").lower()
    return hashlib.md5(normalised.encode()).hexdigest()[:8]
