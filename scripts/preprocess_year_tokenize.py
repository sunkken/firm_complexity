"""
Stage 1: Tokenization preprocessing for 10-K files.

This script:
1. Takes a "year" parameter (e.g., 1993, 1994, etc.)
2. Reads all files in data/raw/year/quarter/ folders
3. Normalizes text and counts total words
4. Stores tokenized output in intermediate parquet format per year
5. Writes in batches to keep driver memory usage low

Output: data/intermediate/tokenized_YYYY.parquet
    - filename: original filename
    - filepath: relative path to file
    - total_words: total word count in file
    - normalized_text: lowercased, punctuation-normalized filing text

Notes:
- BATCH_SIZE controls how many files are processed per write; increase it for fewer writes, decrease it to lower RAM usage.
"""

from __future__ import annotations

import argparse
import gc
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from tqdm import tqdm
from pyspark.sql import SparkSession


BATCH_SIZE = 100


def resolve_year_root(year: int, source_root: str = "data/raw") -> Path:
    """Resolve the year directory inside the raw data folder."""
    return Path(source_root) / str(year)


def read_file_text(filepath: str) -> str:
    """Read text from file, handling encoding errors gracefully."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().lower()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return ""


def normalize_text(text: str) -> str:
    """Lowercase and collapse punctuation/whitespace into single spaces."""
    if not text:
        return ""

    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def chunked(items: list[Path], batch_size: int):
    """Yield slices of the input list."""
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def process_year(
    year: int,
    source_root: str = "data/raw",
    intermediate_dir: str = "data/intermediate",
    batch_size: int = BATCH_SIZE,
) -> None:
    """
    Tokenize all 10-K files for a given year.
    
    Args:
        year: The year folder to process (e.g., 1993)
        source_root: Root folder containing raw year folders
        intermediate_dir: Path to store intermediate tokenized files
        batch_size: Number of files to process and write per batch
    """

    # Initialize Spark session
    spark = SparkSession.builder \
        .appName(f"TokenizeYear_{year}") \
        .config("spark.sql.shuffle.partitions", "4") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Setup paths
    data_root = resolve_year_root(year, source_root)
    intermediate_path = Path(intermediate_dir)
    intermediate_path.mkdir(parents=True, exist_ok=True)
    output_file = intermediate_path / f"tokenized_{year}.parquet"
    if output_file.exists():
        shutil.rmtree(output_file)
    
    print(f"\n{'='*70}")
    print(f"STAGE 1: TOKENIZATION - Year {year}")
    print(f"{'='*70}")
    print(f"Data path: {data_root}")
    print(f"Output file: {output_file}")
    print(f"Batch size: {batch_size}")
    
    if not data_root.exists():
        print(f"ERROR: Data path {data_root} does not exist!")
        sys.exit(1)
    
    # Find all text files in the raw year folder
    all_files = sorted(data_root.rglob("*.txt"))
    print(f"Found {len(all_files):,} text files\n")
    
    if not all_files:
        print("No 10-K files found. Exiting.")
        return
    
    total_batches = (len(all_files) + batch_size - 1) // batch_size
    written_rows = 0
    skipped_rows = 0

    print("Starting scan and batch writes...\n")
    for batch_number, batch_files in enumerate(
        tqdm(chunked(all_files, batch_size), total=total_batches, desc="Writing batches", unit="batch"),
        start=1,
    ):
        batch_records = []

        for filepath in batch_files:
            text = read_file_text(str(filepath))
            if not text:
                skipped_rows += 1
                continue

            normalized_text = normalize_text(text)
            if not normalized_text:
                skipped_rows += 1
                continue

            total_words = len(normalized_text.split())
            filepath_abs = filepath.resolve()
            batch_records.append(
                {
                    "filename": filepath.name,
                    "filepath": str(filepath_abs.relative_to(Path.cwd().resolve())).replace("\\", "/"),
                    "year": year,
                    "total_words": total_words,
                    "normalized_text": normalized_text,
                    "processed_date": datetime.now().isoformat(),
                }
            )

        if not batch_records:
            tqdm.write(f"Batch {batch_number}/{total_batches}: no readable files")
            continue

        batch_df = spark.createDataFrame(batch_records)
        write_mode = "overwrite" if written_rows == 0 else "append"
        batch_df.write.mode(write_mode).parquet(str(output_file))

        written_rows += len(batch_records)
        tqdm.write(
            f"Batch {batch_number}/{total_batches} written: {len(batch_records):,} files | "
            f"total written: {written_rows:,} | skipped so far: {skipped_rows:,}"
        )

        del batch_df
        del batch_records
        gc.collect()

    if written_rows == 0:
        print("No records were written. Exiting.")
        spark.stop()
        return

    print(f"\nSuccessfully wrote {written_rows:,} records to {output_file}")
    print(f"Skipped files: {skipped_rows:,}")
    print("Output is ready for Stage 2 processing.")
    
    print(f"\n{'='*70}")
    print(f"Stage 1 complete for year {year}")
    print(f"{'='*70}\n")
    
    spark.stop()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stage 1: Tokenize 10-K files for a specific year (preprocessing for fast word counting)"
    )
    parser.add_argument(
        "year",
        type=int,
        help="Year to process (e.g., 1993, 1994, ...)"
    )
    parser.add_argument(
        "--source-root",
        default="data/raw",
        help="Root folder containing raw year folders (default: data/raw)"
    )
    parser.add_argument(
        "--intermediate",
        default="data/intermediate",
        help="Intermediate output folder path (default: data/intermediate)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Number of files to process per batch (default: {BATCH_SIZE})"
    )
    
    args = parser.parse_args()
    
    process_year(args.year, args.source_root, args.intermediate, args.batch_size)


if __name__ == "__main__":
    main()
