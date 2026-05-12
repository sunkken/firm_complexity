# Project Plan

## Goal

Replicate the firm complexity workflow from the source paper and adjust it for our own research use.

## Checklist

- [x] Download the cleaned 10-X files from the source website.
- [x] Keep only the 10-K files.
- [x] Create a Python cleanup script that scans all subfolders in a target path.
- [x] Delete files with names containing `10-Q`.
- [x] Delete files with names containing `10-K-A`.
- [ ] Create two-stage preprocessing pipeline for 10-K word extraction.
  - [ ] Move year folders into `data/raw/` for clean separation from intermediate and final outputs.
  - [x] Stage 1: Tokenization script (`preprocess_year_tokenize.py`)
    - [x] Takes "year" parameter and processes all files in that year folder (including subfolders).
    - [x] Prefers `data/raw/<year>/` and falls back to the legacy `data/<year>/` layout.
    - [x] Normalizes filings and writes batched parquet output to limit RAM usage.
    - [x] Emits batch-level progress so scan time and write time are both visible.
    - [x] Designed for PySpark parallelization with a small batch size on a 6-core i5.
    - [ ] Redesign Stage 1 output to persist per-document token counts (`token_counts`) instead of the full normalized text blob.
    - [ ] Estimated runtime: roughly **8-15 minutes per year** on the 6-core i5-8400 / 16GB machine, depending on filing size.
  - [x] Stage 2: Word counting script (`count_financial_words.py`)
    - [x] Reads tokenized intermediate files from Stage 1.
    - [x] Performs keyword counts from `token_counts` without Spark.
    - [x] Stores metadata: filename, total_words, category-prefixed word counts (e.g., `finance_leases`, `legal_litigation`).
    - [x] Creates yearly parquet outputs one row per input file.
    - [x] Output stored in `output/financial_word_counts_<year>.parquet`.
    - [x] Create separate non-Spark helper script for colleagues that mirrors the stage-2 keyword counting logic and runs in chunks.
  - [x] Create word category mapping file (`word_categories.json`) for downstream analysis.
- [ ] Add a small helper to combine yearly parquet outputs into one CSV when needed.
- [ ] Create script to convert parquet output to CSV format (customer preferred).
- [ ] Add additional implementation steps once word count extraction is in place.

Current status: 
- Initial cleanup stage complete. Files have been filtered to keep only 10-K files.
- Current direction: Stage 1 emits per-document token counts, stage 2 writes one parquet per year, and a small helper can combine the yearly parquet outputs into one CSV when needed.
- Next: use the per-year workflow for reruns and combine outputs only when a full CSV is required.

## Project Structure

- `data/` for downloaded source files and intermediate outputs. This folder stays git-ignored.
- `scripts/` for project scripts and helpers.
- `main.py` as the root orchestration entry point.
