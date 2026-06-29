"""P21.5 — RuleEditorAliasService: Rule Editor 中文 Alias 整合服務。

提供：
  resolve_filter_value(text, field_type) → 英文 filter 值字串
  tooltip_basetype(en_text)              → 中文 Tooltip 或 None
  tooltip_class(en_text)                 → 中文 Tooltip 或 None

設計原則：
  - 純 Python，無 Qt 依賴，可在無 GUI 環境測試。
  - 失敗時保留原輸入，不拋出例外。
  - BaseType 使用 AliasResolver.resolve_zh() 解析物品名稱。
  - Class 使用 categories.en_class 解析分類名稱。
"""

from __future__ import annotations

import json
import pathlib
import shlex
from typing import Optional

from core.alias_resolver import AliasResolver

_DATA_FILE = pathlib.Path(__file__).parent.parent / "data" / "bundled_aliases_zh_tw.json"


def _has_chinese(text: str) -> bool:
    """回傳 True 若 text 含任何 CJK 統一表意文字。"""
    return any("一" <= c <= "鿿" for c in text)


class RuleEditorAliasService:
    """Rule Editor 中文輸入 → 英文 Filter 值解析服務。

    BaseType: 透過 AliasResolver.resolve_zh() 解析物品名稱
    Class:    透過 categories.en_class 對應分類名稱

    失敗時保留原輸入，不拋出例外。
    """

    def __init__(
        self,
        resolver: AliasResolver | None = None,
        data_file: pathlib.Path = _DATA_FILE,
    ) -> None:
        self._resolver = resolver or AliasResolver()
        self._zh_to_classes: dict[str, list[str]] = {}   # zh/zh_short → [en_class, ...]
        self._class_to_zh: dict[str, str] = {}            # en_class → zh 顯示名稱
        self._load_category_map(data_file)

    # ------------------------------------------------------------------
    # 初始化 — categories 映射表
    # ------------------------------------------------------------------

    def _load_category_map(self, data_file: pathlib.Path) -> None:
        try:
            with data_file.open(encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            return

        for cat in db.get("categories", {}).values():
            zh       = cat.get("zh", "")
            zh_short = cat.get("zh_short", "")
            en_classes = [c for c in cat.get("en_class", []) if c]
            if not en_classes:
                continue
            if zh and zh not in self._zh_to_classes:
                self._zh_to_classes[zh] = en_classes
            if zh_short and zh_short != zh and zh_short not in self._zh_to_classes:
                self._zh_to_classes[zh_short] = en_classes
            for ec in en_classes:
                if ec not in self._class_to_zh:
                    self._class_to_zh[ec] = zh or zh_short

    # ------------------------------------------------------------------
    # 單一 token 解析
    # ------------------------------------------------------------------

    def resolve_basetype_token(self, token: str) -> str:
        """將單一 BaseType token 解析為英文物品名稱。

        先嘗試 AliasResolver；若無對應則回傳原 token。
        """
        if not token:
            return token
        results = self._resolver.resolve_zh(token)
        return results[0] if results else token

    def resolve_class_token(self, token: str) -> list[str]:
        """將單一 Class token 解析為英文 Class 名稱清單。

        中文分類名稱 → en_class 清單；
        已知英文 Class 名稱 → [token]；
        否則 → [token]（保留原輸入）。
        """
        if not token:
            return []
        en_classes = self._zh_to_classes.get(token)
        if en_classes:
            return list(en_classes)
        return [token]

    # ------------------------------------------------------------------
    # Filter 值解析（多 token）
    # ------------------------------------------------------------------

    def resolve_filter_value(self, text: str, field_type: str) -> str:
        """解析 Filter 欄位值（可能含中文）為英文格式。

        Args:
            text: 欄位文字（如 '混沌石' 或 '"Divine Orb"' 或 '通貨'）
            field_type: "BaseType" 或 "Class"

        Returns:
            英文 filter 值，以引號包覆並以空格分隔，例如 '"Divine Orb" "Chaos Orb"'。
            若無需解析或發生任何錯誤，回傳原輸入。
        """
        if not text or not text.strip():
            return text

        try:
            tokens = shlex.split(text)
        except ValueError:
            # 引號不匹配等情況：fallback 以空白分詞
            tokens = text.split()

        if not tokens:
            return text

        # ── Case A: 含中文 → 逐 token 解析並加引號
        if _has_chinese(text):
            try:
                if field_type == "BaseType":
                    resolved = [self.resolve_basetype_token(t) for t in tokens]
                elif field_type == "Class":
                    resolved = []
                    for t in tokens:
                        resolved.extend(self.resolve_class_token(t))
                else:
                    return text
                return " ".join(f'"{r}"' for r in resolved if r) if resolved else text
            except Exception:
                return text

        # ── Case B: 不含中文，有引號 → 重新正規化引號格式
        if '"' in text or "'" in text:
            return " ".join(f'"{t}"' for t in tokens if t)

        # ── Case C: 不含中文，無引號 → 嘗試以整體文字作為單一 alias 解析
        # 適用：短英文縮寫（"div", "chaos", "vaal"），避免多字英文名被錯誤分拆
        stripped = text.strip()
        if field_type == "BaseType":
            resolved_whole = self.resolve_basetype_token(stripped)
            if resolved_whole != stripped:
                return f'"{resolved_whole}"'
        # 無法解析 → 保留原輸入
        return text

    # ------------------------------------------------------------------
    # Tooltip 產生
    # ------------------------------------------------------------------

    def tooltip_basetype(self, en_text: str) -> Optional[str]:
        """為 BaseType 英文值產生中文 Tooltip。

        Input:  '"Divine Orb" "Chaos Orb"'
        Output: 'Divine Orb\\n(神聖石)\\n\\nChaos Orb\\n(混沌石)'
        """
        if not en_text or not en_text.strip():
            return None
        try:
            tokens = shlex.split(en_text)
        except ValueError:
            tokens = en_text.split()
        if not tokens:
            return None

        parts: list[str] = []
        for token in tokens:
            zh = self._resolver.reverse_resolve(token)
            parts.append(f"{token}\n({zh})" if zh else token)

        return "\n\n".join(parts) if parts else None

    def tooltip_class(self, en_text: str) -> Optional[str]:
        """為 Class 英文值產生中文 Tooltip。

        Input:  '"Stackable Currency" "Currency"'
        Output: 'Stackable Currency\\n(通貨)\\n\\nCurrency\\n(通貨)'
        """
        if not en_text or not en_text.strip():
            return None
        try:
            tokens = shlex.split(en_text)
        except ValueError:
            tokens = en_text.split()
        if not tokens:
            return None

        parts: list[str] = []
        for token in tokens:
            zh = self._class_to_zh.get(token)
            parts.append(f"{token}\n({zh})" if zh else token)

        return "\n\n".join(parts) if parts else None
