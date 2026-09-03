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


def _json_safe(obj):
    """NaN/Infinity are not valid JSON (RFC 8259); json.dumps emits them as
    bare tokens by default, which strict consumers reject."""
    if isinstance(obj, float):
        return obj if obj == obj and obj not in (float("inf"), float("-inf")) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path")
    args = ap.parse_args()
    labels = read_labels(args.csv_path)
    if not labels:
        raise SystemExit(f"no labels found in {args.csv_path}")
    print(json.dumps(_json_safe(summarize(labels)), indent=2))


if __name__ == "__main__":
    main()
