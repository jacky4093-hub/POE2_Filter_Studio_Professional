"""Tests for SettingsManager — v2.6.0

Pure-Python tests; no QApplication required.
Covers JSON persistence, recent files, last_open_dir, splitter_sizes.
"""

import json
import os
import pytest

from core.settings_manager import SettingsManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mgr(tmp_path) -> SettingsManager:
    return SettingsManager(settings_path=str(tmp_path / "settings.json"))


# ---------------------------------------------------------------------------
# TestLoad
# ---------------------------------------------------------------------------

class TestLoad:
    def test_load_nonexistent_file_gives_empty(self, tmp_path):
        mgr = SettingsManager(settings_path=str(tmp_path / "nonexistent.json"))
        assert mgr.recent_files() == []
        assert mgr.last_open_dir == ""

    def test_load_invalid_json_gives_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json", encoding="utf-8")
        mgr = SettingsManager(settings_path=str(p))
        assert mgr.get("any_key") is None

    def test_load_non_dict_json_gives_empty(self, tmp_path):
        p = tmp_path / "arr.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        mgr = SettingsManager(settings_path=str(p))
        assert mgr.get("key") is None


# ---------------------------------------------------------------------------
# TestSaveReload
# ---------------------------------------------------------------------------

class TestSaveReload:
    def test_save_creates_file(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set("x", 42)
        mgr.save()
        p = tmp_path / "settings.json"
        assert p.exists()

    def test_save_creates_parent_dirs(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "settings.json"
        mgr = SettingsManager(settings_path=str(deep))
        mgr.set("k", 1)
        mgr.save()
        assert deep.exists()

    def test_save_reload_round_trip(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set("foo", "bar")
        mgr.save()

        mgr2 = _mgr(tmp_path)
        assert mgr2.get("foo") == "bar"

    def test_save_produces_valid_json(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set("num", 99)
        mgr.save()
        raw = (tmp_path / "settings.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        assert data["num"] == 99


# ---------------------------------------------------------------------------
# TestGetSet
# ---------------------------------------------------------------------------

class TestGetSet:
    def test_get_missing_returns_none(self, tmp_path):
        mgr = _mgr(tmp_path)
        assert mgr.get("missing") is None

    def test_get_missing_custom_default(self, tmp_path):
        mgr = _mgr(tmp_path)
        assert mgr.get("missing", 99) == 99

    def test_set_and_get(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set("color", "red")
        assert mgr.get("color") == "red"

    def test_set_overrides_existing(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set("x", 1)
        mgr.set("x", 2)
        assert mgr.get("x") == 2

    def test_set_various_types(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set("int_val", 42)
        mgr.set("list_val", [1, 2, 3])
        mgr.set("bool_val", True)
        assert mgr.get("int_val") == 42
        assert mgr.get("list_val") == [1, 2, 3]
        assert mgr.get("bool_val") is True


# ---------------------------------------------------------------------------
# TestRecentFiles
# ---------------------------------------------------------------------------

class TestRecentFiles:
    def test_initial_empty(self, tmp_path):
        mgr = _mgr(tmp_path)
        assert mgr.recent_files() == []

    def test_add_single_file(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.add_recent_file("/a/b.filter")
        assert "/a/b.filter" in mgr.recent_files()

    def test_first_added_is_at_index_zero(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.add_recent_file("/first.filter")
        mgr.add_recent_file("/second.filter")
        assert mgr.recent_files()[0] == "/second.filter"

    def test_duplicate_moves_to_top(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.add_recent_file("/a.filter")
        mgr.add_recent_file("/b.filter")
        mgr.add_recent_file("/a.filter")    # re-add /a
        files = mgr.recent_files()
        assert files[0] == "/a.filter"
        assert files.count("/a.filter") == 1  # no duplicate

    def test_max_recent_files_kept(self, tmp_path):
        mgr = _mgr(tmp_path)
        for i in range(15):
            mgr.add_recent_file(f"/file{i}.filter")
        assert len(mgr.recent_files()) == SettingsManager.MAX_RECENT

    def test_oldest_dropped_when_full(self, tmp_path):
        mgr = _mgr(tmp_path)
        for i in range(11):
            mgr.add_recent_file(f"/file{i}.filter")
        # file0 should be gone (pushed out)
        assert "/file0.filter" not in mgr.recent_files()

    def test_clear_recent_files(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.add_recent_file("/a.filter")
        mgr.clear_recent_files()
        assert mgr.recent_files() == []

    def test_returns_copy(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.add_recent_file("/a.filter")
        lst = mgr.recent_files()
        lst.append("/mutated.filter")
        assert "/mutated.filter" not in mgr.recent_files()

    def test_persisted_after_save_reload(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.add_recent_file("/persistent.filter")
        mgr.save()
        mgr2 = _mgr(tmp_path)
        assert "/persistent.filter" in mgr2.recent_files()

    def test_clear_persisted_after_save_reload(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.add_recent_file("/a.filter")
        mgr.clear_recent_files()
        mgr.save()
        mgr2 = _mgr(tmp_path)
        assert mgr2.recent_files() == []


# ---------------------------------------------------------------------------
# TestLastOpenDir
# ---------------------------------------------------------------------------

class TestLastOpenDir:
    def test_initial_empty(self, tmp_path):
        mgr = _mgr(tmp_path)
        assert mgr.last_open_dir == ""

    def test_set_and_get(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.last_open_dir = "/some/directory"
        assert mgr.last_open_dir == "/some/directory"

    def test_persisted_after_save_reload(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.last_open_dir = "/my/filters"
        mgr.save()
        mgr2 = _mgr(tmp_path)
        assert mgr2.last_open_dir == "/my/filters"

    def test_overwrite(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.last_open_dir = "/first"
        mgr.last_open_dir = "/second"
        assert mgr.last_open_dir == "/second"


# ---------------------------------------------------------------------------
# TestWindowGeometry
# ---------------------------------------------------------------------------

class TestWindowGeometry:
    def test_initial_empty(self, tmp_path):
        mgr = _mgr(tmp_path)
        assert mgr.window_geometry == ""

    def test_set_and_get(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.window_geometry = "AAABBBCCC=="
        assert mgr.window_geometry == "AAABBBCCC=="

    def test_persisted_after_save_reload(self, tmp_path):
        import base64
        payload = base64.b64encode(b"\x01\x02\x03").decode()
        mgr = _mgr(tmp_path)
        mgr.window_geometry = payload
        mgr.save()
        mgr2 = _mgr(tmp_path)
        assert mgr2.window_geometry == payload


# ---------------------------------------------------------------------------
# TestSplitterSizes
# ---------------------------------------------------------------------------

class TestSplitterSizes:
    def test_initial_empty(self, tmp_path):
        mgr = _mgr(tmp_path)
        assert mgr.get_splitter_sizes() == []

    def test_set_and_get(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_splitter_sizes([280, 660, 280])
        assert mgr.get_splitter_sizes() == [280, 660, 280]

    def test_named_key(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_splitter_sizes([100, 200], key="panel")
        assert mgr.get_splitter_sizes("panel") == [100, 200]
        assert mgr.get_splitter_sizes("main") == []   # different key

    def test_negative_values_clamped_to_zero(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_splitter_sizes([100, -50, 200])
        assert mgr.get_splitter_sizes() == [100, 0, 200]

    def test_invalid_input_non_list_ignored(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_splitter_sizes("not a list")   # type: ignore
        assert mgr.get_splitter_sizes() == []

    def test_invalid_input_non_int_elements_ignored(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_splitter_sizes([100, "oops", 200])   # type: ignore
        assert mgr.get_splitter_sizes() == []

    def test_empty_list_stored_gives_empty_on_get(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_splitter_sizes([])
        assert mgr.get_splitter_sizes() == []

    def test_persisted_after_save_reload(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_splitter_sizes([300, 500, 200])
        mgr.save()
        mgr2 = _mgr(tmp_path)
        assert mgr2.get_splitter_sizes() == [300, 500, 200]

    def test_tuple_accepted(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_splitter_sizes((150, 450, 150))   # type: ignore  (tuple OK)
        assert mgr.get_splitter_sizes() == [150, 450, 150]


# ---------------------------------------------------------------------------
# TestLastOpenFile
# ---------------------------------------------------------------------------

class TestLastOpenFile:
    def test_initial_empty(self, tmp_path):
        mgr = _mgr(tmp_path)
        assert mgr.get_last_open_file() == ""

    def test_set_and_get(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_last_open_file("/filters/my.filter")
        assert mgr.get_last_open_file() == "/filters/my.filter"

    def test_overwrite(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_last_open_file("/first.filter")
        mgr.set_last_open_file("/second.filter")
        assert mgr.get_last_open_file() == "/second.filter"

    def test_persisted_after_save_reload(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_last_open_file("/persisted.filter")
        mgr.save()
        mgr2 = _mgr(tmp_path)
        assert mgr2.get_last_open_file() == "/persisted.filter"


# ---------------------------------------------------------------------------
# TestRestoreLastFileOnStartup
# ---------------------------------------------------------------------------

class TestRestoreLastFileOnStartup:
    def test_default_false(self, tmp_path):
        mgr = _mgr(tmp_path)
        assert mgr.get_restore_last_file_on_startup() is False

    def test_set_true(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_restore_last_file_on_startup(True)
        assert mgr.get_restore_last_file_on_startup() is True

    def test_set_false_from_true(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_restore_last_file_on_startup(True)
        mgr.set_restore_last_file_on_startup(False)
        assert mgr.get_restore_last_file_on_startup() is False

    def test_persisted_after_save_reload(self, tmp_path):
        mgr = _mgr(tmp_path)
        mgr.set_restore_last_file_on_startup(True)
        mgr.save()
        mgr2 = _mgr(tmp_path)
        assert mgr2.get_restore_last_file_on_startup() is True
