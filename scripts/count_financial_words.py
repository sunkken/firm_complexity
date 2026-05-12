"""
Stage 2: Extract financial word counts from normalized 10-K text.

This script:
1. Takes a "year" parameter (e.g., 1993, 1994, etc.)
2. Reads tokenized files from Stage 1 (data/intermediate/tokenized_YYYY.parquet)
3. Counts financial keywords directly in Spark using SQL expressions
4. Creates category-prefixed columns for easy grouping
5. Appends results to the final parquet dataset

Input: data/intermediate/tokenized_YYYY.parquet (from Stage 1)
Output: output/financial_word_counts.parquet
    - filename, filepath, year, total_words, processed_date
    - finance_leases, finance_collateral, ... (category-prefixed word counts)
    - legal_litigation, legal_covenants, ...
    - ... (other categories)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, expr


def load_word_categories(category_file: str = "word_categories.json") -> dict:
    """Load word categories from JSON file."""
    with open(category_file, "r") as f:
        return json.load(f)


def escape_sql_literal(value: str) -> str:
    """Escape a Python string for use inside a Spark SQL literal."""
    return value.replace("'", "''")


def keyword_count_expr(text_column: str, keyword: str):
    """Build a Spark expression that counts a keyword in normalized text."""
    escaped_keyword = escape_sql_literal(keyword.lower())
    return expr(
        f"size(filter(split(coalesce({text_column}, ''), '\\\\s+'), x -> x = '{escaped_keyword}'))"
    )


def process_year(
    year: int,
    intermediate_dir: str = "data/intermediate",
    output_dir: str = "output"
) -> None:
    """
    Extract financial word counts for a given year.
    
    Args:
        year: The year to process (e.g., 1993)
        intermediate_dir: Path to tokenized intermediate files
        output_dir: Path to store final output
    """
    
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName(f"CountFinancialWords_{year}") \
        .config("spark.sql.shuffle.partitions", "4") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Load word categories and create lookup
    print(f"\n{'='*70}")
    print(f"STAGE 2: WORD COUNTING - Year {year}")
    print(f"{'='*70}")
    
    word_categories = load_word_categories("word_categories.json")
    
    total_keywords = sum(len(data["words"]) for data in word_categories.values())
    print(f"Loaded {len(word_categories)} categories with {total_keywords} keywords")
    print(f"Categories: {', '.join(word_categories.keys())}\n")
    
    # Setup paths
    intermediate_path = Path(intermediate_dir) / f"tokenized_{year}.parquet"
    output_path = Path(output_dir) / "financial_word_counts.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not intermediate_path.exists():
        print(f"ERROR: Tokenized file not found: {intermediate_path}")
        print(f"Did you run Stage 1 (preprocess_year_tokenize.py) first?")
        sys.exit(1)
    
    print(f"Reading tokenized data from: {intermediate_path}")
    
    # Read tokenized parquet
    df = spark.read.parquet(str(intermediate_path))
    print(f"Loaded {df.count():,} files to process\n")

    keyword_columns = []
    for category, data in word_categories.items():
        for word in data["words"]:
            column_name = f"{category}_{word}"
            keyword_columns.append(
                keyword_count_expr("normalized_text", word).alias(column_name)
            )

    print("Extracting word counts with Spark SQL expressions...")
    result_df = df.select(
        col("filename"),
        col("filepath"),
        col("year"),
        col("total_words"),
        col("processed_date"),
        *keyword_columns,
    )
    
    # Check if output file already exists
    if output_path.exists():
        print(f"\nAppending to existing output: {output_path}")
        result_df.write.mode("append").parquet(str(output_path))
    else:
        print(f"\nCreating new output file: {output_path}")
        result_df.write.mode("overwrite").parquet(str(output_path))

    print(f"\nFinished writing year {year} to {output_path}")
    
    print(f"\n{'='*70}")
    print(f"Stage 2 complete for year {year}")
    print(f"Final output: {output_path}")
    print(f"{'='*70}\n")
    
    spark.stop()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stage 2: Extract financial word counts from tokenized 10-K files"
    )
    parser.add_argument(
        "year",
        type=int,
        help="Year to process (e.g., 1993, 1994, ...)"
    )
    parser.add_argument(
        "--intermediate",
        default="data/intermediate",
        help="Intermediate folder path (default: data/intermediate)"
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output folder path (default: output)"
    )
    
    args = parser.parse_args()
    
    process_year(args.year, args.intermediate, args.output)


if __name__ == "__main__":
    main()
