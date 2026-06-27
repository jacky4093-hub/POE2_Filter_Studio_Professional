# POE2 Filter Studio — Performance Benchmark Report

**Python**: 3.11.9  |  **Platform**: win32  |  **Repeats**: 5 (median reported)

## Parse Time

| Rules | Text Size | Median | Min | Max | Throughput | Peak Memory |
|------:|----------:|-------:|----:|----:|-----------:|------------:|
| 1,000 | 99 KB | 6.4 ms | 5.9 ms | 6.7 ms | 111 K/s | 1160 KB |
| 5,000 | 486 KB | 34.9 ms | 31.4 ms | 36.3 ms | 100 K/s | 5660 KB |
| 10,000 | 970 KB | 63.1 ms | 58.2 ms | 76.9 ms | 112 K/s | 11369 KB |
| 20,000 | 1963 KB | 140.6 ms | 133.0 ms | 147.9 ms | 100 K/s | 22844 KB |

## Section Map Rebuild

| Rules | Sections | Median | Min | Max | Throughput |
|------:|---------:|-------:|----:|----:|-----------:|
| 1,000 | 74 | 1.1 ms | 1.0 ms | 1.4 ms | 636 K/s |
| 5,000 | 352 | 4.8 ms | 4.3 ms | 5.9 ms | 726 K/s |
| 10,000 | 686 | 10.3 ms | 10.1 ms | 11.6 ms | 685 K/s |
| 20,000 | 1402 | 19.6 ms | 19.1 ms | 22.2 ms | 716 K/s |

## Search Time

### Query: `Currency`

| Rules | Hits | Median | Min | Max | Throughput |
|------:|-----:|-------:|----:|----:|-----------:|
| 1,000 | 79 | 2.7 ms | 2.6 ms | 2.9 ms | 257 K/s |
| 5,000 | 452 | 12.2 ms | 11.0 ms | 13.5 ms | 285 K/s |
| 10,000 | 916 | 25.0 ms | 24.3 ms | 25.6 ms | 282 K/s |
| 20,000 | 1,868 | 45.3 ms | 43.2 ms | 46.0 ms | 310 K/s |

### Query: `Show`

| Rules | Hits | Median | Min | Max | Throughput |
|------:|-----:|-------:|----:|----:|-----------:|
| 1,000 | 487 | 1.0 ms | 931 us | 1.1 ms | 676 K/s |
| 5,000 | 2,440 | 4.1 ms | 3.7 ms | 5.0 ms | 849 K/s |
| 10,000 | 4,877 | 9.0 ms | 8.9 ms | 10.4 ms | 780 K/s |
| 20,000 | 9,834 | 16.8 ms | 16.5 ms | 17.9 ms | 835 K/s |

### Query: `ItemLevel`

| Rules | Hits | Median | Min | Max | Throughput |
|------:|-----:|-------:|----:|----:|-----------:|
| 1,000 | 314 | 1.9 ms | 1.9 ms | 2.0 ms | 372 K/s |
| 5,000 | 1,589 | 7.9 ms | 7.0 ms | 8.3 ms | 442 K/s |
| 10,000 | 3,223 | 16.6 ms | 15.9 ms | 18.2 ms | 424 K/s |
| 20,000 | 6,281 | 32.1 ms | 31.9 ms | 33.7 ms | 437 K/s |

## Export Time

| Rules | Output Size | Median | Min | Max | Throughput |
|------:|------------:|-------:|----:|----:|-----------:|
| 1,000 | 99 KB | 1.5 ms | 1.4 ms | 2.0 ms | 464 K/s |
| 5,000 | 486 KB | 6.5 ms | 6.2 ms | 7.2 ms | 532 K/s |
| 10,000 | 970 KB | 15.5 ms | 14.8 ms | 15.8 ms | 456 K/s |
| 20,000 | 1963 KB | 28.9 ms | 27.7 ms | 31.0 ms | 485 K/s |

## Memory (tracemalloc peak during parse)

| Rules | Peak KB | Per-Rule bytes |
|------:|--------:|---------------:|
| 1,000 | 1160 KB | 1682 B |
| 5,000 | 5660 KB | 1663 B |
| 10,000 | 11369 KB | 1652 B |
| 20,000 | 22844 KB | 1665 B |

## Scaling Analysis

Rules scale factor: 20×  (1,000 → 20,000)

| Stage | Time ratio | Expected (linear) | Verdict |
|-------|:----------:|:-----------------:|---------|
| Parse | 22.1× | 20× | ✓ linear |
| Section rebuild | 17.7× | 20× | ✓ linear |
| Search 'Currency' | 16.5× | 20× | ✓ linear |
| Export | 19.0× | 20× | ✓ linear |

## Conclusions

Verdicts use 20k-rule median as the worst case:
- **Parse**: 140.6 ms at 20k rules — acceptable (< 200 ms)
- **Section rebuild**: 19.6 ms at 20k rules — fast, safe to call on every mutation
- **Search**: 45.3 ms at 20k rules — consider 150 ms keystroke debounce
- **Export**: 28.9 ms at 20k rules — acceptable
- **Memory**: ~22844 KB peak at 20k rules (~1665 B / rule) — negligible
