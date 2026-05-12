"""
Combine per-year financial word count parquet outputs into one CSV.

This script:
- Finds `financial_word_counts_<year>.parquet` folders in an output directory
- Reads one year at a time with pandas
- Appends each year to a single CSV file

Usage:
    python scripts/combine_financial_word_counts.py
    python scripts/combine_financial_word_counts.py --input-dir output --output-csv output/financial_word_counts.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from tqdm import tqdm


DEFAULT_INPUT_DIR = Path("output")
DEFAULT_OUTPUT_CSV = Path("output/financial_word_counts.csv")


def find_year_parquet_dirs(input_dir: Path) -> list[Path]:
    """Return per-year parquet files or directories in sorted order."""
    year_paths = [path for path in input_dir.glob("financial_word_counts_*.parquet") if path.is_file() or path.is_dir()]
    return sorted(year_paths)


def combine_year_outputs(input_dir: Path, output_csv: Path) -> None:
    """Combine all per-year parquet outputs into a single CSV file."""
    year_dirs = find_year_parquet_dirs(input_dir)
    if not year_dirs:
        print(f"No per-year parquet outputs found in {input_dir}; nothing to combine.")
        return

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if output_csv.exists():
        output_csv.unlink()

    first_write = True
    for year_path in tqdm(year_dirs, desc="Combining years", unit="year"):
        frame = pd.read_parquet(year_path)
        frame.to_csv(output_csv, index=False, mode="a", header=first_write)
        first_write = False

    print(f"Wrote combined CSV to {output_csv}")
    print(f"Included {len(year_dirs)} yearly parquet output(s)")


def main() -> None:
    combine_year_outputs(DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_CSV)


if __name__ == "__main__":
    main()
