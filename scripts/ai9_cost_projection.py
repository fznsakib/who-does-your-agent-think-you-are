"""AI-9: cost + request projection for the frontier BASE run (no pushback arm).

Differs from `ai5_frontier_projection.py`, which is pinned to the AI-5 shape
(base + pushback, 10 epochs, an *assumed* x2.5 frontier output multiplier).
AI-9 is base-only at 20 epochs, and we now have a measured reasoning-model
token rate to scale from instead of an assumption.

Usage:
    uv run python scripts/ai9_cost_projection.py [--epochs 20] [--no-external]
"""
from __future__ import annotations

import argparse

# ---- measured, not assumed ---------------------------------------------------
# Per-sample BASE token rate measured on openai/gpt-5-nano (AI-15 base arm, 600
# samples). gpt-5-nano is a reasoning model, so it is a far better proxy for
# gpt-5 / opus-5 than haiku-4.5 was: the AI-5 projection used haiku's 7,402 in /
# 727 out plus a x2.5 output guess, and the measured reasoning rate is ~8x that
# output figure. This is the single number the whole budget rests on.
AGENT_IN_PER_SAMPLE = 6_457
AGENT_OUT_PER_SAMPLE = 5_723

# Judge is one short classification call per sample (AI-5 measurement). Judge
# cost is <1% of the total; it is carried for completeness, not precision.
JUDGE_IN_PER_SAMPLE = 479
JUDGE_OUT_PER_SAMPLE = 34

# Requests per sample: react cycle model calls + one judge call. Measured at 3
# agent calls/sample on the cheap base arms. Reasoning models are not obviously
# chattier in TOOL calls (they think more per call, not across more calls), so 3
# is carried forward, with retry headroom applied on top.
AGENT_REQS_PER_SAMPLE = 3
JUDGE_REQS_PER_SAMPLE = 1
RETRY_HEADROOM = 1.25

# ---- matrix ------------------------------------------------------------------
CELLS = 60           # 10 scenarios x (5 personas + 1 anonymised baseline)
CELLS_NO_EXTERNAL = 50   # dropping the `external` condition (pinned at 0.000, zero variance)

# ---- pricing $/1M tokens (subject, then judge) --------------------------------
PRICING = {
    "anthropic/claude-opus-5": (5.00, 25.00),
    "openai/gpt-5": (1.25, 10.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "anthropic/claude-haiku-4-5": (1.00, 5.00),
}
# opposite-provider rule (src/principal_eval/judges.py)
JUDGE_FOR = {
    "anthropic/claude-opus-5": "openai/gpt-4o-mini",
    "openai/gpt-5": "anthropic/claude-haiku-4-5",
}

USD_PER_GBP = 1.0 / 0.79  # stated assumption, matches the AI-5 readout


def project(model: str, cells: int, epochs: int) -> dict:
    n = cells * epochs
    a_in_p, a_out_p = PRICING[model]
    judge = JUDGE_FOR[model]
    j_in_p, j_out_p = PRICING[judge]

    agent_in = AGENT_IN_PER_SAMPLE * n
    agent_out = AGENT_OUT_PER_SAMPLE * n
    judge_in = JUDGE_IN_PER_SAMPLE * n
    judge_out = JUDGE_OUT_PER_SAMPLE * n

    agent_cost = agent_in * a_in_p / 1e6 + agent_out * a_out_p / 1e6
    judge_cost = judge_in * j_in_p / 1e6 + judge_out * j_out_p / 1e6

    return {
        "model": model,
        "judge": judge,
        "samples": n,
        "agent_in": agent_in,
        "agent_out": agent_out,
        "total_tokens": agent_in + agent_out + judge_in + judge_out,
        "agent_cost": agent_cost,
        "judge_cost": judge_cost,
        "total_cost": agent_cost + judge_cost,
        # request load lands on DIFFERENT providers for agent vs judge
        "subject_reqs": int(n * AGENT_REQS_PER_SAMPLE * RETRY_HEADROOM),
        "judge_reqs": int(n * JUDGE_REQS_PER_SAMPLE * RETRY_HEADROOM),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--no-external", action="store_true",
                    help="drop the `external` condition (10 fewer cells)")
    args = ap.parse_args()

    cells = CELLS_NO_EXTERNAL if args.no_external else CELLS
    rows = [project(m, cells, args.epochs) for m in JUDGE_FOR]

    print(f"AI-9 frontier BASE run - {cells} cells x {args.epochs} epochs "
          f"= {cells * args.epochs} samples/model, no pushback arm\n")
    print(f"{'model':26s} {'judge':28s} {'Mtok':>6s} {'agent$':>9s} {'judge$':>8s} {'total$':>9s}")
    for r in rows:
        print(f"{r['model']:26s} {r['judge']:28s} {r['total_tokens']/1e6:6.1f} "
              f"{r['agent_cost']:9.2f} {r['judge_cost']:8.2f} {r['total_cost']:9.2f}")

    usd = sum(r["total_cost"] for r in rows)
    print(f"\nTOTAL: ${usd:.2f}  =  GBP {usd * 0.79:.2f}")

    print("\nRequest load by PROVIDER (incl. %d%% retry headroom):"
          % int((RETRY_HEADROOM - 1) * 100))
    by_provider: dict[str, int] = {}
    for r in rows:
        by_provider[r["model"].split("/")[0]] = (
            by_provider.get(r["model"].split("/")[0], 0) + r["subject_reqs"])
        by_provider[r["judge"].split("/")[0]] = (
            by_provider.get(r["judge"].split("/")[0], 0) + r["judge_reqs"])
    for prov, reqs in sorted(by_provider.items()):
        print(f"  {prov:12s} {reqs:7d} requests")
    for r in rows:
        print(f"    {r['model']:26s} subject {r['subject_reqs']:6d} | "
              f"judge {r['judge']:28s} {r['judge_reqs']:6d}")

    print("\nToken rate is MEASURED from gpt-5-nano (AI-15 base, 600 samples): "
          f"{AGENT_IN_PER_SAMPLE:,} in / {AGENT_OUT_PER_SAMPLE:,} out per sample. "
          "Re-run this against the AI-9 smoke measurement before committing spend.")


if __name__ == "__main__":
    main()
