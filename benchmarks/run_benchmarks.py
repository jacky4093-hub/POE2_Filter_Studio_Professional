"""POE2 Filter Studio — Performance Benchmark Suite

Measures wall-clock time and memory for each pipeline stage at 1k/5k/10k/20k rules.
No Qt, no GUI.  Pure core functions only.

Run from project root:
    python benchmarks/run_benchmarks.py

Output is printed as a Markdown table and saved to benchmarks/results/report.md.
"""

import sys
import os
import gc
import time
import tracemalloc
import statistics

# ── path setup ───────────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, _ROOT)

from parser.filter_parser import parse_filter
from parser.filter_exporter import export_filter
from core.sections import build_section_map
from core.search import search_rules, SearchQuery
from benchmarks.generate_filter import make_filter_text

# ── configuration ────────────────────────────────────────────────────────────

SIZES = [1_000, 5_000, 10_000, 20_000]
REPEATS = 5          # repeat each measurement N times, take median
SEARCH_QUERIES = [
    SearchQuery(text="Currency"),
    SearchQuery(text="Show"),
    SearchQuery(text="ItemLevel"),
]

RESULTS_DIR = os.path.join(_HERE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


# ── timing helpers ───────────────────────────────────────────────────────────

def _timeit(fn, repeats: int = REPEATS):
    """Return (median_ms, min_ms, max_ms) over *repeats* runs."""
    times = []
    for _ in range(repeats):
        gc.collect()
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    return statistics.median(times), min(times), max(times)


def _memory_peak(fn):
    """Return peak memory in KB allocated during fn()."""
    gc.collect()
    tracemalloc.start()
    fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024   # KB


# ── benchmark runner ─────────────────────────────────────────────────────────

class BenchmarkResult:
    def __init__(self, n: int):
        self.n = n
        self.gen_ms:        float = 0
        self.text_bytes:    int   = 0
        self.parse_med:     float = 0
        self.parse_min:     float = 0
        self.parse_max:     float = 0
        self.parse_mem_kb:  float = 0
        self.actual_rules:  int   = 0
        self.section_med:   float = 0
        self.section_min:   float = 0
        self.section_max:   float = 0
        self.n_sections:    int   = 0
        self.search_results: dict = {}   # query -> (med, min, max, n_hits)
        self.export_med:    float = 0
        self.export_min:    float = 0
        self.export_max:    float = 0
        self.export_bytes:  int   = 0
        self.rules_mem_kb:  float = 0


def run_one(n: int) -> BenchmarkResult:
    r = BenchmarkResult(n)
    print(f"\n{'='*60}")
    print(f"  n = {n:,} rules")
    print(f"{'='*60}")

    # ── 1. Generate text ──────────────────────────────────────────────
    print("  [1/5] Generating filter text...", end=" ", flush=True)
    t0 = time.perf_counter()
    text = make_filter_text(n)
    r.gen_ms = (time.perf_counter() - t0) * 1000
    r.text_bytes = len(text.encode())
    print(f"{r.gen_ms:.1f} ms  ({r.text_bytes/1024:.0f} KB)")

    # ── 2. Parse ──────────────────────────────────────────────────────
    print("  [2/5] Parsing...", end=" ", flush=True)
    r.parse_med, r.parse_min, r.parse_max = _timeit(lambda: parse_filter(text))

    # Memory peak for a single parse
    r.parse_mem_kb = _memory_peak(lambda: parse_filter(text))

    # Parse once to get rules for subsequent stages
    rules = parse_filter(text)
    r.actual_rules = len([x for x in rules if x.action != "__TAIL__"])
    print(
        f"med={r.parse_med:.1f} ms  min={r.parse_min:.1f}  max={r.parse_max:.1f}"
        f"  | {r.actual_rules:,} visible rules | peak {r.parse_mem_kb:.0f} KB"
    )

    # ── 3. Section map rebuild ────────────────────────────────────────
    print("  [3/5] Section rebuild...", end=" ", flush=True)
    r.section_med, r.section_min, r.section_max = _timeit(
        lambda: build_section_map(rules)
    )
    smap = build_section_map(rules)
    r.n_sections = len(smap.sections)
    print(
        f"med={r.section_med:.2f} ms  min={r.section_min:.2f}  max={r.section_max:.2f}"
        f"  | {r.n_sections} sections"
    )

    # ── 4. Search ─────────────────────────────────────────────────────
    print("  [4/5] Search...", end=" ", flush=True)
    for q in SEARCH_QUERIES:
        med, mn, mx = _timeit(lambda _q=q: search_rules(rules, _q))
        hits = len(search_rules(rules, q))
        r.search_results[q.text] = (med, mn, mx, hits)
        print(f"\n         '{q.text}': med={med:.2f} ms  hits={hits:,}", end="")
    print()

    # ── 5. Export ─────────────────────────────────────────────────────
    print("  [5/5] Export...", end=" ", flush=True)
    r.export_med, r.export_min, r.export_max = _timeit(
        lambda: export_filter(rules)
    )
    exported = export_filter(rules)
    r.export_bytes = len(exported.encode())
    print(
        f"med={r.export_med:.1f} ms  min={r.export_min:.1f}  max={r.export_max:.1f}"
        f"  | {r.export_bytes/1024:.0f} KB output"
    )

    # ── 6. Rules object memory (rough estimate) ───────────────────────
    r.rules_mem_kb = _memory_peak(lambda: parse_filter(text))

    return r


# ── report generation ─────────────────────────────────────────────────────────

def _ms(v: float) -> str:
    if v < 1.0:
        return f"{v*1000:.0f} us"
    return f"{v:.1f} ms"


def _throughput(n: int, med_ms: float) -> str:
    if med_ms <= 0:
        return "—"
    per_sec = n / (med_ms / 1000)
    if per_sec >= 1_000_000:
        return f"{per_sec/1_000_000:.1f} M/s"
    return f"{per_sec/1_000:.0f} K/s"


def build_report(results: list[BenchmarkResult]) -> str:
    lines = [
        "# POE2 Filter Studio — Performance Benchmark Report",
        "",
        f"**Python**: {sys.version.split()[0]}  |  "
        f"**Platform**: {sys.platform}  |  "
        f"**Repeats**: {REPEATS} (median reported)",
        "",
    ]

    # ── Parse table ──────────────────────────────────────────────────
    lines += [
        "## Parse Time",
        "",
        "| Rules | Text Size | Median | Min | Max | Throughput | Peak Memory |",
        "|------:|----------:|-------:|----:|----:|-----------:|------------:|",
    ]
    for r in results:
        lines.append(
            f"| {r.n:,} | {r.text_bytes//1024} KB"
            f" | {_ms(r.parse_med)} | {_ms(r.parse_min)} | {_ms(r.parse_max)}"
            f" | {_throughput(r.actual_rules, r.parse_med)}"
            f" | {r.parse_mem_kb:.0f} KB |"
        )

    # ── Section rebuild table ────────────────────────────────────────
    lines += [
        "",
        "## Section Map Rebuild",
        "",
        "| Rules | Sections | Median | Min | Max | Throughput |",
        "|------:|---------:|-------:|----:|----:|-----------:|",
    ]
    for r in results:
        lines.append(
            f"| {r.n:,} | {r.n_sections}"
            f" | {_ms(r.section_med)} | {_ms(r.section_min)} | {_ms(r.section_max)}"
            f" | {_throughput(r.actual_rules, r.section_med)} |"
        )

    # ── Search table (one sub-table per query) ────────────────────────
    lines += ["", "## Search Time", ""]
    for q in SEARCH_QUERIES:
        lines += [
            f"### Query: `{q.text}`",
            "",
            "| Rules | Hits | Median | Min | Max | Throughput |",
            "|------:|-----:|-------:|----:|----:|-----------:|",
        ]
        for r in results:
            med, mn, mx, hits = r.search_results[q.text]
            lines.append(
                f"| {r.n:,} | {hits:,}"
                f" | {_ms(med)} | {_ms(mn)} | {_ms(mx)}"
                f" | {_throughput(r.actual_rules, med)} |"
            )
        lines.append("")

    # ── Export table ──────────────────────────────────────────────────
    lines += [
        "## Export Time",
        "",
        "| Rules | Output Size | Median | Min | Max | Throughput |",
        "|------:|------------:|-------:|----:|----:|-----------:|",
    ]
    for r in results:
        lines.append(
            f"| {r.n:,} | {r.export_bytes//1024} KB"
            f" | {_ms(r.export_med)} | {_ms(r.export_min)} | {_ms(r.export_max)}"
            f" | {_throughput(r.actual_rules, r.export_med)} |"
        )

    # ── Memory summary ────────────────────────────────────────────────
    lines += [
        "",
        "## Memory (tracemalloc peak during parse)",
        "",
        "| Rules | Peak KB | Per-Rule bytes |",
        "|------:|--------:|---------------:|",
    ]
    for r in results:
        per_rule = (r.rules_mem_kb * 1024) / max(r.actual_rules, 1)
        lines.append(
            f"| {r.n:,} | {r.rules_mem_kb:.0f} KB"
            f" | {per_rule:.0f} B |"
        )

    # ── Scaling analysis ──────────────────────────────────────────────
    if len(results) >= 2:
        lines += ["", "## Scaling Analysis", ""]
        first, last = results[0], results[-1]
        scale = last.n / first.n
        lines.append(f"Rules scale factor: {scale:.0f}×  ({first.n:,} → {last.n:,})\n")

        def _ratio(a, b):
            return f"{b/a:.1f}×" if a > 0 else "—"

        lines += [
            "| Stage | Time ratio | Expected (linear) | Verdict |",
            "|-------|:----------:|:-----------------:|---------|",
            f"| Parse | {_ratio(first.parse_med, last.parse_med)} | {scale:.0f}× | "
            + ("✓ linear" if last.parse_med / first.parse_med < scale * 1.5 else "⚠ super-linear") + " |",
            f"| Section rebuild | {_ratio(first.section_med, last.section_med)} | {scale:.0f}× | "
            + ("✓ linear" if last.section_med / first.section_med < scale * 1.5 else "⚠ super-linear") + " |",
            f"| Search 'Currency' | {_ratio(first.search_results['Currency'][0], last.search_results['Currency'][0])} | {scale:.0f}× | "
            + ("✓ linear" if last.search_results['Currency'][0] / first.search_results['Currency'][0] < scale * 1.5 else "⚠ super-linear") + " |",
            f"| Export | {_ratio(first.export_med, last.export_med)} | {scale:.0f}× | "
            + ("✓ linear" if last.export_med / first.export_med < scale * 1.5 else "⚠ super-linear") + " |",
        ]

    # ── Conclusions ───────────────────────────────────────────────────
    lines += [
        "",
        "## Conclusions",
        "",
        "Verdicts use 20k-rule median as the worst case:",
    ]
    r_worst = results[-1]
    conclusions = []

    # Parse
    if r_worst.parse_med < 200:
        conclusions.append(f"- **Parse**: {_ms(r_worst.parse_med)} at 20k rules — acceptable (< 200 ms)")
    elif r_worst.parse_med < 1000:
        conclusions.append(f"- **Parse**: {_ms(r_worst.parse_med)} at 20k rules — noticeable, consider progress indicator")
    else:
        conclusions.append(f"- **Parse**: {_ms(r_worst.parse_med)} at 20k rules — ⚠ too slow, optimisation required")

    # Section
    if r_worst.section_med < 50:
        conclusions.append(f"- **Section rebuild**: {_ms(r_worst.section_med)} at 20k rules — fast, safe to call on every mutation")
    else:
        conclusions.append(f"- **Section rebuild**: {_ms(r_worst.section_med)} at 20k rules — ⚠ consider caching")

    # Search
    med_s = r_worst.search_results["Currency"][0]
    if med_s < 30:
        conclusions.append(f"- **Search**: {_ms(med_s)} at 20k rules — fast, no debounce needed")
    else:
        conclusions.append(f"- **Search**: {_ms(med_s)} at 20k rules — consider 150 ms keystroke debounce")

    # Export
    if r_worst.export_med < 200:
        conclusions.append(f"- **Export**: {_ms(r_worst.export_med)} at 20k rules — acceptable")
    else:
        conclusions.append(f"- **Export**: {_ms(r_worst.export_med)} at 20k rules — ⚠ consider background thread")

    # Memory
    per_rule = (r_worst.rules_mem_kb * 1024) / max(r_worst.actual_rules, 1)
    conclusions.append(
        f"- **Memory**: ~{r_worst.rules_mem_kb:.0f} KB peak at 20k rules "
        f"(~{per_rule:.0f} B / rule) — negligible"
    )

    lines.extend(conclusions)
    lines.append("")

    return "\n".join(lines)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("POE2 Filter Studio — Benchmark Suite")
    print(f"Sizes: {SIZES}  |  Repeats per measurement: {REPEATS}")

    results = [run_one(n) for n in SIZES]

    report = build_report(results)

    # Save report
    report_path = os.path.join(RESULTS_DIR, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print("\n" + "=" * 60)
    sys.stdout.buffer.write(report.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
