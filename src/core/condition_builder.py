"""P22 — ConditionBuilderService: 條件建立器核心邏輯（純 Python，無 Qt 依賴）。

提供：
  ConditionDef        — 單一條件類型的靜態描述（key、標籤、欄位類型、範圍）
  ConditionValue      — 單一條件的執行期狀態（key、op、value）
  ConditionBuilderService — 解析、驗證、序列化、與 rule.conditions 整合

設計原則：
  - 純 Python，可在無 GUI 環境下測試。
  - 失敗時不拋例外，回傳保守結果。
  - save_to_rule 只修改 CONDITION_DEFS 中已知的 key；未知 key 原樣保留。
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# 資料類別
# ---------------------------------------------------------------------------

class FieldType(Enum):
    ENUM    = auto()   # 固定選項（Rarity）
    NUMERIC = auto()   # 數值 + 比較運算子（ItemLevel、Quality …）
    STRING  = auto()   # 引號字串（Class、BaseType）


@dataclass(frozen=True)
class ConditionDef:
    """單一條件類型的靜態定義（不可變）。"""
    key:        str
    label:      str         # 介面顯示用中文標籤
    field_type: FieldType
    min_val:    int   = 0
    max_val:    int   = 9_999
    choices:    tuple = ()   # ENUM 時的合法英文值
    default_op: str   = ">="


@dataclass
class ConditionValue:
    """單一條件的執行期狀態。"""
    key:   str
    op:    str = ">="
    value: str = ""

    def is_empty(self) -> bool:
        return not self.value.strip()


# ---------------------------------------------------------------------------
# 服務
# ---------------------------------------------------------------------------

class ConditionBuilderService:
    """Condition 解析、驗證、序列化及 rule.conditions 整合服務。

    支援的條件（P22 第一階段）：
      Rarity, ItemLevel, AreaLevel, Quality,
      Sockets, LinkedSockets, StackSize, Class, BaseType
    """

    NUMERIC_OPS = [">=", "<=", "=", ">", "<"]

    CONDITION_DEFS: dict[str, ConditionDef] = {
        "Rarity":        ConditionDef(
            "Rarity",        "稀有度",   FieldType.ENUM,
            choices=("Normal", "Magic", "Rare", "Unique"),
            default_op=">="
        ),
        "ItemLevel":     ConditionDef("ItemLevel",     "物品等級", FieldType.NUMERIC, min_val=0, max_val=100,  default_op=">="),
        "AreaLevel":     ConditionDef("AreaLevel",     "區域等級", FieldType.NUMERIC, min_val=0, max_val=100,  default_op=">="),
        "Quality":       ConditionDef("Quality",       "品質",     FieldType.NUMERIC, min_val=0, max_val=20,   default_op=">="),
        "Sockets":       ConditionDef("Sockets",       "插槽",     FieldType.NUMERIC, min_val=0, max_val=6,    default_op=">="),
        "LinkedSockets": ConditionDef("LinkedSockets", "連結插槽", FieldType.NUMERIC, min_val=0, max_val=6,    default_op=">="),
        "StackSize":     ConditionDef("StackSize",     "堆疊數量", FieldType.NUMERIC, min_val=0, max_val=5000, default_op=">="),
        "Class":         ConditionDef("Class",         "類別",     FieldType.STRING,  default_op=""),
        "BaseType":      ConditionDef("BaseType",      "基底類型", FieldType.STRING,  default_op=""),
    }

    # ------------------------------------------------------------------
    # 查詢
    # ------------------------------------------------------------------

    def get_def(self, key: str) -> Optional[ConditionDef]:
        return self.CONDITION_DEFS.get(key)

    def available_keys(self) -> list[str]:
        return list(self.CONDITION_DEFS.keys())

    # ------------------------------------------------------------------
    # 解析
    # ------------------------------------------------------------------

    def parse_raw(self, key: str, raw_value: str) -> ConditionValue:
        """Parse 原始 filter 條件值字串為 ConditionValue。

        支援：
          ">= 70"   → op=">=", value="70"
          "Rare"    → op=default_op, value="Rare"
          ">= Rare" → op=">=", value="Rare"
          '"Currency"' → op="", value='"Currency"'（STRING 型別）
        """
        raw = (raw_value or "").strip()
        cdef = self.CONDITION_DEFS.get(key)

        if not cdef:
            return ConditionValue(key=key, op="=", value=raw)

        if cdef.field_type == FieldType.STRING:
            return ConditionValue(key=key, op="", value=raw)

        for op in self.NUMERIC_OPS:
            if raw.startswith(op):
                val = raw[len(op):].strip()
                return ConditionValue(key=key, op=op, value=val)

        # 無運算子前綴 → 使用預設 op
        return ConditionValue(key=key, op=cdef.default_op or ">=", value=raw)

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def serialize(self, cv: ConditionValue) -> str:
        """將 ConditionValue 序列化為 filter 條件值字串。

        空值回傳 ""（表示該條件不輸出）。
        """
        if cv.is_empty():
            return ""
        cdef = self.CONDITION_DEFS.get(cv.key)
        if cdef and cdef.field_type == FieldType.STRING:
            return cv.value
        if cv.op:
            return f"{cv.op} {cv.value}"
        return cv.value

    # ------------------------------------------------------------------
    # 驗證
    # ------------------------------------------------------------------

    def validate(self, cv: ConditionValue) -> bool:
        """回傳 True 若 ConditionValue 的內容合法。"""
        if cv.is_empty():
            return False
        cdef = self.CONDITION_DEFS.get(cv.key)
        if cdef is None:
            return True   # 未知 key：放行

        if cdef.field_type == FieldType.ENUM:
            return (cv.value in cdef.choices
                    and cv.op in (">=", "<=", "="))

        if cdef.field_type == FieldType.NUMERIC:
            try:
                v = int(cv.value)
                return (cdef.min_val <= v <= cdef.max_val
                        and cv.op in self.NUMERIC_OPS)
            except (ValueError, TypeError):
                return False

        # STRING: 任何非空值皆合法
        return bool(cv.value.strip())

    # ------------------------------------------------------------------
    # rule.conditions 整合
    # ------------------------------------------------------------------

    def load_from_rule(self, conditions: list) -> list[ConditionValue]:
        """從 rule.conditions 提取 ConditionValue（只含 CONDITION_DEFS 中的 key）。"""
        result: list[ConditionValue] = []
        for item in conditions:
            if len(item) >= 2:
                key = str(item[0])
                if key in self.CONDITION_DEFS:
                    cv = self.parse_raw(key, str(item[1]))
                    if not cv.is_empty():
                        result.append(cv)
        return result

    def save_to_rule(
        self, cvs: list[ConditionValue], existing: list
    ) -> list:
        """合併新 ConditionValues 與現有 conditions 清單。

        規則：
          - key 在 CONDITION_DEFS 且在 cvs → 更新為新值
          - key 在 CONDITION_DEFS 但不在 cvs → 從輸出中移除（使用者刪除）
          - key 不在 CONDITION_DEFS → 原樣保留（未知條件不觸碰）
        """
        cv_map = {cv.key: cv for cv in cvs}
        result:       list      = []
        seen_managed: set[str]  = set()

        for item in existing:
            if len(item) < 2:
                result.append(item)
                continue
            key = str(item[0])
            if key in self.CONDITION_DEFS:
                if key not in seen_managed:
                    seen_managed.add(key)
                    if key in cv_map:
                        serialized = self.serialize(cv_map[key])
                        if serialized:
                            result.append([key, serialized])
                    # key 在 CONDITION_DEFS 但不在 cv_map → 略過（移除）
            else:
                result.append(item)   # 未知 key：原樣保留

        # 追加 cvs 中不存在於 existing 的新條件
        for cv in cvs:
            if cv.key not in seen_managed:
                serialized = self.serialize(cv)
                if serialized:
                    result.append([cv.key, serialized])
                    seen_managed.add(cv.key)

        return result
