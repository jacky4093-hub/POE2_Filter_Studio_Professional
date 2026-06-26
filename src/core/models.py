from dataclasses import dataclass, field

BLOCK_HEADERS = ["Show", "Hide", "Continue", "Minimal"]

KNOWN_CONDITIONS = [
    "AreaLevel", "ItemLevel", "DropLevel", "Quality", "Rarity",
    "Class", "BaseType", "Sockets", "LinkedSockets", "SocketGroup",
    "StackSize", "WaystoneTier", "MapTier", "Corrupted", "Identified",
    "Mirrored", "ElderItem", "ShaperItem", "HasExplicitMod",
    "AnyEnchantment", "HasEnchantment", "FracturedItem", "SynthesisedItem",
    "BlightedMap", "UberBlightedMap", "GemLevel", "AlternateQuality",
    "Replica", "TransfiguredGem", "GemQualityType", "CorruptedMods",
    "HasImplicitMod", "HasSearingExarchImplicit", "HasEaterOfWorldsImplicit",
    "Scourged", "EnchantmentPassiveNum", "EnchantmentPassiveNode",
]

KNOWN_ACTIONS = [
    "SetTextColor", "SetBackgroundColor", "SetBorderColor", "SetFontSize",
    "PlayAlertSound", "PlayAlertSoundPositional", "CustomAlertSound",
    "CustomAlertSoundOptional", "DisableDropSound", "EnableDropSound",
    "DisableDropSoundIfAlertSound", "EnableDropSoundIfAlertSound",
    "MinimapIcon", "PlayEffect",
]


@dataclass
class FilterRule:
    action: str = "Show"
    inline_comment: str = ""
    pre_lines: list = field(default_factory=list)
    conditions: list = field(default_factory=list)   # list of [key, value]
    actions: list = field(default_factory=list)       # list of [key, value]
    unknown_lines: list = field(default_factory=list)
    enabled: bool = True
