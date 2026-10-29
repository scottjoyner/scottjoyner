# Reproducible research benchmarks

[Research inventory](../RESEARCH.md) · [Harness](bench_research.py) · [Tests](test_bench_research.py) · [Run evidence](results/2026-10-29-x1-370.json)

This is a **synthetic CPU microbenchmark**, not a test of private recordings, private location histories, production Neo4j, ROCm, or real GPU inference. It was run on `x1-370` on 2026-10-29.

## Reproduce

Python 3.9+ standard library only. From the repository root:

```bash
python3 -m unittest discover -s benchmarks -p 'test_bench_research.py' -v
python3 benchmarks/bench_research.py --out /tmp/my-research-bench.json
```

To reproduce the recorded workload explicitly:

```bash
python3 benchmarks/bench_research.py --geo-sizes 1000,10000,50000 \
  --vector-sizes 512,2048,8192 --dimensions 48 \
  --geo-queries 200 --vector-queries 20 --repeats 3 \
  --seed 20261029 --out /tmp/my-research-bench.json
```

The JSON records machine, platform, UTC timestamp, Python version, seed, benchmark source SHA-256, sample sizes, per-call p50/p95 latencies, exactness, vector recall and theoretical payload estimates.

## Results recorded on x1-370

**Runtime:** Python 3.12.3, Linux x86_64 CPU. **Seed:** 20261029. **Status:** PASS. **Unit tests:** 6/6 passed.

**Bench source SHA-256:** `21cceec9904967d6a41c652f69752ca0e793adec9a6f6d8500930c63984914cc`.

### Timestamp event lookup

200 seeded queries × 3 repetitions per size; 30-second regularly spaced synthetic event timestamps. Nearest-event matching prefers earlier timestamps on ties. Index and linear scan agreed on every query.

| Events | Linear scan p50 | Binary-search p50 | p50 speedup | Mismatches |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.031700 ms | 0.000210 ms | 150.95× | 0 |
| 10,000 | 0.329672 ms | 0.000231 ms | 1,427.15× | 0 |
| 50,000 | 1.608799 ms | 0.000290 ms | 5,547.58× | 0 |

**Limits:** This measures nearest-timestamp event-index lookup, not GIS position accuracy, GPS interpolation, trip linkage quality, Neo4j queries, network latency, or index construction. Nanosecond-scale Python timings should not be extrapolated to end-to-end system throughput.

### Float64 versus int8 cosine retrieval

20 queries × 3 repetitions per size; 48-dimensional seeded normalized Gaussian vectors, top-k=5. Both methods use brute-force Python scans. Float64 dot product is the exact reference. Int8 rounds each coordinate to 127× value and uses an integer dot product.

| Vectors | float64 p50 | int8 p50 | int8 recall@5 |
| ---: | ---: | ---: | ---: |
| 512 | 0.719749 ms | 1.880732 ms | 0.970 |
| 2,048 | 2.810919 ms | 7.473986 ms | 0.950 |
| 8,192 | 15.267256 ms | 30.195822 ms | 0.960 |

Theoretical raw vector payload is eight times smaller for int8 than float64 (1 vs. 8 bytes/component), but this excludes Python object overhead, indexes, and RSS. **Int8 ran slower in this unoptimized Python implementation.** These results are not claims about quantized SIMD/FAISS/ROCm implementations or real 384/768-dimensional embedding datasets.

## Research next steps and evidence policy

- Release only explicitly permission-reviewed, de-identified reference datasets. Do not publish raw dashcam media, personal GPS histories, private transcripts, or sensitive traces.
- Benchmark real clip-to-trip alignment against independent labels, including within-50m location accuracy, missing timestamps, mislink rate, and end-to-end p50/p95 latency.
- Compare real 384/768-dimensional embeddings against exact cosine, int8, and indexed retrieval at fixed recall@1/5/10, throughput, RSS, build/update time, and hardware conditions.
- Run GPU/ROCm and MLX comparisons separately with pinned model versions, driver versions, warmup policy, repetition counts, and energy/VRAM logging.
- Preserve failures and negative results. Keep one immutable JSON evidence file per benchmark run. Publication claims must point to the code SHA and primary result evidence.

Related public source: [dashcam vision pipeline](https://github.com/scottjoyner/auto-ingest/blob/main/DASHCAM_VISION_PIPELINE.md) and [location linkage/repair](https://github.com/scottjoyner/auto-ingest/blob/main/patch_missing_locationsv2.py).
