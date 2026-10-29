# Research papers, technical reports, and reproducible projects

**Last audited:** 2026-10-28  
**Scope:** Publicly accessible artifacts in repositories under [`@scottjoyner`](https://github.com/scottjoyner). A repository-hosted manuscript or PDF is **not automatically an arXiv publication**. Authorship, arXiv identifiers, and peer-review status should be verified against the document and primary publication record.

## arXiv publication verification

No independently verified arXiv identifier attributable to this collection's author was found in this audit. The linked `arxiv.org` papers **cited by** code or manuscripts may have other authors and should not be counted as original publications. To add a published paper, include its verified `https://arxiv.org/abs/ID` link, title, authors, version, and source repository.

## Public research manuscripts and paper artifacts

| Work | Public artifact | Classification / status |
| --- | --- | --- |
| **Vector Embeddings: Foundations, Compression, and Retrieval-Augmented Generation** | [LaTeX manuscript](https://github.com/scottjoyner/generated_text/blob/main/latex/embeddings.tex) | Public source manuscript; the document currently has an empty `\\author{}` field. arXiv posting not verified. |
| **Geometric Alignment of Compact Language Models: A 1,200-Prompt Multidomain Benchmark** | [LaTeX paper](https://github.com/scottjoyner/llm-geometry/blob/main/docs/PAPER_1200.tex) · [PDF](https://github.com/scottjoyner/llm-geometry/blob/main/docs/PAPER_1200.pdf) · [research repository](https://github.com/scottjoyner/llm-geometry) | March 2026 repository-hosted benchmark manuscript. The source credits “Kipne et al.”; specific authorship and arXiv posting still require verification. |
| **Dashcam Research** (repository filename) | [Dashcam_Research.pdf](https://github.com/scottjoyner/auto-ingest/blob/main/Dashcam_Research.pdf) · [related pipeline](https://github.com/scottjoyner/auto-ingest) | Public PDF research artifact; its internal title, author credits, and arXiv status were **not** verified in this audit. |
| **Graph-Based RAG System with Chain-of-Thought Traceability and Multi-Level Caching** | [LaTeX source](https://github.com/scottjoyner/generated_text/blob/main/latex/cot.tex) | Public **patent proposal**, credited to Scott Joyner as inventor. Not categorized as an arXiv paper. |

### Other public technical writing

- **Hugging Face Hub API Integration Proposal:** [LaTeX source](https://github.com/scottjoyner/generated_text/blob/main/latex/hf.tex). An integration and security proposal, not a research publication.
- **LLM representation geometry research:** [observations](https://github.com/scottjoyner/llm-geometry/blob/main/docs/OBSERVATIONS_1200.md), [Gemma drift cartography](https://github.com/scottjoyner/llm-geometry/blob/main/docs/GEMMA_PART4_DRIFT_CARTOGRAPHY.md), and [operator atlas](https://github.com/scottjoyner/llm-geometry/blob/main/docs/GEMMA_PART5_OPERATOR_ATLAS.md).

## Dashcam embeddings, geospatial alignment, and multimodal graph research

These are **public code and technical artifacts**, rather than verified stand-alone arXiv papers.

| Research area | Public implementation / documentation | Description |
| --- | --- | --- |
| Dashcam object/scene embeddings | [YOLO embedding pipeline](https://github.com/scottjoyner/auto-ingest/blob/main/auto_ingest/dashcam/yolo_embeddings.py) · [structured scene embeddings](https://github.com/scottjoyner/auto-ingest/blob/main/dashcam_yolo_structure_embeddings.py) | Computer-vision features and vector representations for searchable dashcam scenes. |
| Dashcam visual RAG | [Vision RAG design](https://github.com/scottjoyner/auto-ingest/blob/main/DASHCAM_VISION_PIPELINE.md) · [frame description pipeline](https://github.com/scottjoyner/auto-ingest/blob/main/dashcam_frame_vision.py) | Time-aligned frame descriptions, embeddings, and graph/vector retrieval. |
| GPS, location events, and trip linkage | [Location graph queries](https://github.com/scottjoyner/auto-ingest/blob/main/location.cy) · [location repair](https://github.com/scottjoyner/auto-ingest/blob/main/patch_missing_locationsv2.py) · [clip-to-trip linking](https://github.com/scottjoyner/auto-ingest/blob/main/scripts/link_clips_to_trips.py) | Time/geospatial association and location quality repair for multimodal records. |
| Phone geospatial data ingestion | [PhoneLog repository](https://github.com/scottjoyner/phonelog) | Location-event ingestion, idempotent graph upserts, and replay tooling. |
| Audio, transcripts, and multimodal search | [Auto-Ingest repository](https://github.com/scottjoyner/auto-ingest) · [transcript ingestion](https://github.com/scottjoyner/auto-ingest/blob/main/auto_ingest/ingest/transcripts.py) | Graph-linked transcription, diarization, media metadata, and retrieval. |
| Embedding geometry across small LLMs | [LLM Geometry research code](https://github.com/scottjoyner/llm-geometry) | Reproducible representation-similarity benchmarks and supporting paper assets. |

## Maintenance and publication checklist

1. Add a paper to **public research manuscripts** when its title and source/PDF are publicly reachable.
2. Move it to **verified arXiv publications** only after confirming the arXiv abstract page, ID, author list, and version.
3. Pin reproducibility details (benchmark data provenance, code commit, configuration, and evaluation limitations).
4. Do not expose private research repositories, raw dashcam/video/audio recordings, location histories, personal traces, or restricted datasets merely to make a publication link work.
5. Do not mistake third-party work cited in a repository for an authored publication. In particular, the arXiv paper cited by [`vec2vec`](https://github.com/scottjoyner/vec2vec) is credited in that repository to Jha, Zhang, Shmatikov, and Morris.

If a manuscript or preprint later receives a public permanent URL, add it here and link its implementation under the relevant research area.
