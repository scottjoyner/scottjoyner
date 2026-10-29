# Research and publications | Scott Joyner

[← GitHub profile](README.md) · [Machine-readable inventory](RESEARCH_INVENTORY.json) · [Public research implementation](#dashcam-embeddings-and-location-aware-knowledge-graphs)

**Audited:** 2026-10-29 · **Coverage:** Publicly reachable artifacts found within accessible `@scottjoyner` GitHub repositories. This is a source-based inventory, not proof that every manuscript ever written has been found.

## Verified arXiv publications

**None independently verified in this audit.** A paper being written *in arXiv format* or available on GitHub is not the same as an arXiv submission. An arXiv publication must have an attributable arXiv abstract record, ID, authors, and version. Do not infer authorship from repository ownership or from citations to someone else's papers.

The [machine-readable inventory](RESEARCH_INVENTORY.json) tracks `arxiv_id: null` until a primary publication record is confirmed.

## Public papers and manuscripts (arXiv status not confirmed)

| Work | Source, paper, and evidence | Attribution / status |
| --- | --- | --- |
| **Vector Embeddings: Foundations, Compression, and Retrieval-Augmented Generation** | [LaTeX manuscript](https://github.com/scottjoyner/generated_text/blob/main/latex/embeddings.tex) | Public source manuscript. `\\author{}` in the source is empty, so authorship metadata still needs correction or confirmation. **No verified arXiv ID.** |
| **Geometric Alignment of Compact Language Models: A 1,200-Prompt Multidomain Benchmark** | [LaTeX manuscript](https://github.com/scottjoyner/llm-geometry/blob/main/docs/PAPER_1200.tex) · [PDF](https://github.com/scottjoyner/llm-geometry/blob/main/docs/PAPER_1200.pdf) · [abstract](https://github.com/scottjoyner/llm-geometry/blob/main/docs/ABSTRACT_1200.md) · [code](https://github.com/scottjoyner/llm-geometry) | Public March 2026 research manuscript; source lists “Kipne et al.” Author identities and **arXiv posting not independently verified**. |
| **Dashcam Research** (existing PDF filename) | [Dashcam_Research.pdf](https://github.com/scottjoyner/auto-ingest/blob/main/Dashcam_Research.pdf) · [associated code](https://github.com/scottjoyner/auto-ingest) | Public research PDF artifact. Internal title, attribution, and **arXiv ID remain unverified** because the PDF contents could not be independently inspected in this audit. |

### Public proposals and other research writing (not arXiv papers)

- **Patent Proposal: Graph-Based RAG System with Chain-of-Thought Traceability and Multi-Level Caching** — [LaTeX source](https://github.com/scottjoyner/generated_text/blob/main/latex/cot.tex). Lists Scott Joyner as inventor; this is a **patent proposal**, not a verified filing or research publication.
- **Hugging Face Hub API Integration Proposal** — [LaTeX source](https://github.com/scottjoyner/generated_text/blob/main/latex/hf.tex). Technical/security integration proposal, not an academic paper.
- **Geometry follow-up reports:** [observations](https://github.com/scottjoyner/llm-geometry/blob/main/docs/OBSERVATIONS_1200.md) · [Part 2 drift](https://github.com/scottjoyner/llm-geometry/blob/main/docs/PART2_DRIFT_REPORT.md) · [Gemma temporal baseline](https://github.com/scottjoyner/llm-geometry/blob/main/docs/GEMMA_PART3_TEMPORAL_BASELINE.md) · [Part 4 cartography](https://github.com/scottjoyner/llm-geometry/blob/main/docs/GEMMA_PART4_DRIFT_CARTOGRAPHY.md) · [Part 5 operator atlas](https://github.com/scottjoyner/llm-geometry/blob/main/docs/GEMMA_PART5_OPERATOR_ATLAS.md).

## Dashcam embeddings and location-aware knowledge graphs

This is the **public research code and methods** related to the dashcam/GPS examples. These links lead to existing source artifacts, not to independently published arXiv papers.

| Topic | Public links | What the public source demonstrates |
| --- | --- | --- |
| **Dashcam object/scene embeddings** | [YOLO embeddings](https://github.com/scottjoyner/auto-ingest/blob/main/auto_ingest/dashcam/yolo_embeddings.py) · [structured visual embeddings](https://github.com/scottjoyner/auto-ingest/blob/main/dashcam_yolo_structure_embeddings.py) | Scene/object representation with spatial structure and embeddings for downstream graph retrieval. |
| **Visual semantic search / dashcam RAG** | [Pipeline design](https://github.com/scottjoyner/auto-ingest/blob/main/DASHCAM_VISION_PIPELINE.md) · [frame extraction & descriptions](https://github.com/scottjoyner/auto-ingest/blob/main/dashcam_frame_vision.py) | Time-aligned video-frame descriptions, graph storage, and `emb_e5_large` text embeddings/vector retrieval. |
| **GPS/location alignment** | [Location backfill](https://github.com/scottjoyner/auto-ingest/blob/main/patch_missing_locationsv2.py) · [graph location queries](https://github.com/scottjoyner/auto-ingest/blob/main/location.cy) | Linking locations to dashcam entities and repairing missing geospatial associations; source refers to `LocationEvent`, `PhoneLog`, and `DashcamEmbedding`. |
| **Trip reconstruction / temporal linkage** | [Clip-to-trip linking](https://github.com/scottjoyner/auto-ingest/blob/main/scripts/link_clips_to_trips.py) | Temporal overlap and video-clip continuity used to associate or reconstruct trips. |
| **Phone location ingestion** | [PhoneLog](https://github.com/scottjoyner/phonelog) | Location-event ingest with Neo4j upserts and WAL replay. |
| **Audio and transcript graph integration** | [Ingest system](https://github.com/scottjoyner/auto-ingest) · [transcript ingestion](https://github.com/scottjoyner/auto-ingest/blob/main/auto_ingest/ingest/transcripts.py) | Multimodal transcription and graph-linked retrieval infrastructure. |
| **Compact LLM hidden-state/embedding geometry** | [Research repo](https://github.com/scottjoyner/llm-geometry) · [paper](https://github.com/scottjoyner/llm-geometry/blob/main/docs/PAPER_1200.tex) | A 1,200-prompt representational-geometry benchmark across compact LLMs. |

## Record-keeping and source integrity

- The machine-readable [`RESEARCH_INVENTORY.json`](RESEARCH_INVENTORY.json) records the public artifacts, source links, type, attribution status, and arXiv verification fields.
- The citation for **Harnessing the Universal Geometry of Embeddings** (`arXiv:2505.12540`) in [`vec2vec`](https://github.com/scottjoyner/vec2vec) credits Jha, Zhang, Shmatikov, and Morris; **it is not listed here as an authored paper**.
- Several research drafts or experiments may exist in private/local workspaces. This index does not silently publish or expose them. A private draft becomes a public research artifact only after intentional release and authorship/privacy review.
- Keep original recordings, personal location traces, credentials, private training data, and raw transcripts out of the public index. Links should point to already-public reviewed code, sanitized reports, and paper sources.
- Before recording a paper as *arXiv published*, confirm the paper's real `arxiv.org/abs/<ID>` page, exact title, author list, publication/version dates, and code/reproducibility reference.

**Audit limitation:** This is a verified inventory of artifacts found in accessible GitHub repositories, not a complete scan of every machine, private branch, Library document, or unindexed publication service.

## Reproducible benchmarks

**Eight-host replication:** [Public fleet summary (JSON)](benchmarks/results/2026-10-29-fleet-summary.json) and [C/CPU benchmark methodology](benchmarks/README.md). Eight Linux hosts produced eight Python runs and eleven compiled C vector-scan workloads; int8 recall@5 was 0.908333 in the common 8,192×384 synthetic workload, with 2.05–3.87× int8-vs-float32 median latency speedups in compiled code. This is strictly a **synthetic, CPU-only** result; performance and recall cannot be extrapolated to actual dashcam embeddings, production Neo4j, ROCm or LLM inference.


[**Run the reproducible benchmark**](benchmarks/README.md) · [source code](benchmarks/bench_research.py) · [correctness tests](benchmarks/test_bench_research.py) · [machine-readable x1-370 results](benchmarks/results/2026-10-29-x1-370.json)

A **synthetic CPU-only** experiment on x1-370 (2026-10-29) tested nearest-timestamp lookup and float64 versus int8 cosine retrieval. Indexed timestamp lookup matched the linear baseline on all tested queries; at 50,000 events, p50 per-query time was 0.000290 ms indexed versus 1.608799 ms linear. For 48-dimensional synthetic vectors, int8 recall@5 was 0.95–0.97 against float64 exact rankings, but unoptimized Python int8 scans were **slower**, not faster. Six correctness tests passed. These are **not** production Neo4j, dashcam GPS accuracy, ROCm, or published arXiv results; source hashes, seeds, and all timing evidence are linked above.

**High-dimensional validation (2026-10-29):** [30-run, six-host, five-seed 768-dimensional CPU evidence](benchmarks/results/2026-10-29-768d-multiseed.json) · [validation script](benchmarks/check_multiseed.py) · [methodology and GPU blocker details](benchmarks/README.md). Five independent seeded synthetic datasets yielded **mean int8 recall@5 0.840**, ranging 0.783–0.900 against float32. All 30 CPU executions passed correctness checks; no GPU, real-location, production trace DB, or private dashcam retrieval measurements are claimed.

**Two-stage reranking study (2026-10-29):** [Six-host, five-seed shortlist results](benchmarks/results/2026-10-29-rerank-multiseed.json) · [clustered/temporal stress results](benchmarks/results/2026-10-29-rerank-stress-multiseed.json) · [benchmark methods](benchmarks/README.md). Reranking 20 int8 candidates restored 100% top-5 recall on independent synthetic vectors but only 97.33% on the clustered control; 160 candidates reached 100% on those five clustered seeds. **Synthetic CPU evidence only, not real dashcam or GPU benchmarks.**

**Directly measured reranking (2026-10-29):** [Directly timed three-host rerank benchmark](benchmarks/results/2026-10-29-rerank-direct-multihost.json) · [reproduction and caveats](benchmarks/README.md). 45 measured runs across three Linux CPU hosts and 15 distinct synthetic seed/distribution cases. With 160 candidates, exact top-five matches were recovered on all tested cases, while direct end-to-end CPU latency was lower than an exact float32 scan. Quantization setup is measured separately, and **actual dashcam embeddings, GPU and production DB retrieval remain unmeasured**.

**32,768-vector CPU scale-up (2026-10-29):** [Ten directly timed trials](benchmarks/results/2026-10-29-rerank-direct-32768-x1-370.json) · [validated methodology](benchmarks/README.md). At 768 dimensions, int8 scanning plus float32 reranking of 160 candidates measured ~4.89 ms median versus ~14.06 ms exact float32 on clustered synthetic data, with 100% top-5 recall **on these five seeds only**; quantization incurred ~79 ms one-time cost and is excluded from query latency.

**Held-out benchmark validation (2026-10-29):** [80-trial frozen-policy study](benchmarks/results/2026-10-29-holdout-frozen-policy.json) · [40-trial disjoint second validation](benchmarks/results/2026-10-29-policy-v2-second-holdout.json) · [methods, source and caveats](benchmarks/README.md). Initial 99% recall calibration **failed** on both 32,768-vector held-out distributions (98.67%/98.33%). A separately precommitted, more conservative M20/M80 policy reached **99.83%/99.92%** on a second synthetic CPU-only holdout. These are *not* actual dashcam or GPU results.

**Query-only adaptive retrieval (2026-10-29):** [300-query calibration](benchmarks/results/2026-10-29-score-margin-calibration.json) · [960 held-out queries](benchmarks/results/2026-10-29-score-margin-holdout.json) · [40 matched fixed160 comparisons](benchmarks/results/2026-10-29-score-margin-vs-fixed160.json) · [methods](benchmarks/README.md). A fixed quantized-score margin threshold of 0.0064 yielded **99.58–100% top-five recall** across five unseen synthetic CPU groups without a distribution-label oracle. Critical negative control: adaptation yielded only **~2–9% additional median paired speedup over fixed160**, much smaller than the ~2.9× ratio versus full float32 search. No real dashcam, SensorGraft production query, GPU, or arXiv publication is claimed.

**Per-vector int8 scaling replication (2026-10-29):** [60 held-out synthetic CPU trials](benchmarks/results/2026-10-29-quant-scales-60case-holdout.json) · [25 cross-fleet CPU trials](benchmarks/results/2026-10-29-quant-scales-peer.json) · [methods and memory caveats](benchmarks/README.md). At 768 dimensions, per-vector absmax int8 + float32 rerank 20 restored **100% observed top-five recall across six tested synthetic workloads** versus fixed-scale int8 recall of **96.83% / 95.50%** on clustered 8K/32K vectors. Peer replication on Deathstar, Lenovo and Raspberry Pi confirmed deterministic hit totals. This is not a guarantee for real embeddings or a GPU result. Retaining the original float32 representations plus int8 and scale costs **25.1% more raw vector memory than float32 alone**.

**Secondary-storage reranking (2026-10-29):** [100 raw synthetic CPU trials](benchmarks/results/2026-10-29-float-storage-study.json) · [file-backed C benchmark](benchmarks/bench_float_storage.c) · [full methodology](benchmarks/README.md). With 32,768 768D clustered vectors, float32 rerank candidates fetched via warm-cache `pread` used **26.4 MiB measured process RSS** versus **122.3 MiB** for float32 in process RAM, at **4.70 ms versus 4.67 ms** median query time (M20). Cache-drop hints significantly increased latency; Linux page cache means process RSS reductions are **not whole-system memory savings**. This is synthetic CPU evidence, not deployed SensorGraft or ROCm.

**Contiguous float32 candidate-read benchmark (2026-10-29):** [280-run raw evidence](benchmarks/results/2026-10-29-coalesced-reads-280-runs.json) · [C source](benchmarks/bench_coalesced_reads.c) · [full reproducibility and caveats](benchmarks/README.md). Sorting selected float32 candidate IDs and combining adjacent records cut `pread` calls **99.3%** for the 32,768-vector temporal/M160 synthetic CPU workload, but **0%** for clustered data with scattered IDs. Correctness parity passed on all 40 seeded dataset/M cases across seven modes. Latency gains are locality-dependent and noisy; cache-hint results do not prove cold-device latency. This is not production SensorGraft or ROCm performance.

**Synchronized concurrency benchmark (2026-10-29):** [48 gated groups / 112 low-priority worker processes / 10,752 timed synthetic queries](benchmarks/results/2026-10-29-concurrent-candidate-io.json) · [compiled worker](benchmarks/bench_concurrent_reads.c) · [methods and limitations](benchmarks/README.md). For 32,768 temporal 768D vectors per worker, four independent warm file-backed coalesced workers delivered **574 completed queries/s** with **7.66 ms pooled p95**; for clustered data, **688 queries/s** and **7.14 ms pooled p95**. Cache-hinted clustered retrieval fell to **219 queries/s** and **21.48 ms p95**. All synthetic exact top-5 checks passed. These are independent per-process indexes and files, **not a shared production SensorGraft service**; summed process RSS excludes kernel page cache.
