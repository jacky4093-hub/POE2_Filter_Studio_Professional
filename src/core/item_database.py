"""P23.1 — ItemDatabase: Item Selector Wizard 資料層。

提供 POE2 物品的分類瀏覽與搜尋功能，整合 P21 AliasResolver 的中文別名系統。

資料架構：
    ItemDefinition — 單一物品描述（dataclass）
    ItemDatabase   — 分類查詢 + 中英文搜尋服務

搜尋策略：
    1. name_en 英文包含匹配（大小寫不敏感）
    2. name_zh / tags 中文包含匹配
    3. AliasResolver.resolve_zh() 中文別名 → 英文名稱 → 物品匹配
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Optional

from core.alias_resolver import AliasResolver

_DATA_FILE = pathlib.Path(__file__).parent.parent / "data" / "bundled_aliases_zh_tw.json"

_CATEGORY_ORDER = ["Weapons", "Armour", "Jewellery", "Currency", "Waystones", "Tablets"]

# alias DB category → (ItemDatabase.category, ItemDatabase.subcategory)
_ALIAS_CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "currency":  ("Currency",  "基本通貨"),
    "distilled": ("Currency",  "淬鍊精華"),
    "essence":   ("Currency",  "精華"),
    "rune":      ("Currency",  "符文"),
    "catalyst":  ("Currency",  "催化劑"),
    "waystone":  ("Waystones", "傳送石"),
    "tablet":    ("Tablets",   "石板"),
}

# (id, name_en, name_zh, category, subcategory, tags)
_STATIC: list[tuple[str, str, str, str, str, list[str]]] = [
    # ── Weapons: 單手劍 ─────────────────────────────────────────────────────
    ("w-rusted-sword",      "Rusted Sword",          "鏽劍",         "Weapons", "單手劍", ["劍", "單手"]),
    ("w-sabre",             "Sabre",                 "彎刀",         "Weapons", "單手劍", ["劍", "單手"]),
    ("w-broad-sword",       "Broad Sword",           "闊劍",         "Weapons", "單手劍", ["劍", "單手"]),
    ("w-war-sword",         "War Sword",             "戰劍",         "Weapons", "單手劍", ["劍", "單手"]),
    ("w-ancient-sword",     "Ancient Sword",         "古代劍",       "Weapons", "單手劍", ["劍", "單手"]),
    ("w-elegant-sword",     "Elegant Sword",         "優雅劍",       "Weapons", "單手劍", ["劍", "單手"]),
    ("w-jewelled-foil",     "Jewelled Foil",         "寶石佩劍",     "Weapons", "單手劍", ["劍", "單手", "刺客"]),
    ("w-variscite-blade",   "Variscite Blade",       "磷灰石刃",     "Weapons", "單手劍", ["劍", "單手"]),
    # ── Weapons: 雙手劍 ─────────────────────────────────────────────────────
    ("w-corroded-blade",    "Corroded Blade",        "腐蝕刃",       "Weapons", "雙手劍", ["劍", "雙手"]),
    ("w-longsword",         "Longsword",             "長劍",         "Weapons", "雙手劍", ["劍", "雙手"]),
    ("w-bastard-sword",     "Bastard Sword",         "雜種劍",       "Weapons", "雙手劍", ["劍", "雙手"]),
    ("w-claymore",          "Claymore",              "大劍",         "Weapons", "雙手劍", ["劍", "雙手"]),
    ("w-highland-blade",    "Highland Blade",        "高地刃",       "Weapons", "雙手劍", ["劍", "雙手"]),
    # ── Weapons: 弓 ──────────────────────────────────────────────────────────
    ("w-crude-bow",         "Crude Bow",             "粗製弓",       "Weapons", "弓",     ["弓", "遠程"]),
    ("w-short-bow",         "Short Bow",             "短弓",         "Weapons", "弓",     ["弓", "遠程"]),
    ("w-long-bow",          "Long Bow",              "長弓",         "Weapons", "弓",     ["弓", "遠程"]),
    ("w-composite-bow",     "Composite Bow",         "合成弓",       "Weapons", "弓",     ["弓", "遠程"]),
    ("w-recurve-bow",       "Recurve Bow",           "反曲弓",       "Weapons", "弓",     ["弓", "遠程"]),
    # ── Weapons: 爪 ──────────────────────────────────────────────────────────
    ("w-glass-shank",       "Glass Shank",           "玻璃刃",       "Weapons", "爪",     ["爪", "敏捷"]),
    ("w-twin-prongs",       "Twin Prongs",           "雙叉爪",       "Weapons", "爪",     ["爪", "敏捷"]),
    ("w-gouger",            "Gouger",                "挖鑿爪",       "Weapons", "爪",     ["爪", "敏捷"]),
    ("w-fright-claw",       "Fright Claw",           "恐懼爪",       "Weapons", "爪",     ["爪", "敏捷"]),
    # ── Weapons: 魔棒 ────────────────────────────────────────────────────────
    ("w-driftwood-wand",    "Driftwood Wand",        "浮木魔棒",     "Weapons", "魔棒",   ["魔棒", "法術"]),
    ("w-quartz-wand",       "Quartz Wand",           "石英魔棒",     "Weapons", "魔棒",   ["魔棒", "法術"]),
    ("w-bone-wand",         "Bone Wand",             "骨質魔棒",     "Weapons", "魔棒",   ["魔棒", "法術"]),
    # ── Weapons: 法杖 ────────────────────────────────────────────────────────
    ("w-gnarled-branch",    "Gnarled Branch",        "扭曲枝幹",     "Weapons", "法杖",   ["法杖", "雙手"]),
    ("w-long-staff",        "Long Staff",            "長法杖",       "Weapons", "法杖",   ["法杖", "雙手"]),
    ("w-iron-staff",        "Iron Staff",            "鐵法杖",       "Weapons", "法杖",   ["法杖", "雙手"]),
    # ── Weapons: 杖 (Sceptre) ────────────────────────────────────────────────
    ("w-driftwood-sceptre", "Driftwood Sceptre",     "浮木杖",       "Weapons", "杖",     ["杖", "法術"]),
    ("w-painted-sceptre",   "Painted Sceptre",       "彩繪杖",       "Weapons", "杖",     ["杖", "法術"]),
    # ── Weapons: 斧 ──────────────────────────────────────────────────────────
    ("w-rusted-hatchet",    "Rusted Hatchet",        "鏽斧",         "Weapons", "斧",     ["斧", "力量"]),
    ("w-jade-hatchet",      "Jade Hatchet",          "翡翠斧",       "Weapons", "斧",     ["斧", "敏捷"]),
    ("w-broad-axe",         "Broad Axe",             "闊斧",         "Weapons", "斧",     ["斧", "雙手", "力量"]),
    # ── Weapons: 錘 ──────────────────────────────────────────────────────────
    ("w-driftwood-club",    "Driftwood Club",        "浮木棍棒",     "Weapons", "錘",     ["錘", "棍棒", "力量"]),
    ("w-stone-hammer",      "Stone Hammer",          "石錘",         "Weapons", "錘",     ["錘", "力量"]),
    # ── Weapons: 矛 ──────────────────────────────────────────────────────────
    ("w-crude-spear",       "Crude Spear",           "粗製矛",       "Weapons", "矛",     ["矛", "敏捷"]),
    ("w-iron-spear",        "Iron Spear",            "鐵矛",         "Weapons", "矛",     ["矛", "敏捷"]),
    # ── Weapons: 連枷 ────────────────────────────────────────────────────────
    ("w-iron-flail",        "Iron Flail",            "鐵連枷",       "Weapons", "連枷",   ["連枷", "力量"]),
    ("w-bronze-flail",      "Bronze Flail",          "青銅連枷",     "Weapons", "連枷",   ["連枷", "力量"]),
    # ── Armour: 胸甲 ────────────────────────────────────────────────────────
    ("a-plate-vest",        "Plate Vest",            "鐵板背心",     "Armour",  "胸甲",   ["力量", "護甲"]),
    ("a-shabby-jerkin",     "Shabby Jerkin",         "破舊皮夾克",   "Armour",  "胸甲",   ["敏捷", "逃避"]),
    ("a-simple-robe",       "Simple Robe",           "簡單長袍",     "Armour",  "胸甲",   ["智慧", "能量護盾"]),
    ("a-scale-vest",        "Scale Vest",            "鱗甲背心",     "Armour",  "胸甲",   ["力量", "敏捷"]),
    ("a-chainmail-vest",    "Chainmail Vest",        "鎖甲背心",     "Armour",  "胸甲",   ["力量", "智慧"]),
    ("a-ornate-ringmail",   "Ornate Ringmail",       "華麗環甲",     "Armour",  "胸甲",   ["敏捷", "智慧"]),
    ("a-occultist-vest",    "Occultist's Vestment",  "秘術師長袍",   "Armour",  "胸甲",   ["智慧"]),
    # ── Armour: 頭盔 ────────────────────────────────────────────────────────
    ("a-plate-helm",        "Plate Helm",            "鐵板頭盔",     "Armour",  "頭盔",   ["力量"]),
    ("a-leather-cap",       "Leather Cap",           "皮革帽",       "Armour",  "頭盔",   ["敏捷"]),
    ("a-vine-circlet",      "Vine Circlet",          "藤蔓頭環",     "Armour",  "頭盔",   ["智慧"]),
    ("a-battered-helm",     "Battered Helm",         "破損頭盔",     "Armour",  "頭盔",   ["力量"]),
    ("a-sallet",            "Sallet",                "輕型頭盔",     "Armour",  "頭盔",   ["敏捷"]),
    ("a-velvet-cap",        "Velvet Cap",            "天鵝絨帽",     "Armour",  "頭盔",   ["智慧"]),
    # ── Armour: 手套 ────────────────────────────────────────────────────────
    ("a-iron-gauntlets",    "Iron Gauntlets",        "鐵手套",       "Armour",  "手套",   ["力量"]),
    ("a-rawhide-gloves",    "Rawhide Gloves",        "生皮手套",     "Armour",  "手套",   ["敏捷"]),
    ("a-wool-gloves",       "Wool Gloves",           "羊毛手套",     "Armour",  "手套",   ["智慧"]),
    ("a-chain-gloves",      "Chain Gloves",          "鎖甲手套",     "Armour",  "手套",   ["力量", "智慧"]),
    ("a-mesh-gloves",       "Mesh Gloves",           "網格手套",     "Armour",  "手套",   ["敏捷", "智慧"]),
    # ── Armour: 鞋子 ────────────────────────────────────────────────────────
    ("a-iron-greaves",      "Iron Greaves",          "鐵脛甲",       "Armour",  "鞋子",   ["力量"]),
    ("a-rawhide-boots",     "Rawhide Boots",         "生皮靴子",     "Armour",  "鞋子",   ["敏捷"]),
    ("a-wool-shoes",        "Wool Shoes",            "羊毛鞋",       "Armour",  "鞋子",   ["智慧"]),
    ("a-chain-boots",       "Chain Boots",           "鎖甲靴子",     "Armour",  "鞋子",   ["力量", "智慧"]),
    ("a-soldier-boots",     "Soldier Boots",         "士兵靴子",     "Armour",  "鞋子",   ["力量", "敏捷"]),
    ("a-silk-slippers",     "Silk Slippers",         "絲綢拖鞋",     "Armour",  "鞋子",   ["智慧"]),
    # ── Armour: 盾牌 ────────────────────────────────────────────────────────
    ("a-plank-kite-shield", "Plank Kite Shield",     "木板鳶形盾",   "Armour",  "盾牌",   ["力量"]),
    ("a-twig-spirit-shield","Twig Spirit Shield",    "枝條靈魂盾",   "Armour",  "盾牌",   ["智慧"]),
    ("a-corroded-tower",    "Corroded Tower Shield", "腐蝕塔盾",     "Armour",  "盾牌",   ["力量"]),
    ("a-buckskin-buckler",  "Buckskin Buckler",      "鹿皮小圓盾",   "Armour",  "盾牌",   ["敏捷"]),
    ("a-ebony-tower-shield","Ebony Tower Shield",    "烏木塔盾",     "Armour",  "盾牌",   ["力量"]),
    # ── Jewellery: 項鍊 ─────────────────────────────────────────────────────
    ("j-coral-amulet",      "Coral Amulet",          "珊瑚護符",     "Jewellery","項鍊",  ["護符", "生命"]),
    ("j-paua-amulet",       "Paua Amulet",           "鮑魚護符",     "Jewellery","項鍊",  ["護符", "魔力"]),
    ("j-amber-amulet",      "Amber Amulet",          "琥珀護符",     "Jewellery","項鍊",  ["護符", "力量"]),
    ("j-jade-amulet",       "Jade Amulet",           "翡翠護符",     "Jewellery","項鍊",  ["護符", "敏捷"]),
    ("j-lapis-amulet",      "Lapis Amulet",          "青金石護符",   "Jewellery","項鍊",  ["護符", "智慧"]),
    ("j-onyx-amulet",       "Onyx Amulet",           "縞瑪瑙護符",   "Jewellery","項鍊",  ["護符"]),
    ("j-gold-amulet",       "Gold Amulet",           "黃金護符",     "Jewellery","項鍊",  ["護符"]),
    ("j-turquoise-amulet",  "Turquoise Amulet",      "綠松石護符",   "Jewellery","項鍊",  ["護符"]),
    # ── Jewellery: 戒指 ─────────────────────────────────────────────────────
    ("j-iron-ring",         "Iron Ring",             "鐵戒",         "Jewellery","戒指",  ["戒指"]),
    ("j-coral-ring",        "Coral Ring",            "珊瑚戒",       "Jewellery","戒指",  ["戒指", "生命"]),
    ("j-paua-ring",         "Paua Ring",             "鮑魚戒",       "Jewellery","戒指",  ["戒指", "魔力"]),
    ("j-sapphire-ring",     "Sapphire Ring",         "藍寶石戒",     "Jewellery","戒指",  ["戒指", "冷元素"]),
    ("j-topaz-ring",        "Topaz Ring",            "黃玉戒",       "Jewellery","戒指",  ["戒指", "閃電元素"]),
    ("j-ruby-ring",         "Ruby Ring",             "紅寶石戒",     "Jewellery","戒指",  ["戒指", "火元素"]),
    ("j-amethyst-ring",     "Amethyst Ring",         "紫晶戒",       "Jewellery","戒指",  ["戒指", "混沌"]),
    ("j-two-stone-ring",    "Two-Stone Ring",        "雙石戒",       "Jewellery","戒指",  ["戒指"]),
    # ── Jewellery: 腰帶 ─────────────────────────────────────────────────────
    ("j-chain-belt",        "Chain Belt",            "鎖鏈腰帶",     "Jewellery","腰帶",  ["腰帶", "魔力"]),
    ("j-leather-belt",      "Leather Belt",          "皮革腰帶",     "Jewellery","腰帶",  ["腰帶", "生命"]),
    ("j-rustic-sash",       "Rustic Sash",           "粗製腰帶",     "Jewellery","腰帶",  ["腰帶"]),
    ("j-studded-belt",      "Studded Belt",          "鑲釘腰帶",     "Jewellery","腰帶",  ["腰帶"]),
    ("j-heavy-belt",        "Heavy Belt",            "重型腰帶",     "Jewellery","腰帶",  ["腰帶", "力量"]),
    ("j-cloth-belt",        "Cloth Belt",            "布腰帶",       "Jewellery","腰帶",  ["腰帶", "智慧"]),
]


# ── 資料模型 ────────────────────────────────────────────────────────────────

@dataclass
class ItemDefinition:
    """單一物品的描述。"""
    id:          str
    name_en:     str
    name_zh:     str
    category:    str
    subcategory: str
    tags:        list[str] = field(default_factory=list)


# ── 資料庫 ──────────────────────────────────────────────────────────────────

class ItemDatabase:
    """POE2 物品分類查詢與搜尋服務。

    整合 P21 AliasResolver：搜尋時自動解析中文別名（如「混沌」→ Chaos Orb）。
    """

    def __init__(
        self,
        data_file: pathlib.Path = _DATA_FILE,
        alias_resolver: Optional[AliasResolver] = None,
    ) -> None:
        self._alias_resolver: Optional[AliasResolver] = (
            alias_resolver if alias_resolver is not None
            else self._try_build_resolver(data_file)
        )
        self._items: list[ItemDefinition] = []
        self._add_static_items()
        self._load_from_json(data_file)
        self._build_index()

    # ── 公開 API ──────────────────────────────────────────────────────────

    def get_categories(self) -> list[str]:
        """回傳所有頂層分類（依 _CATEGORY_ORDER 排序）。"""
        order = {cat: i for i, cat in enumerate(_CATEGORY_ORDER)}
        return sorted(self._cats.keys(), key=lambda c: order.get(c, 999))

    def get_subcategories(self, category: str) -> list[str]:
        """回傳指定分類下的子分類清單（依新增順序）。"""
        return list(self._cats.get(category, []))

    def get_items(self, category: str, subcategory: str) -> list[ItemDefinition]:
        """回傳指定分類 + 子分類的物品清單。"""
        return list(self._by_sub.get((category, subcategory), []))

    def search(self, query: str) -> list[ItemDefinition]:
        """搜尋物品。支援英文名稱、中文名稱、標籤及 P21 中文別名。

        搜尋順序（結果不重複）：
          1. name_en 包含匹配（大小寫不敏感）
          2. name_zh 包含匹配
          3. tags 包含匹配
          4. AliasResolver.resolve_zh() 別名解析 → name_en 匹配
        """
        query = query.strip()
        if not query:
            return []

        q_lower = query.lower()
        seen_ids: set[str] = set()
        results: list[ItemDefinition] = []

        def _add(item: ItemDefinition) -> None:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                results.append(item)

        for item in self._items:
            if q_lower in item.name_en.lower():
                _add(item)

        for item in self._items:
            if query in item.name_zh:
                _add(item)

        for item in self._items:
            if any(query in t for t in item.tags):
                _add(item)

        if self._alias_resolver is not None:
            en_names = self._alias_resolver.resolve_zh(query)
            en_lower_set = {e.lower() for e in en_names}
            for item in self._items:
                if item.name_en.lower() in en_lower_set:
                    _add(item)

        return results

    def all_items(self) -> list[ItemDefinition]:
        """回傳所有物品（測試 / 工具用）。"""
        return list(self._items)

    # ── 內部方法 ──────────────────────────────────────────────────────────

    @staticmethod
    def _try_build_resolver(data_file: pathlib.Path) -> Optional[AliasResolver]:
        try:
            return AliasResolver(data_file)
        except Exception:
            return None

    def _add_static_items(self) -> None:
        for row in _STATIC:
            iid, name_en, name_zh, cat, sub, tags = row
            self._items.append(ItemDefinition(
                id=iid, name_en=name_en, name_zh=name_zh,
                category=cat, subcategory=sub, tags=list(tags),
            ))

    def _load_from_json(self, data_file: pathlib.Path) -> None:
        try:
            with data_file.open(encoding="utf-8") as f:
                db = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        existing_ids = {item.id for item in self._items}
        for raw in db.get("items", []):
            alias_cat = raw.get("category", "")
            if alias_cat not in _ALIAS_CATEGORY_MAP:
                continue
            item_id = raw.get("id", "")
            if item_id in existing_ids:
                continue
            cat, sub = _ALIAS_CATEGORY_MAP[alias_cat]
            self._items.append(ItemDefinition(
                id=item_id,
                name_en=raw.get("en", ""),
                name_zh=raw.get("zh", ""),
                category=cat,
                subcategory=sub,
                tags=list(raw.get("aliases_zh", [])),
            ))
            existing_ids.add(item_id)

    def _build_index(self) -> None:
        self._cats: dict[str, list[str]] = {}
        self._by_sub: dict[tuple[str, str], list[ItemDefinition]] = {}
        seen_subs: dict[str, dict[str, None]] = {}

        for item in self._items:
            if item.category not in self._cats:
                self._cats[item.category] = []
                seen_subs[item.category] = {}
            if item.subcategory not in seen_subs[item.category]:
                seen_subs[item.category][item.subcategory] = None
                self._cats[item.category].append(item.subcategory)
            key = (item.category, item.subcategory)
            if key not in self._by_sub:
                self._by_sub[key] = []
            self._by_sub[key].append(item)
