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

## Eight-host fleet replication: compiled 384-dimensional vector scans

**2026-10-29 — eight Linux nodes, 11 compiled runs, all PASS.** [Machine-readable fleet summary](results/2026-10-29-fleet-summary.json) · [Evidence folder](results/) · [C benchmark source](bench_vector.c) · [summary generator](summarize_results.py).

This is a **different and more representative compute implementation** than the pure-Python experiment above. It stores 384-dimensional normalized synthetic vectors as either float32 or quantized int8 and scans them using portable C compiled with `gcc -O3 -Wall -Wextra -std=c11 -lm`. Float32 uses float32 accumulation; int8 uses integer accumulation. Results compare ranking overlap against the same workload's exact float32 scan. **This is still CPU-only brute-force search, not GPU/ROCm, Neo4j, LLM inference or an indexed ANN system.**

| Node | Float32 p50 | Int8 p50 | Int8 speedup | Raw evidence |
| --- | ---: | ---: | ---: | --- |
| xwing | 1.498 ms | 0.731 ms | 2.05× | [JSON](results/2026-10-29-xwing-compiled-8192x384.json) |
| joyner (R9700 host, CPU only) | 1.641 ms | 0.424 ms | 3.87× | [JSON](results/2026-10-29-joyner-compiled-8192x384.json) |
| x1-370 | 1.663 ms | 0.559 ms | 2.98× | [JSON](results/2026-10-29-x1-370-compiled-8192x384.json) |
| OptiPlex 9030 | 2.610 ms | 1.064 ms | 2.45× | [JSON](results/2026-10-29-scott-optiplex-9030-aio-compiled-8192x384.json) |
| Deathstar XPS | 3.573 ms | 1.077 ms | 3.32× | [JSON](results/2026-10-29-deathstar-xps-8920-compiled-8192x384.json) |
| Lenovo 330S | 3.694 ms | 1.091 ms | 3.39× | [JSON](results/2026-10-29-scott-lenovo-ideapad-330s-15ikb-compiled-8192x384.json) |
| Destroyer | 4.310 ms | 1.305 ms | 3.30× | [JSON](results/2026-10-29-destroyer-compiled-8192x384.json) |
| Raspberry Pi | 7.533 ms | 3.619 ms | 2.08× | [JSON](results/2026-10-29-raspberrypi-compiled-8192x384.json) |

The same 8,192-vector, 384-dimensional workload used 24 seeded queries × 3 repetitions with top-k=5. **Int8 recall@5 was 0.908333 on every host** because the inputs were generated deterministically and identically; it is not eight independent accuracy samples. Float32 raw vector payload: 12 MiB; int8: 3 MiB (4× lower raw storage). Actual memory usage, index overhead, and quantization setup costs were not measured.

### Scaling to 32,768 vectors

12 seeded queries × 2 repetitions, 384 dimensions. Recall@5 **0.883333** on all three systems (same deterministic inputs).

| Node | Float32 p50 | Int8 p50 | Speedup | Evidence |
| --- | ---: | ---: | ---: | --- |
| xwing | 5.348 ms | 2.600 ms | 2.06× | [JSON](results/2026-10-29-xwing-compiled-32768x384.json) |
| joyner | 6.566 ms | 1.703 ms | 3.86× | [JSON](results/2026-10-29-joyner-compiled-32768x384.json) |
| x1-370 | 6.654 ms | 2.210 ms | 3.01× | [JSON](results/2026-10-29-x1-370-compiled-32768x384.json) |

### Reproduction and compiler caveats

From the repository root:

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_vector.c -lm -o /tmp/bench_vector
nice -n 12 /tmp/bench_vector 8192 384 24 3
nice -n 12 /tmp/bench_vector 32768 384 12 2
python3 benchmarks/summarize_results.py --directory benchmarks/results --date 2026-10-29
```

Pinned compiled C source commit: [`1fbfc9d`](https://github.com/scottjoyner/scottjoyner/blob/1fbfc9d1a343890cc525708379d101da7ba0730d/benchmarks/bench_vector.c); SHA-256 `e443f9e8d794f53f11fe1b3f66dfd5b7013e98a14d3d00dac601691ef7a60aea`. The generator uses SplitMix64 to avoid correlations found in an earlier rejected exploratory LCG run; rejected results were **not published**. The C benchmark also checks top-k ranking validity and duplicate/invalid hits. Int8 accuracy is lower than float32 by design; a PASS indicates that the program ran and passed sanity checks, not that it had perfect retrieval accuracy.

The Raspberry Pi's default GCC 14.2.0 crashed inside its AArch64/SVE compiler initialization. Its evidence was successfully produced with **GCC 13.3.0** instead, using the same source and optimization flags. No compiler or package replacement was performed. The MacBook Air could not be accessed with existing passwordless SSH and was excluded. Every benchmark ran at reduced scheduling priority without stopping running models.

Per-host results are exploratory one-session timings on machines with different CPUs, versions of GCC and varying concurrent workloads. They should not be taken as controlled hardware rankings, robust statistical confidence intervals, or paper-ready performance claims without repeatability runs, temperature/power monitoring, and warmup/load controls.

## Five-seed 768-dimensional replication (2026-10-29)

[Six-host, 30-run raw JSON](results/2026-10-29-768d-multiseed.json) · [Seed-enabled C source](bench_vector.c) · [Evidence validator](check_multiseed.py)

**Scope:** Synthetic CPU-only brute-force search, not real dashcam embeddings, SensorGraft/Neo4j or ROCm. Six Linux hosts ran five common SplitMix64 seeds (20261029–20261033) at reduced process priority, giving **30 successful runs but only five independent datasets**. Each seed generated 8,192 normalized 768-dimensional vectors; ranking accuracy used 12 queries × 2 repetitions and top-k=5, with float32 retrieval as the exact baseline.

**Recall@5 by seed:** 0.900000, 0.833333, 0.783333, 0.866667, 0.816667. **Mean 0.840000**, range 0.783333–0.900000. Variation is due to different synthetic data and shows real quantization accuracy cost. A PASS means validation and execution passed, not that retrieval accuracy is sufficient for production.

| CPU node | Float32 median p50 | Int8 median p50 | Ratio |
| --- | ---: | ---: | ---: |
| x1-370 | 3.565 ms | 1.189 ms | 3.00× |
| Deathstar | 6.756 ms | 1.987 ms | 3.40× |
| Destroyer | 7.999 ms | 2.329 ms | 3.43× |
| Lenovo 330S | 7.573 ms | 2.159 ms | 3.51× |
| OptiPlex | 5.363 ms | 2.109 ms | 2.54× |
| Raspberry Pi | 14.919 ms | 7.021 ms | 2.13× |

Median of five per-seed median latencies, not one pooled timing. Background load and power management are uncontrolled. The identical seed accuracy across hosts is a reproducibility check, not 30 independent evaluations.

**Pinned benchmark source:** [commit 0e9de945](https://github.com/scottjoyner/scottjoyner/blob/0e9de94548b1c6475f5658fe8e72952cf893c45f/benchmarks/bench_vector.c); SHA-256: 439281cc5c46379571596437dc96f9aebc5e6b0ffd85be163a457e7c779caa73.

Reproduction commands:

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_vector.c -lm -o /tmp/bench_vector
for seed in 20261029 20261030 20261031 20261032 20261033; do
  nice -n 15 /tmp/bench_vector 8192 768 12 2 "$seed"
done
python3 benchmarks/check_multiseed.py benchmarks/results/2026-10-29-768d-multiseed.json
```

On the Raspberry Pi, GCC 13 was used after the system GCC 14 crashed during compilation; no compiler settings were modified. The joyner host was skipped due to severely constrained available RAM, xwing due to a busy GPU, and MacBook Air due to lack of passwordless SSH access.

### GPU readiness, not GPU benchmarking

- **joyner:** AMD GPU and /dev/kfd exposed, but HIP/ROCm tools were absent in the active shell and host RAM was critically constrained. No GPU tests performed.
- **xwing:** ROCm tools present but GPU utilization measured at 100%; skipped to avoid contention.
- **x1-370:** ROCm device discovery worked, but the hipcc wrapper failed due to missing clang-17 and rocm_agent_enumerator paths. No change to production ROCm configuration.

No GPU throughput, real embedding accuracy, real GPS quality, production Neo4j query latency, memory RSS, ANN performance, or end-to-end RAG benchmark is established by these runs.

## Two-stage int8 shortlist + float32 reranking (2026-10-29)

This research prototype uses the CPU for an int8 **top-160 candidate scan** over 8,192 vectors × 768 dimensions, then rescoring the first 5, 10, 20, 40, 80, or 160 candidate IDs using the original float32 vectors. There is no graph database, ANN index or GPU execution in these tests.

**Evidence:** [30-run, six-host independent-vector study](results/2026-10-29-rerank-multiseed.json) · [30-run, three-host correlated/clustered stress study](results/2026-10-29-rerank-stress-multiseed.json).

**Source and validators:** [C prototype](bench_rerank.c) · [validator](check_rerank.py) · [correlated/clustered C variant](bench_rerank_stress.c) · [stress validator](check_rerank_stress.py). Both validator programs passed on the locally saved evidence.

Mean top-five recall versus exact float32, calculated over **five distinct seeds for each synthetic distribution** (12 query vectors × 2 repeated timings per seed). Identical seeds on multiple machines verify reproducibility, not additional independent data:

| Int8 shortlist reranked | Independent Gaussian | Temporal-correlation control | Clustered-vector control |
| ---: | ---: | ---: | ---: |
| 5 | 84.00% | 98.00% | 70.33% |
| 10 | 98.00% | 100.00% | 87.67% |
| 20 | 100.00% | 100.00% | 97.33% |
| 40 | 100.00% | 100.00% | 99.33% |
| 80 | 100.00% | 100.00% | 99.67% |
| 160 | 100.00% | 100.00% | 100.00% |

**Finding:** Using 20 candidates restored all exact top-five neighbors in the *independent* and *temporal* synthetic controls, but missed some neighbors in *clustered* synthetic vectors. M=80 reached 99.67% mean recall in the clustered control; M=160 reached 100% on the five tested clustered seeds. **These figures are not a guarantee or a production tuning threshold.**

The shortlisted approximate stage alone measured about 1.2 ms median on x1-370 for 8,192 × 768 vectors in the initial run versus about 3.5 ms for the exact float32 full scan. Reranking the 20-item shortlist added roughly 0.01 ms. The JSON field `approx_plus_rerank_p50_ms_estimate` explicitly denotes **sum of individually measured median components**, *not* a directly measured end-to-end percentile. An initial x1-370 run measured around 19 ms to quantize vectors plus query vectors, which is **excluded** from search latency. Real system evaluation must include indexing, embedding generation, quantization, updates, I/O and request overhead.

Reproduce an independent-vector trial:

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_rerank.c -lm -o /tmp/bench_rerank
nice -n 15 /tmp/bench_rerank 8192 768 12 2 20261029
python3 benchmarks/check_rerank.py benchmarks/results/2026-10-29-rerank-multiseed.json
```

Reproduce the clustered and temporal controls:

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_rerank_stress.c -lm -o /tmp/bench_rerank_stress
nice -n 15 /tmp/bench_rerank_stress 8192 768 12 2 20261029 clustered
nice -n 15 /tmp/bench_rerank_stress 8192 768 12 2 20261029 temporal
python3 benchmarks/check_rerank_stress.py benchmarks/results/2026-10-29-rerank-stress-multiseed.json
```

**Limitations:** The temporal control consists of locally correlated, normalized synthetic frames; the clustered control consists of 32 seeded synthetic centroids. Neither distribution is validated against real dashcam frame embeddings, GPS traces or user data. Candidate selection pays the full top-160 scan cost even when evaluating smaller M, deliberately holding the first-stage search fixed. It should be benchmarked against separate top-M indexes, exact vector search, ANN, and mixed-precision kernels before deploying an adaptive shortlist. GCC 13 was used on the Raspberry Pi after an unrelated GCC 14 compiler crash. Real retrieval tests require an explicitly approved, de-identified corpus.
