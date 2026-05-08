# Project Plan

## Goal

Replicate the firm complexity workflow from the source paper and adjust it for our own research use.

## Checklist

- [x] Download the cleaned 10-X files from the source website.
- [x] Keep only the 10-K files.
- [x] Create a Python cleanup script that scans all subfolders in a target path.
- [x] Delete files with names containing `10-Q`.
- [x] Delete files with names containing `10-K-A`.
- [ ] Define the data and analysis adjustments needed for our paper.
- [ ] Add the next implementation steps once the cleanup stage is in place.

Current status: the initial 2025 folder has been copied and filtered. Repeat the same copy-and-filter step as additional years are added.

## Project Structure

- `data/` for downloaded source files and intermediate outputs. This folder stays git-ignored.
- `scripts/` for project scripts and helpers.
- `main.py` as the root orchestration entry point.
