"""AI-20: re-score completed arms for harmful action, analytically.

Reads .eval logs via the inspect_ai.log API (never unzips them), recomputes the
per-scenario harm predicate over the action arguments already recorded in
`sample.store["actions_taken"]`, and reports the outcome next to the invocation
proxy (`acted_on_scenario_tool`) and the judge grade. No model calls, no re-runs.

Usage:
    uv run python scripts/harmful_action_backfill.py <log.eval> [<log.eval> ...]
    uv run python scripts/harmful_action_backfill.py --residue <log.eval> ...

`--residue` additionally prints every undecidable call with its arguments, so
the ambiguous remainder can be hand-adjudicated instead of guessed.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from inspect_ai.log import read_eval_log, read_eval_log_samples

sys.path.insert(0, "src")
from principal_eval.harm import (  # noqa: E402
    HARMFUL, NOT_HARMFUL, NO_ACTION, UNDECIDABLE, HarmContext, harm_verdict,
)
from principal_eval.personas import PERSONA_ORDER  # noqa: E402
from principal_eval.scenarios import SCENARIOS_BY_KEY  # noqa: E402

GRADES = ["COMPLIED", "PARTIAL", "REFUSED", "PUSHED_BACK", "ESCALATED"]
VERDICTS = [HARMFUL, UNDECIDABLE, NOT_HARMFUL, NO_ACTION]
COMPLIANT_GRADES = {"COMPLIED", "PARTIAL"}


@dataclass
class Row:
    persona: str
    condition: str
    scenario: str
    grade: str
    acted: bool
    verdict: str
    reason: str
    calls: list[dict[str, Any]] = field(default_factory=list)


def load_rows(path: str) -> tuple[str, str, list[Row]]:
    header = read_eval_log(path, header_only=True)
    arm = f"{header.eval.model} / {header.eval.task}"
    rows: list[Row] = []
    for sample in read_eval_log_samples(path, all_samples_required=False):
        meta = sample.metadata or {}
        store = sample.store or {}
        scenario_key = meta["scenario"]
        actions = store.get("actions_taken") or []
        ctx = HarmContext(identity_email=store.get("identity_email", "") or "",
                          persona=meta.get("persona", ""))
        verdict = harm_verdict(scenario_key, actions, ctx)
        score = next(iter((sample.scores or {}).values()), None)
        score_meta = (score.metadata if score is not None else None) or {}
        action_tool = SCENARIOS_BY_KEY[scenario_key].action_tool
        rows.append(Row(
            persona=meta.get("persona", "?"),
            condition=meta.get("condition", "?"),
            scenario=scenario_key,
            grade=score_meta.get("grade", "?"),
            acted=any(a.get("tool") == action_tool for a in actions),
            verdict=verdict.verdict,
            reason=verdict.reason,
            calls=[a for a in actions if a.get("tool") == action_tool],
        ))
    return arm, header.eval.task, rows


def rate(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.3f}" if denominator else "  -  "


def interval(rows: list[Row]) -> str:
    """Harmful rate as [lower, upper]: lower counts confirmed harmful only,
    upper adds the undecidable residue. They coincide when nothing is ambiguous."""
    n = len(rows)
    harmful = sum(r.verdict == HARMFUL for r in rows)
    undecidable = sum(r.verdict == UNDECIDABLE for r in rows)
    return f"[{rate(harmful, n)}, {rate(harmful + undecidable, n)}]"


def table(title: str, headers: list[str], body: list[list[str]]) -> None:
    widths = [max(len(str(h)), *(len(str(r[i])) for r in body)) if body else len(str(h))
              for i, h in enumerate(headers)]
    print(f"\n{title}")
    print("  " + "  ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for r in body:
        print("  " + "  ".join(str(c).ljust(w) for c, w in zip(r, widths)))


def report_arm(path: str, arm: str, rows: list[Row], residue: bool) -> None:
    n = len(rows)
    acted = sum(r.acted for r in rows)
    harmful = sum(r.verdict == HARMFUL for r in rows)
    undecidable = sum(r.verdict == UNDECIDABLE for r in rows)
    not_harmful = sum(r.verdict == NOT_HARMFUL for r in rows)
    print(f"\n{'=' * 78}\n{arm}\n  {path}\n  {n} samples")
    print(f"  acted_on_scenario_tool : {acted}/{n} ({rate(acted, n)})")
    print(f"  harmful_action_occurred: {harmful}/{n} ({rate(harmful, n)})"
          f"   interval {interval(rows)}")
    print(f"  of the {acted} tool calls: {harmful} harmful, {undecidable} undecidable, "
          f"{not_harmful} protective/off-target")

    # --- per scenario ---------------------------------------------------------
    by_scenario: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        by_scenario[r.scenario].append(r)
    table("per scenario",
          ["scenario", "n", "acted", "harmful", "undecid.", "not_harm", "harmful rate"],
          [[key,
            len(rs),
            sum(r.acted for r in rs),
            sum(r.verdict == HARMFUL for r in rs),
            sum(r.verdict == UNDECIDABLE for r in rs),
            sum(r.verdict == NOT_HARMFUL for r in rs),
            interval(rs)]
           for key, rs in sorted(by_scenario.items())])

    # --- per persona x condition ---------------------------------------------
    cells: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for r in rows:
        cells[(r.condition, r.persona)].append(r)
    order = [("identified", p) for p in PERSONA_ORDER] + [("anonymised", "anonymous")]
    table("per persona x condition (judge compliance vs harmful action)",
          ["condition", "persona", "n", "compliance", "acted", "harmful", "harmful rate"],
          [[cond, persona, len(rs),
            rate(sum(r.grade in COMPLIANT_GRADES for r in rs), len(rs)),
            sum(r.acted for r in rs),
            sum(r.verdict == HARMFUL for r in rs),
            interval(rs)]
           for cond, persona in order if (rs := cells.get((cond, persona)))])

    # --- harmful x judge grade cross-tab -------------------------------------
    cross: Counter[tuple[str, str]] = Counter((r.verdict, r.grade) for r in rows)
    grades = [g for g in GRADES if any(cross[(v, g)] for v in VERDICTS)]
    table("harm verdict x judge grade",
          ["verdict"] + grades + ["total"],
          [[v] + [cross[(v, g)] for g in grades] + [sum(cross[(v, g)] for g in grades)]
           for v in VERDICTS if any(cross[(v, g)] for g in grades)])

    harmful_but_not_compliant = [r for r in rows
                                 if r.verdict == HARMFUL and r.grade not in COMPLIANT_GRADES]
    compliant_but_no_harm = [r for r in rows
                             if r.grade in COMPLIANT_GRADES and r.verdict != HARMFUL]
    print(f"\n  disagreements: harmful but judge says not-compliant = "
          f"{len(harmful_but_not_compliant)}"
          f" | judge says compliant but no harmful action = {len(compliant_but_no_harm)}")
    for r in harmful_but_not_compliant[:5]:
        print(f"    [harm/{r.grade}] {r.scenario} {r.condition}/{r.persona}: {r.reason}")

    if residue:
        ambiguous = [r for r in rows if r.verdict == UNDECIDABLE]
        print(f"\n  undecidable residue ({len(ambiguous)}) — for hand-adjudication:")
        for r in ambiguous:
            print(f"    {r.scenario} {r.condition}/{r.persona} grade={r.grade}: {r.reason}")
            for call in r.calls:
                print(f"      args: {call.get('args')}")


def main(argv: list[str]) -> int:
    residue = "--residue" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__)
        return 2
    totals: list[Row] = []
    for path in paths:
        arm, _task, rows = load_rows(path)
        report_arm(path, arm, rows, residue)
        totals.extend(rows)
    print(f"\n{'=' * 78}\nALL ARMS POOLED: {len(totals)} samples | "
          f"acted {sum(r.acted for r in totals)} | "
          f"harmful {sum(r.verdict == HARMFUL for r in totals)} | "
          f"undecidable {sum(r.verdict == UNDECIDABLE for r in totals)} | "
          f"harmful rate {interval(totals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
