"""Root entry point for the firm complexity project."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    """Run the current project orchestration flow."""

    subprocess.run([sys.executable, "scripts/filter_10x_files.py"], check=True)


if __name__ == "__main__":
    main()