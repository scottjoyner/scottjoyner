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

## Directly timed int8 shortlist + float32 reranking (2026-10-29)

**Evidence:** [45 completed synthetic CPU runs over three hosts](results/2026-10-29-rerank-direct-multihost.json) · [end-to-end C timing harness](bench_rerank_direct.c) · [evidence validator](check_rerank_direct.py). The validator passed on x1-370.

This corrects an important limitation of the earlier shortlist study: each candidate count **5/10/20/40/80/160** independently executes a full int8 scan over 8,192 768-dimensional vectors **and** float32 reranking for that query. The benchmark times the full search operation directly, and reports separate stage measurements. Its per-query timing **does not include** one-time quantization, embedding generation, database reads, network transfer, index construction or updates. The quantization step is reported separately in raw JSON.

Three Linux CPU hosts × three synthetic distributions (independent, temporal, clustered) × five seeded datasets yielded **45 successful measured runs representing 15 distinct data cases**. Each case used 12 queries and two timing repetitions; identical seeded datasets across hosts confirm recall reproducibility, not independent recall samples.

### Clustered synthetic vectors: five-seed results

| Host | Exact float32 p50 | Int8 + float32 rerank 20 p50 | Recall@5, M20 | Int8 + float32 rerank 160 p50 | Recall@5, M160 |
| --- | ---: | ---: | ---: | ---: | ---: |
| x1-370 | 3.559 ms | 1.213 ms | 97.33% | 1.397 ms | 100% |
| Deathstar XPS | 6.825 ms | 2.013 ms | 97.33% | 2.208 ms | 100% |
| Raspberry Pi | 14.775 ms | 6.928 ms | 97.33% | 7.482 ms | 100% |

Each latency is the **median of five independent-seed p50 timings** for that method on that host. M160 achieved 100% top-5 ranking overlap **only on these five clustered synthetic seeds**; it is not a claim of perfect accuracy on real media embeddings. Top-160 vs float32 p50 ratios on this study are approximately 2.55×, 3.09× and 1.97× for x1-370, Deathstar and Raspberry Pi respectively.

For the same seeds, the **independent and temporal** cases both achieved 100% recall@5 using M20; the **clustered** case reached only 97.33%. An adaptive policy should therefore be tested on genuinely held-out real embeddings before publication, not be advertised from training-set or small synthetic calibration alone.

### Reproduction

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_rerank_direct.c -lm -o /tmp/bench_rerank_direct
nice -n 15 /tmp/bench_rerank_direct 8192 768 12 2 20261029 clustered
python3 benchmarks/check_rerank_direct.py benchmarks/results/2026-10-29-rerank-direct-multihost.json
```

Pinned implementation: [source commit 845d0604](https://github.com/scottjoyner/scottjoyner/blob/845d0604f7abc672af699424c01ebea9ed9f493d/benchmarks/bench_rerank_direct.c); source SHA-256 `6d18da89bdba1c07cfbd970c936327903701d81ef3bef542c344c6fc99c27fec`. Raspberry Pi used GCC 13 due to an earlier compiler issue with GCC 14. No active model services were stopped.

**Do not generalize this to GPU or vector DB speed:** all results are CPU brute-force retrieval on synthetic vectors. Profile-accurate confidence intervals, full pipeline latency, memory allocation/RSS, read/update throughput, index selection, precision-recall curves on actual data, and ROCm results remain unmeasured.

## 32,768-vector scale-up: directly measured rerank latencies

[Ten raw x1-370 synthetic CPU trials](results/2026-10-29-rerank-direct-32768-x1-370.json) · [validator](check_rerank_scale.py) · [timed source code](bench_rerank_direct.c)

The same seed-enabled C benchmark was rerun on **32,768 normalized synthetic vectors × 768 dimensions**, five independent seeds each for independent and clustered distributions, 12 queries × 2 timing repeats per seed. The source remains pinned at [commit 845d0604](https://github.com/scottjoyner/scottjoyner/blob/845d0604f7abc672af699424c01ebea9ed9f493d/benchmarks/bench_rerank_direct.c) and SHA-256 `6d18da89bdba1c07cfbd970c936327903701d81ef3bef542c344c6fc99c27fec`.

| Metric | Independent vectors | Clustered vectors |
| --- | ---: | ---: |
| Exact float32 p50, median of seeds | 14.110 ms | 14.061 ms |
| Direct int8 scan + float32 rerank 160 p50, median of seeds | 4.898 ms | 4.886 ms |
| Mean top-5 recall, M=20 | 100.00% | 95.67% |
| Mean top-5 recall, M=40 | 100.00% | 99.00% |
| Mean top-5 recall, M=80 | 100.00% | 99.33% |
| Mean top-5 recall, M=160 | 100.00% | 100.00% |
| Pre-search vector/query quantization, median | 79.170 ms | 79.189 ms |

At this size the direct M160 query is **about 2.88× faster** in its seeded median than an exact float32 scan, on this one CPU host. The quantization timing is reported separately and excluded from query p50, as are embedding generation, index build/update, database overhead and network costs. Its measured one-time 79 ms cost should be amortized (or explicitly included) before suggesting an end-to-end production speedup.

The evidence validator passed. Independent or clustered synthetic vectors are not real dashcam embeddings, and M160's observed 100% recall is not a universal guarantee. This benchmark is CPU-only and has no published arXiv, ROCm, Neo4j or SensorGraft GPU performance claim.

To reproduce this larger workload:

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_rerank_direct.c -lm -o /tmp/bench_rerank_direct
nice -n 15 /tmp/bench_rerank_direct 32768 768 12 2 20261029 clustered
python3 benchmarks/check_rerank_scale.py
```

## Held-out policy validation: two-stage evaluation (2026-10-29)

This sequence intentionally records **failures and revisions**, rather than tuning on test data while reporting the same scores as confirmation.

**Primary artifacts:** [80-trial first held-out dataset](results/2026-10-29-holdout-frozen-policy.json) · [40-trial second held-out dataset](results/2026-10-29-policy-v2-second-holdout.json) · [calibration/first holdout runner](bench_holdout.py) · [V2 second-holdout runner](bench_policy_v2.py) · [independent validators](check_holdout.py) and [V2 validator](check_policy_v2.py). Validators recompute outcomes from recorded per-trial evidence; the first validator also reconstructs the selected policy from the previously committed calibration files.

### Phase 1: freeze 99% recall thresholds from original five seeds

The original calibration used seeds 20261029–20261033. For each workload/distribution, the policy chose the **smallest** shortlist M whose exact top-five hit count reached at least **99% aggregate calibration recall**. The policy was then frozen, before using the first held-out seeds beginning at 20261034.

| Dataset | Calibration-selected M | First held-out tests | Held-out recall@5 | 99% target |
| --- | ---: | ---: | ---: | --- |
| 8,192 independent vectors | 20 | 20 distinct seeds | 100.00% | Pass |
| 8,192 temporally correlated vectors | 10 | 20 distinct seeds | 100.00% | Pass |
| 8,192 clustered vectors | 40 | 20 distinct seeds | 99.33% | Pass |
| 32,768 independent vectors | 10 | 10 distinct seeds | **98.67%** | **FAIL** |
| 32,768 clustered vectors | 40 | 10 distinct seeds | **98.33%** | **FAIL** |

All **80 synthetic CPU trial executions passed correctness/sanity checks**, but the two large-workload selection policies failed their desired *accuracy* target. These are intentionally different checks. The first holdout used 20 seeds at 8,192 vectors × 3 distributions plus 10 seeds at 32,768 vectors × 2 distributions. The five original calibration seeds were excluded. Each trial used 12 queries × 2 timing repeats and top-k=5.

### Phase 2: more conservative policy, then a second untouched holdout

After observing the first holdout, a more conservative V2 policy was fixed **before** evaluating seeds 20261054–20261073. This second set contains 20 seeds per mode at 32,768 vectors × 768 dimensions, giving 40 newly run synthetic CPU trials.

| 32,768-vector distribution | Prior M (second set) | Prior recall@5 | Revised fixed M | Revised recall@5 | V2 passes 99%? |
| --- | ---: | ---: | ---: | ---: | --- |
| Independent | 10 | 98.50% | 20 | **99.83%** | Yes |
| Clustered | 40 | 99.08% | 80 | **99.92%** | Yes |

The revised policy measured approximate **3.07×** and **2.89×** median synthetic CPU query speedups versus the full float32 scan for independent and clustered vectors. These are nominal ratios of observed per-seed p50 medians on one host, not controlled performance confidence bounds. One-time vector/query quantization, embedding generation, persistence, network transfer and database indexing are excluded from query latency and should be included in end-to-end planning.

**Research interpretation:** A calibration set of five seeds was inadequate to ensure 99% recall on the first large held-out set. Enlarging M and testing on a **new, disjoint second holdout** provided better evidence of acceptable synthetic recall, but the new setting is not proven safe on real embeddings or unseen distributions. The simulated distribution class is supplied as an oracle label; this work **does not implement an automatic per-query distribution classifier**, a production adaptive router or an online safety/recall guarantee. The top-five hit count is not a statistically independent sample of actual dashcam retrieval quality.

Reproduce the first trial series (requires the two pinned, previously published calibration receipts):

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_rerank_direct.c -lm -o /tmp/bench_rerank_direct
nice -n 15 python3 benchmarks/bench_holdout.py --binary /tmp/bench_rerank_direct \
  --c-source benchmarks/bench_rerank_direct.c \
  --small-calibration benchmarks/results/2026-10-29-rerank-direct-multihost.json \
  --large-calibration benchmarks/results/2026-10-29-rerank-direct-32768-x1-370.json \
  --small-seeds 20 --large-seeds 10 --output /tmp/bench-holdout.json
python3 benchmarks/check_holdout.py
```

Reproduce the *separately fixed* revised policy on the second seed range:

```bash
nice -n 15 python3 benchmarks/bench_policy_v2.py \
  --binary /tmp/bench_rerank_direct --source benchmarks/bench_rerank_direct.c \
  --count 20 --out /tmp/bench-policy-v2.json
python3 benchmarks/check_policy_v2.py
```

**Next validation gate:** explicitly approved real embedding datasets with temporal train/test separation, corrupted GPS/clip cases, a measured distribution-difficulty classifier or distribution-agnostic policy, and a full precompute/update/CPU/GPU/DB cost model. Do not promote the synthetic M20/M80 settings to a production contract.

## Query-only adaptive shortlist: frozen score-margin calibration and unseen seeds (2026-10-29)

**Goal:** Choose M=20, 40, 80, or 160 using **only the quantized top-160 score distribution**. No distribution label, actual video/location data, float32 reference result, or learned classifier is supplied at retrieval time. This replaces the previous oracle-labeled synthetic policy *only in a new standalone benchmark*, not in deployed SensorGraft.

**Source:** [compiled C query policy](bench_score_margin.c) · [frozen threshold calibration receipt](results/2026-10-29-score-margin-calibration.json) · [holdout runner](bench_margin_holdout.py) · [held-out raw evidence](results/2026-10-29-score-margin-holdout.json) · [independent calibration/holdout validator](check_margin_policy.py).

### Policy and calibration

For each query, scan int8 embeddings for its best 160 quantized matches, then inspect the normalized gap between the 5th-ranked and the 20th/40th/80th-ranked int8 scores. Choose the **smallest** M in {20,40,80} whose gap exceeds the frozen threshold; otherwise rerank M=160 candidate vectors in the original float32 representation. The choice uses only quantized scores. The exact float32 top-five oracle is computed separately for *evaluation*, never for the choice.

Original calibration seeds 20261029–20261033 yielded 25 seeded CPU runs and **300 distinct query cases** spanning 8,192- and 32,768-vector synthetic datasets. A grid search over thresholds 0.0000–0.0100 in 0.0001 increments minimized mean M subject to **at least 99.5% aggregate top-five recall** and **at least 99% recall within every dataset-size/distribution group**. The selected and separately committed threshold was **0.0064**, with 99.8% aggregate calibration recall and a mean of 36.53 candidates. The threshold was committed before evaluating new seeds.

### Disjoint synthetic holdout

New seeds 20261100–20261115 had not been used in prior calibration or earlier 202610xx holdouts. Five workload/distribution groups × 16 seeds gave **80 successful CPU executions and 960 query cases** (12 queries per case, 2 timing repetitions; top-k=5). The pinned C source SHA-256 is `ce4fa7173f7237fcdc5460671c9d8643685679bec4f0547dfe3b039bb95ffac0` and commit [5d723b51](https://github.com/scottjoyner/scottjoyner/blob/5d723b513186601ce1b0d0cc25c136da08db81da/benchmarks/bench_score_margin.c). The independent validator recomputed the threshold choice from the raw calibration and checked all 960 held-out decisions.

| Workload (768D synthetic) | Mean chosen M | Top-five recall on unseen seeds | Nominal exact-float32 / adaptive query-speed ratio |
| --- | ---: | ---: | ---: |
| 8,192 independent | 20.0 | 100.00% | 2.84× |
| 8,192 temporal | 20.0 | 100.00% | 2.88× |
| 8,192 clustered | 43.8 | 100.00% | 2.84× |
| 32,768 independent | 20.0 | 100.00% | 2.96× |
| 32,768 clustered | 69.3 | 99.58% | 2.92× |

**Interpretation:** All five *synthetic* workload groups exceeded 99% aggregate recall on the disjoint seeds, but the harder clustered 32,768-vector case still missed several exact top-five results. No guaranteed bound, statistically representative field accuracy, per-query SLA, actual dashcam embedding evaluation, production ANN/index improvement or GPU result was established. Disjoint seeds still use the same toy data-generator families.

### Essential matched control: is adaptation itself actually faster?

[Forty matched seed/workload A/B pairs](results/2026-10-29-score-margin-vs-fixed160.json) · [paired validator](check_margin_comparison.py). Same C kernel, same generator and same seeds, with test order alternated by seed parity. Comparison: frozen adaptive threshold versus a high threshold that **always chooses M=160**. Both methods first compute the same full top-160 int8 scan, so the only possible savings are in the float32 rescoring phase. These are matched *timing controls on seeds already included in the held-out evaluation*, not new independent accuracy evidence.

| Workload | Median paired fixed160/adaptive ratio | Adaptive hits | Fixed160 hits |
| --- | ---: | ---: | ---: |
| 8,192 independent | 1.091× | 480/480 | 480/480 |
| 8,192 temporal | 1.071× | 480/480 | 480/480 |
| 8,192 clustered | 1.066× | 480/480 | 480/480 |
| 32,768 independent | 1.027× | 480/480 | 480/480 |
| 32,768 clustered | 1.019× | 479/480 | 480/480 |

**Negative result / important tradeoff:** Relative to an already-quantized fixed-M160 search, adapting M saved only about **2–9%** in these noisy paired CPU timings and missed one of 480 exact neighbors in the 32,768 clustered timing control, versus zero misses for fixed160. The larger ~2.9× ratios compare adaptive int8 retrieval with **full exact float32 scanning**, not with fixed160. Given modest incremental gain, fixed160 is the simpler candidate for future *evaluation* while a real-world safety/accuracy and profiling gate remains open; **neither should replace production exact search yet**.

### Reproduce

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_score_margin.c -lm -o /tmp/bench_score_margin
/tmp/bench_score_margin 8192 768 12 2 20261100 clustered 0.0064
python3 benchmarks/check_margin_policy.py
python3 benchmarks/check_margin_comparison.py
```

Live GPU/ROCm, real dashcam/GNSS validation, SensorGraft integration, quantization of actual model-derived embeddings, and end-to-end network/DB latency were **not executed** in this series. All benchmarks ran on synthetic CPU workloads, at reduced process priority, without stopping existing services. Query timing excludes one-time quantization, embedding generation, indexing and persistence. GPU resource contention and disk pressure remain deployment constraints.

## Per-vector 8-bit scaling: held-out synthetic CPU comparison (2026-10-29)

The earlier retrieval prototype quantized normalized vectors as `round(x * 127)` with the same fixed scale for every vector. At 768 dimensions, many normalized components are much smaller than 1.0, making this a needlessly coarse quantization scheme. This new study compares that baseline against **symmetric int8 per-vector absmax scaling**, `scale = max(abs(x_i)) / 127`, with each normalized vector's own 4-byte float32 scale. Search uses the int8 dot product *multiplied by the candidate vector's scale*. The query's scale is constant for all candidates in that query, so it is omitted from the relative-score comparison. The original float32 vectors remain available for exact candidate reranking. This is not an LLM-weight quantization result.

### Recorded results

Source: [C implementation](bench_quant_scales.c) at [commit ad6abd06](https://github.com/scottjoyner/scottjoyner/blob/ad6abd06b1ebfb2814044870789f6a03bf420c46/benchmarks/bench_quant_scales.c), SHA-256 `b95bf19e86cc24f3c360eef782f0e357e6ec63bf61f4cd269070413d5f738e50`.

Evidence: [60 seeded x1-370 trials](results/2026-10-29-quant-scales-60case-holdout.json) · [25 CPU peer-replication trials](results/2026-10-29-quant-scales-peer.json) · [single-host data validator](check_quant_scales.py) · [peer-replication validator](check_quant_peers.py) · [frozen trial runner](run_quant_scales.py). Both validators passed. The same ten fresh seeds (20261120–20261129) were used for the six primary CPU workloads, with 12 queries × two latency repetitions per seed. Each group had 600 top-five hit opportunities. For peer replication, five new seeds (20261130–20261134) were replayed across three other machines; repeated copies of an identical seed do not constitute new independent datasets.

| 768D synthetic workload | Fixed global-scale int8 + float32 rerank 20 recall@5 | Per-vector absmax int8 + float32 rerank 20 recall@5 | Per-vector direct query p50* |
| --- | ---: | ---: | ---: |
| 8,192 independent | 100.00% | **100.00%** | 1.211 ms |
| 8,192 temporal | 100.00% | **100.00%** | 1.210 ms |
| 8,192 clustered | 96.83% | **100.00%** | 1.215 ms |
| 32,768 independent | 100.00% | **100.00%** | 7.205 ms |
| 32,768 temporal | 100.00% | **100.00%** | 4.892 ms |
| 32,768 clustered | 95.50% | **100.00%** | 4.865 ms |

`*` Median across seed-specific p50 timings, not a controlled system-wide timing distribution; 32,768-independent timings were affected by variable host load. Each M value uses an independently timed **int8 top-M full scan plus float32 reranking**, not the sum of two separate medians. Results are exploratory, not a production SLA. Per-vector scaling added no material median latency in the observed pairs but may have different SIMD/GPU behavior.

Peer replication with 20 candidates, all CPU-only:

| Clustered 768D workload | Fixed int8 recall@5 | Per-vector absmax recall@5 | Hosts |
| --- | ---: | ---: | --- |
| 8,192 vectors | 97.33% | **100.00%** | Deathstar, Lenovo 330S, Raspberry Pi |
| 32,768 vectors | 90.67% | **100.00%** | Deathstar, Lenovo 330S |

The 25 peer trial executions span **10 independent seeded workload cases**, because the same seed/dataset is executed on multiple machines. Cross-host deterministic hit totals match, even across x86_64 and aarch64. This is CPU code portability/reproducibility evidence, not representative production recall.

### Storage and preparation: the crucial caveat

For **768-dimensional vectors**:

| Representation | Bytes/vector |
| --- | ---: |
| Float32 only | 3,072 B |
| Standalone per-vector int8 plus float32 scale | 772 B |
| Float32 original **plus** per-vector int8 and scale (the benchmark's reranking design) | **3,844 B** |

At 32,768 vectors, this means approximately **96 MiB of original float32**, plus **24 MiB of int8** and **0.125 MiB of scale metadata**, totaling **120.125 MiB**, i.e. ~25.1% more than float32 alone. A 4× smaller *int8 vector payload* does **not** imply a 4× smaller full retrieval system. To save RAM, a real implementation would need a compressed/remote/secondary float32 store or a different reranking design, with its I/O cost measured. Metadata/IDs/index overhead and resident RSS are not included.

The CPU harness reports one-time quantization and allocation separately. Primary x1-370 per-vector quantization/preparation medians were roughly **23 ms for 8,192 clustered vectors** and **80 ms for 32,768 clustered vectors**, excluding synthetic embedding generation and disk I/O. These costs must be amortized across enough queries or included in cold-start metrics. No production database was modified.

### Reproduce

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_quant_scales.c -lm -o /tmp/bench_quant_scales
nice -n 15 /tmp/bench_quant_scales 8192 768 12 2 20261120 clustered
python3 benchmarks/check_quant_scales.py
python3 benchmarks/check_quant_peers.py
```

Next research gate: use **approved, representative real embedding distributions** with privacy and provenance controls, separate holdout periods, adversarial normalization/outliers and CPU-versus-ROCm SIMD measurements. Keep exact float32 search available when recall requirements are strict. Do not conflate these synthetic retrieval-vector results with LFM3 quantization, model-weight compression or neural self-modification.

## Secondary-storage float32 candidate reranking: process memory versus latency

**Study date:** 2026-10-29 · **Status:** Measured on x1-370 with synthetic 768D CPU vectors, research-only. This tests an architectural possibility for SensorGraft **without modifying or benchmarking a production SensorGraft service**.

**Source and evidence:** [bounded C harness](bench_float_storage.c), pinned commit [`a957936c`](https://github.com/scottjoyner/scottjoyner/blob/a957936ce1d9b39e98dff2c9522390320646cced/benchmarks/bench_float_storage.c), SHA-256 `5823f169d9476f5105d41c78a9d77d08a507139240554dd5b1d08f6542f2b1e5` · [100-trial results](results/2026-10-29-float-storage-study.json) · [deterministic runner](run_float_storage.py) · [independent validator](check_float_storage.py). All recorded trials passed the ranking/sanity checks, the validator recomputed timing/RSS summaries, and GitHub Actions runs the same evidence validator.

### Storage configurations

Each new process generates identical normalized synthetic float32 source vectors and clustered queries from the recorded seed, quantizes into **per-vector absmax int8 + float32 scales**, and computes an exact float32 top-five oracle before releasing or retaining the original float32 source. The search selects either **M=20** or **M=160** int8 candidates and then reranks them using full-precision float32 data:

- `ram`: retain the complete original float32 vectors in process heap memory, alongside compressed vectors.
- `pread_warm`: store float32 vectors in an automatically unlinked temporary regular file, free the complete float32 heap allocation, and fetch each candidate using one complete `pread`; data may be served by the Linux page cache.
- `pread_hint`: same as `pread_warm`, but `fsync` before queries and request `POSIX_FADV_DONTNEED` for this specific temporary file before each timed query. This is a **cache-drop hint**, not a guarantee of a cold SSD read.
- `mmap_warm`: use file-backed `mmap` to fetch float32 candidate vectors. Mapping is lazy, but touched mapped pages count toward process RSS.
- `mmap_hint`: before each query, request `MADV_DONTNEED` and `POSIX_FADV_DONTNEED` for the benchmark's own backing file. Page faults are counted. This is a **cold-ish hint**, not a measured universal cache miss rate.

The fixture is a real, bounded temporary file on the host's normal filesystem; it is unlinked immediately after creation and closed on exit. No real user audio, media, GPS, traces, graph or fleet credentials are written. All modes use the same algorithmic scoring, query vectors and oracle. Trials run at reduced scheduling priority; the underlying drive is already heavily utilized, so other I/O can influence readings. RSS is measured from `/proc/self/status`, and Linux kernel page-cache memory **is not included**.

### Measured results: five seeds per combination, 12 queries × two timed repetitions

| Clustered 768D vectors | Shortlist M | RAM query p50 | Warm pread query p50 | Cache-hinted pread p50 | Warm mmap p50 | Cache-hinted mmap p50 | RAM process RSS | Warm pread process RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8,192 | 20 | 1.175 ms | 1.186 ms | 2.795 ms | 1.178 ms | 4.417 ms | 32.2 MiB | 8.3 MiB |
| 8,192 | 160 | 1.310 ms | 1.341 ms | 14.414 ms | 1.298 ms | 26.411 ms | 32.2 MiB | 8.3 MiB |
| 32,768 | 20 | 4.673 ms | 4.698 ms | 6.700 ms | 4.748 ms | 8.394 ms | 122.3 MiB | 26.4 MiB |
| 32,768 | 160 | 4.861 ms | 4.903 ms | 14.292 ms | 4.845 ms | 31.258 ms | 122.3 MiB | 26.4 MiB |

Each metric is the **median of five per-seed p50 timings** (for the query p50 column) or median of five process RSS readings. Each trial has 12 unique queries repeated twice for latency. All five storage paths yielded **100% observed exact top-five recall** for each of these synthetic seed/dataset/M combinations; they share the same retrieval results by construction, not 100 independent relevance datasets. There are **100 completed process executions** but only **20 distinct seed/dataset/shortlist accuracy cases**, with five different storage modes per case.

### Engineering conclusions

1. **Warm-cache pread has attractive process-level memory characteristics.** At M20 and 32,768 vectors it used about 26.4 MiB RSS instead of 122.3 MiB, while p50 increased from 4.67 ms to 4.70 ms; at 8,192 vectors, RSS fell from 32.2 MiB to 8.3 MiB. The OS page cache may still hold the original ~96 MiB float32 backing file. This is **not** proof that whole-system RAM fell by the same fraction.
2. **Cold-ish re-fetching is risky.** The M160 hinted-pread workload took ~14 ms instead of 4.9 ms at 32,768 vectors; mmap with the eviction hint reached ~31 ms. File eviction hints are best-effort, so a properly controlled cold-read/`O_DIRECT` study is still needed.
3. **Memory-mapping is not automatic savings.** Warm mapped pages contributed near-RAM-baseline RSS after all queries. Hinting away mapped pages reduced RSS but increased latency and page faults.
4. **Stable IDs and an access pattern matter.** This prototype issues one `pread` per candidate, no batching or sorted offsets. A follow-up should test physical-offset sorting/coalescing, readahead, hybrid hot-cache strategies, simultaneous queries, and update/compaction correctness.
5. **Float32 results have external storage costs.** The backing file is `vectors × 768 × 4` bytes, plus in-process int8 vectors and float32 scales. The file is written during setup, and its write/fsync time is included in the evidence separately but excluded from query p50. The quantization/embedding cost is likewise separate. Any full system benchmark must include those costs and page-cache accounting.

**Reproduction** (low-priority; synthetic only):

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_float_storage.c -lm -o /tmp/bench_float_storage
nice -n 15 /tmp/bench_float_storage 8192 768 12 2 20261140 clustered ram 20
nice -n 15 /tmp/bench_float_storage 8192 768 12 2 20261140 clustered pread_warm 20
nice -n 15 /tmp/bench_float_storage 8192 768 12 2 20261140 clustered pread_hint 20
python3 benchmarks/check_float_storage.py
```

**Do not overgeneralize:** The exercise neither measured Tensor/ROCm inference nor ran real SensorGraft/Neo4j graph retrieval or real dashcam embeddings. It is not a deployment readiness, persistence integrity, privacy, cold-cache guarantee or production SLA claim. The biggest remaining gap is a controlled full-node prototype that writes approved embedding data and measures combined process+page-cache memory and end-to-end query/update overhead.

## Locality-sensitive candidate I/O: rank, sorted and contiguous-coalesced reads (2026-10-29)

**Status: research-only synthetic CPU test** on x1-370; not a production SensorGraft update, not a benchmark of actual dashcam embeddings, and not a controlled SSD device study.

**Artifacts:** [C implementation](bench_coalesced_reads.c) · [frozen synthetic runner](run_coalesced_reads.py) · [280 raw trial receipts](results/2026-10-29-coalesced-reads-280-runs.json) · [independent evidence validator](check_coalesced_reads.py). The executable source was committed first at [`8d811446`](https://github.com/scottjoyner/scottjoyner/blob/8d811446ebc5c36c89844ab307faf37619d190e8/benchmarks/bench_coalesced_reads.c), SHA-256 `d2f4ed078d87bff565dcc26e74f67c3967b801311ac08087b27b915159496c4e`.

### Design

All queries first perform the same 768D per-vector-absmax int8 candidate scan and rerank the selected float32 vectors to exact top-5. For file-backed modes, the float32 source is stored in an automatically unlinked temporary regular file on the controller's main filesystem. Each read strategy changes only the **physical order and number of float32 candidate fetches**, not the final scoring algorithm.

- `ram`: complete original float32 vectors kept in process RAM.
- `pread_rank_warm` / `pread_rank_hint`: one `pread` per candidate in approximate rank order.
- `pread_sorted_warm` / `pread_sorted_hint`: sort candidate IDs by float32 file offset, then one `pread` per candidate.
- `pread_coalesced_warm` / `pread_coalesced_hint`: sort candidate IDs by file offset, merge **consecutive vector IDs** into contiguous runs and issue one `pread` per run, scoring each fetched vector with its original stable ID.

The `_hint` modes use `fsync` before query measurements and best-effort `posix_fadvise(..., DONTNEED)` before each query, which **does not guarantee true cold SSD reads**. The `_warm` modes can benefit from Linux page cache. Timings use 12 queries × 2 repeats; n=8,192 and 32,768; temporal and clustered vector modes; M=20 and M=160; five seeds 20261150–20261154. Each mode ran in a new low-priority process. This is **280 executions** (4 workloads × 2 M × 5 seeds × 7 modes), representing **40 distinct seeded dataset/M cases** for accuracy, not 280 independent datasets. All modes matched the exact float32 top-5 oracle in these cases, with no recorded sanity failures. The separate verifier checks read-call conservation, total bytes fetched, stable top-5 parity, seed coverage, and timing summaries.

### Read amplification: sum of measured candidate pread calls across five seeded cases

| Workload | M | Rank-order calls | Coalesced calls | Read-call reduction |
| --- | ---: | ---: | ---: | ---: |
| 8,192 temporal | 20 | 2,400 | 120 | 95.0% |
| 8,192 temporal | 160 | 19,200 | 150 | 99.22% |
| 32,768 temporal | 20 | 2,400 | 120 | 95.0% |
| 32,768 temporal | 160 | 19,200 | 134 | 99.30% |
| 8,192 clustered | 20 | 2,400 | 2,400 | 0% |
| 8,192 clustered | 160 | 19,200 | 19,200 | 0% |
| 32,768 clustered | 20 | 2,400 | 2,400 | 0% |
| 32,768 clustered | 160 | 19,200 | 19,200 | 0% |

This is **read syscall reduction**, not data-byte reduction: every strategy fetches M float32 vectors per query, so the total candidate vector bytes remain the same. Coalescing works here because synthetic temporal embeddings tend to select consecutive IDs; the synthetic clustered generator does not make its nearby vectors physically adjacent. A real database must explicitly maintain and measure its own embedding-ID locality to benefit.

### Observed median query latencies (ms; medians of seed-specific p50)

| Workload | M | Warm ranked | Warm sorted | Warm coalesced | Hint ranked | Hint coalesced |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8,192 temporal | 20 | 1.243 | 1.235 | 1.230 | 2.070 | 1.512 |
| 8,192 temporal | 160 | 1.401 | 1.384 | 1.383 | 4.277 | 2.626 |
| 32,768 temporal | 20 | 4.977 | 4.908 | 4.871 | 6.047 | 6.261 |
| 32,768 temporal | 160 | 7.304 | 5.019 | 5.443 | 7.922 | 6.081 |
| 8,192 clustered | 20 | 1.375 | 1.334 | 1.360 | 3.270 | 3.156 |
| 8,192 clustered | 160 | 1.522 | 1.547 | 1.749 | 11.575 | 11.545 |
| 32,768 clustered | 20 | 7.681 | 5.611 | 7.282 | 10.026 | 9.661 |
| 32,768 clustered | 160 | 6.273 | 5.845 | 5.659 | 22.706 | 23.221 |

**Interpretation:** Contiguous coalescing is structurally valuable when retrieval candidates are also physically close. It can reduce read calls by >99%, but this does **not guarantee latency gain**: the compressed int8 candidate scan, process scheduling, kernel page cache, and I/O contention dominate many timings. Some workload medians reversed order under variable load; this is not sufficient to rank implementations by microsecond differences. Coalescing offered no read-count improvement on scattered clustered IDs and sometimes added sorting/merging overhead. The hint-only performance is not a true physical-media cold-run measurement.

### Reproduce

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_coalesced_reads.c -lm -o /tmp/bench_coalesced_reads
nice -n 15 /tmp/bench_coalesced_reads 8192 768 12 2 20261150 temporal pread_rank_warm 160
nice -n 15 /tmp/bench_coalesced_reads 8192 768 12 2 20261150 temporal pread_coalesced_warm 160
python3 benchmarks/check_coalesced_reads.py
```

**Next integration gate:** measured physical-record order and workload locality on approved real embeddings, write/update/compaction handling for stable IDs, batched asynchronous read strategies, multi-query contention, cgroup+page-cache memory, and controlled cold-cache / direct-I/O testing. Do not deploy against production traces, media or storage without a reversible and audited plan.

## Concurrent file-backed reranking: synchronized synthetic CPU workers (2026-10-29)

**Scope:** 32,768 normalized synthetic vectors at 768 dimensions **per worker**, per-vector absmax int8 shortlist M=160 and exact float32 top-five rerank. This deliberately measures independent low-priority workers sharing the x1-370 host's CPU, page cache and main filesystem. Workers do **not** share one SensorGraft DB, trace source, index, admission-control queue or backing-file object. There is no GPU or actual media/model inference.

**Code and provenance:** [gated C worker](bench_concurrent_reads.c) at commit [`b121ad09`](https://github.com/scottjoyner/scottjoyner/blob/b121ad090df96d3ecc4e9ee4c16ee7aecefdb8c2/benchmarks/bench_concurrent_reads.c) and SHA-256 `445585be11c90f9c81c347d4a5b052f6d3a0b389abcc37e03e5523641dec47cd` · [bounded orchestrator](run_concurrent_reads.py) · [48 synchronized workload groups, 112 worker-process receipts and 10,752 individual query latencies](results/2026-10-29-concurrent-candidate-io.json) · [independent per-query and summary validator](check_concurrent_reads.py). The validator recomputes pooled latency p50/p95, read-call accounting, hits and sums of process RSS. GitHub Actions compiles the worker and tests a gated two-process smoke case.

### Method and execution

Workers independently generate synthetic embeddings, build in-memory int8 vectors and a local temporary float32 file, precompute the full float32 retrieval oracle, warm candidate pages (where applicable), and then signal a readiness marker. The parent releases a file-based start gate only after every worker is ready. Each worker subsequently performs **24 unique queries × 4 timing repetitions = 96 timed queries**, with direct int8 full scan and top-160 float32 reranking. Query-loop wall time excludes generation, index construction, oracle generation, and backing file writes. The externally measured *completed queries per second* includes some gate-release polling, JSON output, process exit and scheduling; it is therefore a conservative completed-query throughput estimate, **not an independently controlled server throughput benchmark**.

Each distribution (temporal, clustered) × four paths (RAM, ranked `pread` warm, coalesced `pread` warm, coalesced `pread` cache-hint) × 1/2/4 workers × two seed-base repeats yielded **48 synchronized groups**, launching **112 short-lived workers**. Each worker has its own 32,768-vector synthetic dataset. The 10,752 query executions consist of repeated simulated queries and do not constitute 10,752 independent production relevance events. All exact-result and sanity checks passed. Workers were `nice -n 15`, with a hard cap of four processes and memory/disk free-space safeguards; no services or real datasets were interrupted.

### Completed-query throughput and pooled p95

*All figures below are medians across two seed-base groups per concurrency level, with p95 pooled over worker query durations within each group. Reporting p95 medians is not the same as a combined percentile across every group.*

| Synthetic distribution | Float32 rerank storage | QPS, 1 worker | QPS, 2 workers | QPS, 4 workers | Pooled p95, 4 workers |
| --- | --- | ---: | ---: | ---: | ---: |
| Temporal | RAM | 199 | 367 | 703 | 6.34 ms |
| Temporal | Warm ranked `pread` | 182 | 361 | 733 | 5.94 ms |
| Temporal | Warm coalesced `pread` | 200 | 362 | 574 | 7.66 ms |
| Temporal | Cache-hinted coalesced `pread` | 159 | 282 | 567 | 8.65 ms |
| Clustered | RAM | 201 | 379 | 564 | 7.43 ms |
| Clustered | Warm ranked `pread` | 196 | 357 | 612 | 7.41 ms |
| Clustered | Warm coalesced `pread` | 199 | 389 | 688 | 7.14 ms |
| Clustered | Cache-hinted coalesced `pread` | 57 | 114 | 219 | 21.48 ms |

**Important negative findings:** More workers increase aggregate throughput but are not uniformly linear, and pooled p95 may worsen. Coalescing is not a universal winner: under four temporal workers, warm coalesced reads (574 QPS) trailed warm ranked reads (733 QPS), even though coalescing dramatically reduces I/O syscall count on contiguous candidate IDs. The load/OS cache/CPU scheduling were uncontrolled; there are only two repeats per workload. For clustered data, cold-ish cache-hinted file reads were especially costly (about 219 QPS and 21.5 ms p95 at four workers), compared with 688 QPS and 7.1 ms for warm file-backed coalescing.

### Process memory, not whole-system memory

At four workers the summed post-query process RSS was approximately **501,328 KiB for temporal RAM** versus **110,270 KiB for temporal warm file-backed coalescing**, and **501,340 KiB for clustered RAM** versus **108,348 KiB for clustered warm file-backed coalescing**. These are sums of *per-worker RSS observations after the query loops*, **not a measured simultaneous peak**. They exclude Linux page cache, which may retain all float32 files; private memory use, cgroup memory, page-cache residency, and total system peak were not measured. Each worker independently owns its int8 index and optional file; the benchmark is not measuring a shared read-only index or single service.

### Reproduce

```bash
gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_concurrent_reads.c -lm -o /tmp/bench_concurrent_reads
nice -n 15 python3 benchmarks/run_concurrent_reads.py \
  --binary /tmp/bench_concurrent_reads --source benchmarks/bench_concurrent_reads.c \
  --output /tmp/concurrent-candidate-io.json
python3 benchmarks/check_concurrent_reads.py
```

**Next release gates:** benchmark a real shared, read-only SensorGraft-compatible index served to concurrent clients (not independent process copies); capture end-to-end p50/p95 including queue admission, I/O, backpressure and updates; measure cgroup memory + page cache and actual cold-media accesses under a controlled condition; and validate approved, representative real embedding datasets, ideally also across ROCm-capable fleet nodes. Do not interpret these synthetic throughput numbers as a production scaling guarantee.

## Shared read-only Unix-socket synthetic retrieval server: queueing and overload (2026-10-29)

**Progress beyond previous independent-worker studies:** This experiment runs a **single C server with one read-only int8 index and one optional float32 backing file per test group**. Multiple concurrent clients connect over a local Unix-domain socket, submit synthetic query IDs, and receive exact-parity status plus server queue and computation durations. A bounded fixed worker pool drains a FIFO admission queue. The server does not start or modify production SensorGraft, models, Neo4j, fleet services, traces or media.

**Artifact links:** [C Unix-socket shared-index server](bench_shared_server.c) · [synchronized client runner](run_shared_server.py) · [72-group / 4,992-request raw receipts](results/2026-10-29-shared-server-uds.json) · [receipt validator](check_shared_server.py) · [18-group overload runner](run_shared_overload.py) · [432 overload-response receipts](results/2026-10-29-shared-server-overload.json) · [overload validator](check_shared_overload.py). Source pinned at commit [`dc4c6637`](https://github.com/scottjoyner/scottjoyner/blob/dc4c66371e80b43d17ed37092a31362aea6fcef4/benchmarks/bench_shared_server.c), SHA-256 `6fc33c4fb5061d02bae11d9daac5fe4dce3b835905f2ddb601b6bae3a093f694`.

### Experiment

Each server builds **32,768 normalized synthetic 768D vectors**, quantizes per-vector absmax into symmetric int8, and computes exact float32 top-five references for **12 synthetic queries**. It retains one shared int8 index plus scales and either **RAM** float32 originals or an **anonymous unlinked temporary file** from which it fetches top-160 candidates by rank or coalescing adjacent file offsets. Four-worker configurations use four threads on the **same shared index and backing file**, not four replicated indexes. The server speaks a fixed 4-byte query-ID request and 24-byte binary response over Unix sockets; every response includes status, hit count, queue wait time, and worker compute time. The client additionally measures end-to-end socket/request latency, which includes connection, queueing, computation and response.

The bounded baseline matrix includes **2 distributions (temporal/clustered) × 3 storage modes (RAM/rank `pread`/coalesced `pread`) × 2 thread counts (1/4) × 3 client counts (1/4/8) × 2 seeds = 72 groups**. Each client makes 16 sequential requests. This yields **4,992 completed client requests**, not 4,992 independent relevance datasets. The dataset and oracle are synthetic and repeated across clients by design. **All baseline requests were accepted, and all returned the exact top five.** Queue capacity was 8 pending connections; no baseline rejections were expected.

### Eight-client results: median across two test seeds

| Distribution | Storage | Worker threads | Completed QPS | Client-observed p95 | Server queue p95 | Server ready-state VmRSS |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Temporal | RAM | 1 | 193 | 49.40 ms | 43.55 ms | 122.2 MiB |
| Temporal | Coalesced file | 1 | 198 | 47.38 ms | 42.37 ms | 26.3 MiB |
| Temporal | RAM | 4 | 684 | 15.48 ms | 7.63 ms | 122.2 MiB |
| Temporal | Coalesced file | 4 | 656 | 14.71 ms | 7.28 ms | 26.4 MiB |
| Clustered | RAM | 1 | 190 | 52.21 ms | 45.77 ms | 122.2 MiB |
| Clustered | Coalesced file | 1 | 186 | 54.37 ms | 47.93 ms | 26.3 MiB |
| Clustered | RAM | 4 | 686 | 14.57 ms | 7.21 ms | 122.3 MiB |
| Clustered | Coalesced file | 4 | 666 | 14.81 ms | 7.31 ms | 26.3 MiB |

**What this establishes:** A real, single shared server can expose and measure queueing and worker-pool saturation. One worker serving eight clients was near its ~190–200 QPS CPU throughput ceiling, increasing p95 primarily through queue wait. Four workers delivered roughly 3–4× more completed requests/s at eight clients, with ~14–15 ms end-to-end p95. The file-backed option reduced observed server **process RSS** by ~78%, while roughly preserving warm-cache throughput. These are single-host Unix-socket synthetic results, not production throughput guarantees. Linux page cache may still hold the float32 backing file; ready-state RSS is not system peak memory or page-cache accounting.

### Explicit overload test

A separate, deliberately overloaded matrix used **24 simultaneous clients × 1 request**, with **one worker** and only **two FIFO waiting slots**, on three storage modes × two distributions × three seeds = **18 test groups and 432 total requests**. The server returned **378 explicit `BUSY` replies**, while **54 requests were processed successfully** and all their top-five results matched exact float32. The independent validator checked every raw status and confirmed there were no unaccounted requests *in the tested runs*. This demonstrates bounded admission and explicit rejection, **not** automatic retries, idempotency, client backoff, persistent queues, fair scheduling or production-safe load shedding.

### Reproduction and constraints

```bash
gcc -O3 -Wall -Wextra -std=c11 -pthread benchmarks/bench_shared_server.c -lm -o /tmp/bench_shared_server
python3 benchmarks/check_shared_server.py
python3 benchmarks/check_shared_overload.py
# The complete multi-process benchmark is opt-in and may contend with other work:
nice -n 15 python3 benchmarks/run_shared_server.py \
  --binary /tmp/bench_shared_server --source benchmarks/bench_shared_server.c \
  --output /tmp/shared-server-uds.json
```

Research caveats: all inputs and results are deterministic synthetic vectors, the Unix socket is local to one host, only 1/4 worker threads and 1/4/8 clients were tested, there are only two seeds per normal configuration, the filesystem cache and system scheduler were uncontrolled, and the float32 file is written at build time before query measurements. Client query requests contain **query IDs**, not arbitrary user-supplied embeddings, and there is no auth, cross-host transport, on-disk crash recovery, eviction-aware memory accounting or full SensorGraft integration. **Do not deploy this microservice as-is.** Next gate: a single protected, shared, read-only SensorGraft-compatible test index, representative approved real embeddings, queue fairness, overload retries and concurrent update isolation.
