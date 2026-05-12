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
    - [ ] Estimated runtime: roughly **8-15 minutes per year** on the 6-core i5-8400 / 16GB machine, depending on filing size.
  - [x] Stage 2: Word counting script (`count_financial_words.py`)
    - [x] Reads tokenized intermediate files from Stage 1.
    - [x] Performs Spark-native keyword counts from normalized text.
    - [x] Stores metadata: filename, total_words, category-prefixed word counts (e.g., `finance_leases`, `legal_litigation`).
    - [x] Creates/appends results to parquet dataset one row per input file.
    - [x] Output stored in `output/financial_word_counts.parquet`.
  - [x] Create word category mapping file (`word_categories.json`) for downstream analysis.
- [ ] Create script to convert parquet output to CSV format (customer preferred).
- [ ] Add additional implementation steps once word count extraction is in place.

Current status: 
- Initial cleanup stage complete. Files have been filtered to keep only 10-K files.
- Next: Validate the new batched tokenization and Spark-native word counting flow on 2025.

## Project Structure

- `data/` for downloaded source files and intermediate outputs. This folder stays git-ignored.
- `scripts/` for project scripts and helpers.
- `main.py` as the root orchestration entry point.
