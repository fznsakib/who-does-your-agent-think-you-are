"""Build a stratified hand-labelling manifest from a set of eval logs.

Usage:
    uv run python scripts/sample_for_labelling.py \\
        logs/ai15-gpt5nano/base logs/ai15-gpt5nano/pushback \\
        logs/ai5-pilot/haiku-base logs/ai5-pilot/haiku-pushback \\
        --n 60 --out docs/pilots/data/manifest.json

Default n=60. See docs/analysis-and-hand-labelling.md for the stratum
quotas and how the harmful_action_occurred stratum behaves on logs scored
before AI-20 added that field.
"""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "src")
from principal_eval.sampling import load_candidates, stratified_sample, write_manifest  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+", help="log files or directories")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=6)
    ap.add_argument("--out", default="docs/pilots/data/manifest.json")
    args = ap.parse_args()

    candidates = load_candidates(args.paths)
    if not candidates:
        raise SystemExit(f"no scored samples found under: {args.paths}")
    sample = stratified_sample(candidates, args.n, seed=args.seed)
    write_manifest(sample, args.out)

    from collections import Counter
    strata_counts = Counter(s for c in sample for s in c.strata())
    print(f"{len(sample)} / {len(candidates)} candidates sampled -> {args.out}")
    print(f"stratum coverage: {dict(strata_counts)}")
    print(f"models: {sorted({c.model for c in sample})}")
    print(f"scenarios covered: {len({c.scenario for c in sample})}")


if __name__ == "__main__":
    main()
