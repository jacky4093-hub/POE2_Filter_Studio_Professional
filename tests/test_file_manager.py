"""Tests for FilterFileManager — v2.5.0

No QApplication required; all tests are pure-Python file I/O.
"""

import os
import pytest

from core.file_manager import FilterFileManager
from core.models import FilterRule


# ---------------------------------------------------------------------------
# TestDirtyState
# ---------------------------------------------------------------------------

class TestDirtyState:
    def test_initial_not_dirty(self):
        mgr = FilterFileManager()
        assert mgr.is_dirty is False

    def test_mark_dirty(self):
        mgr = FilterFileManager()
        mgr.mark_dirty()
        assert mgr.is_dirty is True

    def test_mark_clean(self):
        mgr = FilterFileManager()
        mgr.mark_dirty()
        mgr.mark_clean()
        assert mgr.is_dirty is False

    def test_clean_after_mark_dirty_twice(self):
        mgr = FilterFileManager()
        mgr.mark_dirty()
        mgr.mark_dirty()
        mgr.mark_clean()
        assert mgr.is_dirty is False


# ---------------------------------------------------------------------------
# TestCurrentPath
# ---------------------------------------------------------------------------

class TestCurrentPath:
    def test_initial_path_empty(self):
        mgr = FilterFileManager()
        assert mgr.current_path == ""

    def test_path_unchanged_after_mark_dirty(self):
        mgr = FilterFileManager()
        mgr.mark_dirty()
        assert mgr.current_path == ""


# ---------------------------------------------------------------------------
# TestLoad
# ---------------------------------------------------------------------------

class TestLoad:
    def test_load_reads_file_text(self, tmp_path):
        p = tmp_path / "t.filter"
        p.write_text("Show\n    Class \"Currency\"\n", encoding="utf-8")
        mgr = FilterFileManager()
        text = mgr.load(str(p))
        assert "Show" in text
        assert "Currency" in text

    def test_load_does_not_update_path(self, tmp_path):
        p = tmp_path / "t.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr = FilterFileManager()
        mgr.load(str(p))
        assert mgr.current_path == ""

    def test_load_does_not_change_dirty(self, tmp_path):
        p = tmp_path / "t.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr = FilterFileManager()
        mgr.mark_dirty()
        mgr.load(str(p))
        assert mgr.is_dirty is True   # load must not alter dirty

    def test_load_raises_on_missing_file(self):
        mgr = FilterFileManager()
        with pytest.raises(OSError):
            mgr.load("/nonexistent/absolutely/missing.filter")


# ---------------------------------------------------------------------------
# TestOpen
# ---------------------------------------------------------------------------

class TestOpen:
    def test_open_returns_file_text(self, tmp_path):
        p = tmp_path / "t.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr = FilterFileManager()
        text = mgr.open(str(p))
        assert text.strip() == "Show"

    def test_open_updates_current_path(self, tmp_path):
        p = tmp_path / "t.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr = FilterFileManager()
        mgr.open(str(p))
        assert mgr.current_path == str(p)

    def test_open_marks_clean(self, tmp_path):
        p = tmp_path / "t.filter"
        p.write_text("Show\n", encoding="utf-8")
        mgr = FilterFileManager()
        mgr.mark_dirty()
        mgr.open(str(p))
        assert mgr.is_dirty is False

    def test_open_raises_on_missing_leaves_path_unchanged(self):
        mgr = FilterFileManager()
        mgr._current_path = "/original/path.filter"
        with pytest.raises(OSError):
            mgr.open("/nonexistent/file.filter")
        # current_path must NOT be updated when load fails
        assert mgr.current_path == "/original/path.filter"


# ---------------------------------------------------------------------------
# TestSave
# ---------------------------------------------------------------------------

class TestSave:
    def test_save_returns_false_without_path(self):
        mgr = FilterFileManager()
        result = mgr.save("Show\n")
        assert result is False

    def test_save_returns_true_with_path(self, tmp_path):
        p = tmp_path / "t.filter"
        mgr = FilterFileManager()
        mgr._current_path = str(p)
        result = mgr.save("Show\n")
        assert result is True

    def test_save_writes_to_current_path(self, tmp_path):
        p = tmp_path / "t.filter"
        mgr = FilterFileManager()
        mgr._current_path = str(p)
        mgr.save("Show\n    Class \"Currency\"\n")
        content = p.read_text(encoding="utf-8")
        assert "Show" in content
        assert "Currency" in content

    def test_save_marks_clean(self, tmp_path):
        p = tmp_path / "t.filter"
        mgr = FilterFileManager()
        mgr._current_path = str(p)
        mgr.mark_dirty()
        mgr.save("Show\n")
        assert mgr.is_dirty is False

    def test_save_does_not_change_path(self, tmp_path):
        p = tmp_path / "t.filter"
        path_str = str(p)
        mgr = FilterFileManager()
        mgr._current_path = path_str
        mgr.save("Show\n")
        assert mgr.current_path == path_str

    def test_save_round_trip_via_open(self, tmp_path):
        p = tmp_path / "t.filter"
        mgr = FilterFileManager()
        mgr.save_as("Show\n", str(p))
        mgr.mark_dirty()
        mgr.save("Hide\n")
        text2 = mgr.load(str(p))
        assert text2 == "Hide\n"


# ---------------------------------------------------------------------------
# TestSaveAs
# ---------------------------------------------------------------------------

class TestSaveAs:
    def test_save_as_creates_file(self, tmp_path):
        p = tmp_path / "new.filter"
        mgr = FilterFileManager()
        mgr.save_as("Show\n", str(p))
        assert p.exists()

    def test_save_as_writes_content(self, tmp_path):
        p = tmp_path / "new.filter"
        mgr = FilterFileManager()
        mgr.save_as("Show\n    Class \"Currency\"\n", str(p))
        content = p.read_text(encoding="utf-8")
        assert "Currency" in content

    def test_save_as_updates_current_path(self, tmp_path):
        p = tmp_path / "new.filter"
        mgr = FilterFileManager()
        mgr.save_as("Show\n", str(p))
        assert mgr.current_path == str(p)

    def test_save_as_marks_clean(self, tmp_path):
        p = tmp_path / "new.filter"
        mgr = FilterFileManager()
        mgr.mark_dirty()
        mgr.save_as("Show\n", str(p))
        assert mgr.is_dirty is False

    def test_save_as_overwrites_old_path(self, tmp_path):
        p1 = tmp_path / "a.filter"
        p2 = tmp_path / "b.filter"
        mgr = FilterFileManager()
        mgr.save_as("first", str(p1))
        mgr.save_as("second", str(p2))
        assert mgr.current_path == str(p2)
        assert p2.read_text(encoding="utf-8") == "second"


# ---------------------------------------------------------------------------
# TestSerializeRules
# ---------------------------------------------------------------------------

class TestSerializeRules:
    def test_serialize_simple_rule(self):
        rule = FilterRule(action="Show")
        mgr = FilterFileManager()
        text = mgr.serialize_rules([rule])
        assert "Show" in text

    def test_serialize_preserves_pre_lines(self):
        rule = FilterRule(
            action="Show",
            pre_lines=["# Section header", "# ============"],
        )
        mgr = FilterFileManager()
        text = mgr.serialize_rules([rule])
        assert "# Section header" in text
        assert "# ============" in text

    def test_serialize_preserves_unknown_lines(self):
        rule = FilterRule(
            action="Show",
            unknown_lines=["UnknownDirective something"],
        )
        mgr = FilterFileManager()
        text = mgr.serialize_rules([rule])
        assert "UnknownDirective something" in text

    def test_serialize_preserves_inline_comment(self):
        rule = FilterRule(action="Show", inline_comment="important rule")
        mgr = FilterFileManager()
        text = mgr.serialize_rules([rule])
        assert "important rule" in text

    def test_serialize_disabled_rule_prefixed(self):
        rule = FilterRule(action="Show", enabled=False)
        mgr = FilterFileManager()
        text = mgr.serialize_rules([rule])
        assert "# Show" in text

    def test_serialize_conditions_present(self):
        rule = FilterRule(
            action="Show",
            conditions=[["Class", '"Currency"'], ["Rarity", "Unique"]],
        )
        mgr = FilterFileManager()
        text = mgr.serialize_rules([rule])
        assert "Class" in text
        assert '"Currency"' in text
        assert "Rarity" in text

    def test_serialize_actions_present(self):
        rule = FilterRule(
            action="Show",
            actions=[["SetFontSize", "36"], ["SetTextColor", "255 200 0 255"]],
        )
        mgr = FilterFileManager()
        text = mgr.serialize_rules([rule])
        assert "SetFontSize" in text
        assert "36" in text
        assert "SetTextColor" in text

    def test_serialize_tail_rule_no_header(self):
        tail = FilterRule(action="__TAIL__", pre_lines=["# end"])
        mgr = FilterFileManager()
        text = mgr.serialize_rules([tail])
        assert "__TAIL__" not in text
        assert "# end" in text

    def test_serialize_round_trip_via_save_and_load(self, tmp_path):
        """Serialize → save → reload should contain the same key content."""
        rule = FilterRule(
            action="Show",
            pre_lines=["# Round trip test"],
            conditions=[["Class", '"Currency"']],
            actions=[["SetFontSize", "40"]],
        )
        mgr = FilterFileManager()
        text = mgr.serialize_rules([rule])
        p = tmp_path / "rt.filter"
        mgr.save_as(text, str(p))
        loaded = mgr.load(str(p))
        assert "# Round trip test" in loaded
        assert "Class" in loaded
        assert "SetFontSize" in loaded

    def test_serialize_empty_list(self):
        mgr = FilterFileManager()
        text = mgr.serialize_rules([])
        assert text == ""


# ---------------------------------------------------------------------------
# TestWriteEncoding
# ---------------------------------------------------------------------------

class TestWriteEncoding:
    def test_save_as_utf8_no_bom(self, tmp_path):
        p = tmp_path / "enc.filter"
        mgr = FilterFileManager()
        mgr.save_as("Show # 中文\n", str(p))
        raw = p.read_bytes()
        assert raw[:3] != b'\xef\xbb\xbf'   # no UTF-8 BOM
        assert "中文" in raw.decode("utf-8")

    def test_save_as_lf_line_endings(self, tmp_path):
        p = tmp_path / "lf.filter"
        mgr = FilterFileManager()
        mgr.save_as("Show\nHide\n", str(p))
        raw = p.read_bytes()
        assert b'\r\n' not in raw   # no Windows CRLF
