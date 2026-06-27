# POE2 Filter Studio — UI Scalability Benchmark Report

**Python**: 3.11.9  |  **Platform**: offscreen (no GPU)  |  **Qt**: 6.11.1  |  **Repeats**: 3 (median reported)

> Scroll / Expand operations run without rendering (offscreen).
> Times reflect Qt layout & data-structure cost only, not GPU paint.

## 1. load_rules() — QTreeWidget Build

| Rules | Sections | Tree Items | Median | Min | Max | Peak Mem |
|------:|---------:|-----------:|-------:|----:|----:|---------:|
| 500 | 50 | 550 | 16.3 ms | 16.1 ms | 23.7 ms | 91 KB |
| 1,000 | 100 | 1,100 | 22.5 ms | 22.3 ms | 28.1 ms | 192 KB |
| 3,000 | 300 | 3,300 | 71.6 ms | 63.9 ms | 74.5 ms | 650 KB |
| 5,000 | 500 | 5,500 | 97.4 ms | 95.8 ms | 113.8 ms | 940 KB |
| 10,000 | 1,000 | 11,000 | 232.3 ms | 205.8 ms | 239.3 ms | 1897 KB |

## 2. expandAll() / collapseAll()

| Rules | expandAll Median | collapseAll Median | Sections |
|------:|----------------:|-------------------:|---------:|
| 500 | 10.4 ms | 11.6 ms | 50 |
| 1,000 | 11.3 ms | 17.6 ms | 100 |
| 3,000 | 20.4 ms | 18.8 ms | 300 |
| 5,000 | 28.5 ms | 29.5 ms | 500 |
| 10,000 | 70.9 ms | 66.7 ms | 1,000 |

## 3. Search Highlight (set_highlights + tree refresh)

| Rules | Hits | Median | Min | Max |
|------:|-----:|-------:|----:|----:|
| 500 | 333 | 22.8 ms | 22.6 ms | 24.4 ms |
| 1,000 | 667 | 27.8 ms | 24.8 ms | 31.9 ms |
| 3,000 | 2,000 | 62.8 ms | 62.1 ms | 109.4 ms |
| 5,000 | 3,333 | 105.0 ms | 100.2 ms | 264.3 ms |
| 10,000 | 6,667 | 233.0 ms | 229.5 ms | 876.2 ms |

## 4. Selection Navigation (100 ops)

| Rules | Total Median | Per-Op | Min | Max |
|------:|------------:|-------:|----:|----:|
| 500 | 29.8 ms | 0.30 ms | 29.5 ms | 57.7 ms |
| 1,000 | 14.3 ms | 0.14 ms | 12.3 ms | 54.6 ms |
| 3,000 | 12.6 ms | 0.13 ms | 12.4 ms | 120.4 ms |
| 5,000 | 12.3 ms | 0.12 ms | 12.2 ms | 190.5 ms |
| 10,000 | 13.5 ms | 0.13 ms | 12.2 ms | 364.8 ms |

## 5. Scroll Performance (50 scrollToItem ops)

| Rules | Total Median | Per-Scroll | Min | Max |
|------:|------------:|-----------:|----:|----:|
| 500 | 10.4 ms | 0.21 ms | 9.5 ms | 10.5 ms |
| 1,000 | 3.6 ms | 0.07 ms | 3.6 ms | 4.8 ms |
| 3,000 | 3.6 ms | 0.07 ms | 3.6 ms | 4.7 ms |
| 5,000 | 3.9 ms | 0.08 ms | 3.6 ms | 4.2 ms |
| 10,000 | 4.0 ms | 0.08 ms | 3.9 ms | 4.0 ms |

## 6. Memory Growth (tracemalloc peak, widget + rules)

| Rules | Peak KB | Per-Rule |
|------:|--------:|---------:|
| 500 | 103 KB | 210 B |
| 1,000 | 204 KB | 209 B |
| 3,000 | 658 KB | 225 B |
| 5,000 | 954 KB | 195 B |
| 10,000 | 1909 KB | 195 B |

## 7. Scaling Analysis (500 → 10,000 rules, 20x)

| Operation | Time ratio | Expected | Verdict |
|-----------|:----------:|:--------:|---------|
| load_rules | 14.3x | 20x | ✓ linear |
| expandAll  | 6.8x | 20x | ✓ linear |
| collapseAll | 5.8x | 20x | ✓ linear |
| set_highlights | 10.2x | 20x | ✓ linear |
| select_real_index | 0.5x | 20x | ✓ linear |
| scrollToItem | 0.4x | 20x | ✓ linear |
| Memory | 18.6x | 20x | ✓ linear |

## 8. Conclusions

- **load_rules**: 232.3 ms at 10,000 rules — acceptable, consider progress indicator
- **expandAll**: 70.9 ms at 10,000 rules — acceptable
- **collapseAll**: 66.7 ms at 10,000 rules — acceptable
- **set_highlights**: 233.0 ms at 10,000 rules — ⚠ slow — consider background refresh
- **select_real_index**: 135 us at 10,000 rules — fast per-op
- **scrollToItem**: 79 us at 10,000 rules — fast per-op
- **Memory**: 1909 KB widget peak at 10,000 rules  (~195 B/rule) — negligible

_Typical real POE2 filters: 200–2000 rules. 5k+ is extreme stress test._