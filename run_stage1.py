"""
Stage 1 multi-year orchestrator.

Runs the existing year-level tokenization script across a list of years.
"""

from __future__ import annotations

import argparse
from typing import Iterable

from scripts.preprocess_year_tokenize import process_year as process_stage1_year


def expand_year_tokens(tokens: Iterable[str]) -> list[int]:
    """Accept tokens like '2025' or '2015-2020' and expand to ints."""
    years: list[int] = []
    for tok in tokens:
        tok = str(tok)
        if "-" in tok:
            parts = tok.split("-")
            if len(parts) != 2:
                raise ValueError(f"Invalid year range: {tok}")
            start, end = int(parts[0]), int(parts[1])
            if start > end:
                raise ValueError(f"Invalid year range (start> end): {tok}")
            years.extend(list(range(start, end + 1)))
        else:
            years.append(int(tok))
    # remove duplicates while preserving order
    seen = set()
    result: list[int] = []
    for y in years:
        if y not in seen:
            seen.add(y)
            result.append(y)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Stage 1 tokenization for one or more years (supports ranges like 2015-2020)"
    )
    parser.add_argument("years", nargs="+", type=str, help="Years or ranges to process (e.g. 2022 2015-2019)")
    parser.add_argument("--source-root", default="data/raw", help="Root folder containing raw year folders (default: data/raw)")
    parser.add_argument("--intermediate", default="data/intermediate", help="Intermediate output folder path (default: data/intermediate)")
    parser.add_argument("--batch-size", type=int, default=200, help="Number of files to process per batch (default: 200)")
    parser.add_argument("--target-file-mb", type=int, default=256, help="Target size (MB) per output file after compaction (default: 256)")

    args = parser.parse_args()

    years = expand_year_tokens(args.years)
    successes: list[int] = []
    failures: dict[int, str] = {}

    for year in years:
        try:
            print(f"\n--- Stage 1: processing year {year} ---")
            process_stage1_year(year, args.source_root, args.intermediate, args.batch_size, args.target_file_mb)
            successes.append(year)
        except Exception as exc:  # keep minimal and robust
            failures[year] = str(exc)
            print(f"Error processing year {year}: {exc}")

    print("\n=== Stage 1 Summary ===")
    print(f"Successful years: {len(successes)} -> {successes}")
    if failures:
        print(f"Failed years: {len(failures)}")
        for y, msg in failures.items():
            print(f" - {y}: {msg}")
        # exit non-zero to indicate partial failure
        import sys

        sys.exit(1)


if __name__ == "__main__":
    main()
