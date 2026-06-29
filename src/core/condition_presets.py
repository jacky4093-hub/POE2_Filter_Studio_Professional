"""P22.3 — ConditionPresetService: 條件預設模板服務（純 Python，無 Qt 依賴）。

提供常用條件組合模板，使用者可一鍵套用至 ConditionBuilderWidget。

資料流：
    ConditionPresetService.preset_to_conditions(key)
    → list[list[str]]  (rule.conditions 相容格式)
    → ConditionBuilderWidget.set_conditions()
    → conditions_changed Signal
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.condition_builder import ConditionBuilderService, ConditionValue


# ---------------------------------------------------------------------------
# 資料類別
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PresetDefinition:
    """單一 Preset 的靜態描述（不可變）。"""
    key:        str
    label:      str            # 介面顯示用中文標籤
    conditions: tuple          # ((cond_key, raw_value), ...) 元組


# ---------------------------------------------------------------------------
# 服務
# ---------------------------------------------------------------------------

class ConditionPresetService:
    """條件預設模板查詢與轉換服務。

    PRESETS 內所有 key / raw_value 皆以 ConditionBuilderService.CONDITION_DEFS
    相容格式定義，可直接傳入 ConditionBuilderWidget.set_conditions()。
    """

    PRESETS: dict[str, PresetDefinition] = {
        "high_value_currency": PresetDefinition(
            key="high_value_currency",
            label="高價值通貨",
            conditions=(
                ("Class", '"Currency"'),
            ),
        ),
        "high_quality_gem": PresetDefinition(
            key="high_quality_gem",
            label="高品質寶石",
            conditions=(
                ("Class",    '"Skill Gem"'),
                ("Quality",  ">= 20"),
            ),
        ),
        "six_link": PresetDefinition(
            key="six_link",
            label="六連接物品",
            conditions=(
                ("LinkedSockets", ">= 6"),
            ),
        ),
        "endgame_rare": PresetDefinition(
            key="endgame_rare",
            label="後期稀有裝備",
            conditions=(
                ("Rarity",    ">= Rare"),
                ("ItemLevel", ">= 82"),
            ),
        ),
        "high_tier_waystone": PresetDefinition(
            key="high_tier_waystone",
            label="高階傳送石",
            conditions=(
                ("Class",      '"Waystone"'),
                ("AreaLevel",  ">= 79"),
            ),
        ),
        "empty": PresetDefinition(
            key="empty",
            label="空模板",
            conditions=(),
        ),
    }

    def __init__(self) -> None:
        self._svc = ConditionBuilderService()

    # ------------------------------------------------------------------
    # 查詢
    # ------------------------------------------------------------------

    def available_presets(self) -> list[PresetDefinition]:
        """回傳所有 Preset 定義（依定義順序）。"""
        return list(self.PRESETS.values())

    def get_preset(self, key: str) -> Optional[PresetDefinition]:
        """回傳指定 key 的 PresetDefinition；key 不存在時回傳 None。"""
        return self.PRESETS.get(key)

    # ------------------------------------------------------------------
    # 轉換
    # ------------------------------------------------------------------

    def preset_to_conditions(self, key: str) -> list:
        """將 preset key 轉換為 rule.conditions 相容格式清單。

        回傳 [[cond_key, raw_value], ...] 或 []（key 不存在 / empty preset）。
        """
        preset = self.PRESETS.get(key)
        if preset is None:
            return []
        return [[ck, rv] for ck, rv in preset.conditions]

    def preset_to_condition_values(self, key: str) -> list[ConditionValue]:
        """將 preset key 轉換為 ConditionValue 清單（widget row 格式）。"""
        conditions = self.preset_to_conditions(key)
        return self._svc.load_from_rule(conditions)
