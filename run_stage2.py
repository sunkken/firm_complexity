"""
Stage 2 multi-year orchestrator.

Runs Stage 2 for multiple years and then executes Stage 3 once, after all
yearly outputs are finished successfully.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from scripts.combine_financial_word_counts import combine_year_outputs
from scripts.count_financial_words import process_year as process_stage2_year


def expand_year_tokens(tokens: Iterable[str]) -> list[int]:
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
        description="Run Stage 2 keyword counting for one or more years (supports ranges like 2015-2020)"
    )
    parser.add_argument("years", nargs="+", type=str, help="Years or ranges to process (e.g. 2022 2015-2019)")
    parser.add_argument("--intermediate", default="data/intermediate", help="Intermediate folder path (default: data/intermediate)")
    parser.add_argument("--output", default="output", help="Output folder path (default: output)")
    parser.add_argument("--batch-size", type=int, default=256, help="Number of parquet rows to process per batch (default: 256)")
    parser.add_argument("--word-categories", default="word_categories.json", help="Path to the word category JSON file (default: word_categories.json)")
    parser.add_argument("--output-csv", default="output/financial_word_counts.csv", help="Combined CSV path written after Stage 2 completes (default: output/financial_word_counts.csv)")
    parser.add_argument("--no-combine", action="store_true", help="Do not run the combine (Stage 3) step after counting")

    args = parser.parse_args()

    years = expand_year_tokens(args.years)
    successes: list[int] = []
    failures: dict[int, str] = {}

    for year in years:
        try:
            print(f"\n--- Stage 2: processing year {year} ---")
            process_stage2_year(year, args.intermediate, args.output, args.batch_size, args.word_categories)
            successes.append(year)
        except Exception as exc:
            failures[year] = str(exc)
            print(f"Error processing year {year}: {exc}")

    # combine only those years that succeeded (or always combine all outputs?)
    if args.no_combine:
        print("\nSkipping combine step (--no-combine set).")
    else:
        try:
            print("\nCombining available yearly outputs into final CSV...")
            combine_year_outputs(Path(args.output), Path(args.output_csv))
        except Exception as exc:
            print(f"Error during combine step: {exc}")
            failures['combine'] = str(exc)

    print("\n=== Stage 2 Summary ===")
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
