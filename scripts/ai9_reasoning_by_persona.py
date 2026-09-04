"""EXPLORATORY (AI-9): does the model deliberate longer for higher-status users?

SUPERSEDED by `scripts/ai32_reasoning_readout.py`. This script prints cell means
with no interval and no episode-length control -- "a lead to test properly, not a
result", as its own last line says. AI-32 pre-registered the estimand, the
scenario-clustered interval, the turn-count control and the artefact/survivor
decision rule (docs/analysis-plan.md section J) and then ran them. Use that script
for any number that will be published; this one is kept because it produced the
AI-9 section 7a lead and re-running it reproduces that readout as it stood.

NOT part of the pre-registered readout in docs/analysis-plan.md section G. Any
number this prints is exploratory and must be labelled as such in the write-up.

The motivation is that Claude 4.7+ (including Opus 5) is always in *adaptive*
thinking: the model chooses its own reasoning depth per sample. `reasoning_effort`
sets a target, not the realised spend. So if a model spends more reasoning tokens
once it believes it is talking to the CEO than to the analyst, that is a mechanism
signal sitting in logs we already paid for -- and it is measured without the judge,
so it cannot inherit the judge's ~0.57 kappa against a human.

Three things this gets right that a naive version does not:

  * **The control must be VISIBLE output, not total output.** `ModelUsage.output_tokens`
    INCLUDES reasoning tokens, so comparing reasoning against total output compares a
    quantity against itself plus noise. If visible text stayed flat while reasoning
    grew, both columns would rise and the probe would wrongly read "just writing more".
    The control here is `output_tokens - reasoning_tokens`.
  * **`status_irrelevant` only, by default.** The three `role_gated` scenarios make
    authorisation differ by persona BY DESIGN (ceo authorised in two, researcher in
    one, analyst in none), so a pooled token delta can be driven entirely by legitimate
    role-gating rather than by deliberation about status. Pass --all-families to pool
    anyway; it prints a warning.
  * **Limit-hit samples are excluded.** One submit loop capped near the 150k task limit
    would dominate a persona mean and look exactly like status-dependent deliberation.
    AI-17 added those limits precisely because such runaways happened before.

Usage:
    uv run python scripts/ai9_reasoning_by_persona.py <log.eval|log-dir> [...] [--all-families]
"""
from __future__ import annotations

import glob
import os
import statistics
import sys
from collections import defaultdict

from inspect_ai.log import read_eval_log, read_eval_log_samples

PERSONA_ORDER = ["ceo", "chief_of_staff", "researcher", "anonymous", "analyst", "external"]


def collect(path: str, all_families: bool) -> tuple[str, dict, int, int]:
    header = read_eval_log(path, header_only=True)
    model = str(header.eval.model)
    cells: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    skipped_limit = skipped_family = 0

    for sample in read_eval_log_samples(path, all_samples_required=False):
        if sample.error is not None:
            continue
        if sample.limit is not None:
            skipped_limit += 1
            continue
        meta = sample.metadata or {}
        if not all_families and meta.get("family") != "status_irrelevant":
            skipped_family += 1
            continue

        reasoning = output = 0
        for name, usage in (sample.model_usage or {}).items():
            # the model under test only -- never the judge, which is a different
            # provider answering a different question
            if name.split("/")[-1] not in model.split("/")[-1]:
                continue
            reasoning += getattr(usage, "reasoning_tokens", None) or 0
            output += usage.output_tokens or 0
        # visible = what the user would actually read; output_tokens includes reasoning
        visible = max(0, output - reasoning)
        cells[(meta.get("persona"), meta.get("condition"))].append((reasoning, visible))

    return model, cells, skipped_limit, skipped_family


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    all_families = "--all-families" in sys.argv
    if not args:
        raise SystemExit(__doc__)

    paths: list[str] = []
    for a in args:
        paths.extend(sorted(glob.glob(f"{a}/**/*.eval", recursive=True))
                     if os.path.isdir(a) else [a])

    for path in paths:
        model, cells, skipped_limit, skipped_family = collect(path, all_families)
        print(f"\n=== {model} ===")
        print("EXPLORATORY — not in the pre-registered section G readout")
        if all_families:
            print("!! --all-families: role_gated pooled in. Authorisation differs by "
                  "persona there BY DESIGN, so any delta below may be role-gating, "
                  "not deliberation.")
        else:
            print(f"status_irrelevant only ({skipped_family} role_gated samples excluded)")
        print(f"limit-hit samples excluded: {skipped_limit}\n")

        print(f"{'persona':16s} {'condition':12s} {'n':>4s} "
              f"{'reasoning/sample':>17s} {'VISIBLE out/sample':>19s} {'ratio':>7s}")
        by_persona: dict[str, float] = {}
        vis_by_persona: dict[str, float] = {}
        for (persona, condition), vals in sorted(cells.items(), key=lambda kv: str(kv[0])):
            n = len(vals)
            r = statistics.mean(v[0] for v in vals)
            v = statistics.mean(v[1] for v in vals)
            by_persona[persona] = r
            vis_by_persona[persona] = v
            print(f"{str(persona):16s} {str(condition):12s} {n:4d} "
                  f"{r:17.0f} {v:19.0f} {(r / v if v else 0):7.2f}")

        for label, a, b in (("ceo - analyst (deference)", "ceo", "analyst"),
                            ("chief_of_staff - analyst (proximity)", "chief_of_staff", "analyst")):
            if a in by_persona and b in by_persona:
                dr = by_persona[a] - by_persona[b]
                dv = vis_by_persona[a] - vis_by_persona[b]
                base = by_persona[b] or 1
                print(f"\n  {label}")
                print(f"    reasoning delta   {dr:+.0f} tokens/sample ({dr / base:+.1%})")
                print(f"    VISIBLE out delta {dv:+.0f} tokens/sample "
                      f"<- if this moves with reasoning, the model is writing more, "
                      f"not thinking harder")

        print("\n  Cell means only, no interval. A lead to test properly, not a result.")


if __name__ == "__main__":
    main()
