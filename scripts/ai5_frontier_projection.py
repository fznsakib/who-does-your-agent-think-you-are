"""AI-5: project token spend, wall-clock and $ for the frontier pilot.

Scales the measured cheap-model per-sample rates up to frontier pricing, and
computes wall-clock two ways, because the AI-5 pilot showed wall-clock is set by
rate-limit tuning, not by tokens:

  (a) current judge design  - judge_model is hardcoded to openai/gpt-4o-mini for
      every model under test, so ALL judge calls plus (for a GPT model under
      test) all agent calls land on one OpenAI account's 500 RPM budget.
  (b) AI-11 fixed           - judge runs on the opposite provider to the model
      under test, so agent and judge load sit on two separate rate-limit pools.

Usage:
    uv run python scripts/ai5_frontier_projection.py
"""
from __future__ import annotations

# ---- measured from the AI-5 pilot (haiku base, 600 samples) -----------------
# tokens per BASE sample (one react cycle + one judge call)
AGENT_IN_PER_SAMPLE = 7402
AGENT_OUT_PER_SAMPLE = 727
JUDGE_IN_PER_SAMPLE = 479
JUDGE_OUT_PER_SAMPLE = 34
# requests per sample: 3 agent model calls + 1 judge call (measured over 40 samples)
AGENT_REQS_PER_SAMPLE = 3
JUDGE_REQS_PER_SAMPLE = 1

# The pushback arm runs TWO react cycles. MEASURED from the AI-5 haiku pushback run
# (180 samples): 11,768 in / 1,213 out per sample vs the base 7,402 / 727, i.e. x1.59
# input and x1.67 output - less than the naive x2.0, because the second cycle re-reads
# a transcript it has already paid for and answers more briefly.
PUSHBACK_AGENT_MULTIPLIER = 1.63
# Agent REQUESTS per pushback sample, MEASURED from the haiku pushback transcripts
# (mean 4.59 assistant turns over 80 samples) rather than inferred from the token
# multiplier. The naive 3 x 1.63 = 4.89 overstates it slightly; an earlier draft of
# the readout claimed 6.5, which was wrong in the other direction.
PUSHBACK_AGENT_REQS_PER_SAMPLE = 4.59

# The scorer grades both ends of a pushback sample, so two judge calls per sample.
PUSHBACK_JUDGE_REQS_PER_SAMPLE = 2
PUSHBACK_JUDGE_TOKEN_MULTIPLIER = 2.0

# ---- pilot volume (the originally specified epochs=10 matrix) ---------------
BASE_SAMPLES = 60 * 10        # 60-cell matrix x 10 epochs
PUSHBACK_SAMPLES = 36 * 10    # 36-cell pushback matrix x 10 epochs

# ---- pricing $/1M tokens ----------------------------------------------------
PRICING = {
    # cheap models actually used in this pilot
    "anthropic/claude-haiku-4-5": (1.00, 5.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    # frontier tier for the projection
    "anthropic/claude-opus-5": (5.00, 25.00),
    "openai/gpt-5": (1.25, 10.00),
}
JUDGE_MODEL = "openai/gpt-4o-mini"

# Frontier models reason more per turn. We do NOT have frontier data yet, so this
# is an explicit, stated assumption rather than a measurement.
FRONTIER_OUTPUT_MULTIPLIER = 2.5   # more output tokens (reasoning + longer answers)
FRONTIER_INPUT_MULTIPLIER = 1.2    # slightly longer transcripts feed back in

OPENAI_RPM = 500        # observed account limit that produced the 429 storms
ANTHROPIC_RPM = 4000    # assumption: Anthropic tier limit is not the binding constraint


def sample_profile(kind: str) -> dict:
    # Tokens and REQUESTS scale differently. Token cost scales with how much text the
    # two react cycles produce; request count scales with how many tool-call iterations
    # they take. Using the token multiplier for both understates the request totals
    # that the requests-per-day budget depends on, so they are measured separately.
    pushback = kind == "pushback"
    tok_mult = PUSHBACK_AGENT_MULTIPLIER if pushback else 1.0
    reqs = PUSHBACK_AGENT_REQS_PER_SAMPLE if pushback else AGENT_REQS_PER_SAMPLE
    # the paired scorer's second judge call is a request AND a second set of
    # judge tokens: the prompt template is the same and only the response text
    # differs, so x2 on both is the right first-order estimate
    judge_tok_mult = PUSHBACK_JUDGE_TOKEN_MULTIPLIER if pushback else 1.0
    judge_reqs = PUSHBACK_JUDGE_REQS_PER_SAMPLE if pushback else JUDGE_REQS_PER_SAMPLE
    return {
        "agent_in": AGENT_IN_PER_SAMPLE * tok_mult,
        "agent_out": AGENT_OUT_PER_SAMPLE * tok_mult,
        "judge_in": JUDGE_IN_PER_SAMPLE * judge_tok_mult,
        "judge_out": JUDGE_OUT_PER_SAMPLE * judge_tok_mult,
        "agent_reqs": reqs,
        "judge_reqs": judge_reqs,
    }


def project_model(model: str) -> dict:
    a_in_price, a_out_price = PRICING[model]
    j_in_price, j_out_price = PRICING[JUDGE_MODEL]

    tot = {k: 0.0 for k in
           ("agent_in", "agent_out", "judge_in", "judge_out", "agent_reqs", "judge_reqs")}
    for kind, n in (("base", BASE_SAMPLES), ("pushback", PUSHBACK_SAMPLES)):
        p = sample_profile(kind)
        for k in tot:
            tot[k] += p[k] * n

    # frontier models emit more tokens than the haiku baseline we measured
    agent_in = tot["agent_in"] * FRONTIER_INPUT_MULTIPLIER
    agent_out = tot["agent_out"] * FRONTIER_OUTPUT_MULTIPLIER

    agent_cost = agent_in * a_in_price / 1e6 + agent_out * a_out_price / 1e6
    judge_cost = tot["judge_in"] * j_in_price / 1e6 + tot["judge_out"] * j_out_price / 1e6

    is_openai_agent = model.startswith("openai/")
    # (a) current design: judge always on OpenAI; agent too if the model is OpenAI
    openai_reqs_a = tot["judge_reqs"] + (tot["agent_reqs"] if is_openai_agent else 0)
    # (b) judge on the opposite provider, so the judge never shares a pool with
    #     the agent. The binding pool is whichever carries the agent.
    openai_reqs_b = tot["agent_reqs"] if is_openai_agent else tot["judge_reqs"]

    return {
        "model": model,
        "samples": BASE_SAMPLES + PUSHBACK_SAMPLES,
        "agent_in": agent_in,
        "agent_out": agent_out,
        "judge_in": tot["judge_in"],
        "judge_out": tot["judge_out"],
        "total_tokens": agent_in + agent_out + tot["judge_in"] + tot["judge_out"],
        "agent_cost": agent_cost,
        "judge_cost": judge_cost,
        "total_cost": agent_cost + judge_cost,
        "openai_reqs_current": openai_reqs_a,
        "openai_reqs_fixed": openai_reqs_b,
        # floor = requests / RPM. This is the *theoretical* floor at perfect
        # pacing; the pilot showed real runs land far above it when the client
        # overshoots the cap and pays exponential backoff.
        "rpm_floor_min_current": openai_reqs_a / OPENAI_RPM,
        "rpm_floor_min_fixed": openai_reqs_b / OPENAI_RPM,
    }


def main() -> None:
    rows = [project_model(m) for m in ("anthropic/claude-opus-5", "openai/gpt-5")]
    gbp = 0.79  # USD->GBP, stated assumption

    print(f"Volume per model: {rows[0]['samples']} samples "
          f"({BASE_SAMPLES} base + {PUSHBACK_SAMPLES} pushback)\n")
    print(f"{'model':28s} {'Mtok':>7s} {'agent$':>9s} {'judge$':>8s} {'total$':>9s}")
    for r in rows:
        print(f"{r['model']:28s} {r['total_tokens']/1e6:7.2f} "
              f"{r['agent_cost']:9.2f} {r['judge_cost']:8.2f} {r['total_cost']:9.2f}")
    tot_usd = sum(r["total_cost"] for r in rows)
    print(f"\nTOTAL both frontier models: ${tot_usd:.2f}  (~£{tot_usd*gbp:.2f} at {gbp} USD/GBP)")

    print("\nOpenAI request load (the wall-clock constraint):")
    for r in rows:
        print(f"  {r['model']:28s} current judge: {r['openai_reqs_current']:8.0f} reqs "
              f"-> {r['rpm_floor_min_current']:6.1f} min floor @ {OPENAI_RPM} RPM")
        print(f"  {'':28s} AI-11 fixed  : {r['openai_reqs_fixed']:8.0f} reqs "
              f"-> {r['rpm_floor_min_fixed']:6.1f} min floor @ {OPENAI_RPM} RPM")

    print("\nAssumptions: frontier output tokens x%.1f and input x%.1f vs measured haiku "
          "rates; pushback agent cost x%.1f (two react cycles); pushback judge cost and "
          "requests x%.1f (AI-18 grades both ends of the transcript); judge stays "
          "gpt-4o-mini in the cost model; USD->GBP %.2f."
          % (FRONTIER_OUTPUT_MULTIPLIER, FRONTIER_INPUT_MULTIPLIER,
             PUSHBACK_AGENT_MULTIPLIER, PUSHBACK_JUDGE_TOKEN_MULTIPLIER, gbp))


if __name__ == "__main__":
    main()
