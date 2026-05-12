# Project Plan

## Goal

Replicate the firm complexity workflow from the source paper and adjust it for our own research use.

## Checklist

- [x] Download the cleaned 10-X files from the source website.
- [x] Keep only the 10-K files.
- [x] Create a Python cleanup script that scans all subfolders in a target path.
- [x] Delete files with names containing `10-Q`.
- [x] Delete files with names containing `10-K-A`.
- [x] Create two-stage preprocessing pipeline for 10-K word extraction.
  - [x] Move year folders into `data/raw/` for clean separation from intermediate and final outputs.
  - [x] Stage 1: Tokenization script (`preprocess_year_tokenize.py`)
    - [x] Takes "year" parameter and processes all files in that year folder (including subfolders).
    - [x] Prefers `data/raw/<year>/` and falls back to the legacy `data/<year>/` layout.
    - [x] Normalizes filings and writes batched parquet output to limit RAM usage.
    - [x] Emits batch-level progress so scan time and write time are both visible.
    - [x] Designed for PySpark parallelization with a small batch size on a 6-core i5.
    - [x] Redesign Stage 1 output to persist per-document token counts (`token_counts`) instead of the full normalized text blob.
    - [x] Estimated runtime: roughly **8-15 minutes per year** on the 6-core i5-8400 / 16GB machine, depending on filing size.
  - [x] Stage 2: Word counting script (`count_financial_words.py`)
    - [x] Reads tokenized intermediate files from Stage 1.
    - [x] Performs keyword counts from `token_counts` without Spark.
    - [x] Stores metadata: filename, total_words, category-prefixed word counts (e.g., `finance_leases`, `legal_litigation`).
    - [x] Creates yearly parquet outputs one row per input file.
    - [x] Output stored in `output/financial_word_counts_<year>.parquet`.
    - [x] Create separate non-Spark helper script for colleagues that mirrors the stage-2 keyword counting logic and runs in chunks.
  - [x] Create word category mapping file (`word_categories.json`) for downstream analysis.
- [x] Add a small helper to combine yearly parquet outputs into one CSV when needed.
- [x] Create script to convert parquet output to CSV format (customer preferred).
- [ ] Add next-stage transformations for final complexity measures.
  - [ ] Scale each target word by total word count.
  - [ ] Calculate the 75th percentile for each word.
  - [ ] Rank each word within its word group.

Current status: 
- **Pipeline Complete**: Stage 1 tokenization, Stage 2 word counting, and CSV combiner all implemented and tested.
- **Architecture**: Stage 1 emits per-document token counts (dict) to intermediate parquet files. Stage 2 reads token counts in chunks without Spark and writes yearly parquet outputs. Combiner merges all yearly outputs into a single CSV.
- **Performance**: Tested on 2025 data (~6,700 filings). Stage 1: ~6 minutes. Stage 2: ~10 seconds. Combiner: <1 second.
- **Memory Efficiency**: Non-Spark Stage 2 eliminates OOM issues on constrained hardware. Per-year outputs enable flexible reruns.
- **Ready for Production**: All scripts tested and validated. Ready to scale to full 1993–2025 dataset.

## Project Structure

- `data/` for downloaded source files and intermediate outputs. This folder stays git-ignored.
- `scripts/` for project scripts:
  - `preprocess_year_tokenize.py` — Stage 1: tokenize raw 10-K files to token counts (run per year)
  - `count_financial_words.py` — Stage 2: extract financial keyword counts from tokenized data (run per year)
  - `combine_financial_word_counts.py` — Merge all yearly outputs into a single CSV
- `word_categories.json` — Keyword definitions for Stage 2 (edit to change keyword mappings)
