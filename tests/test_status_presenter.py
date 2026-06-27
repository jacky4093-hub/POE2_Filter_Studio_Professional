from app_info import APP_NAME, APP_VERSION
from presenters.status_presenter import StatusPresenter

_BASE = f"{APP_NAME} {APP_VERSION}"


def test_title_formatting_for_clean_and_dirty_states():
    presenter = StatusPresenter()

    assert presenter.format_window_title("", False) == _BASE
    assert presenter.format_window_title("", True) == f"* {_BASE}"
    assert presenter.format_window_title("my.filter", False) == f"{_BASE} — my.filter"
    assert presenter.format_window_title("my.filter", True) == f"* {_BASE} — my.filter"


def test_status_text_uses_file_name_dirty_marker_and_rule_count():
    presenter = StatusPresenter()

    assert presenter.format_status_text("/tmp/example.filter", False, 3) == "example.filter  ·  3 條規則"
    assert presenter.format_status_text("/tmp/example.filter", True, 5) == "example.filter [已修改]  ·  5 條規則"


def test_status_text_uses_default_name_when_no_file_path():
    presenter = StatusPresenter()

    assert presenter.format_status_text("", False, 0) == "（未開啟）  ·  0 條規則"
    assert presenter.format_status_text("", True, 1) == "（未開啟） [已修改]  ·  1 條規則"


def test_dirty_marker_is_empty_for_clean_state():
    presenter = StatusPresenter()

    assert presenter.format_dirty_marker(False) == ""
    assert presenter.format_dirty_marker(True) == " [已修改]"
