from dataclasses import dataclass, field
from enum import Enum, auto


class FieldType(Enum):
    STRING      = auto()   # QLineEdit, free text (Class, BaseType, HasExplicitMod)
    ENUM        = auto()   # QComboBox with fixed choices (Rarity)
    BOOL        = auto()   # True / False combo (Corrupted, Identified, ...)
    INT_OP      = auto()   # operator + SpinBox  (AreaLevel >= 68)
    INT         = auto()   # plain SpinBox       (SetFontSize 18)
    COLOR       = auto()   # 4 × SpinBox + swatch (SetTextColor R G B A)
    SOUND_ID    = auto()   # SpinBox ID + SpinBox Volume (PlayAlertSound)
    CUSTOM_SND  = auto()   # LineEdit filename + SpinBox Volume (CustomAlertSound)
    MINIMAP     = auto()   # Size + Color + Shape combos (MinimapIcon)
    PLAY_EFFECT = auto()   # Color + optional Temp combos (PlayEffect)


# Sections used in the editor
SECTION_GENERAL    = "General"
SECTION_CONDITIONS = "Conditions"
SECTION_APPEARANCE = "Appearance"
SECTION_AUDIO      = "Audio"


OPERATORS     = [">=", "<=", "=", ">", "<", "!="]
RARITY_OPTIONS = ["Normal", "Magic", "Rare", "Unique"]
BOOL_OPTIONS   = ["True", "False"]

SOUND_COLORS  = ["Red", "Green", "Blue", "Brown", "White", "Yellow",
                 "Cyan", "Grey", "Orange", "Pink", "Purple"]
BEAM_SHAPES   = ["Circle", "Diamond", "Hexagon", "Square", "Star", "Triangle"]
MINIMAP_SIZES = ["0", "1", "2"]
EFFECT_COLORS = ["Red", "Green", "Blue", "Brown", "White", "Yellow",
                 "Cyan", "Grey", "Orange", "Pink", "Purple"]


@dataclass
class FieldDef:
    # --- core (required) ---
    key:          str
    display_name: str
    field_type:   FieldType
    section:      str
    # --- numeric range ---
    min_val:      int  = 0
    max_val:      int  = 100
    # --- enum / bool choices ---
    options:      list = field(default_factory=list)
    # --- documentation ---
    description:  str  = ""
    tooltip:      str  = ""       # hover text shown in the editor
    placeholder:  str  = ""       # hint text for text-input widgets
    category:     str  = ""       # reserved: sub-group within a section
    # --- metadata (reserved for future use) ---
    icon:         str  = ""       # reserved: icon name / resource path
    experimental: bool = False    # reserved: mark as experimental / beta
    deprecated:   bool = False    # reserved: mark as deprecated


# ---------------------------------------------------------------------------
# Condition schema
# ---------------------------------------------------------------------------

CONDITION_SCHEMA: dict[str, FieldDef] = {
    "AreaLevel": FieldDef(
        "AreaLevel", "區域等級", FieldType.INT_OP, SECTION_CONDITIONS, 1, 100,
        tooltip="地圖或關卡的等級，通常 1–100",
    ),
    "ItemLevel": FieldDef(
        "ItemLevel", "物品等級", FieldType.INT_OP, SECTION_CONDITIONS, 0, 100,
        tooltip="物品掉落時的等級，影響詞綴池",
    ),
    "DropLevel": FieldDef(
        "DropLevel", "掉落等級", FieldType.INT_OP, SECTION_CONDITIONS, 0, 100,
    ),
    "Quality": FieldDef(
        "Quality", "品質", FieldType.INT_OP, SECTION_CONDITIONS, 0, 30,
        tooltip="物品品質百分比，0–30",
    ),
    "Rarity": FieldDef(
        "Rarity", "稀有度", FieldType.ENUM, SECTION_CONDITIONS,
        options=RARITY_OPTIONS,
        tooltip="Normal / Magic / Rare / Unique",
    ),
    "Class": FieldDef(
        "Class", "物品類別", FieldType.STRING, SECTION_CONDITIONS,
        placeholder='"Currency" "Gems"',
        tooltip='以空格分隔多個類別名稱，每個名稱加引號',
    ),
    "BaseType": FieldDef(
        "BaseType", "物品基底", FieldType.STRING, SECTION_CONDITIONS,
        placeholder='"Divine Orb" "Chaos Orb"',
        tooltip='以空格分隔多個基底名稱，每個名稱加引號',
    ),
    "Sockets":      FieldDef("Sockets",      "插槽數",     FieldType.INT_OP,  SECTION_CONDITIONS, 0, 6),
    "LinkedSockets":FieldDef("LinkedSockets","連結插槽",   FieldType.INT_OP,  SECTION_CONDITIONS, 0, 6),
    "SocketGroup":  FieldDef("SocketGroup",  "插槽顏色組", FieldType.STRING,  SECTION_CONDITIONS,
                             placeholder="RRGB",
                             tooltip="以顏色字母組合表示插槽，R=紅 G=綠 B=藍 W=白"),
    "StackSize":    FieldDef("StackSize",    "堆疊數量",   FieldType.INT_OP,  SECTION_CONDITIONS, 0, 9999),
    "WaystoneTier": FieldDef("WaystoneTier", "路標階層",   FieldType.INT_OP,  SECTION_CONDITIONS, 1, 16),
    "MapTier":      FieldDef("MapTier",      "地圖階層",   FieldType.INT_OP,  SECTION_CONDITIONS, 1, 17),
    "Corrupted":    FieldDef("Corrupted",    "腐化",       FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "Identified":   FieldDef("Identified",   "已鑑定",     FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "Mirrored":     FieldDef("Mirrored",     "映像",       FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "ElderItem":    FieldDef("ElderItem",    "長老物品",   FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "ShaperItem":   FieldDef("ShaperItem",   "塑者物品",   FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "FracturedItem":FieldDef("FracturedItem","裂變物品",   FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "SynthesisedItem":FieldDef("SynthesisedItem","合成物品",FieldType.BOOL,   SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "Scourged":     FieldDef("Scourged",     "腐化烙印",   FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "BlightedMap":  FieldDef("BlightedMap",  "枯萎地圖",   FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "UberBlightedMap":FieldDef("UberBlightedMap","超級枯萎地圖",FieldType.BOOL,SECTION_CONDITIONS,options=BOOL_OPTIONS),
    "AnyEnchantment":FieldDef("AnyEnchantment","任意附魔", FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "HasEnchantment":FieldDef("HasEnchantment","指定附魔", FieldType.STRING,  SECTION_CONDITIONS,
                              placeholder='"Enkindling Orb"'),
    "HasExplicitMod":FieldDef("HasExplicitMod","指定詞綴", FieldType.STRING,  SECTION_CONDITIONS,
                              placeholder='"AddedFireDamage"',
                              tooltip="詞綴的內部 ID，以空格分隔多個"),
    "HasImplicitMod":FieldDef("HasImplicitMod","隱式詞綴", FieldType.STRING,  SECTION_CONDITIONS),
    "GemLevel":     FieldDef("GemLevel",     "寶石等級",   FieldType.INT_OP,  SECTION_CONDITIONS, 1, 21),
    "AlternateQuality":FieldDef("AlternateQuality","替代品質",FieldType.BOOL, SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "Replica":      FieldDef("Replica",      "複製品",     FieldType.BOOL,    SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "TransfiguredGem":FieldDef("TransfiguredGem","變形寶石",FieldType.BOOL,   SECTION_CONDITIONS, options=BOOL_OPTIONS),
    "GemQualityType":FieldDef("GemQualityType","寶石品質類型",FieldType.STRING,SECTION_CONDITIONS),
    "CorruptedMods":FieldDef("CorruptedMods","腐化詞綴數", FieldType.INT_OP,  SECTION_CONDITIONS, 0, 10),
    "HasSearingExarchImplicit":FieldDef("HasSearingExarchImplicit","灼熱督軍隱式",FieldType.INT_OP,SECTION_CONDITIONS,0,6),
    "HasEaterOfWorldsImplicit":FieldDef("HasEaterOfWorldsImplicit","噬界者隱式",FieldType.INT_OP,SECTION_CONDITIONS,0,6),
    "EnchantmentPassiveNum":FieldDef("EnchantmentPassiveNum","附魔被動數",FieldType.INT_OP,SECTION_CONDITIONS,0,10),
    "EnchantmentPassiveNode":FieldDef("EnchantmentPassiveNode","附魔被動節點",FieldType.STRING,SECTION_CONDITIONS),
}


# ---------------------------------------------------------------------------
# Action schema
# ---------------------------------------------------------------------------

ACTION_SCHEMA: dict[str, FieldDef] = {
    "SetTextColor": FieldDef(
        "SetTextColor", "文字顏色", FieldType.COLOR, SECTION_APPEARANCE,
        tooltip="物品名稱文字的 RGBA 顏色，每個分量 0–255",
    ),
    "SetBackgroundColor": FieldDef(
        "SetBackgroundColor", "背景顏色", FieldType.COLOR, SECTION_APPEARANCE,
        tooltip="物品標籤背景的 RGBA 顏色",
    ),
    "SetBorderColor": FieldDef(
        "SetBorderColor", "邊框顏色", FieldType.COLOR, SECTION_APPEARANCE,
        tooltip="物品標籤邊框的 RGBA 顏色",
    ),
    "SetFontSize": FieldDef(
        "SetFontSize", "字體大小", FieldType.INT, SECTION_APPEARANCE, 1, 45,
        tooltip="物品名稱文字大小，1–45（預設 32）",
    ),
    "MinimapIcon":  FieldDef("MinimapIcon",  "小地圖圖示", FieldType.MINIMAP,    SECTION_APPEARANCE,
                             tooltip="在小地圖上顯示的圖示：大小 / 顏色 / 形狀"),
    "PlayEffect":   FieldDef("PlayEffect",   "光柱效果",   FieldType.PLAY_EFFECT, SECTION_APPEARANCE,
                             tooltip="物品掉落時的光柱顏色，加 Temp 表示僅在滑鼠懸停前顯示"),
    "PlayAlertSound": FieldDef(
        "PlayAlertSound", "警報音效", FieldType.SOUND_ID, SECTION_AUDIO, 0, 16,
        tooltip="內建音效 ID (1–16) 與音量 (0–300)",
    ),
    "PlayAlertSoundPositional": FieldDef(
        "PlayAlertSoundPositional", "定位音效", FieldType.SOUND_ID, SECTION_AUDIO, 0, 16,
        tooltip="根據物品位置播放方向音效",
    ),
    "CustomAlertSound": FieldDef(
        "CustomAlertSound", "自訂音效", FieldType.CUSTOM_SND, SECTION_AUDIO,
        placeholder='"alert.mp3"',
        tooltip='自訂音效檔案路徑（相對於 POE2 目錄）與音量',
    ),
    "CustomAlertSoundOptional": FieldDef(
        "CustomAlertSoundOptional", "自訂音效(可選)", FieldType.CUSTOM_SND, SECTION_AUDIO,
        placeholder='"alert.mp3"',
    ),
    "DisableDropSound":  FieldDef("DisableDropSound",  "停用掉落音", FieldType.BOOL, SECTION_AUDIO,
                                  options=BOOL_OPTIONS),
    "EnableDropSound":   FieldDef("EnableDropSound",   "啟用掉落音", FieldType.BOOL, SECTION_AUDIO,
                                  options=BOOL_OPTIONS),
    "DisableDropSoundIfAlertSound": FieldDef("DisableDropSoundIfAlertSound",
                                             "警報時停用掉落音", FieldType.BOOL, SECTION_AUDIO,
                                             options=BOOL_OPTIONS),
    "EnableDropSoundIfAlertSound":  FieldDef("EnableDropSoundIfAlertSound",
                                             "警報時啟用掉落音", FieldType.BOOL, SECTION_AUDIO,
                                             options=BOOL_OPTIONS),
}


def get_field_def(key: str) -> FieldDef | None:
    """Return the FieldDef for *key*, searching both schemas. None if unknown."""
    return CONDITION_SCHEMA.get(key) or ACTION_SCHEMA.get(key)
