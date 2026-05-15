# Firm Complexity Project

This repository contains a lightweight reimplementation of the firm complexity workflow for 10-K filings. The pipeline keeps the data flow simple and reproducible:

1. tokenize each filing and store token counts per document
2. count financial keywords from those token counts
3. merge yearly results into a single CSV when needed

The goal is practical research use on a normal laptop, not a heavy production pipeline.

## What Stage 1 Does

Stage 1 lives in [scripts/preprocess_year_tokenize.py](scripts/preprocess_year_tokenize.py) and turns each filing into a parquet row with these fields (in this order):

- `filename`
- `filepath`
- `form_type`
- `processed_date`
- `cik`
- `filing_date`
- `period_end_date`
- `total_words`
- `token_counts`

The important part is `token_counts`: instead of saving the full cleaned text, we save a frequency map of every token in the filing. Stage 1 also preserves light metadata (`form_type`, `cik`, `filing_date`, `period_end_date`) so downstream counting and analysis can include those fields without extra joins. That makes Stage 2 fast and reusable.

Tokenization rules (summary): tokens are extracted with a simple regex that captures lowercase alphanumeric runs (`[a-z0-9]+`), then tokens of length 1 and purely-numeric tokens are discarded. In practice this means:

- Text is lowercased before tokenizing.
- Punctuation, apostrophes, and hyphens break tokens. For example, "company's" is tokenized to `company` (the trailing `s` is dropped because single-letter tokens are removed), and "state-of-the-art" becomes `state`, `of`, `the`, `art`.
- Numbers-only tokens are ignored (e.g., `2023`).

Because of this behavior, changing the keyword list to include forms with apostrophes or combined punctuation may not match existing tokens unless you adjust the tokenizer.

Compared with the original authors’ parsing approach, our tokenizer is simpler and more reusable. Their code tokenized the raw text with word-regex rules and then only counted words found in the finance dictionary. Our version stores all token frequencies up front, so later keyword definitions can be changed without rerunning Stage 1 as long as the new words match the same tokenization rules.

Stage 1 uses Spark for file processing and parquet writing. It has been working well in WSL/Linux, but it is not a good fit for a Windows-only setup.

## What Stage 2 Does

Stage 2 lives in [scripts/count_financial_words.py](scripts/count_financial_words.py). It reads one year of tokenized parquet output, applies the keyword list from [word_categories.json](word_categories.json), and writes yearly parquet output with one row per filing.

If you want a single CSV for analysis, [scripts/combine_financial_word_counts.py](scripts/combine_financial_word_counts.py) merges all yearly parquet outputs into `output/financial_word_counts.csv`.

## Project Layout

- `data/` stores downloaded source files and intermediate outputs. This folder is ignored by git.
- `output/` stores yearly word-count results and the final combined CSV.
- `scripts/` holds the year-level pipeline scripts.
- `word_categories.json` defines the Stage 2 keyword groups.

## Setup

1. Create a virtual environment:
	`python -m venv .venv`
2. Activate it:
	`source .venv/bin/activate`
3. Install dependencies:
	`pip install -r requirements.txt`

## How To Run

Use the root orchestrators for normal runs. They accept either one year or many years.

### Stage 1 Orchestrator: Tokenize one or more years

```bash
python run_stage1.py 2025
```

Optional arguments:

- `--source-root data/raw` to point at a different raw-data folder
- `--intermediate data/intermediate` to change the Stage 1 output folder
- `--batch-size 100` to process more or fewer filings per batch
- `--target-file-mb 256` to control the compacted parquet file size

Example with multiple years:

```bash
python run_stage1.py 2022 2023 2024
```

Example with a range:

```bash
python run_stage1.py 2015-2025
```

### Stage 2 Orchestrator: Count one or more years, then merge them

```bash
python run_stage2.py 2025
```

Optional arguments:

- `--intermediate data/intermediate` to point at the Stage 1 output
- `--output output` to change the Stage 2 output folder
- `--batch-size 256` to control chunk size during counting
- `--word-categories word_categories.json` to use a different keyword file
- `--no-combine` to skip the Stage 3 combine step (useful when running counting only)

Example with multiple years:

```bash
python run_stage2.py 2022 2023 2024
```

Example with a range:

```bash
python run_stage2.py 2015-2025
```

This runs Stage 2 for each year in order and then runs Stage 3 automatically after the last year finishes. Both orchestrators print a per-year success/failure summary at the end.

### Stage 3: Merge all yearly outputs into one CSV

```bash
python scripts/combine_financial_word_counts.py
```

This looks for all files named `financial_word_counts_<year>.parquet` in `output/` and writes `output/financial_word_counts.csv`.

## Typical Workflow

If Stage 1 output already exists and you only want to change keywords, rerun Stage 2 with the root orchestrator:

```bash
python run_stage2.py 2025
```

For a single year, the usual flow is:

```bash
python run_stage1.py 2025
python run_stage2.py 2025
```

If you need to rebuild the combined CSV separately, run:

```bash
python scripts/combine_financial_word_counts.py
```

The year-level scripts in [scripts/](scripts) are still available if you want to run one stage manually, but the root orchestrators are the preferred entry points.

## Notes

- Stage 1 is designed to keep memory usage low by writing in batches and compacting the final parquet output.
- Stage 1 depends on Spark, so this repo is best used in WSL/Linux rather than a Windows-only environment.
- Stage 2 does not use Spark, which keeps it fast and avoids the memory issues we hit on a laptop.
- You can change the keyword categories later by editing `word_categories.json` and rerunning Stage 2 only.
