"""
Stage 1: Tokenization preprocessing for 10-K files.

This script:
- Takes a `year` parameter (e.g., 1993, 1994, ...)
- Reads all files in `data/raw/<year>/...` folders
- Tokenizes text and stores per-document token counts
- Stores tokenized output in intermediate parquet format per year
- Writes in batches to keep driver memory usage low
- Compacts the intermediate parquet files to target file sizes (snappy)

Output: `data/intermediate/tokenized_<year>.parquet`
    - filename, filepath, year, total_words, token_counts, processed_date

Notes:
- BATCH_SIZE controls how many files are processed per write; increase it for fewer writes, decrease it to lower RAM usage.
- TOKEN_PATTERN defines how text is tokenized; currently it captures lowercase alphanumeric tokens of length > 1 that are not purely digits.
"""

from __future__ import annotations

import argparse
import gc
import math
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

from pyspark.sql import SparkSession
from tqdm import tqdm


BATCH_SIZE = 100
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

def resolve_year_root(year: int, source_root: str = "data/raw") -> Path:
    return Path(source_root) / str(year)


def read_file_text(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return ""

def tokenize_and_count(text: str) -> tuple[dict[str, int], int]:
    if not text:
        return {}, 0

    tokens = [token for token in TOKEN_PATTERN.findall(text.lower()) if len(token) > 1 and not token.isdigit()]
    if not tokens:
        return {}, 0

    token_counts = Counter(tokens)
    return dict(token_counts), len(tokens)


def chunked(items: list[Path], batch_size: int):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def process_year(
    year: int,
    source_root: str = "data/raw",
    intermediate_dir: str = "data/intermediate",
    batch_size: int = BATCH_SIZE,
    target_file_mb: int = 256,
) -> None:
    # Initialize Spark
    spark = (
        SparkSession.builder.appName(f"TokenizeYear_{year}")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.parquet.enableVectorizedReader", "false")
        .config("spark.sql.parquet.columnarReaderBatchSize", "256")
        .config("spark.sql.files.maxPartitionBytes", "64m")
        .getOrCreate()
    )
    # suppress noisy spark warnings that break tqdm
    spark.sparkContext.setLogLevel("ERROR")

    data_root = resolve_year_root(year, source_root)
    intermediate_path = Path(intermediate_dir)
    intermediate_path.mkdir(parents=True, exist_ok=True)

    raw_output = intermediate_path / f"tokenized_{year}_raw.parquet"
    final_output = intermediate_path / f"tokenized_{year}.parquet"

    # ensure clean output
    if raw_output.exists():
        shutil.rmtree(raw_output)
    if final_output.exists():
        shutil.rmtree(final_output)

    print(f"\n{'='*70}")
    print(f"STAGE 1: TOKENIZATION - Year {year}")
    print(f"{'='*70}")
    print(f"Data path: {data_root}")
    print(f"Staging (raw) output: {raw_output}")
    print(f"Final output (compacted): {final_output}")
    print(f"Target file size (MB): {target_file_mb}")
    print(f"Batch size: {batch_size}\n")

    if not data_root.exists():
        print(f"ERROR: Data path {data_root} does not exist!")
        spark.stop()
        sys.exit(1)

    all_files = sorted(data_root.rglob("*.txt"))
    print(f"Found {len(all_files):,} text files\n")
    if not all_files:
        print("No 10-K files found. Exiting.")
        spark.stop()
        return

    total_batches = (len(all_files) + batch_size - 1) // batch_size
    written_rows = 0
    skipped_rows = 0

    print("Starting scan and batch writes...\n")
    for batch_files in tqdm(chunked(all_files, batch_size), total=total_batches, desc="Writing batches", unit="batch"):
        batch_records = []
        for filepath in batch_files:
            text = read_file_text(str(filepath))
            if not text:
                skipped_rows += 1
                continue

            token_counts, total_words = tokenize_and_count(text)
            if not token_counts:
                skipped_rows += 1
                continue

            filepath_abs = filepath.resolve()
            batch_records.append(
                {
                    "filename": filepath.name,
                    "filepath": str(filepath_abs.relative_to(Path.cwd().resolve())).replace("\\", "/"),
                    "year": year,
                    "total_words": total_words,
                    "token_counts": token_counts,
                    "processed_date": datetime.now().isoformat(),
                }
            )

        if not batch_records:
            continue

        batch_df = spark.createDataFrame(batch_records)
        write_mode = "overwrite" if written_rows == 0 else "append"
        batch_df.write.mode(write_mode).parquet(str(raw_output))
        written_rows += len(batch_records)

        # free memory
        del batch_df
        del batch_records
        gc.collect()

    if written_rows == 0:
        print("No records were written. Exiting.")
        spark.stop()
        return

    print(f"\nSuccessfully wrote {written_rows:,} records to {raw_output}")
    print(f"Skipped files: {skipped_rows:,}")
    print("Output ready; compacting to target size now...\n")

    # compute raw size and target partitions
    total_bytes = 0
    for f in raw_output.rglob("*"):
        if f.is_file():
            try:
                total_bytes += f.stat().st_size
            except Exception:
                pass

    target_bytes = max(1, int(target_file_mb) * 1024 * 1024)
    num_output_files = max(1, int(math.ceil(total_bytes / target_bytes)))

    from tqdm import tqdm as _tqdm
    print(f"Compacting {raw_output} ({total_bytes / 1024**2:.1f} MB) into {num_output_files} file(s) -> {final_output} ...")
    with _tqdm(total=1, desc="Compacting", unit="step") as comp_bar:
        raw_df = spark.read.parquet(str(raw_output))
        raw_df.repartition(num_output_files).write.mode("overwrite").option("compression", "snappy").parquet(str(final_output))
        comp_bar.update(1)

    # remove staging
    try:
        if raw_output.exists():
            shutil.rmtree(raw_output)
    except Exception as e:
        print(f"Warning: failed to remove staging folder {raw_output}: {e}")

    # final summary
    final_size = 0
    final_parts = 0
    if final_output.exists():
        for p in final_output.rglob("*"):
            if p.is_file():
                final_size += p.stat().st_size
                if p.name.startswith("part-"):
                    final_parts += 1

    print(f"Final coalesced output written to {final_output}")
    print(f"Final size: {final_size / 1024**2:.2f} MB in {final_parts} part file(s)")
    print(f"\n{'='*70}")
    print(f"Stage 1 complete for year {year}")
    print(f"{'='*70}\n")

    spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 1: Tokenize 10-K files for a specific year (preprocessing for fast word counting)"
    )
    parser.add_argument("year", type=int, help="Year to process (e.g., 1993, 1994, ...)")
    parser.add_argument("--source-root", default="data/raw", help="Root folder containing raw year folders (default: data/raw)")
    parser.add_argument("--intermediate", default="data/intermediate", help="Intermediate output folder path (default: data/intermediate)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help=f"Number of files to process per batch (default: {BATCH_SIZE})")
    parser.add_argument("--target-file-mb", type=int, default=256, help="Target size (MB) per output file after compaction (default: 256)")

    args = parser.parse_args()
    process_year(args.year, args.source_root, args.intermediate, args.batch_size, args.target_file_mb)


if __name__ == "__main__":
    main()
