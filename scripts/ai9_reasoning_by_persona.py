"""EXPLORATORY (AI-9): does the model deliberate longer for higher-status users?

NOT part of the pre-registered readout in docs/analysis-plan.md section G. Any
number this prints is exploratory and must be labelled as such in the write-up.

The motivation is that Claude 4.7+ (including Opus 5) is always in *adaptive*
thinking: the model chooses its own reasoning depth per sample. `reasoning_effort`
sets a ceiling/target, not the realised spend. So if a model spends more reasoning
tokens once it believes it is talking to the CEO than to the analyst, that is a
mechanism signal sitting in logs we already paid for -- and it is measured without
the judge, so it cannot inherit the judge's ~0.57 kappa.

Two things this deliberately reports side by side:
  * reasoning tokens per sample by persona (the exploratory signal), and
  * total output tokens by persona (the control: if BOTH move together the model
    is simply writing more, not thinking harder).

Usage:
    uv run python scripts/ai9_reasoning_by_persona.py <log.eval> [<log.eval> ...]
"""
from __future__ import annotations

import statistics
import sys
from collections import defaultdict

from inspect_ai.log import read_eval_log, read_eval_log_samples


def collect(path: str) -> tuple[str, dict[tuple[str, str], list[tuple[int, int]]]]:
    header = read_eval_log(path, header_only=True)
    model = str(header.eval.model)
    cells: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for sample in read_eval_log_samples(path, all_samples_required=False):
        if sample.error is not None:
            continue
        meta = sample.metadata or {}
        persona = meta.get("persona")
        condition = meta.get("condition")
        reasoning = output = 0
        for name, usage in (sample.model_usage or {}).items():
            # count only the model under test, never the judge: the judge is a
            # different provider and a different question.
            if name.split("/")[-1] not in model.split("/")[-1]:
                continue
            reasoning += getattr(usage, "reasoning_tokens", None) or 0
            output += usage.output_tokens or 0
        cells[(persona, condition)].append((reasoning, output))
    return model, cells


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        raise SystemExit(__doc__)

    for path in paths:
        model, cells = collect(path)
        print(f"\n=== {model}  ({path}) ===")
        print("EXPLORATORY - not in the pre-registered section G readout\n")
        print(f"{'persona':16s} {'condition':12s} {'n':>4s} "
              f"{'reasoning/sample':>17s} {'output/sample':>14s} {'reason share':>13s}")
        rows = []
        for (persona, condition), vals in sorted(cells.items()):
            n = len(vals)
            r = statistics.mean(v[0] for v in vals)
            o = statistics.mean(v[1] for v in vals)
            share = (r / o) if o else 0.0
            rows.append((persona, r))
            print(f"{str(persona):16s} {str(condition):12s} {n:4d} "
                  f"{r:17.0f} {o:14.0f} {share:12.1%}")

        by_persona = {p: r for p, r in rows}
        if "ceo" in by_persona and "analyst" in by_persona:
            d = by_persona["ceo"] - by_persona["analyst"]
            base = by_persona["analyst"] or 1
            print(f"\n  ceo - analyst reasoning delta: {d:+.0f} tokens/sample "
                  f"({d / base:+.1%} vs analyst)")
        if "chief_of_staff" in by_persona and "analyst" in by_persona:
            d = by_persona["chief_of_staff"] - by_persona["analyst"]
            base = by_persona["analyst"] or 1
            print(f"  chief_of_staff - analyst (proximity): {d:+.0f} tokens/sample "
                  f"({d / base:+.1%} vs analyst)")
        print("\n  Cell means only - no CI. Treat as a lead to test properly, "
              "not a result. A difference here is uninterpretable unless the "
              "output-token column stays flat.")


if __name__ == "__main__":
    main()
