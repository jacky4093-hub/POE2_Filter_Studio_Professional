"""P24.1 — RuleTemplate 系統：快速規則模板核心模組。

提供：
  RuleTemplate            — 模板資料類別
  get_templates()         — 取得所有模板清單（深拷貝）
  get_template(id)        — 依 id 取得單一模板（深拷貝），不存在回傳 None
  create_rule_from_template(id) — 建立可被 Rule Editor 使用的 FilterRule

條件 / 動作格式與 FilterRule 完全相容：
  conditions: list of [key, raw_value]  例如 ["Rarity", ">= Unique"]
  actions:    list of [key, raw_value]  例如 ["SetFontSize", "45"]
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from core.models import FilterRule


# ---------------------------------------------------------------------------
# 資料類別
# ---------------------------------------------------------------------------

@dataclass
class RuleTemplate:
    """單一規則模板的靜態描述。

    Attributes
    ----------
    id              唯一識別碼（英文，小寫底線）
    name            使用者可見的中文名稱
    description     說明文字
    rule_class      若設定，將生成 Class "<rule_class>" 條件
    conditions      額外條件清單（FilterRule.conditions 格式：[[key, value], …]）
    text_color      SetTextColor 值（如 "255 200 0 255"）
    background_color SetBackgroundColor 值
    border_color    SetBorderColor 值
    font_size       SetFontSize 值（int）
    play_alert_sound 若 True，輸出 PlayAlertSound 1 300
    """
    id:               str
    name:             str
    description:      str
    rule_class:       str | None        = None
    conditions:       list              = field(default_factory=list)
    text_color:       str | None        = None
    background_color: str | None        = None
    border_color:     str | None        = None
    font_size:        int | None        = None
    play_alert_sound: bool              = False


# ---------------------------------------------------------------------------
# 內建模板清單
# ---------------------------------------------------------------------------

_TEMPLATES: list[RuleTemplate] = [
    RuleTemplate(
        id="high_value_currency",
        name="高價貨幣",
        description="高價貨幣顯示規則：放大字體並加上金色邊框。",
        rule_class="Currency",
        font_size=45,
        border_color="212 175 55 255",
    ),
    RuleTemplate(
        id="unique_item",
        name="傳奇物品",
        description="稀有度為傳奇（Unique）的物品，放大字體顯示。",
        conditions=[["Rarity", ">= Unique"]],
        font_size=42,
    ),
    RuleTemplate(
        id="rare_equipment",
        name="稀有裝備",
        description="稀有度為稀有（Rare）的物品。",
        conditions=[["Rarity", ">= Rare"]],
    ),
    RuleTemplate(
        id="high_tier_waystone",
        name="高階地圖",
        description="高等級傳送石（AreaLevel >= 75）。",
        rule_class="Waystones",
        conditions=[["AreaLevel", ">= 75"]],
    ),
    RuleTemplate(
        id="high_quality_gem",
        name="高品質技能石",
        description="品質 20% 以上的技能石。",
        conditions=[["Quality", ">= 20"]],
    ),
    RuleTemplate(
        id="empty_rule",
        name="空白規則",
        description="不帶任何條件或動作的空白規則，供自訂使用。",
    ),
]

# 快速查詢索引（id → template）
_TEMPLATE_MAP: dict[str, RuleTemplate] = {t.id: t for t in _TEMPLATES}


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def get_templates() -> list[RuleTemplate]:
    """回傳所有模板的深拷貝清單；修改回傳值不影響內部資料。"""
    return [copy.deepcopy(t) for t in _TEMPLATES]


def get_template(template_id: str) -> RuleTemplate | None:
    """根據 id 取得模板深拷貝；找不到回傳 None。"""
    tmpl = _TEMPLATE_MAP.get(template_id)
    return copy.deepcopy(tmpl) if tmpl is not None else None


def create_rule_from_template(template_id: str) -> FilterRule | None:
    """從模板建立 FilterRule。

    條件 / 動作的 raw_value 格式直接相容 filter_parser / filter_exporter。
    template_id 不存在時回傳 None。

    生成順序
    ---------
    conditions:  [Class] → [額外條件]
    actions:     SetTextColor → SetBackgroundColor → SetBorderColor
                 → SetFontSize → PlayAlertSound
    """
    tmpl = get_template(template_id)
    if tmpl is None:
        return None

    rule = FilterRule()
    rule.action = "Show"
    rule.enabled = True

    # 條件：Class 優先，再接模板的額外條件
    if tmpl.rule_class:
        rule.conditions.append(["Class", f'"{tmpl.rule_class}"'])
    rule.conditions.extend(copy.deepcopy(tmpl.conditions))

    # 動作：依欄位是否有值逐一加入
    if tmpl.text_color:
        rule.actions.append(["SetTextColor", tmpl.text_color])
    if tmpl.background_color:
        rule.actions.append(["SetBackgroundColor", tmpl.background_color])
    if tmpl.border_color:
        rule.actions.append(["SetBorderColor", tmpl.border_color])
    if tmpl.font_size is not None:
        rule.actions.append(["SetFontSize", str(tmpl.font_size)])
    if tmpl.play_alert_sound:
        rule.actions.append(["PlayAlertSound", "1 300"])

    return rule
