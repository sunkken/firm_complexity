# Firm Complexity Project

This repository contains a lightweight reimplementation of the firm complexity workflow for 10-K filings. The pipeline keeps the data flow simple and reproducible:

1. tokenize each filing and store token counts per document
2. count financial keywords from those token counts
3. merge yearly results into a single CSV when needed

The goal is practical research use on a normal laptop, not a heavy production pipeline.

## What Stage 1 Does

Stage 1 lives in [scripts/preprocess_year_tokenize.py](scripts/preprocess_year_tokenize.py) and turns each filing into a parquet row with these fields:

- `filename`
- `filepath`
- `year`
- `total_words`
- `token_counts`
- `processed_date`

The important part is `token_counts`: instead of saving the full cleaned text, we save a frequency map of every token in the filing. That makes Stage 2 fast and reusable.

Compared with the original authors’ parsing approach, our tokenizer is simpler and more reusable. Their code tokenized the raw text with word-regex rules and then only counted words found in the finance dictionary. Our version stores all token frequencies up front, so later keyword definitions can be changed without rerunning Stage 1 as long as the new words match the same tokenization rules.

Stage 1 uses Spark for file processing and parquet writing. It has been working well in WSL/Linux, but it is not a good fit for a Windows-only setup.

## What Stage 2 Does

Stage 2 lives in [scripts/count_financial_words.py](scripts/count_financial_words.py). It reads one year of tokenized parquet output, applies the keyword list from [word_categories.json](word_categories.json), and writes yearly parquet output with one row per filing.

If you want a single CSV for analysis, [scripts/combine_financial_word_counts.py](scripts/combine_financial_word_counts.py) merges all yearly parquet outputs into `output/financial_word_counts.csv`.

## Project Layout

- `data/` stores downloaded source files and intermediate outputs. This folder is ignored by git.
- `output/` stores yearly word-count results and the final combined CSV.
- `scripts/` holds the three pipeline scripts.
- `word_categories.json` defines the Stage 2 keyword groups.

## Setup

1. Create a virtual environment:
	`python -m venv .venv`
2. Activate it:
	`source .venv/bin/activate`
3. Install dependencies:
	`pip install -r requirements.txt`

## How To Run

Run the scripts one at a time, one year at a time.

### Stage 1: Tokenize a year

```bash
python scripts/preprocess_year_tokenize.py 2025
```

Optional arguments:

- `--source-root data/raw` to point at a different raw-data folder
- `--intermediate data/intermediate` to change the Stage 1 output folder
- `--batch-size 100` to process more or fewer filings per batch
- `--target-file-mb 256` to control the compacted parquet file size

### Stage 2: Count financial keywords for that year

```bash
python scripts/count_financial_words.py 2025
```

Optional arguments:

- `--intermediate data/intermediate` to point at the Stage 1 output
- `--output output` to change the Stage 2 output folder
- `--batch-size 256` to control chunk size during counting
- `--word-categories word_categories.json` to use a different keyword file

### Stage 3: Merge all yearly outputs into one CSV

```bash
python scripts/combine_financial_word_counts.py
```

This looks for all files named `financial_word_counts_<year>.parquet` in `output/` and writes `output/financial_word_counts.csv`.

## Typical Workflow

If Stage 1 output already exists and you only want to change keywords, skip preprocessing and rerun Stage 2 and 3 only.

For a single year, the usual flow is:

```bash
python scripts/preprocess_year_tokenize.py 2025
python scripts/count_financial_words.py 2025
```

When all years are finished, run:

```bash
python scripts/combine_financial_word_counts.py
```

## Notes

- Stage 1 is designed to keep memory usage low by writing in batches and compacting the final parquet output.
- Stage 1 depends on Spark, so this repo is best used in WSL/Linux rather than a Windows-only environment.
- Stage 2 does not use Spark, which keeps it fast and avoids the memory issues we hit on a laptop.
- You can change the keyword categories later by editing `word_categories.json` and rerunning Stage 2 only.
