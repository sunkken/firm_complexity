# Firm Complexity Project

This project replicates the workflow used in the paper and data resources on measuring firm complexity, then adapts it for our own paper.

Reference overview: the SRAF complexity page describes an omnibus text-based complexity measure for 10-K filings, built using machine learning and an application-specific lexicon, and paired with 10-K file size as a useful proxy.

## Start Point

The first step is to download the cleaned 10-X files from the source website and keep only the 10-K filings.

## Next Steps

- Build a Python script that walks all subfolders under a target path.
- Remove any file whose name includes `10-Q` or `10-K-A`.
- Keep the rest of the workflow focused on the data pipeline and analysis needed for our version of the paper.

## Project Layout

- `data/` stores downloaded files and stays out of version control.
- `scripts/` holds the project scripts.
- `main.py` is the top-level entry point for orchestration.

## Local Setup

1. Create the virtual environment: `python -m venv .venv`
2. Activate it in PowerShell: `.\.venv\Scripts\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the filter script: `python scripts/filter_10x_files.py`

If `python` is not on your PATH, use the Windows Python launcher instead: `py -3 -m venv .venv`.
