# POE2 Filter Studio — UI Scalability Benchmark Report

**Python**: 3.11.9  |  **Platform**: offscreen (no GPU)  |  **Qt**: 6.11.1  |  **Repeats**: 3 (median reported)

> Scroll / Expand operations run without rendering (offscreen).
> Times reflect Qt layout & data-structure cost only, not GPU paint.

## 1. load_rules() — QTreeWidget Build

| Rules | Sections | Tree Items | Median | Min | Max | Peak Mem |
|------:|---------:|-----------:|-------:|----:|----:|---------:|
| 500 | 50 | 550 | 14.9 ms | 14.8 ms | 19.9 ms | 93 KB |
| 1,000 | 100 | 1,100 | 28.4 ms | 27.5 ms | 30.4 ms | 192 KB |
| 3,000 | 300 | 3,300 | 73.8 ms | 69.1 ms | 75.6 ms | 659 KB |
| 5,000 | 500 | 5,500 | 130.7 ms | 111.3 ms | 136.3 ms | 959 KB |
| 10,000 | 1,000 | 11,000 | 283.5 ms | 243.8 ms | 284.3 ms | 1933 KB |

## 2. expandAll() / collapseAll()

| Rules | expandAll Median | collapseAll Median | Sections |
|------:|----------------:|-------------------:|---------:|
| 500 | 16.1 ms | 9.6 ms | 50 |
| 1,000 | 22.6 ms | 22.1 ms | 100 |
| 3,000 | 22.0 ms | 32.6 ms | 300 |
| 5,000 | 42.1 ms | 32.4 ms | 500 |
| 10,000 | 87.6 ms | 66.6 ms | 1,000 |

## 3. Search Highlight (set_highlights + tree refresh)

| Rules | Hits | Median | Min | Max |
|------:|-----:|-------:|----:|----:|
| 500 | 333 | 101 us | 93 us | 31.9 ms |
| 1,000 | 667 | 705 us | 426 us | 73.3 ms |
| 3,000 | 2,000 | 695 us | 641 us | 227.5 ms |
| 5,000 | 3,333 | 932 us | 891 us | 377.3 ms |
| 10,000 | 6,667 | 1.9 ms | 1.8 ms | 762.1 ms |

## 4. Selection Navigation (100 ops)

| Rules | Total Median | Per-Op | Min | Max |
|------:|------------:|-------:|----:|----:|
| 500 | 30.0 ms | 0.30 ms | 26.9 ms | 30.3 ms |
| 1,000 | 29.2 ms | 0.29 ms | 21.2 ms | 30.2 ms |
| 3,000 | 20.1 ms | 0.20 ms | 18.6 ms | 20.4 ms |
| 5,000 | 15.3 ms | 0.15 ms | 13.6 ms | 15.8 ms |
| 10,000 | 18.1 ms | 0.18 ms | 15.3 ms | 21.6 ms |

## 5. Scroll Performance (50 scrollToItem ops)

| Rules | Total Median | Per-Scroll | Min | Max |
|------:|------------:|-----------:|----:|----:|
| 500 | 12.7 ms | 0.25 ms | 11.6 ms | 13.0 ms |
| 1,000 | 11.5 ms | 0.23 ms | 10.2 ms | 11.5 ms |
| 3,000 | 4.2 ms | 0.08 ms | 4.1 ms | 4.6 ms |
| 5,000 | 4.1 ms | 0.08 ms | 4.0 ms | 4.2 ms |
| 10,000 | 5.2 ms | 0.10 ms | 5.2 ms | 5.2 ms |

## 6. Memory Growth (tracemalloc peak, widget + rules)

| Rules | Peak KB | Per-Rule |
|------:|--------:|---------:|
| 500 | 106 KB | 217 B |
| 1,000 | 206 KB | 211 B |
| 3,000 | 667 KB | 228 B |
| 5,000 | 972 KB | 199 B |
| 10,000 | 1954 KB | 200 B |

## 7. Scaling Analysis (500 → 10,000 rules, 20x)

| Operation | Time ratio | Expected | Verdict |
|-----------|:----------:|:--------:|---------|
| load_rules | 19.0x | 20x | ✓ linear |
| expandAll  | 5.4x | 20x | ✓ linear |
| collapseAll | 6.9x | 20x | ✓ linear |
| set_highlights | 19.1x | 20x | ✓ linear |
| select_real_index | 0.6x | 20x | ✓ linear |
| scrollToItem | 0.4x | 20x | ✓ linear |
| Memory | 18.4x | 20x | ✓ linear |

## 8. Conclusions

- **load_rules**: 283.5 ms at 10,000 rules — acceptable, consider progress indicator
- **expandAll**: 87.6 ms at 10,000 rules — acceptable
- **collapseAll**: 66.6 ms at 10,000 rules — acceptable
- **set_highlights**: 1.9 ms at 10,000 rules — fast — no debounce needed
- **select_real_index**: 181 us at 10,000 rules — fast per-op
- **scrollToItem**: 104 us at 10,000 rules — fast per-op
- **Memory**: 1954 KB widget peak at 10,000 rules  (~200 B/rule) — negligible

_Typical real POE2 filters: 200–2000 rules. 5k+ is extreme stress test._