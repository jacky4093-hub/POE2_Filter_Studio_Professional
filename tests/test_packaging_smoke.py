"""Packaging smoke tests — P17.3 Packaging Readiness

Verifies that the project is ready for packaging:
- app_info constants are importable and complete
- Main entry-point module exists and is importable
- bootstrap.main / apply_theme are callable
- Asset directories (styles, icons) exist with content
- packaging/ artifacts (spec, README) are in place
"""

import ast
import importlib.util
import pathlib

import pytest
from PySide6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


# ---------------------------------------------------------------------------
# Path helpers (no QApp needed)
# ---------------------------------------------------------------------------

def _src_dir() -> pathlib.Path:
    """Resolve src/ by finding app_info on sys.path."""
    spec = importlib.util.find_spec("app_info")
    assert spec and spec.origin, "app_info not found on pythonpath"
    return pathlib.Path(spec.origin).parent


def _project_root() -> pathlib.Path:
    return _src_dir().parent


def _assets_dir() -> pathlib.Path:
    return _src_dir() / "assets"


# ---------------------------------------------------------------------------
# TestAppInfoImportable
# ---------------------------------------------------------------------------

class TestAppInfoImportable:

    def test_module_importable(self):
        import app_info  # noqa: F401

    def test_app_name_is_non_empty_string(self):
        from app_info import APP_NAME
        assert isinstance(APP_NAME, str) and APP_NAME.strip()

    def test_app_version_is_non_empty_string(self):
        from app_info import APP_VERSION
        assert isinstance(APP_VERSION, str) and APP_VERSION.strip()

    def test_app_author_is_non_empty_string(self):
        from app_info import APP_AUTHOR
        assert isinstance(APP_AUTHOR, str) and APP_AUTHOR.strip()

    def test_app_description_is_non_empty_string(self):
        from app_info import APP_DESCRIPTION
        assert isinstance(APP_DESCRIPTION, str) and APP_DESCRIPTION.strip()

    def test_app_name_and_version_are_different(self):
        from app_info import APP_NAME, APP_VERSION
        assert APP_NAME != APP_VERSION

    def test_version_has_dot_separator(self):
        from app_info import APP_VERSION
        assert "." in APP_VERSION

    def test_app_info_file_is_in_src(self):
        spec = importlib.util.find_spec("app_info")
        p = pathlib.Path(spec.origin)
        assert p.parent.name == "src" or "src" in str(p), (
            f"app_info.py should live inside src/, found: {p}"
        )


# ---------------------------------------------------------------------------
# TestMainModuleImportable
# ---------------------------------------------------------------------------

class TestMainModuleImportable:

    def test_main_py_file_exists(self):
        main_py = _project_root() / "src" / "main.py"
        assert main_py.is_file(), f"src/main.py not found at {main_py}"

    def test_main_py_references_bootstrap(self):
        main_py = (_project_root() / "src" / "main.py").read_text(encoding="utf-8")
        assert "bootstrap" in main_py

    def test_bootstrap_module_importable(self, qapp):
        import app.bootstrap  # noqa: F401

    def test_bootstrap_main_callable(self, qapp):
        from app import bootstrap
        assert callable(bootstrap.main)

    def test_bootstrap_apply_theme_callable(self, qapp):
        from app import bootstrap
        assert callable(bootstrap.apply_theme)

    def test_bootstrap_assets_dir_resolves(self, qapp):
        from app.bootstrap import _assets_dir
        d = _assets_dir()
        assert d.is_dir(), f"_assets_dir() → {d} does not exist"

    def test_bootstrap_uses_app_name(self, qapp):
        bootstrap_path = _project_root() / "src" / "app" / "bootstrap.py"
        src = bootstrap_path.read_text(encoding="utf-8")
        assert "APP_NAME" in src, "bootstrap.py must use APP_NAME from app_info"

    def test_bootstrap_uses_app_version(self, qapp):
        bootstrap_path = _project_root() / "src" / "app" / "bootstrap.py"
        src = bootstrap_path.read_text(encoding="utf-8")
        assert "APP_VERSION" in src, "bootstrap.py must use APP_VERSION from app_info"

    def test_bootstrap_imports_app_info(self, qapp):
        bootstrap_path = _project_root() / "src" / "app" / "bootstrap.py"
        src = bootstrap_path.read_text(encoding="utf-8")
        assert "app_info" in src, "bootstrap.py must import from app_info"

    def test_bootstrap_has_frozen_guard(self, qapp):
        bootstrap_path = _project_root() / "src" / "app" / "bootstrap.py"
        src = bootstrap_path.read_text(encoding="utf-8")
        assert "frozen" in src, "bootstrap.py must handle sys.frozen for PyInstaller"

    def test_bootstrap_has_meipass_reference(self, qapp):
        bootstrap_path = _project_root() / "src" / "app" / "bootstrap.py"
        src = bootstrap_path.read_text(encoding="utf-8")
        assert "_MEIPASS" in src, "bootstrap.py must reference sys._MEIPASS for frozen builds"


# ---------------------------------------------------------------------------
# TestAssetsPathExists
# ---------------------------------------------------------------------------

class TestAssetsPathExists:

    def test_assets_dir_exists(self):
        d = _assets_dir()
        assert d.is_dir(), f"assets/ not found at {d}"

    def test_styles_dir_exists(self):
        d = _assets_dir() / "styles"
        assert d.is_dir(), f"assets/styles/ not found at {d}"

    def test_icons_dir_exists(self):
        d = _assets_dir() / "icons"
        assert d.is_dir(), f"assets/icons/ not found at {d}"

    def test_styles_has_qss_files(self):
        files = list((_assets_dir() / "styles").glob("*.qss"))
        assert len(files) > 0, "No .qss files in assets/styles/"

    def test_icons_has_svg_files(self):
        files = list((_assets_dir() / "icons").glob("*.svg"))
        assert len(files) > 0, "No .svg files in assets/icons/"

    def test_base_qss_exists(self):
        f = _assets_dir() / "styles" / "base.qss"
        assert f.is_file(), "base.qss missing from assets/styles/"

    def test_editor_qss_exists(self):
        f = _assets_dir() / "styles" / "editor.qss"
        assert f.is_file(), "editor.qss missing from assets/styles/"

    def test_browser_qss_exists(self):
        f = _assets_dir() / "styles" / "browser.qss"
        assert f.is_file(), "browser.qss missing from assets/styles/"

    def test_qss_files_are_non_empty(self):
        for f in (_assets_dir() / "styles").glob("*.qss"):
            assert f.stat().st_size > 0, f"{f.name} is empty"

    def test_svg_files_are_non_empty(self):
        for f in (_assets_dir() / "icons").glob("*.svg"):
            assert f.stat().st_size > 0, f"{f.name} is empty"


# ---------------------------------------------------------------------------
# TestPackagingArtifacts
# ---------------------------------------------------------------------------

class TestPackagingArtifacts:

    def test_packaging_dir_exists(self):
        d = _project_root() / "packaging"
        assert d.is_dir(), "packaging/ directory not found"

    def test_spec_file_exists(self):
        f = _project_root() / "packaging" / "poe2_filter_studio.spec"
        assert f.is_file(), "poe2_filter_studio.spec not found in packaging/"

    def test_spec_references_main_py(self):
        spec = (_project_root() / "packaging" / "poe2_filter_studio.spec").read_text(encoding="utf-8")
        assert "main.py" in spec

    def test_spec_references_styles(self):
        spec = (_project_root() / "packaging" / "poe2_filter_studio.spec").read_text(encoding="utf-8")
        assert "styles" in spec

    def test_spec_references_icons(self):
        spec = (_project_root() / "packaging" / "poe2_filter_studio.spec").read_text(encoding="utf-8")
        assert "icons" in spec

    def test_spec_has_console_false(self):
        spec = (_project_root() / "packaging" / "poe2_filter_studio.spec").read_text(encoding="utf-8")
        assert "console=False" in spec

    def test_spec_has_hidden_imports(self):
        spec = (_project_root() / "packaging" / "poe2_filter_studio.spec").read_text(encoding="utf-8")
        assert "hiddenimports" in spec

    def test_readme_exists(self):
        f = _project_root() / "packaging" / "README.md"
        assert f.is_file(), "packaging/README.md not found"

    def test_readme_mentions_draft(self):
        readme = (_project_root() / "packaging" / "README.md").read_text(encoding="utf-8")
        assert "草案" in readme or "draft" in readme.lower()

    def test_readme_mentions_pyinstaller(self):
        readme = (_project_root() / "packaging" / "README.md").read_text(encoding="utf-8")
        assert "pyinstaller" in readme.lower()

    def test_readme_mentions_app_version(self):
        readme = (_project_root() / "packaging" / "README.md").read_text(encoding="utf-8")
        assert "APP_VERSION" in readme or "app_info" in readme
