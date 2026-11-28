Markdown
## Citation If you use these benchmarks or reference the Virtual Memory Pipeline (VMP) and SDO-Tokenization architecture, please cite: > Tsao, S. A. (2026). *Zero-Copy Memory Substrates and Structural S-Tokens: Solving the AI Data Ingestion and Context Bottleneck*. Zenodo. https://doi.org/10.5281/zenodo.24553576 ```bibtex @misc{tsao2026zerocopy,   author       = {Tsao, Sheng Augustin},   title        = {Zero-Copy Memory Substrates and Structural S-Tokens: Solving the AI Data Ingestion and Context Bottleneck},   year         = {2026},   publisher    = {Zenodo},   doi          = {10.5281/zenodo.24553576},   url          = {[https://doi.org/10.5281/zenodo.24553576](https://doi.org/10.5281/zenodo.24553576)} } 

# GUDT / VMP & SDO-Tokenization Empirical Benchmarks

Official reproducible benchmark suite accompanying the paper:
**"Zero-Copy Memory Substrates and Structural S-Tokens: Solving the AI Data Ingestion and Context Bottleneck"**  
Author: Sheng Augustin Tsao  
Protected under U.S. Provisional Patent Application No. 64/124,511 and 64/201,281 

## Overview
This repository provides the synthetic data generators and benchmark harnesses used in Section VI of the paper to evaluate:
1. **Multi-Scale Workload Generation** (`generate_workloads.py`): Generates 1K–1M record relational tables and 100-page (1,000-paragraph) word-processing corpora with deterministic byte-level ground-truth verification files.
2. **Cross-Substrate Storage & Hydration Benchmark** (`run_cross_substrate_bench.py`): Compares redundant JSON, Markdown tables, CSV, indexed SQLite B-Trees, Apache Parquet, Apache Arrow IPC (`mmap`), and memory-aligned `.sdo` Virtual Memory Pipeline (`mmap`) images across disk size, BPE token count (`cl100k_base`), cold mount latency, and $O(1)$ random point lookups.
3. **Frontier LLM Table-QA Reasoning & Token Evaluation** (`run_llm_tableqa_eval.py`): Evaluates exact-match reasoning accuracy and native prompt token consumption (`N = 100` multi-column tables) across JSON, flat CSV, and GUDT S-Token coordinate matrices.

## Quick Start
```bash
pip install -r requirements.txt
python generate_workloads.py
python run_cross_substrate_bench.py
``` 



