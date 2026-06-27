"""IconRegistry — v1.0.0  (P15.1 Icon System)

Centralised icon lookup.  All widgets must query icons through this class —
no widget may hardcode icon paths or construct QIcon directly.

Usage:
    from assets.icon_registry import IconRegistry
    icon = IconRegistry.get_category_icon(Category.CURRENCY)
    icon = IconRegistry.get_rule_action_icon("Show")
    icon = IconRegistry.get_template_icon("Currency")

To upgrade art: replace SVG files in src/assets/icons/ and call
IconRegistry.clear_cache() (or restart the app).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

try:
    import PySide6.QtSvg  # noqa: F401 — registers SVG image-format plugin
except ImportError:
    pass

from core.categorizer import Category

_ICONS_DIR = Path(__file__).parent / "icons"

# Template name → icon file stem (without .svg).
# Templates that share a category icon reuse the category_*.svg file directly.
_TEMPLATE_ICON_MAP: dict[str, str] = {
    "Currency":    "category_currency",
    "Unique 物品": "category_unique",
    "Rare 物品":   "template_rare",
    "Magic 物品":  "template_magic",
    "Gem":         "category_gems",
    "Waystone":    "category_maps",
    "空規則":      "template_empty",
}


class IconRegistry:
    """Thread-safe singleton icon cache.

    Icons are loaded on first use and cached for the lifetime of the process.
    Widgets never construct QIcon themselves; they call the class-methods here.
    """

    _cache: dict[str, QIcon] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def get_category_icon(cls, category: Category) -> QIcon:
        """Return the QIcon for a sidebar Category.  Never returns None."""
        return cls._load(f"category_{category.value}")

    @classmethod
    def get_rule_action_icon(cls, action: str) -> QIcon:
        """Return the QIcon for a rule Action (Show / Hide / Continue).

        Returns a null QIcon for unknown actions (e.g. __TAIL__); callers
        should guard with `if not icon.isNull()`.
        """
        return cls._load(f"action_{action.lower()}")

    @classmethod
    def get_template_icon(cls, template_name: str) -> QIcon:
        """Return the QIcon for a RuleCreationDialog template row."""
        stem = _TEMPLATE_ICON_MAP.get(template_name, "template_empty")
        return cls._load(stem)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    @classmethod
    def clear_cache(cls) -> None:
        """Flush the icon cache.  Useful in tests and after art upgrades."""
        cls._cache.clear()

    # ------------------------------------------------------------------
    # Internal loader
    # ------------------------------------------------------------------

    @classmethod
    def _load(cls, stem: str) -> QIcon:
        """Load *stem*.svg from the icons directory, with per-stem caching."""
        if stem not in cls._cache:
            path = _ICONS_DIR / f"{stem}.svg"
            cls._cache[stem] = QIcon(str(path)) if path.exists() else QIcon()
        return cls._cache[stem]

    # ------------------------------------------------------------------
    # Introspection (used by tests)
    # ------------------------------------------------------------------

    @classmethod
    def icon_path(cls, stem: str) -> Path:
        """Return the expected file path for *stem* (useful for tests)."""
        return _ICONS_DIR / f"{stem}.svg"
