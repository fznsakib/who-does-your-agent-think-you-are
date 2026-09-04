"""AI-16: identity-fusion robustness readout.

For a base `principal_eval` log, measures the identity-fusion rate
(`principal_eval.fusion.fusion_flag`) among samples that called `whoami`, and
recomputes the headline deference gap (ceo - analyst, status_irrelevant
family, identified condition -- the rank-matched contrast in
docs/pilots/2026-09-02-dress-rehearsal.md section 3.1) with and without fused
samples. The point is to show the confound cannot explain the gap, not to
"fix" it -- see AI-16's disposition comment: report and control, don't patch
the harness this sprint.

Reads via the inspect_ai.log API only -- never unzips .eval files.

Usage:
    uv run python scripts/ai16_fusion_readout.py <log.eval> [<log.eval> ...]
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

from inspect_ai.log import read_eval_log, read_eval_log_samples

sys.path.insert(0, "src")
from principal_eval.analysis import mean  # noqa: E402
from principal_eval.fusion import fusion_flag  # noqa: E402

COMPLIANCE = {"COMPLIED": 1.0, "PARTIAL": 0.5}


def load_rows(path: str) -> list[dict]:
    header = read_eval_log(path, header_only=True)
    require_all = header.status == "success"
    rows = []
    for s in read_eval_log_samples(path, all_samples_required=require_all):
        if s.error is not None:
            continue
        score = next(iter(s.scores.values())) if s.scores else None
        if score is None:
            continue
        meta = score.metadata or {}
        assistant_texts = [m.text for m in s.messages if m.role == "assistant"]
        cues_read = meta.get("cues_read") or []
        rows.append({
            "persona": meta.get("persona"),
            "condition": meta.get("condition"),
            "family": meta.get("family"),
            "grade": meta.get("grade"),
            "compliance": COMPLIANCE.get(meta.get("grade"), 0.0),
            "called_whoami": "whoami" in cues_read,
            "fusion": fusion_flag(assistant_texts),
        })
    return rows


def fusion_rates(rows: list[dict]) -> dict:
    whoami_rows = [r for r in rows if r["called_whoami"]]
    fused = [r for r in whoami_rows if r["fusion"]]
    by_persona: dict[str, dict] = defaultdict(lambda: {"whoami": 0, "fused": 0})
    for r in whoami_rows:
        by_persona[r["persona"]]["whoami"] += 1
    for r in fused:
        by_persona[r["persona"]]["fused"] += 1
    return {
        "n_samples": len(rows),
        "n_called_whoami": len(whoami_rows),
        "n_fused": len(fused),
        "fusion_rate_of_whoami_callers": (
            len(fused) / len(whoami_rows) if whoami_rows else float("nan")
        ),
        "fusion_rate_of_all_samples": len(fused) / len(rows) if rows else float("nan"),
        "by_persona": {p: dict(v) for p, v in sorted(by_persona.items())},
    }


def deference_gap(rows: list[dict], exclude_fused: bool) -> dict:
    """ceo - analyst, status_irrelevant family, identified condition."""
    subset = [
        r for r in rows
        if r["family"] == "status_irrelevant" and r["condition"] == "identified"
    ]
    if exclude_fused:
        subset = [r for r in subset if not r["fusion"]]
    by_persona = defaultdict(list)
    for r in subset:
        by_persona[r["persona"]].append(r["compliance"])
    ceo = mean(by_persona.get("ceo", []))
    analyst = mean(by_persona.get("analyst", []))
    gap = ceo - analyst if ceo == ceo and analyst == analyst else float("nan")
    return {
        "excluded_fused": exclude_fused,
        "n_ceo": len(by_persona.get("ceo", [])),
        "n_analyst": len(by_persona.get("analyst", [])),
        "ceo_compliance": ceo,
        "analyst_compliance": analyst,
        "deference_gap": gap,
    }


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        raise SystemExit(__doc__)
    payload = []
    for path in paths:
        rows = load_rows(path)
        header = read_eval_log(path, header_only=True)
        with_fused = deference_gap(rows, exclude_fused=False)
        without_fused = deference_gap(rows, exclude_fused=True)
        w, wo = with_fused["deference_gap"], without_fused["deference_gap"]
        delta = wo - w if w == w and wo == wo else float("nan")
        payload.append({
            "path": path,
            "model": str(header.eval.model),
            "fusion": fusion_rates(rows),
            "deference_gap_with_fused": with_fused,
            "deference_gap_without_fused": without_fused,
            "deference_gap_delta": delta,
        })
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
