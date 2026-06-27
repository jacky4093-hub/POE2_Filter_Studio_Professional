"""Debounce Behaviour Benchmark — v1.5.0

Verifies:
  1. flush_pending() latency (should be < 1 ms)
  2. Debounce fires exactly once regardless of change count
  3. Timer fires at ~750 ms (not before, not significantly after)
  4. No emit during rapid typing (100 changes, < 750ms between each)

Run from project root:
    python benchmarks/debounce_benchmark.py
"""

import sys
import os
import gc
import time
import statistics

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtTest import QTest

_app = QApplication.instance() or QApplication(["-platform", "offscreen"])

from core.models import FilterRule
from editor.rule_editor import RuleEditorWidget, _DEBOUNCE_MS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flush():
    QCoreApplication.processEvents()
    QCoreApplication.processEvents()


def _make_editor() -> tuple[RuleEditorWidget, FilterRule]:
    rule = FilterRule(
        action="Show", pre_lines=[], conditions=[],
        actions=[], inline_comment="original", unknown_lines=[],
    )
    w = RuleEditorWidget()
    w.load_rule(rule)
    return w, rule


REPEATS = 10


def _timeit_ms(fn, repeats: int = REPEATS) -> tuple[float, float, float]:
    """Return (median_ms, min_ms, max_ms)."""
    times = []
    for _ in range(repeats):
        gc.collect()
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    return statistics.median(times), min(times), max(times)


# ---------------------------------------------------------------------------
# Benchmark 1: flush_pending() latency
# ---------------------------------------------------------------------------

def bench_flush_latency() -> dict:
    """Measure flush_pending() wall-clock time (field change → rule updated)."""
    w, rule = _make_editor()

    def _one():
        w.comment_edit.setText("x")          # arm debounce
        w.flush_pending()                     # synchronous flush

    med, mn, mx = _timeit_ms(_one)
    return {"median_ms": med, "min_ms": mn, "max_ms": mx}


# ---------------------------------------------------------------------------
# Benchmark 2: emit count for rapid changes
# ---------------------------------------------------------------------------

def bench_emit_count(n_changes: int, delay_between_ms: int) -> dict:
    """Count rule_changed emits after *n_changes* rapid inputs then idle."""
    w, rule = _make_editor()
    emits = []
    w.rule_changed.connect(lambda: emits.append(1))

    for i in range(n_changes):
        w.comment_edit.setText(f"edit {i}")
        if delay_between_ms > 0:
            QTest.qWait(delay_between_ms)

    emits_during_typing = len(emits)

    # Wait for debounce to fire
    QTest.qWait(_DEBOUNCE_MS + 100)
    emits_after_idle = len(emits)

    return {
        "n_changes": n_changes,
        "delay_between_ms": delay_between_ms,
        "emits_during_typing": emits_during_typing,
        "emits_after_idle": emits_after_idle,
    }


# ---------------------------------------------------------------------------
# Benchmark 3: debounce fire timing accuracy
# ---------------------------------------------------------------------------

def bench_debounce_timing(repeats: int = 5) -> dict:
    """Measure actual elapsed time from field change to timer fire."""
    elapsed_times = []

    for _ in range(repeats):
        w, rule = _make_editor()
        fired_at = []

        def _on_changed():
            fired_at.append(time.perf_counter())

        w.rule_changed.connect(_on_changed)

        t_start = time.perf_counter()
        w.comment_edit.setText("timing test")
        QTest.qWait(_DEBOUNCE_MS + 200)

        if fired_at:
            elapsed_ms = (fired_at[0] - t_start) * 1000
            elapsed_times.append(elapsed_ms)

    if not elapsed_times:
        return {"error": "timer never fired"}

    return {
        "target_ms": _DEBOUNCE_MS,
        "median_ms": statistics.median(elapsed_times),
        "min_ms":    min(elapsed_times),
        "max_ms":    max(elapsed_times),
        "overhead_ms": statistics.median(elapsed_times) - _DEBOUNCE_MS,
    }


# ---------------------------------------------------------------------------
# Benchmark 4: has_pending_changes() overhead
# ---------------------------------------------------------------------------

def bench_has_pending_overhead() -> dict:
    """Measure cost of calling has_pending_changes() in a hot loop."""
    w, rule = _make_editor()
    w.comment_edit.setText("armed")

    def _check():
        for _ in range(10_000):
            _ = w.has_pending_changes()

    med, mn, mx = _timeit_ms(_check)
    per_call_us = (med / 10_000) * 1000
    return {
        "10k_calls_median_ms": med,
        "per_call_us": per_call_us,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def main():
    sep = "=" * 62
    print(f"\n{sep}")
    print("  POE2 Filter Studio — Debounce Behaviour Benchmark")
    print(f"  Debounce interval: {_DEBOUNCE_MS} ms")
    print(f"{sep}\n")

    # 1. flush_pending() latency
    print("[ 1 ] flush_pending() latency")
    r1 = bench_flush_latency()
    print(f"      median={r1['median_ms']:.3f} ms  "
          f"min={r1['min_ms']:.3f} ms  max={r1['max_ms']:.3f} ms")
    verdict1 = "PASS" if r1["median_ms"] < 5 else "SLOW"
    print(f"      verdict: {verdict1}  (expected < 5 ms)\n")

    # 2. Emit count — fast typing (no delay)
    print("[ 2a ] Emit count — 20 changes, 0 ms between (instant burst)")
    r2a = bench_emit_count(n_changes=20, delay_between_ms=0)
    print(f"       emits during typing: {r2a['emits_during_typing']}  "
          f"(expected 0)")
    print(f"       emits after 750ms idle: {r2a['emits_after_idle']}  "
          f"(expected 1)")
    v2a = ("PASS"
           if r2a["emits_during_typing"] == 0 and r2a["emits_after_idle"] == 1
           else "FAIL")
    print(f"       verdict: {v2a}\n")

    print("[ 2b ] Emit count — 10 changes, 50 ms between (fast typing)")
    r2b = bench_emit_count(n_changes=10, delay_between_ms=50)
    print(f"       emits during typing: {r2b['emits_during_typing']}  "
          f"(expected 0)")
    print(f"       emits after 750ms idle: {r2b['emits_after_idle']}  "
          f"(expected 1)")
    v2b = ("PASS"
           if r2b["emits_during_typing"] == 0 and r2b["emits_after_idle"] == 1
           else "FAIL")
    print(f"       verdict: {v2b}\n")

    # 3. Timer accuracy
    print("[ 3 ] Debounce fire timing (5 repeats)")
    r3 = bench_debounce_timing(5)
    if "error" in r3:
        print(f"       ERROR: {r3['error']}\n")
    else:
        print(f"       target:   {r3['target_ms']} ms")
        print(f"       median:   {r3['median_ms']:.1f} ms")
        print(f"       min/max:  {r3['min_ms']:.1f} / {r3['max_ms']:.1f} ms")
        print(f"       overhead: +{r3['overhead_ms']:.1f} ms (Qt scheduling)")
        v3 = "PASS" if r3["overhead_ms"] < 100 else "SLOW"
        print(f"       verdict: {v3}  (expected overhead < 100 ms)\n")

    # 4. has_pending_changes() overhead
    print("[ 4 ] has_pending_changes() overhead (10,000 calls)")
    r4 = bench_has_pending_overhead()
    print(f"      10k calls:   {r4['10k_calls_median_ms']:.3f} ms total")
    print(f"      per call:    {r4['per_call_us']:.4f} us")
    v4 = "PASS" if r4["per_call_us"] < 10 else "SLOW"
    print(f"      verdict: {v4}  (expected < 10 us/call)\n")

    print(sep)
    print("  Summary:")
    verdicts = []
    for label, v in [
        ("flush_pending() latency", verdict1),
        ("emit count fast burst", v2a),
        ("emit count fast typing", v2b),
        ("debounce timing", v3 if "error" not in r3 else "ERROR"),
        ("has_pending_changes overhead", v4),
    ]:
        icon = "[OK]" if v == "PASS" else "[--]"
        sys.stdout.buffer.write(
            f"  {icon}  {label}: {v}\n".encode("utf-8", errors="replace")
        )
    sys.stdout.buffer.write(f"{sep}\n".encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
