"""P21.2 — AliasResolver: 中文 Alias 解析服務。

從 bundled_aliases_zh_tw.json 載入資料，提供：
  resolve_zh(text)     → list[str]   (英文名稱清單，priority 小的優先)
  reverse_resolve(en)  → str | None  (中文主名稱)
"""

from __future__ import annotations

import json
import pathlib
from typing import Optional

_DATA_FILE = pathlib.Path(__file__).parent.parent / "data" / "bundled_aliases_zh_tw.json"


class AliasResolver:
    """中文 Alias → 英文名稱 解析器。

    搜尋優先順序（依序嘗試，同層結果再按 priority 排序）：
      1. zh 完全匹配
      2. aliases_zh 完全匹配
      3. zh 開頭匹配
      4. aliases_zh 開頭匹配
      5. zh 包含匹配
      6. aliases_zh 包含匹配
    """

    def __init__(self, data_file: pathlib.Path = _DATA_FILE) -> None:
        with data_file.open(encoding="utf-8") as f:
            db = json.load(f)
        self._items: list[dict] = db.get("items", [])
        # 預建反查索引 en → zh
        self._en_to_zh: dict[str, str] = {
            item["en"]: item["zh"] for item in self._items
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_zh(self, text: str) -> list[str]:
        """將中文搜尋詞轉換為英文名稱清單。

        回傳的清單按 priority 升序排列（數字小 = 優先級高）。
        同一 priority 內維持原始資料順序。
        回傳空清單代表無匹配。
        """
        if not text:
            return []

        # 收集各層匹配結果（用 dict 去重，保留首次出現）
        # tiers: list of (priority, en_name)
        seen: set[str] = set()
        results: list[tuple[int, str]] = []

        def _add(item: dict) -> None:
            en = item["en"]
            if en not in seen:
                seen.add(en)
                results.append((item["priority"], en))

        # 按六層優先順序掃描
        for tier_fn in (
            self._match_zh_exact,
            self._match_alias_exact,
            self._match_zh_startswith,
            self._match_alias_startswith,
            self._match_zh_contains,
            self._match_alias_contains,
        ):
            for item in self._items:
                if tier_fn(item, text):
                    _add(item)

        results.sort(key=lambda t: t[0])
        return [en for _, en in results]

    def reverse_resolve(self, en_name: str) -> Optional[str]:
        """將英文名稱轉換為繁體中文主名稱。

        完全匹配（大小寫敏感）。找不到回傳 None。
        """
        return self._en_to_zh.get(en_name)

    # ------------------------------------------------------------------
    # Internal matchers
    # ------------------------------------------------------------------

    @staticmethod
    def _match_zh_exact(item: dict, text: str) -> bool:
        return item["zh"] == text

    @staticmethod
    def _match_alias_exact(item: dict, text: str) -> bool:
        return text in item["aliases_zh"]

    @staticmethod
    def _match_zh_startswith(item: dict, text: str) -> bool:
        return item["zh"].startswith(text) and item["zh"] != text

    @staticmethod
    def _match_alias_startswith(item: dict, text: str) -> bool:
        return any(
            a.startswith(text) and a != text
            for a in item["aliases_zh"]
        )

    @staticmethod
    def _match_zh_contains(item: dict, text: str) -> bool:
        return text in item["zh"] and not item["zh"].startswith(text)

    @staticmethod
    def _match_alias_contains(item: dict, text: str) -> bool:
        return any(
            text in a and not a.startswith(text)
            for a in item["aliases_zh"]
        )
