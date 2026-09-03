"""AI-33: does the OpenAI tier-shrinkage claim survive a PROPER cross-model test?

Every earlier tier table (AI-9, AI-31, and this PR's first draft) compared each model's
own E1-vs-zero interval and read "the intervals overlap" as "the ladder is flat" or "the
shrinkage disappeared". That is not a test of whether two models differ from each other —
overlapping marginal intervals do not establish non-difference (Codex review, PR #26).

This script runs the actual test: a scenario-clustered bootstrap on the PAIRWISE
DIFFERENCE `E1(model_a) - E1(model_b)`, paired on the same resampled scenario multiset per
draw (same method rule 10 uses for a single model's E1-vs-zero, applied to a difference of
two models' E1 instead of one model's E1 minus zero).

Reuses `scripts/ai31_tier_table.py`'s `load()` (backfills harm for the pre-AI-20
`gpt-5-nano`/`haiku-4-5` logs, applies the AI-23 `exfiltration`/`external_disclosure`
exclusion on harm) rather than re-implementing it, so this script and the tier table never
disagree about what a cell value is.

CROSS-FORK CAVEAT: `gpt-5-nano` and `haiku-4-5` sit on the OLD side of the AI-16 harness
fork (pre-anonymisation-fixture system prompt) — rule 18 makes arms on opposite sides of
that fork non-comparable for a capability-tier contrast. Their rows below are printed for
completeness but are NOT a same-harness comparison; only `luna`/`terra`/`sol`/`sonnet-5`/
`opus-5` (all post-AI-16, mutually clean) support the "does the shrinkage survive" claim.

Usage:
    uv run python scripts/ai33_cross_model_bootstrap.py [--logs <root>]
"""
from __future__ import annotations

import argparse
import random
import sys
from statistics import mean

sys.path.insert(0, "scripts")
import ai31_tier_table as T  # noqa: E402

BOOT, SEED = 10_000, 0

OPENAI_PAIRS = [
    ("gpt-5.6-luna [AI-33]", "gpt-5.6-terra"),
    ("gpt-5.6-terra", "gpt-5.6-sol"),
    ("gpt-5.6-luna [AI-33]", "gpt-5.6-sol"),
    ("gpt-5-nano", "gpt-5.6-luna [AI-33]"),   # cross-fork caveat applies
]
ANTHROPIC_PAIRS = [
    ("claude-sonnet-5", "claude-opus-5"),
    ("claude-haiku-4-5", "claude-sonnet-5"),  # cross-fork caveat applies
]
CLEAN_LABELS = {"gpt-5.6-luna [AI-33]", "gpt-5.6-terra", "gpt-5.6-sol",
                "claude-sonnet-5", "claude-opus-5"}


def e1_diff(d_a, d_b, scens):
    """E1(a) - E1(b) = [C(ceo,a) - C(analyst,a)] - [C(ceo,b) - C(analyst,b)],
    resampling the shared scenario set with replacement each draw."""
    def pm(d, p, ss):
        v = [x for s in ss for x in d[p][s]]
        return mean(v) if v else 0.0

    def e1(d, ss):
        return pm(d, "ceo", ss) - pm(d, "analyst", ss)

    rng = random.Random(SEED)
    obs = e1(d_a, scens) - e1(d_b, scens)
    draws = []
    for _ in range(BOOT):
        drawn = [scens[rng.randrange(len(scens))] for _ in scens]
        draws.append(e1(d_a, drawn) - e1(d_b, drawn))
    draws.sort()
    return obs, draws[int(0.025 * BOOT)], draws[int(0.975 * BOOT)]


def flag(lo: float, hi: float) -> str:
    return "EXCLUDES 0" if (lo > 0 or hi < 0) else "includes 0"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=T.LOGS_DEFAULT)
    args = ap.parse_args()
    T.LOGS = args.logs
    arms = {a[0]: a[:4] + (a[4].replace(T.LOGS_DEFAULT, args.logs),) + a[5:] for a in T.ARMS}

    cache = {}

    def get(label):
        if label not in cache:
            _, _, _, _, d, _ = arms[label]
            comp, harm, *_ = T.load(d)
            cache[label] = (comp, harm)
        return cache[label]

    print("AI-33 cross-model bootstrap — scenario-clustered pairwise E1 difference, "
          f"{BOOT:,} draws, seed {SEED}\n")
    print("DESCRIPTIVE (rule 13's confirmatory set is E1/E2/E3/E5 per model, never a "
          "cross-model contrast). This tests whether the visible point-estimate decline "
          "across the tier table is distinguishable from scenario-resampling noise.\n")

    for title, pairs in (("OpenAI", OPENAI_PAIRS), ("Anthropic", ANTHROPIC_PAIRS)):
        print(f"--- {title} ---")
        for a, b in pairs:
            comp_a, harm_a = get(a)
            comp_b, harm_b = get(b)
            note = "" if (a in CLEAN_LABELS and b in CLEAN_LABELS) else \
                "  [CROSS-FORK: AI-16 pre/post -- not a same-harness comparison, rule 18]"
            for outcome_name, d_a, d_b, exclude_harm in (
                ("compliance", comp_a, comp_b, False),
                ("harm", harm_a, harm_b, True),
            ):
                cs_a = {s for v in d_a.values() for s in v}
                cs_b = {s for v in d_b.values() for s in v}
                scens = sorted(cs_a & cs_b)
                obs, lo, hi = e1_diff(d_a, d_b, scens)
                print(f"  {a:22s} - {b:22s}  {outcome_name:10s} "
                      f"diff={obs:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  "
                      f"{flag(lo, hi)}{note}")
        print()


if __name__ == "__main__":
    main()
