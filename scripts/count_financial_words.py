"""
Stage 2: Extract financial word counts from tokenized 10-K data.

This script:
- Reads token-count parquet output from Stage 1 (`token_counts` maps)
- Counts category keywords in chunks without Spark
- Writes a parquet result that mirrors the old stage-2 output shape

Input: `data/intermediate/tokenized_<year>.parquet`
Output: `output/financial_word_counts.parquet`

Notes:
- `word_categories.json` controls the keywords at runtime.
- This script is designed to be easy for colleagues to rerun locally.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from tqdm import tqdm


def load_word_categories(category_file: str = "word_categories.json") -> dict:
    """Load word categories from JSON file."""
    with open(category_file, "r", encoding="utf-8") as f:
        return json.load(f)


def build_keyword_lookup(word_categories: dict) -> tuple[list[str], dict[str, list[str]]]:
    """Build output columns and a token -> output column lookup."""
    output_columns: list[str] = []
    token_lookup: dict[str, list[str]] = defaultdict(list)

    for category, data in word_categories.items():
        for word in data["words"]:
            column_name = f"{category}_{word}"
            output_columns.append(column_name)
            token_lookup[word.lower()].append(column_name)

    return output_columns, token_lookup


def coerce_token_counts(value) -> dict[str, int]:
    """Normalize the token_counts field into a plain Python dict."""
    if value is None:
        return {}

    if hasattr(value, "as_py"):
        value = value.as_py()

    if isinstance(value, dict):
        return {str(key).lower(): int(count) for key, count in value.items()}

    if isinstance(value, list):
        counts: dict[str, int] = {}
        for item in value:
            if hasattr(item, "as_py"):
                item = item.as_py()

            if isinstance(item, dict):
                if "key" in item and "value" in item:
                    counts[str(item["key"]).lower()] = int(item["value"])
                elif len(item) == 2:
                    key, count = next(iter(item.items()))
                    counts[str(key).lower()] = int(count)
            elif isinstance(item, (tuple, list)) and len(item) >= 2:
                counts[str(item[0]).lower()] = int(item[1])

        return counts

    try:
        return {str(key).lower(): int(count) for key, count in dict(value).items()}
    except Exception:
        return {}


def process_year(
    year: int,
    intermediate_dir: str = "data/intermediate",
    output_dir: str = "output",
    batch_size: int = 256,
    word_categories_file: str = "word_categories.json",
) -> None:
    """Count financial keywords for a given year without Spark."""

    print(f"\n{'='*70}")
    print(f"STAGE 2: WORD COUNTING - Year {year}")
    print(f"{'='*70}")

    word_categories = load_word_categories(word_categories_file)
    keyword_columns, token_lookup = build_keyword_lookup(word_categories)
    total_keywords = len(keyword_columns)

    print(f"Loaded {len(word_categories)} categories with {total_keywords} keywords")
    print(f"Categories: {', '.join(word_categories.keys())}\n")

    intermediate_path = Path(intermediate_dir) / f"tokenized_{year}.parquet"
    output_path = Path(output_dir) / f"financial_word_counts_{year}.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not intermediate_path.exists():
        print(f"ERROR: Tokenized file not found: {intermediate_path}")
        print("Did you run Stage 1 (preprocess_year_tokenize.py) first?")
        sys.exit(1)

    if output_path.exists():
        if output_path.is_dir():
            shutil.rmtree(output_path)
        else:
            output_path.unlink()

    print(f"Reading tokenized data from: {intermediate_path}")

    dataset = ds.dataset(str(intermediate_path), format="parquet")
    total_rows = dataset.count_rows()
    print(f"Loaded {total_rows:,} tokenized filings\n")

    available_columns = set(dataset.schema.names)
    if "token_counts" not in available_columns:
        raise ValueError("Input parquet must contain token_counts (Stage 1 must be regenerated)")

    print("Using Stage 1 token_counts column\n")

    read_columns = [
        "filename",
        "filepath",
        "form_type",
        "processed_date",
        "cik",
        "filing_date",
        "period_end_date",
        "total_words",
        "token_counts",
    ]
    output_columns = [
        "filename",
        "filepath",
        "form_type",
        "processed_date",
        "cik",
        "filing_date",
        "period_end_date",
        "total_words",
        *keyword_columns,
    ]

    writer: pq.ParquetWriter | None = None
    written_rows = 0
    batch_rows = 0

    batches = dataset.to_batches(batch_size=batch_size, columns=read_columns)
    for batch in tqdm(batches, total=max(1, (total_rows + batch_size - 1) // batch_size), desc="Counting batches", unit="batch"):
        frame = batch.to_pandas()
        output_records: list[dict] = []

        for row in frame.itertuples(index=False):
            token_counts = coerce_token_counts(row.token_counts)
            row_counts = {column: 0 for column in keyword_columns}

            for token, count in token_counts.items():
                matching_columns = token_lookup.get(token)
                if not matching_columns:
                    continue

                count_int = int(count)
                for column_name in matching_columns:
                    row_counts[column_name] += count_int

            output_record = {
                "filename": row.filename,
                "filepath": row.filepath,
                "form_type": getattr(row, "form_type", ""),
                "processed_date": row.processed_date,
                "cik": getattr(row, "cik", None),
                "filing_date": getattr(row, "filing_date", ""),
                "period_end_date": getattr(row, "period_end_date", ""),
                "total_words": int(row.total_words),
            }
            output_record.update(row_counts)
            output_records.append(output_record)

        if not output_records:
            continue

        batch_frame = pd.DataFrame(output_records, columns=output_columns)
        batch_table = pa.Table.from_pandas(batch_frame, preserve_index=False)

        if writer is None:
            writer = pq.ParquetWriter(str(output_path), batch_table.schema, compression="snappy")

        writer.write_table(batch_table)
        written_rows += len(output_records)
        batch_rows += len(output_records)

    if writer is not None:
        writer.close()

    print(f"\nFinished writing {written_rows:,} rows to {output_path}")
    print(f"Processed year {year} successfully.")
    print(f"Final output: {output_path}")
    print(f"{'='*70}\n")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stage 2: Extract financial word counts from token-count parquet files"
    )
    parser.add_argument("year", type=int, help="Year to process (e.g., 1993, 1994, ...)")
    parser.add_argument(
        "--intermediate",
        default="data/intermediate",
        help="Intermediate folder path (default: data/intermediate)",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output folder path (default: output)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Number of parquet rows to process per batch (default: 256)",
    )
    parser.add_argument(
        "--word-categories",
        default="word_categories.json",
        help="Path to the word category JSON file (default: word_categories.json)",
    )

    args = parser.parse_args()
    process_year(args.year, args.intermediate, args.output, args.batch_size, args.word_categories)


if __name__ == "__main__":
    main()
