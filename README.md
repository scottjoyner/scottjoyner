
<h1 align="center">Hi 👋, I'm Scott Joyner</h1>
<h3 align="center">An Software Developer with a Passion for Graph Databases, AI, and More</h3>

As a dedicated software engineer, I thrive at the intersection of data, technology, and finance. My journey has been marked by a relentless pursuit of knowledge in cutting-edge technologies such as graph databases, artificial intelligence, and the fascinating world of stock markets. I specialize in developing intelligent solutions that leverage large language models (LLMs) and chatbots to drive efficiency, insights, and value.

## Public research and manuscripts

[**Full research and publication inventory**](RESEARCH.md) · [**Structured citation/source inventory**](RESEARCH_INVENTORY.json) · [**Reproducible benchmarks**](benchmarks/README.md) · [**Raw benchmark evidence**](benchmarks/results/2026-10-29-x1-370.json)

| Research area | Public work |
| --- | --- |
| **Dashcam embeddings & visual RAG** | [YOLO/scene embeddings](https://github.com/scottjoyner/auto-ingest/blob/main/auto_ingest/dashcam/yolo_embeddings.py) · [Vision RAG pipeline](https://github.com/scottjoyner/auto-ingest/blob/main/DASHCAM_VISION_PIPELINE.md) · [Dashcam research PDF](https://github.com/scottjoyner/auto-ingest/blob/main/Dashcam_Research.pdf) |
| **Geospatial video & GPS linkage** | [Location association](https://github.com/scottjoyner/auto-ingest/blob/main/patch_missing_locationsv2.py) · [Trip reconstruction](https://github.com/scottjoyner/auto-ingest/blob/main/scripts/link_clips_to_trips.py) · [PhoneLog](https://github.com/scottjoyner/phonelog) |
| **Vector embeddings, graph search & RAG** | [Public LaTeX manuscript](https://github.com/scottjoyner/generated_text/blob/main/latex/embeddings.tex) |
| **Compact LLM representation geometry** | [1,200-prompt LaTeX paper](https://github.com/scottjoyner/llm-geometry/blob/main/docs/PAPER_1200.tex) · [PDF](https://github.com/scottjoyner/llm-geometry/blob/main/docs/PAPER_1200.pdf) · [experiments](https://github.com/scottjoyner/llm-geometry) |

*These are existing public manuscripts, research PDFs, and implementations. An authored arXiv submission has not been independently verified; see the inventory for status and attribution.*

**Directly measured reranking (2026-10-29):** [Directly timed three-host rerank benchmark](benchmarks/results/2026-10-29-rerank-direct-multihost.json) · [reproduction and caveats](benchmarks/README.md). 45 measured runs across three Linux CPU hosts and 15 distinct synthetic seed/distribution cases. With 160 candidates, exact top-five matches were recovered on all tested cases, while direct end-to-end CPU latency was lower than an exact float32 scan. Quantization setup is measured separately, and **actual dashcam embeddings, GPU and production DB retrieval remain unmeasured**.

**Two-stage reranking study (2026-10-29):** [Six-host, five-seed shortlist results](benchmarks/results/2026-10-29-rerank-multiseed.json) · [clustered/temporal stress results](benchmarks/results/2026-10-29-rerank-stress-multiseed.json) · [benchmark methods](benchmarks/README.md). Reranking 20 int8 candidates restored 100% top-5 recall on independent synthetic vectors but only 97.33% on the clustered control; 160 candidates reached 100% on those five clustered seeds. **Synthetic CPU evidence only, not real dashcam or GPU benchmarks.**

**October 2026: high-dimensional quantization replication.** [**768D multi-seed results (30 runs)**](benchmarks/results/2026-10-29-768d-multiseed.json) · [Methods and GPU readiness](benchmarks/README.md). Five independent synthetic seeds across six Linux hosts; int8 recall@5 averaged 84.0% versus float32. CPU only.

**Fleet benchmark replication (2026-10-29)**: [Eight-host results, methods and code](benchmarks/README.md) · [Machine-readable comparison](benchmarks/results/2026-10-29-fleet-summary.json) · [Compiled C benchmark](benchmarks/bench_vector.c). Eight CPU hosts completed the synthetic Python and compiled vector tests; no production location data or GPU inference was benchmarked.

- 🔭 I’m currently working on **an AI-powered Assistant.**

- 🌱 I’m currently learning **advanced techniques in graph databases and data modeling.**

- 👯 I’m looking to collaborate on **projects involving AI, LLMs, and data analytics.**

- 💬 Ask me about ** RAG architechure, graph databases, computer vision, or Transformers**

- ⚡ Fun fact: **I'm an avid developer and a technology enthusiast who loves exploring the latest in tech and finance.**

<h3 align="left">Languages and Tools:</h3>
<p align="left"> List your skills and tools here </p>

<p align="left"> <img src="https://komarev.com/ghpvc/?username=scottjoyner&label=Profile%20views&color=0e75b6&style=flat" alt="scottjoyner" /> </p>

[![Scott's GitHub Streak](https://github-readme-streak-stats.herokuapp.com/?user=scottjoyner&theme=tokyonight)](https://git.io/streak-stats)

<p align="left"> <a href="https://github.com/ryo-ma/github-profile-trophy"><img src="https://github-profile-trophy.vercel.app/?username=scottjoyner" alt="scottjoyner" /></a> </p>

<!-- You can add or modify sections according to your preferences -->

**32,768-vector CPU scale-up (2026-10-29):** [Ten directly timed trials](benchmarks/results/2026-10-29-rerank-direct-32768-x1-370.json) · [validated methodology](benchmarks/README.md). At 768 dimensions, int8 scanning plus float32 reranking of 160 candidates measured ~4.89 ms median versus ~14.06 ms exact float32 on clustered synthetic data, with 100% top-5 recall **on these five seeds only**; quantization incurred ~79 ms one-time cost and is excluded from query latency.

**Held-out benchmark validation (2026-10-29):** [80-trial frozen-policy study](benchmarks/results/2026-10-29-holdout-frozen-policy.json) · [40-trial disjoint second validation](benchmarks/results/2026-10-29-policy-v2-second-holdout.json) · [methods, source and caveats](benchmarks/README.md). Initial 99% recall calibration **failed** on both 32,768-vector held-out distributions (98.67%/98.33%). A separately precommitted, more conservative M20/M80 policy reached **99.83%/99.92%** on a second synthetic CPU-only holdout. These are *not* actual dashcam or GPU results.

**Query-only adaptive retrieval (2026-10-29):** [300-query calibration](benchmarks/results/2026-10-29-score-margin-calibration.json) · [960 held-out queries](benchmarks/results/2026-10-29-score-margin-holdout.json) · [40 matched fixed160 comparisons](benchmarks/results/2026-10-29-score-margin-vs-fixed160.json) · [methods](benchmarks/README.md). A fixed quantized-score margin threshold of 0.0064 yielded **99.58–100% top-five recall** across five unseen synthetic CPU groups without a distribution-label oracle. Critical negative control: adaptation yielded only **~2–9% additional median paired speedup over fixed160**, much smaller than the ~2.9× ratio versus full float32 search. No real dashcam, SensorGraft production query, GPU, or arXiv publication is claimed.

**Per-vector int8 scaling replication (2026-10-29):** [60 held-out synthetic CPU trials](benchmarks/results/2026-10-29-quant-scales-60case-holdout.json) · [25 cross-fleet CPU trials](benchmarks/results/2026-10-29-quant-scales-peer.json) · [methods and memory caveats](benchmarks/README.md). At 768 dimensions, per-vector absmax int8 + float32 rerank 20 restored **100% observed top-five recall across six tested synthetic workloads** versus fixed-scale int8 recall of **96.83% / 95.50%** on clustered 8K/32K vectors. Peer replication on Deathstar, Lenovo and Raspberry Pi confirmed deterministic hit totals. This is not a guarantee for real embeddings or a GPU result. Retaining the original float32 representations plus int8 and scale costs **25.1% more raw vector memory than float32 alone**.

**Secondary-storage reranking (2026-10-29):** [100 raw synthetic CPU trials](benchmarks/results/2026-10-29-float-storage-study.json) · [file-backed C benchmark](benchmarks/bench_float_storage.c) · [full methodology](benchmarks/README.md). With 32,768 768D clustered vectors, float32 rerank candidates fetched via warm-cache `pread` used **26.4 MiB measured process RSS** versus **122.3 MiB** for float32 in process RAM, at **4.70 ms versus 4.67 ms** median query time (M20). Cache-drop hints significantly increased latency; Linux page cache means process RSS reductions are **not whole-system memory savings**. This is synthetic CPU evidence, not deployed SensorGraft or ROCm.

**Contiguous float32 candidate-read benchmark (2026-10-29):** [280-run raw evidence](benchmarks/results/2026-10-29-coalesced-reads-280-runs.json) · [C source](benchmarks/bench_coalesced_reads.c) · [full reproducibility and caveats](benchmarks/README.md). Sorting selected float32 candidate IDs and combining adjacent records cut `pread` calls **99.3%** for the 32,768-vector temporal/M160 synthetic CPU workload, but **0%** for clustered data with scattered IDs. Correctness parity passed on all 40 seeded dataset/M cases across seven modes. Latency gains are locality-dependent and noisy; cache-hint results do not prove cold-device latency. This is not production SensorGraft or ROCm performance.

**Synchronized concurrency benchmark (2026-10-29):** [48 gated groups / 112 low-priority worker processes / 10,752 timed synthetic queries](benchmarks/results/2026-10-29-concurrent-candidate-io.json) · [compiled worker](benchmarks/bench_concurrent_reads.c) · [methods and limitations](benchmarks/README.md). For 32,768 temporal 768D vectors per worker, four independent warm file-backed coalesced workers delivered **574 completed queries/s** with **7.66 ms pooled p95**; for clustered data, **688 queries/s** and **7.14 ms pooled p95**. Cache-hinted clustered retrieval fell to **219 queries/s** and **21.48 ms p95**. All synthetic exact top-5 checks passed. These are independent per-process indexes and files, **not a shared production SensorGraft service**; summed process RSS excludes kernel page cache.

**Shared-index concurrency and backpressure (2026-10-29):** [72 synchronized groups / 4,992 exact synthetic client requests](benchmarks/results/2026-10-29-shared-server-uds.json) · [18 overload groups / 432 explicit response receipts](benchmarks/results/2026-10-29-shared-server-overload.json) · [shared C Unix-socket server](benchmarks/bench_shared_server.c) · [methods and caveats](benchmarks/README.md). One shared read-only synthetic 32,768 × 768D index was served by 1 or 4 threads to 1/4/8 concurrent clients. At eight clients, four-worker file-backed coalesced retrieval delivered about **656–666 QPS** with **14.7–14.8 ms client p95**, versus **186–198 QPS** and **47–54 ms p95** on one worker; queue delay drove the difference. Server ready-state process RSS was **~27 MiB file-backed vs ~125 MiB float32 RAM**; Linux page cache remains unaccounted. Under deliberate overload, a one-worker/two-slot queue returned **378 explicit BUSY replies** and **54 exact successful responses**. This is synthetic UDS research, not production SensorGraft or ROCm.
