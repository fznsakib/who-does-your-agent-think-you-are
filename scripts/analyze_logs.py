"""Analysis pipeline CLI: every headline checklist item, per model, from a
set of log paths (files or directories, forwarded to
`inspect_ai.log.list_eval_logs`).

Usage:
    uv run python scripts/analyze_logs.py logs/ai15-gpt5nano/base logs/ai15-gpt5nano/pushback
    uv run python scripts/analyze_logs.py logs/ai5-pilot/haiku-base logs/ai5-pilot/haiku-pushback --out-json out.json

See docs/analysis-and-hand-labelling.md for what each section means.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from inspect_ai.log import list_eval_logs

sys.path.insert(0, "src")
from principal_eval.analysis import full_report, load_rows  # noqa: E402


def _json_safe(obj):
    """Recursively replaces non-finite floats (NaN/Infinity) with None.
    `json.dumps` emits the bare tokens NaN/Infinity for these by default,
    which is not valid JSON (RFC 8259) and gets rejected by strict
    consumers such as `JSON.parse` -- exactly the risk for the documented
    `--out-json` artifact."""
    if isinstance(obj, float):
        return obj if obj == obj and obj not in (float("inf"), float("-inf")) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def expand_paths(paths: list[str]) -> list[str]:
    out = []
    for p in paths:
        if p.endswith(".eval") or p.endswith(".json"):
            out.append(p)
        else:
            out.extend(info.name for info in list_eval_logs(p, recursive=True))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+", help="log files or directories")
    ap.add_argument("--out-json", default=None, help="write the full report JSON here too")
    args = ap.parse_args()

    all_paths = expand_paths(args.paths)
    if not all_paths:
        raise SystemExit(f"no .eval/.json logs found under: {args.paths}")

    load_report = load_rows(all_paths)
    by_model: dict[str, dict[str, list]] = defaultdict(lambda: {"base": [], "pushback": []})
    for r in load_report.rows:
        by_model[r.model][r.variant].append(r)

    results = {}
    for model, variants in by_model.items():
        results[model] = full_report(variants["base"], variants["pushback"], load_report)

    payload = {
        "logs_loaded": load_report.logs_loaded,
        "n_errors": load_report.n_errors,
        "n_malformed": load_report.n_malformed,
        "fields_available": load_report.fields_available,
        "by_model": results,
    }
    text = json.dumps(_json_safe(payload), indent=2, default=str)
    print(text)
    if args.out_json:
        with open(args.out_json, "w") as f:
            f.write(text)


if __name__ == "__main__":
    main()
