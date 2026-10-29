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
