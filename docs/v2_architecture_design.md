POE2 Filter Studio v2.0 UI Architecture Design
1. Layout 差異分析
v1 (現況) — 3 欄 + Menu Bar

┌─────────────────────────────────────────────────────────────┐
│ MenuBar: 檔案(F) | 編輯(E)                                   │
│ Toolbar: 開啟 儲存 新增規則 復原 取消復原                     │
│ SearchBar: 搜尋規則 (Ctrl+F)...              [< >]          │
├────────────┬───────────────────────────────┬────────────────┤
│            │  General (QGroupBox)           │                │
│  Rule List │  Conditions ▼                 │    Preview     │
│            │  Appearance ▼                 │   "Item Name"  │
│  [1 Show]  │  Audio ▼                      │   (text only)  │
│  (QTree)   │  [套用修改 ✓]                  │                │
│  + - 複製  │                               │                │
├────────────┴───────────────────────────────┴────────────────┤
│ StatusBar: （未開啟）[已修改] · 1 條規則                      │
└─────────────────────────────────────────────────────────────┘
v2 (目標) — 4 欄 + Top Navigation Bar

┌─────────────────────────────────────────────────────────────┐
│ NavBar: [Logo] [過濾][搜索][...] [工具列]                    │
├──────┬───────────────┬──────────────────────┬───────────────┤
│ Cat  │               │                      │               │
│ Side │  Rule Cards   │   Visual Editor      │  In-Game      │
│ bar  │  通貨 (143)   │   碎裂石 ◈            │  Preview      │
│      │               │   Class / BaseType   │  (光柱+小地圖) │
│ 分類  │  [cards]     │   Color Swatches     │               │
│ 列表  │              │   Beam Color Circles │  Minimap      │
│      │               │   Minimap Shapes     │  Syntax       │
└──────┴───────────────┴──────────────────────┴───────────────┘
面向	v1	v2
欄數	3	4
Menu Bar	有（MenuBar + Toolbar 分開）	無（整合進 NavBar）
Category Sidebar	無	有
Rule 顯示方式	QTreeWidget plain text	視覺化 Card + 縮圖
主題色系	系統預設（亮色）	深藍暗色 + 色彩 Accent
Preview	純文字 "Item Name"	In-game 光柱 + 小地圖渲染
StatusBar	有	無（整合進 NavBar 右側）
2. UX 差異分析
核心 UX 模型轉變
面向	v1 (表單導向)	v2 (視覺導向)
資訊架構	Flat list → 展開 form	分類 → 卡片 → 視覺編輯
分類方式	無（所有規則混在一起）	Left sidebar 按物品類型分類
規則選取	點選 list row	點選視覺 Card
顏色設定	4 個 SpinBox + 小色塊	大型色彩 swatch，可點擊
光柱效果	EnumPropertyWidget dropdown	彩色圓圈選擇器（視覺即答案）
小地圖圖示	3 個 ComboBox	形狀圖示格（視覺即答案）
即時反饋	右側小文字 Preview	右側 in-game 渲染（光柱、小地圖）
音效	文字欄 + SpinBox	▶ 試聽按鈕 + 視覺化音效指示
規則識別	[1] Show — Empty Rule	物品名 + 彩色左邊條 + 圖示
操作流程比較
v1 流程（設定 Currency 規則）：

點 + 新增 → 2. 點 + 新增條件 → 3. 選 Class → 4. 輸入 "Currency" → 5. 點 + 新增顯示設定 → 6. 選 SetTextColor → 7. 輸入 RGBA → 8. 等 750ms 或點套用
v2 流程：

點 Left Sidebar "通貨" → 2. 點選現有 Currency 規則卡片 → 3. 直接調整右側色彩 swatch → 4. 即時預覽 → 5. 750ms auto-save
UX 提升：步驟數 8 → 5，且每步都有視覺反饋。

3. Visual Design 差異分析
色彩系統
元素	v1	v2
背景色	系統白色 #FFFFFF	深藍 #0d1117 / #161b22
面板色	淺灰 #F0F0F0	深藍灰 #1c2433
卡片色	無（list rows）	#1e2a45 + 細邊框
Accent	系統藍（選取色）	多色（依物品類型：紫/金/藍/綠）
文字	系統黑	主文字 #e2e8f0，副文字 #94a3b8
邊框	系統灰	#2d3748，hover 時 #4a5568
排版
元素	v1	v2
圓角	0-2px	6-12px (card)，4px (badge)
間距	Qt 預設 4-6px	統一 8px / 12px / 16px
字型	系統預設	等寬（Syntax）/ 無襯線（UI）
圖示	文字符號（＋ ✕ ▼ ▶）	需 SVG icon
視覺元件差異
元件	v1	v2
顏色選擇器	4 個 SpinBox 橫排 + 10×10 swatch	大型可點擊色塊 + Hex 輸入
光柱顏色	EnumComboBox	彩色圓圈按鈕排列
小地圖形狀	文字 Combo（"Circle", "Diamond"...）	實際形狀的圖示格
規則卡片	純文字列	卡片（彩色左條 + 名稱 + 圖示）
In-game 預覽	QLabel("Item Name") 黑底	QPainter 渲染完整光柱效果
4. MainWindow Layout 設計
結構

QMainWindow
└── Central Widget (QWidget)
    └── QVBoxLayout
        ├── NavigationBar (QWidget, 固定高度 48px)
        └── ContentArea (QWidget)
            └── QSplitter (Horizontal)
                ├── CategorySidebar     (固定 160px, min 140px)
                ├── RuleCardBrowser     (固定 300px, min 240px)
                ├── RuleEditorPanel     (彈性, min 380px)
                └── PreviewPanel        (固定 260px, min 200px)
NavigationBar

┌─────────────────────────────────────────────────────────────┐
│ [🔷Logo] POE2 Filter Studio  │ Open Save │ Undo Redo │ Search──── │ FileName● │
└─────────────────────────────────────────────────────────────┘
左：Logo + 品牌名
中左：Open / Save / Separator / Undo / Redo（icon buttons，固定寬度）
中：SearchBar（現有 SearchBar widget 直接複用）
右：當前檔案名 + dirty indicator ● + 規則總數
取消 MenuBar 和 StatusBar：功能整合進 NavBar，減少視覺複雜度。

5. Category Sidebar 設計
視覺

┌────────────────────┐
│  分類                │
├────────────────────┤
│ ◈  全部規則   234   │
│ ─────────────────  │
│ ●  通貨        18  │  ← 金色圓點
│ ●  地圖        24  │  ← 藍色圓點
│ ●  碎片        12  │  ← 紫色圓點
│ ●  技能石      16  │  ← 綠色圓點
│ ●  精華         8  │
│ ●  符文         6  │
│ ●  傳奇         20 │  ← 橙色圓點
│ ─────────────────  │
│ ●  裝備        45  │
│ ●  其他        85  │
│ ─────────────────  │
│ 📁 段落             │
│   Currency sec  8  │
│   End Game     12  │
└────────────────────┘
分類邏輯（src/core/categorizer.py）
基於 FilterRule.conditions 掃描，優先順序：


1. 通貨 (CURRENCY)
   Class ∋ {"Currency", "Stackable Currency", "Shard", "Piece"}
   BaseType ∋ {"Orb", "Shard", "Splinter", "Stone"}

2. 地圖 (MAPS)
   Class ∋ {"Maps", "Waystones", "Tablet", "Atlas"}
   or 有 WaystoneTier / MapTier 條件

3. 碎片 (FRAGMENTS)
   Class ∋ {"Map Fragments", "Breachstone", "Scarab",
             "Simulacrum", "Offering", "Vial", "Piece"}

4. 技能石 (GEMS)
   Class ∋ {"Gem", "Skill Gem", "Support Gem", "Miniature Gem"}

5. 精華 (ESSENCES)
   Class ∋ {"Essence"} or BaseType ∋ {"Essence"}

6. 符文 (RUNES)
   Class ∋ {"Rune"} or BaseType ∋ {"Rune"}

7. 傳奇 (UNIQUE)
   Rarity = "Unique"

8. 裝備 (EQUIPMENT)
   Class ∋ {"Helmet", "Body Armour", "Gloves", "Boots",
             "Weapon", "Two Hand", "One Hand", "Shield",
             "Belt", "Amulet", "Ring", "Flask"}

9. 其他 (OTHER)   ← 未命中以上
Widget 實作
CategorySidebarWidget(QWidget)
內部使用 QListWidget + custom paint（不用 delegate，用 stylesheet）
每個 item：setCategoryItem(icon_color, name, count)
選中狀態：左側 3px 色條 + 淡色背景
Count badge：QLabel 右對齊
6. Rule Browser 設計
卡片視覺

┌────────────────────────────────────────┐
│ ║█ Show  神聖石 (Divine Orb)       ★  │  56px 高
│ ║  Class "Currency"    [45pt] ████    │
└────────────────────────────────────────┘
元素	說明
左 3px 色條	Show=#4ade80, Hide=#64748b, Continue=#60a5fa, Minimal=#fbbf24
主標題	rule.inline_comment 或 auto-generated 物品名
副標題	前 2 個 conditions 摘要
FontSize badge	右上，圓角，SetFontSize 值
顏色條	SetTextColor RGBA 渲染為 40×8px 色條
★	FilterRule.starred 標記（metadata only）
暗灰背景	disabled rule 時降低不透明度
技術方案：QListView + RuleCardDelegate

class RuleCardDelegate(QStyledItemDelegate):
    CARD_HEIGHT = 60
    
    def sizeHint(self, option, index) -> QSize:
        if index.data(IS_SECTION_HEADER_ROLE):
            return QSize(0, 28)
        return QSize(0, self.CARD_HEIGHT)
    
    def paint(self, painter, option, index):
        if index.data(IS_SECTION_HEADER_ROLE):
            self._paint_section_header(painter, option, index)
        else:
            self._paint_rule_card(painter, option, index)
為何不用 QTreeWidget
QTreeWidget row 高度統一（難以做 section header vs card 不同高度）
QTreeWidget 不支援自定義每列繪製圓角
QListView + model/delegate 分離更適合 category filter（只需換 filter model，不需重建 widget）
Section Header 行

─────────  通貨  (18 rules)  ─────────────
插入為 RuleCardModel 中的特殊行，IS_SECTION_HEADER_ROLE=True，不可選取。

7. Rule Editor 設計
整體佈局（QScrollArea 包裹的 QVBoxLayout）

┌──────────────────────────────────────────┐
│ [Inline Preview]  碎裂石                  │  ← 新增
│  ████ TextColor  ▌邊框  背景             │
├──────────────────────────────────────────┤
│ [General]                                │
│  動作: [Show ▼]   備註: [         ]      │
├──────────────────────────────────────────┤
│ [Conditions]              + 新增條件      │
│  物品類別: [                          ]  │
│  ItemLevel: [>= ][60]                    │
├──────────────────────────────────────────┤
│ [Display 顯示設定]                        │
│  Text  ████ [R][G][B][A]   #FF6B00       │
│  BG    ████ [R][G][B][A]   #000000       │
│  Font  [32    ]                          │
├──────────────────────────────────────────┤
│ [Visual Effects 視覺效果]                 │
│  Beam:  ● ● ● ● ● ● ●  (彩色圓圈)       │  ← 視覺化改版
│  Minimap: [大小] ◯◇□★△ (形狀圖示格)    │  ← 視覺化改版
│           Color: ● ● ● ● ●              │
├──────────────────────────────────────────┤
│ [Audio 音效]              ▶ 折疊         │
│  ▶ 試聽  PlayAlertSound [1][300]        │
├──────────────────────────────────────────┤
│ [立即套用]                                │
└──────────────────────────────────────────┘
新增：Inline Preview Widget
在 editor 頂部加入一個小型 ItemLabelWidget：


class ItemLabelWidget(QWidget):
    """Mini in-game style item label, reacts to editor changes."""
    
    def paintEvent(self, event):
        # QPainter: 繪製 BG color, Border color, Text color, FontSize
        # 直接讀取 editor 當前 widget 值，不依賴 rule flush
此元件在 editor 每次 _on_field_changed() 時即時更新（純視覺，不走 flush 路徑）。

光柱顏色選擇器
新元件 BeamColorPicker(QWidget) 取代 PlayEffect 的 EnumPropertyWidget：


Beam Color:  ●Red  ●Green  ●Blue  ●Brown  ●White  ●Yellow  ●Cyan  ●Orange  ●Pink  ●Purple  [ Temp ]
每個顏色用 24×24 圓角方塊
選中者有白色外框
[ Temp ] 為 checkbox（PlayEffect 的 Temp 修飾詞）
小地圖圖示選擇器
新元件 MinimapIconPicker(QWidget) 取代 3 個 ComboBox：


大小:  [0] [1] [2]

形狀:  ◯ ◇ ⬡ □ ★ △

顏色:  ●R ●G ●B ●Br ●W ●Y ●Cy ●Gy ●O ●Pk ●Pu
8. Preview Panel 設計
結構（QTabWidget）

[Ground ▌] [Minimap] [Syntax] [Audio]
Tab 1: Ground Preview（重寫）

┌──────────────────────────────┐
│  [深色背景]                   │
│                              │
│   ┌──────────────────┐       │
│   │  碎裂石          │       │  ← QPainter 渲染
│   └──────────────────┘       │
│             │                │
│          橙色光柱             │  ← QPropertyAnimation 可選
└──────────────────────────────┘
ItemGroundRenderer 使用 QPainter：

背景：可切換（黑/草地/城市）
物品標籤：BG color + Border color + Text color + FontSize
光柱：PlayEffect color → 垂直漸層矩形
光柱動畫：可選（暫時不實作）
Tab 2: Minimap Preview

┌──────────────────────────────┐
│  [小地圖風格暗色底]            │
│    ·  ·  ·  ·  ·  ·         │
│  ·    ★    ·   ·    ·        │  ← MinimapDotRenderer
│    ·  ·  ·  ·  ·  ·         │
│  Size: 1  Color: Yellow      │
│  Shape: Star                 │
└──────────────────────────────┘
MinimapDotRenderer 使用 QPainter：

Circle → drawEllipse()
Diamond → 旋轉 45° 的方形
Hexagon → 6 邊多邊形
Square → drawRect()
Star → 5 角星多邊形路徑
Triangle → 3 邊多邊形路徑
Tab 3: Syntax Preview

┌──────────────────────────────┐
│  # Filter Syntax             │
│  ───────────────────         │
│  Show                        │
│      Class "Currency"        │
│      SetTextColor 255 165 0  │
│      SetFontSize 40          │
│      PlayEffect Orange       │
│      MinimapIcon 1 Yellow St │
└──────────────────────────────┘
QPlainTextEdit（唯讀）+ FilterSyntaxHighlighter（QSyntaxHighlighter 子類）。

內容 = Exporter.export_filter([current_rule]) 結果，每次 rule_changed 更新。

Tab 4: Audio

┌──────────────────────────────┐
│  🔔 PlayAlertSound 1         │
│  Volume: 300                 │
│  [▶ 試聽]                     │
│                              │
│  Drop Sound: 預設啟用          │
└──────────────────────────────┘
9. Theme System 設計
色彩調色盤（src/assets/theme.py）

# Base layers
BG_DEEPEST   = "#0d1117"   # 最深背景（視窗底）
BG_BASE      = "#161b22"   # 主面板底
BG_PANEL     = "#1c2433"   # 面板
BG_CARD      = "#1e2a45"   # 卡片
BG_CARD_HOV  = "#253350"   # 卡片 hover
BG_CARD_SEL  = "#2d3f63"   # 卡片 selected
BG_SURFACE   = "#0f3460"   # 凸起面（editor header）

# Accents（依物品類型）
ACC_CURRENCY = "#f6c90e"   # 金色（通貨）
ACC_MAPS     = "#60a5fa"   # 藍色（地圖）
ACC_GEMS     = "#4ade80"   # 綠色（技能石）
ACC_UNIQUE   = "#f97316"   # 橙色（傳奇）
ACC_FRAGMENT = "#a855f7"   # 紫色（碎片）
ACC_DEFAULT  = "#7c3aed"   # 紫色（預設 / UI accent）

# Text
TEXT_PRIMARY   = "#e2e8f0"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED     = "#475569"
TEXT_LINK      = "#7c3aed"

# Rule action colors
ACTION_SHOW    = "#4ade80"
ACTION_HIDE    = "#64748b"
ACTION_CONT    = "#60a5fa"
ACTION_MIN     = "#fbbf24"

# Borders
BORDER_BASE  = "#2d3748"
BORDER_FOCUS = "#7c3aed"

# Sizes
RADIUS_CARD   = 8
RADIUS_BADGE  = 4
RADIUS_BUTTON = 6
QSS 管理方式
檔案：src/assets/styles/


styles/
  base.qss          ← 全域 widget（QWidget, QScrollBar, QToolTip）
  navbar.qss        ← NavigationBar
  sidebar.qss       ← CategorySidebarWidget
  browser.qss       ← QListView（RuleCardBrowser）
  editor.qss        ← RuleEditorPanel, CollapsibleSection
  preview.qss       ← PreviewPanel, QTabWidget
  dialogs.qss       ← QMenu, QDialog
啟動時載入：


# bootstrap.py
def apply_theme(app: QApplication):
    qss = ""
    styles_dir = Path(__file__).parent / "assets" / "styles"
    for f in sorted(styles_dir.glob("*.qss")):
        qss += f.read_text(encoding="utf-8") + "\n"
    app.setStyleSheet(qss)
分拆 QSS 的好處：每個階段只需新增對應的 .qss 檔，不修改其他檔案。

Icon System

src/assets/icons/
  file-open.svg
  file-save.svg
  undo.svg
  redo.svg
  search.svg
  show.svg
  hide.svg
  star-empty.svg
  star-filled.svg
  trash.svg
  plus.svg
  chevron-down.svg
  chevron-right.svg
使用 QIcon.fromTheme() + fallback：


def icon(name: str) -> QIcon:
    path = Path(__file__).parent / "assets" / "icons" / f"{name}.svg"
    return QIcon(str(path))
10. Migration Strategy
檔案處置矩陣
檔案	方向	備註
src/core/models.py	零修改	只加 starred: bool = False
src/core/document.py	零修改	
src/core/commands.py	零修改	
src/core/sections.py	零修改	
src/core/search.py	零修改	
src/core/filter_schema.py	零修改	
src/parser/	零修改	
src/services/	零修改	
src/editor/property_widgets.py	零修改	value_changed 系統完整保留
src/widgets/search_bar.py	零修改	直接複用
src/editor/collapsible_section.py	輕度改	移除 hardcoded style → QSS objectName
src/editor/rule_editor.py	中度改	新增 BeamColorPicker / MinimapIconPicker，加 Inline Preview；核心邏輯（debounce, flush）不動
src/ui/preview_panel.py	重寫	QTabWidget 容器，保留 update_preview(rule) API
src/widgets/rule_list.py	退役	v2.2 後被 RuleCardBrowser 取代，舊檔保留但不再使用
src/ui/main_window.py	重寫	佈局改 4 欄，所有 signal slots 邏輯保留
src/app/bootstrap.py	輕度改	加 apply_theme()
新增檔案

src/core/categorizer.py              ← 純函式，classify_rule()
src/ui/navigation_bar.py             ← NavigationBar widget
src/ui/category_sidebar.py           ← CategorySidebarWidget
src/ui/rule_card_browser.py          ← RuleCardBrowser + RuleCardModel + RuleCardDelegate
src/ui/panels/item_ground_renderer.py ← QPainter in-game 渲染
src/ui/panels/minimap_renderer.py    ← QPainter minimap 渲染
src/ui/panels/syntax_preview.py      ← QPlainTextEdit + Highlighter
src/editor/widgets/beam_color_picker.py    ← BeamColorPicker（取代 PlayEffect dropdown）
src/editor/widgets/minimap_icon_picker.py  ← MinimapIconPicker（取代 3 ComboBox）
src/editor/widgets/item_label_preview.py   ← Inline item label preview
src/assets/styles/base.qss
src/assets/styles/navbar.qss
src/assets/styles/sidebar.qss
src/assets/styles/browser.qss
src/assets/styles/editor.qss
src/assets/styles/preview.qss
src/assets/styles/dialogs.qss
src/assets/icons/*.svg               ← 約 15 個 SVG
11. Risk Analysis
風險	嚴重度	說明	緩解
QPainter 光柱渲染準確度	中	遊戲內視覺和工具渲染不可能 100% 一致	明確標示「示意圖」，不保證像素一致
BeamColorPicker 整合 property_widgets	高	PlayEffect 目前走 PLAY_EFFECT FieldType → PlayEffectPropertyWidget；替換後需確保 get_raw_value() 格式一致	新 widget 保持 BasePropertyWidget 介面，只改視覺層
RuleCardDelegate 效能（大型 filter）	高	10k rules，每次 scroll 重繪 → paint() 呼叫密集	paint() 絕對不分配 Python 物件；pre-compute colors；使用 model caching
Category filter + highlight 同步	中	搜尋高亮在 category filter 後仍需正確顯示	highlight 用 real_index 不用 visual row index；category filter 只改 proxyModel，不動 highlight set
AutoSave 與 category 聯動	中	flush_pending 後若 Class 欄位被修改，rule 可能跑到另一分類	flush 後呼叫 _recategorize(real_index) 更新 sidebar count；不需重建整個 model
main_window.py 重寫風險	高	signal slot 連接複雜，重寫容易漏線	先為每個 slot 寫 smoke test，再重寫 MainWindow
Starred 持久化	低	starred 不在 .filter 語法，需獨立儲存	存入 QSettings per-file 的 JSON section，key = rule hash（rule text MD5）
SVG icon 打包	低	PyInstaller 需在 spec 加 datas	已有 assets datas 設定，確認路徑即可
CollapsibleSection QSS 移除後回歸	低	v2.0.0 Theme 移除 hardcoded style，若 QSS 設定有誤則 UI 破版	Theme Shell 作為獨立 PR，先做視覺 smoke test
12. 分階段實作計畫
v2.0.0 — Theme Shell
目標：零功能改動，只讓現有 UI 套上暗色主題。

修改：

src/assets/styles/base.qss（新增）
src/app/bootstrap.py（加 apply_theme()）
src/editor/collapsible_section.py（移除 hardcoded QSS → objectName）
驗證：python src/main.py 目視確認；pytest（所有現有測試全過）

v2.1.0 — Category Sidebar
目標：左側出現 Category Sidebar，點選可過濾當前 rule list。

修改：

src/core/categorizer.py（新增）
src/ui/category_sidebar.py（新增）
src/ui/main_window.py（splitter 從 3 → 4 欄，加 sidebar）
src/assets/styles/sidebar.qss（新增）
驗證：

tests/test_categorizer.py（新增 ~12 tests，純邏輯）
手動：點 "通貨" → 只顯示 Currency rules
v2.2.0 — Rule Card Browser
目標：Rule list 升級為視覺化 Card 樣式。

修改：

src/ui/rule_card_browser.py（新增：Model + Delegate + Browser）
src/ui/main_window.py（替換 rule_list → rule_card_browser）
src/assets/styles/browser.qss（新增）
保留 API：rule_selected(Signal(int)), load_rules(), set_highlights(), clear_highlights(), select_real_index()

驗證：

tests/test_rule_card_model.py（新增 ~15 tests）
現有 test_rule_list_highlight.py 通過（API 不變）
v2.3.0 — Visual Effects Pickers
目標：PlayEffect 和 MinimapIcon 從 Combo dropdown 改為視覺化選擇器。

修改：

src/editor/widgets/beam_color_picker.py（新增）
src/editor/widgets/minimap_icon_picker.py（新增）
src/editor/rule_editor.py（替換對應 widget，flush_pending 路徑不動）
src/assets/styles/editor.qss（更新）
驗證：

tests/test_visual_pickers.py（新增：get_raw_value / set_raw_value 格式測試）
確認 PlayEffect "Orange Temp" 字串格式和原 widget 完全一致
v2.4.0 — Preview Panel
目標：Preview Panel 升級為 4-tab 含 in-game 渲染。

修改：

src/ui/panels/item_ground_renderer.py（新增）
src/ui/panels/minimap_renderer.py（新增）
src/ui/panels/syntax_preview.py（新增）
src/ui/preview_panel.py（重寫）
src/assets/styles/preview.qss（新增）
驗證：

tests/test_renderers.py（paintEvent 不 crash，任意合法 rule）
tests/test_syntax_preview.py（內容與 Exporter 一致）
v2.5.0 — Navigation Bar & Polish
目標：最終視覺整合，Navigation Bar，icon buttons，細節打磨。

修改：

src/ui/navigation_bar.py（新增）
src/ui/main_window.py（MenuBar/StatusBar 替換為 NavigationBar）
src/assets/icons/*.svg（新增 ~15 個）
src/assets/styles/navbar.qss, dialogs.qss（新增）
src/editor/widgets/item_label_preview.py（新增 inline preview）
POE2FilterStudio.spec（確認 icons/ 打包）
驗證：

tests/test_ui_smoke.py（新增：MainWindow instantiate + 完整操作流程）
所有現有 134 tests 全過（非迴歸）
打包 EXE 手動目視確認
是否需要 v1.6–v1.9？
建議：直接 v1.5 → v2.0（不加 v1.6–v1.9）
原因：

v1.5 的核心能力（parser / exporter / document / commands / search / autosave）已完整且穩定
v1.6–v1.9 如果只是加功能（validation、filter export options 等）在舊的 UI 架構下開發，這些功能之後仍需在 v2.0 中重新整合，造成雙重工作
v2.0 採分階段實作（v2.0.0 → v2.5.0），每個子版本都是可運行、可測試的增量交付，風險可控
舊 UI 已經展示並確認（v1_current_ui.png），用戶看到的是現況；繼續在舊 UI 加功能沒有動力
例外情況（可加 v1.6）：

如果有以下需求，可在 v2.0.0 Theme Shell 之前插入 v1.6.0 Filter Validation：

需要在現有介面上加欄位驗證（空值警告、RGBA 範圍）
原因：validation 是純邏輯層改動，與 UI 無關，放在 v2.x 任何版本都可以
版本路線圖建議

v1.5.0  Rule Editor Auto-Save      ← ✅ 已完成 (2026-06-27)
   │
   └─→ v2.0.0  Theme Shell          ← 視覺基礎建設（~2-3天）
         │
         └─→ v2.1.0  Category Sidebar   ← 新增分類導覽（~3-4天）
               │
               └─→ v2.2.0  Rule Card Browser  ← 最複雜（~5-7天）
                     │
                     └─→ v2.3.0  Visual Effects Pickers  (~3-4天）
                           │
                           └─→ v2.4.0  Preview Panel    (~4-5天）
                                 │
                                 └─→ v2.5.0  NavBar & Polish  (~3-4天）
預估修改檔案數量
類別	數量
零修改保留	12 個核心檔
輕度改（QSS / 介面整合）	3 個
中度改（邏輯保留，視覺重做）	2 個（rule_editor.py, preview_panel.py）
重寫（保留 API）	1 個（main_window.py）
新增 Python 檔	12 個
新增 QSS 檔	7 個
新增 SVG icon	~15 個
合計	~52 個檔案
預估工時
版本	主要工作	估計工時
v2.0.0 Theme Shell	QSS 暗色主題 + bootstrap	2-3 天
v2.1.0 Category Sidebar	categorizer + sidebar widget	3-4 天
v2.2.0 Rule Card Browser	Model + Delegate + Browser	5-7 天
v2.3.0 Visual Pickers	Beam + Minimap 視覺選擇器	3-4 天
v2.4.0 Preview Panel	QPainter 渲染 + TabWidget	4-5 天
v2.5.0 NavBar & Polish	NavBar + icons + smoke tests	3-4 天
合計		20-27 天
（以每天 3-4 小時有效開發時間估算）

最大風險區域
🔴 最高風險：v2.2.0 Rule Card Browser
原因：

QStyledItemDelegate.paint() 中的任何 Python 物件分配都會造成 scroll lag（每 frame 呼叫多次）
RuleCardModel 需要和 category filter、search highlight、section grouping 三個系統同步
取代現有 rule_list.py 時必須確保所有 signals（rule_selected, set_highlights, clear_highlights）行為完全一致，否則會破壞 auto-save 的 flush 時序
緩解措施：

先寫 tests/test_rule_card_model.py（覆蓋所有 real_index 映射情境），再實作
Delegate paint() 使用靜態顏色常數，不做任何 dict lookup
舊 rule_list.py 保留不刪，並排存在直到 v2.2.0 完整測試通過
🟠 高風險：v2.3.0 PlayEffect format 相容性
原因：BeamColorPicker 的 get_raw_value() 必須輸出和舊 PlayEffectPropertyWidget 完全相同的字串格式（例如 "Orange" 或 "Orange Temp"），否則 Exporter 輸出的 .filter 內容會改變，破壞 round-trip 正確性。

緩解措施：為新 widget 寫明確的格式測試（"Red", "Blue Temp", "" 三種情境），在 CI 中跑。