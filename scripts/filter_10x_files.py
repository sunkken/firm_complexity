"""Filter downloaded 10-X files down to the 10-K set.

The script walks a target directory recursively and deletes any file whose
name contains ``10-Q`` or ``10-K-A``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REMOVE_MARKERS = ("10-Q", "10-K-A")
PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..")))
DATA_ROOT = PROJECT_ROOT / "data"


def print_progress(current_index: int, total_count: int, folder_name: str | None = None) -> None:
    """Print a compact one-line progress bar with an optional folder label.

    Folder name is truncated to avoid very long lines and the extra string
    formatting is negligible compared to I/O and file operations.
    """

    bar_width = 24
    filled_width = int(bar_width * current_index / total_count) if total_count else bar_width
    bar = "#" * filled_width + "-" * (bar_width - filled_width)
    percent = int(100 * current_index / total_count) if total_count else 100
    if folder_name:
        display_name = folder_name
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."
        label = f"Filtering ({display_name}):"
    else:
        label = "Filtering:"

    print(f"\r{label} [{bar}] {percent:3d}%", end="", flush=True)


def should_remove_file(file_path: Path) -> bool:
    """Return True when a file should be removed from the dataset."""

    file_name = file_path.name.upper()
    return any(marker in file_name for marker in REMOVE_MARKERS)


def filter_10x_files(data_root_path: str | Path) -> tuple[int, int, int]:
    """Remove files that are not part of the 10-K-only dataset.

    `data_root_path` should point to the project `data/` folder. The function
    walks that folder and its subfolders and removes files matching
    `REMOVE_MARKERS`. The first-level subfolder name (e.g., year) is used in
    the progress label.

    Returns a tuple with the number of removed files, the number of files
    inspected, and the number of files kept.
    """

    data_root = Path(data_root_path)
    removed_count = 0
    inspected_count = 0

    if not data_root.exists():
        raise FileNotFoundError(f"Target folder does not exist: {data_root}")

    folders = [data_root, *[path for path in data_root.rglob("*") if path.is_dir()]]

    for index, folder in enumerate(folders, start=1):
        # Determine the first-level subfolder name (e.g., year) relative to data_root
        top_name: str | None = None
        try:
            rel = folder.relative_to(data_root)
            if rel.parts:
                top_name = f"{rel.parts[0]}/"
        except Exception:
            top_name = None

        print_progress(index - 1, len(folders), top_name)
        for file_path in folder.iterdir():
            if not file_path.is_file():
                continue

            inspected_count += 1
            if should_remove_file(file_path):
                file_path.unlink()
                removed_count += 1

    print_progress(len(folders), len(folders))
    print()

    kept_count = inspected_count - removed_count
    return removed_count, inspected_count, kept_count


def print_filter_summary(scanned_count: int, removed_count: int, kept_count: int) -> None:
    """Print a short summary of the filter run."""

    print(f"Scanned {scanned_count} files.")
    print(f"Deleted {removed_count} files.")
    print(f"Kept {kept_count} files.")


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line interface for the script."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root_path",
        nargs="?",
        default=DATA_ROOT,
        help="Path to the project data folder (e.g. project_root/data).",
    )
    return parser


def main() -> None:
    """Run the file filter against the chosen data folder."""

    parser = build_argument_parser()
    args = parser.parse_args()
    removed_count, inspected_count, kept_count = filter_10x_files(args.root_path)
    print_filter_summary(inspected_count, removed_count, kept_count)


if __name__ == "__main__":
    main()