"""Regenerate the judge-agreement summary from a hand-label CSV.

Usage:
    uv run python scripts/label_summary.py docs/pilots/data/hand-labels.csv
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "src")
from principal_eval.labels import read_labels, summarize  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path")
    args = ap.parse_args()
    labels = read_labels(args.csv_path)
    if not labels:
        raise SystemExit(f"no labels found in {args.csv_path}")
    print(json.dumps(summarize(labels), indent=2))


if __name__ == "__main__":
    main()
