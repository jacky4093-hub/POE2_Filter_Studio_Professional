"""POE2 Filter Studio — UI Scalability Benchmark

Measures QTreeWidget-based RuleListWidget at 500/1k/3k/5k/10k rules.
Uses PySide6 offscreen platform — no display required.

Run from project root:
    python benchmarks/ui_benchmarks.py

Output saved to benchmarks/results/ui_report.md
"""

import sys
import os
import gc
import time
import tracemalloc
import statistics

# ── path setup ───────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

# ── Qt must be initialised before any Qt import ──────────────────────────────
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

_app = QApplication.instance() or QApplication(["-platform", "offscreen"])
_app.setApplicationName("BenchmarkRunner")

# ── project imports ───────────────────────────────────────────────────────────
from core.models import FilterRule
from core.sections import build_section_map
from core.search import search_rules, SearchQuery
from widgets.rule_list import RuleListWidget

# ── configuration ────────────────────────────────────────────────────────────

SIZES   = [500, 1_000, 3_000, 5_000, 10_000]
REPEATS = 3   # UI operations are slower; 3 repeats is sufficient

SECTION_EVERY   = 10   # inject section header every N rules
SCROLL_OPS      = 50   # number of individual scroll-to-item jumps
NAV_OPS         = 100  # number of select_real_index calls

RESULTS_DIR = os.path.join(_HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

_SEP        = "#" + "=" * 48
_SECTION_NAMES = [
    "Currency", "Stackable Currency", "Fragments", "Maps", "Gems",
    "Unique Items", "Rare Items", "Magic Items", "Normal Items", "Flasks",
    "Waystones", "Jewels", "Amulets", "Rings", "Belts",
    "Weapons", "Armour", "Sanctum Relics", "End-Game", "Levelling",
]


# ── synthetic data builder (direct FilterRule objects, no parsing) ────────────

def make_rules(n: int, section_every: int = SECTION_EVERY) -> list[FilterRule]:
    """Return n visible FilterRule objects plus __TAIL__, with section headers."""
    rules: list[FilterRule] = []
    sec_idx = 0

    for i in range(n):
        if section_every > 0 and i % section_every == 0:
            name = _SECTION_NAMES[sec_idx % len(_SECTION_NAMES)]
            sec_idx += 1
            pre = ["", _SEP, f"# {name}", _SEP]
        else:
            pre = [""]

        kind = i % 3
        if kind == 0:
            rules.append(FilterRule(
                action="Show",
                pre_lines=pre,
                conditions=[["Class", '"Currency"'], ["ItemLevel", ">= 60"]],
                actions=[["SetTextColor", "255 200 0 255"],
                         ["SetBorderColor", "200 150 0 255"],
                         ["PlayAlertSound", "1 300"]],
                inline_comment="",
                unknown_lines=[],
            ))
        elif kind == 1:
            rules.append(FilterRule(
                action="Hide",
                pre_lines=pre,
                conditions=[["Rarity", "Normal"], ["ItemLevel", "<= 40"]],
                actions=[],
                inline_comment="",
                unknown_lines=[],
            ))
        else:
            rules.append(FilterRule(
                action="Show",
                pre_lines=pre,
                conditions=[["AreaLevel", ">= 68"]],
                actions=[["SetFontSize", "40"],
                         ["SetMinimapIcon", "1 Yellow Star"]],
                inline_comment="high tier",
                unknown_lines=[],
            ))

    rules.append(FilterRule(
        action="__TAIL__", pre_lines=[""],
        conditions=[], actions=[], inline_comment="", unknown_lines=[],
    ))
    return rules


# ── timing helpers ────────────────────────────────────────────────────────────

def _flush():
    QCoreApplication.processEvents()
    QCoreApplication.processEvents()   # double-flush to drain deferred events


def _timeit(fn, repeats: int = REPEATS):
    """Return (median_ms, min_ms, max_ms) over repeats runs."""
    times = []
    for _ in range(repeats):
        gc.collect()
        _flush()
        t0 = time.perf_counter()
        fn()
        _flush()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    return statistics.median(times), min(times), max(times)


def _memory_peak_kb(fn) -> float:
    gc.collect()
    tracemalloc.start()
    fn()
    _flush()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024


# ── result container ──────────────────────────────────────────────────────────

class UIResult:
    __slots__ = [
        "n", "n_sections", "n_items",
        "load_med", "load_min", "load_max", "load_mem_kb",
        "expand_med", "expand_min", "expand_max",
        "collapse_med", "collapse_min", "collapse_max",
        "highlight_med", "highlight_min", "highlight_max", "n_hits",
        "nav_med", "nav_min", "nav_max",
        "scroll_med", "scroll_min", "scroll_max",
        "mem_after_load_kb",
    ]

    def __init__(self, n):
        for s in self.__slots__:
            object.__setattr__(self, s, 0)
        self.n = n


# ── per-size benchmark ────────────────────────────────────────────────────────

def run_one(n: int) -> UIResult:
    r = UIResult(n)
    sep = "=" * 60
    print(f"\n{sep}\n  n = {n:,} rules\n{sep}")

    # Pre-build data (not timed)
    rules    = make_rules(n)
    smap     = build_section_map(rules)
    r.n_sections = len(smap.sections)
    visible  = [x for x in rules if x.action != "__TAIL__"]

    # Pre-compute search hits (not timed)
    matches = search_rules(rules, SearchQuery(text="Show"))
    r.n_hits = len(matches)
    match_set = set(matches)
    current_hit = matches[0] if matches else -1

    # ── 1. load_rules (QTreeWidget build) ─────────────────────────────────
    print("  [1/7] load_rules()...", end=" ", flush=True)

    widget = RuleListWidget()
    widget.show()
    _flush()

    def _load():
        widget.load_rules(rules, smap)

    r.load_med, r.load_min, r.load_max = _timeit(_load)
    r.load_mem_kb = _memory_peak_kb(_load)

    # Count actual QTreeWidgetItem objects
    r.n_items = widget.list_widget.topLevelItemCount()
    for i in range(widget.list_widget.topLevelItemCount()):
        top = widget.list_widget.topLevelItem(i)
        r.n_items += top.childCount()

    print(
        f"med={r.load_med:.1f} ms  min={r.load_min:.1f}  max={r.load_max:.1f}"
        f"  | sections={r.n_sections}  items={r.n_items:,}  peak={r.load_mem_kb:.0f} KB"
    )

    # Ensure tree is populated for subsequent tests
    widget.load_rules(rules, smap)
    _flush()

    # ── 2. expandAll ──────────────────────────────────────────────────────
    print("  [2/7] expandAll()...", end=" ", flush=True)

    def _expand():
        widget.list_widget.collapseAll()   # start collapsed
        _flush()
        widget.list_widget.blockSignals(True)
        widget.list_widget.expandAll()
        widget.list_widget.blockSignals(False)

    r.expand_med, r.expand_min, r.expand_max = _timeit(_expand)
    print(f"med={r.expand_med:.1f} ms  min={r.expand_min:.1f}  max={r.expand_max:.1f}")

    widget.list_widget.expandAll()
    _flush()

    # ── 3. collapseAll ────────────────────────────────────────────────────
    print("  [3/7] collapseAll()...", end=" ", flush=True)

    def _collapse():
        widget.list_widget.expandAll()
        _flush()
        widget.list_widget.blockSignals(True)
        widget.list_widget.collapseAll()
        widget.list_widget.blockSignals(False)

    r.collapse_med, r.collapse_min, r.collapse_max = _timeit(_collapse)
    print(f"med={r.collapse_med:.1f} ms  min={r.collapse_min:.1f}  max={r.collapse_max:.1f}")

    widget.list_widget.expandAll()
    _flush()

    # ── 4. set_highlights (search highlight + section auto-expand) ─────────
    print("  [4/7] set_highlights()...", end=" ", flush=True)

    def _highlight():
        widget.set_highlights(match_set, current_hit)

    r.highlight_med, r.highlight_min, r.highlight_max = _timeit(_highlight)
    print(
        f"med={r.highlight_med:.1f} ms  min={r.highlight_min:.1f}  max={r.highlight_max:.1f}"
        f"  hits={r.n_hits:,}"
    )

    # Reset highlights
    widget.clear_highlights()
    _flush()

    # ── 5. select_real_index navigation (jump around the list) ────────────
    print("  [5/7] selection navigation...", end=" ", flush=True)

    n_vis = len(visible)
    step  = max(1, n_vis // NAV_OPS)
    nav_indices = list(range(0, n_vis, step))[:NAV_OPS]

    def _navigate():
        for idx in nav_indices:
            widget.select_real_index(idx)

    r.nav_med, r.nav_min, r.nav_max = _timeit(_navigate)
    ops = len(nav_indices)
    per_op = r.nav_med / ops if ops else 0
    print(
        f"med={r.nav_med:.1f} ms ({ops} ops, {per_op:.2f} ms/op)"
        f"  min={r.nav_min:.1f}  max={r.nav_max:.1f}"
    )

    # ── 6. scroll performance ──────────────────────────────────────────────
    print("  [6/7] scroll performance...", end=" ", flush=True)

    # Collect real item references (rule items only)
    real_items = []
    for i in range(widget.list_widget.topLevelItemCount()):
        top = widget.list_widget.topLevelItem(i)
        if top.childCount() > 0:
            real_items.extend(
                top.child(j) for j in range(top.childCount())
            )
        else:
            real_items.append(top)

    scroll_step = max(1, len(real_items) // SCROLL_OPS)
    scroll_targets = real_items[::scroll_step][:SCROLL_OPS]

    def _scroll():
        for item in scroll_targets:
            widget.list_widget.scrollToItem(item)

    r.scroll_med, r.scroll_min, r.scroll_max = _timeit(_scroll)
    s_ops = len(scroll_targets)
    per_scroll = r.scroll_med / s_ops if s_ops else 0
    print(
        f"med={r.scroll_med:.1f} ms ({s_ops} ops, {per_scroll:.2f} ms/op)"
        f"  min={r.scroll_min:.1f}  max={r.scroll_max:.1f}"
    )

    # ── 7. memory after load ───────────────────────────────────────────────
    print("  [7/7] memory growth...", end=" ", flush=True)
    r.mem_after_load_kb = _memory_peak_kb(
        lambda: RuleListWidget().load_rules(rules, smap)
    )
    print(f"peak {r.mem_after_load_kb:.0f} KB  (~{r.mem_after_load_kb/n:.1f} KB/rule)")

    # Cleanup
    widget.close()
    del widget
    gc.collect()

    return r


# ── report builder ────────────────────────────────────────────────────────────

def _ms(v: float) -> str:
    return f"{v:.1f} ms" if v >= 1 else f"{v*1000:.0f} us"


def _fps(med_ms: float) -> str:
    if med_ms <= 0:
        return "—"
    fps = 1000 / med_ms
    return f"{fps:.0f} fps" if fps < 1000 else ">1000 fps"


def build_report(results: list[UIResult]) -> str:
    lines = [
        "# POE2 Filter Studio — UI Scalability Benchmark Report",
        "",
        f"**Python**: {sys.version.split()[0]}  |  "
        f"**Platform**: offscreen (no GPU)  |  "
        f"**Qt**: {_qt_version()}  |  "
        f"**Repeats**: {REPEATS} (median reported)",
        "",
        "> Scroll / Expand operations run without rendering (offscreen).",
        "> Times reflect Qt layout & data-structure cost only, not GPU paint.",
        "",
    ]

    # ── 1. load_rules ────────────────────────────────────────────────────
    lines += [
        "## 1. load_rules() — QTreeWidget Build",
        "",
        "| Rules | Sections | Tree Items | Median | Min | Max | Peak Mem |",
        "|------:|---------:|-----------:|-------:|----:|----:|---------:|",
    ]
    for r in results:
        lines.append(
            f"| {r.n:,} | {r.n_sections:,} | {r.n_items:,}"
            f" | {_ms(r.load_med)} | {_ms(r.load_min)} | {_ms(r.load_max)}"
            f" | {r.load_mem_kb:.0f} KB |"
        )

    # ── 2. expandAll / collapseAll ────────────────────────────────────────
    lines += [
        "",
        "## 2. expandAll() / collapseAll()",
        "",
        "| Rules | expandAll Median | collapseAll Median | Sections |",
        "|------:|----------------:|-------------------:|---------:|",
    ]
    for r in results:
        lines.append(
            f"| {r.n:,} | {_ms(r.expand_med)} | {_ms(r.collapse_med)}"
            f" | {r.n_sections:,} |"
        )

    # ── 3. Search Highlight ───────────────────────────────────────────────
    lines += [
        "",
        "## 3. Search Highlight (set_highlights — partial background update)",
        "",
        "| Rules | Hits | Median | Min | Max |",
        "|------:|-----:|-------:|----:|----:|",
    ]
    for r in results:
        lines.append(
            f"| {r.n:,} | {r.n_hits:,}"
            f" | {_ms(r.highlight_med)} | {_ms(r.highlight_min)} | {_ms(r.highlight_max)} |"
        )

    # ── 4. Selection Navigation ───────────────────────────────────────────
    lines += [
        "",
        f"## 4. Selection Navigation ({NAV_OPS} ops)",
        "",
        "| Rules | Total Median | Per-Op | Min | Max |",
        "|------:|------------:|-------:|----:|----:|",
    ]
    for r in results:
        per_op = r.nav_med / NAV_OPS
        lines.append(
            f"| {r.n:,} | {_ms(r.nav_med)}"
            f" | {per_op:.2f} ms | {_ms(r.nav_min)} | {_ms(r.nav_max)} |"
        )

    # ── 5. Scroll Performance ─────────────────────────────────────────────
    lines += [
        "",
        f"## 5. Scroll Performance ({SCROLL_OPS} scrollToItem ops)",
        "",
        "| Rules | Total Median | Per-Scroll | Min | Max |",
        "|------:|------------:|-----------:|----:|----:|",
    ]
    for r in results:
        per_scroll = r.scroll_med / SCROLL_OPS
        lines.append(
            f"| {r.n:,} | {_ms(r.scroll_med)}"
            f" | {per_scroll:.2f} ms | {_ms(r.scroll_min)} | {_ms(r.scroll_max)} |"
        )

    # ── 6. Memory Growth ──────────────────────────────────────────────────
    lines += [
        "",
        "## 6. Memory Growth (tracemalloc peak, widget + rules)",
        "",
        "| Rules | Peak KB | Per-Rule |",
        "|------:|--------:|---------:|",
    ]
    for r in results:
        per_rule = (r.mem_after_load_kb * 1024) / r.n if r.n else 0
        lines.append(
            f"| {r.n:,} | {r.mem_after_load_kb:.0f} KB | {per_rule:.0f} B |"
        )

    # ── 7. Scaling Analysis ───────────────────────────────────────────────
    if len(results) >= 2:
        first, last = results[0], results[-1]
        scale = last.n / first.n

        def _ratio(a, b):
            return f"{b/a:.1f}x" if a > 0 else "—"

        def _verdict(a, b, threshold=1.8):
            if a <= 0:
                return "—"
            ratio = b / a
            expected = scale
            return "✓ linear" if ratio < expected * threshold else "⚠ super-linear"

        lines += [
            "",
            f"## 7. Scaling Analysis ({first.n:,} → {last.n:,} rules, {scale:.0f}x)",
            "",
            "| Operation | Time ratio | Expected | Verdict |",
            "|-----------|:----------:|:--------:|---------|",
            f"| load_rules | {_ratio(first.load_med, last.load_med)} | {scale:.0f}x | {_verdict(first.load_med, last.load_med)} |",
            f"| expandAll  | {_ratio(first.expand_med, last.expand_med)} | {scale:.0f}x | {_verdict(first.expand_med, last.expand_med)} |",
            f"| collapseAll | {_ratio(first.collapse_med, last.collapse_med)} | {scale:.0f}x | {_verdict(first.collapse_med, last.collapse_med)} |",
            f"| set_highlights | {_ratio(first.highlight_med, last.highlight_med)} | {scale:.0f}x | {_verdict(first.highlight_med, last.highlight_med)} |",
            f"| select_real_index | {_ratio(first.nav_med, last.nav_med)} | {scale:.0f}x | {_verdict(first.nav_med, last.nav_med)} |",
            f"| scrollToItem | {_ratio(first.scroll_med, last.scroll_med)} | {scale:.0f}x | {_verdict(first.scroll_med, last.scroll_med)} |",
            f"| Memory | {_ratio(first.mem_after_load_kb, last.mem_after_load_kb)} | {scale:.0f}x | {_verdict(first.mem_after_load_kb, last.mem_after_load_kb)} |",
        ]

    # ── 8. Conclusions ────────────────────────────────────────────────────
    worst = results[-1]
    lines += ["", "## 8. Conclusions", ""]

    def _verdict_threshold(label, med, thresholds):
        for limit, status in thresholds:
            if med < limit:
                return f"- **{label}**: {_ms(med)} at {worst.n:,} rules — {status}"
        _, last_status = thresholds[-1]
        return f"- **{label}**: {_ms(med)} at {worst.n:,} rules — {last_status}"

    lines += [
        _verdict_threshold("load_rules", worst.load_med,
            [(100, "fast (<100 ms)"),
             (500, "acceptable, consider progress indicator"),
             (float("inf"), "⚠ slow — optimise QTreeWidget rebuild")]),
        _verdict_threshold("expandAll", worst.expand_med,
            [(50, "fast"),
             (200, "acceptable"),
             (float("inf"), "⚠ slow — consider lazy expand")]),
        _verdict_threshold("collapseAll", worst.collapse_med,
            [(50, "fast"),
             (200, "acceptable"),
             (float("inf"), "⚠ slow")]),
        _verdict_threshold("set_highlights", worst.highlight_med,
            [(100, "fast — no debounce needed"),
             (200, "acceptable"),
             (float("inf"), "⚠ slow — consider background refresh")]),
        _verdict_threshold("select_real_index", worst.nav_med / NAV_OPS,
            [(5, "fast per-op"),
             (20, "acceptable"),
             (float("inf"), "⚠ slow per-op")]),
        _verdict_threshold("scrollToItem", worst.scroll_med / SCROLL_OPS,
            [(5, "fast per-op"),
             (20, "acceptable"),
             (float("inf"), "⚠ slow per-op")]),
        f"- **Memory**: {worst.mem_after_load_kb:.0f} KB widget peak at {worst.n:,} rules"
        f"  (~{worst.mem_after_load_kb*1024/worst.n:.0f} B/rule)"
        + (" — negligible" if worst.mem_after_load_kb < 100_000 else " — ⚠ large"),
        "",
        f"_Typical real POE2 filters: 200–2000 rules. 5k+ is extreme stress test._",
    ]

    return "\n".join(lines)


def _qt_version() -> str:
    try:
        from PySide6 import __version__
        return __version__
    except Exception:
        return "unknown"


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("POE2 Filter Studio — UI Benchmark Suite")
    print(f"Sizes: {SIZES}  |  Repeats: {REPEATS}  |  Platform: offscreen")

    results = [run_one(n) for n in SIZES]

    report = build_report(results)
    path   = os.path.join(RESULTS_DIR, "ui_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)

    print("\n" + "=" * 60)
    # Write via buffer to handle any Unicode in report safely
    sys.stdout.buffer.write(report.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    print(f"\nReport saved to: {path}")


if __name__ == "__main__":
    main()
