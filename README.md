
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
