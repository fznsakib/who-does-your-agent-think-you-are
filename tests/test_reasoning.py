"""Tests for the AI-32 R-series (docs/analysis-plan.md § J, 2026-09-03).

The tests that matter here are the ones that would catch a *silent* corruption
of the estimand: judge tokens folded into the subject's count, total output used
as the control instead of visible output, `role_gated` pooled back in, limit-hit
runaways averaged into a persona mean, or the verdict table drifting from the
one that was pre-registered. Each has its own test below.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from principal_eval.reasoning import (
    LADDER,
    attach_independent_checks,
    external_rows,
    independent_relative_gap_from_logs,
    REASONING_PER_SAMPLE,
    REASONING_PER_TURN,
    VISIBLE_PER_SAMPLE,
    ReasoningRow,
    contrast,
    independent_relative_gap,
    is_subject_usage,
    ladder_rows,
    load_reasoning_rows,
    monotonicity,
    per_scenario_gap,
    persona_table,
    reasoning_report,
    turns_covariate,
    verdict,
)


def _row(persona, scenario, reasoning, turns=2, visible=10, family="status_irrelevant",
         condition=None, model="m", excluded=None, arm="base", run_id="r1"):
    return ReasoningRow(
        model=model, arm=arm, run_id=run_id, persona=persona,
        condition=condition or ("anonymised" if persona == "anonymous" else "identified"),
        scenario=scenario, family=family, epoch=1, sample_id=1,
        reasoning=reasoning, visible=visible, turns=turns, excluded=excluded,
    )


# ---- R0: extraction -------------------------------------------------------

def test_is_subject_usage_matches_exact_and_bare_name():
    assert is_subject_usage("anthropic/claude-opus-5", "anthropic/claude-opus-5")
    assert is_subject_usage("claude-opus-5", "anthropic/claude-opus-5")
    assert is_subject_usage("openai/gpt-5.6-sol", "gpt-5.6-sol")


def test_is_subject_usage_rejects_the_judge():
    """The blind judge is a different provider answering a different question;
    folding its tokens in would add a constant with its own variance."""
    assert not is_subject_usage("openai/gpt-4o-mini", "anthropic/claude-opus-5")
    assert not is_subject_usage("anthropic/claude-haiku-4-5", "openai/gpt-5.6-sol")


def test_is_subject_usage_does_not_match_on_substring():
    """Substring matching would let `gpt-4o-mini` (the Anthropic-subject judge)
    match a `gpt-4o` subject and silently sum judge tokens into the subject."""
    assert not is_subject_usage("openai/gpt-4o-mini", "openai/gpt-4o")
    assert not is_subject_usage("openai/gpt-4o", "openai/gpt-4o-mini")


def _fake_sample(persona, scenario, *, reasoning, output, turns, family="status_irrelevant",
                 error=None, limit=None, judge_reasoning=0, judge_output=0,
                 condition="identified"):
    usage = {"anthropic/claude-opus-5": SimpleNamespace(
        reasoning_tokens=reasoning, output_tokens=output)}
    if judge_output or judge_reasoning:
        usage["openai/gpt-4o-mini"] = SimpleNamespace(
            reasoning_tokens=judge_reasoning, output_tokens=judge_output)
    return SimpleNamespace(
        id=1, epoch=1, error=error, limit=limit,
        metadata={"persona": persona, "scenario": scenario, "family": family,
                  "condition": condition},
        model_usage=usage,
        messages=[SimpleNamespace(role="assistant", text="x")] * turns,
    )


def _load(samples, status="success", task="principal_eval", run_id="run-1"):
    header = SimpleNamespace(
        eval=SimpleNamespace(model="anthropic/claude-opus-5", task=task, run_id=run_id),
        status=status)
    with patch("principal_eval.reasoning.read_eval_log", return_value=header), \
         patch("principal_eval.reasoning.read_eval_log_samples", return_value=iter(samples)):
        return load_reasoning_rows(["fake.eval"])


BASE = "anthropic/claude-opus-5 [base]"
PUSH = "anthropic/claude-opus-5 [pushback]"


def test_load_counts_only_subject_tokens_and_visible_is_output_minus_reasoning():
    load = _load([_fake_sample("ceo", "killswitch", reasoning=100, output=250, turns=3,
                               judge_reasoning=500, judge_output=900)])
    (row,) = load.rows
    assert row.reasoning == 100          # judge's 500 excluded
    assert row.visible == 150            # 250 total output MINUS the 100 reasoning
    assert row.turns == 3


def test_load_clamps_visible_at_zero_rather_than_going_negative():
    load = _load([_fake_sample("ceo", "k", reasoning=100, output=40, turns=1)])
    assert load.rows[0].visible == 0


def test_load_excludes_errored_and_limit_hit_but_keeps_them_for_disposition():
    """Plan rule 15: a submit-loop runaway capped at the task token limit would
    dominate a persona mean and look exactly like status-dependent deliberation."""
    load = _load([
        _fake_sample("ceo", "k", reasoning=10, output=20, turns=2),
        _fake_sample("ceo", "k", reasoning=999_999, output=999_999, turns=99,
                     limit=SimpleNamespace(type="token")),
        _fake_sample("ceo", "k", reasoning=0, output=0, turns=0, error="boom"),
    ], status="error")
    assert len(load.rows) == 3
    assert load.n_limit == 1 and load.n_error == 1
    assert [r.reasoning for r in load.analysable()] == [10]


def test_load_does_not_read_tokens_from_excluded_samples():
    load = _load([_fake_sample("ceo", "k", reasoning=999_999, output=999_999, turns=99,
                               limit=SimpleNamespace(type="token"))], status="error")
    assert load.rows[0].reasoning == 0


# ---- scope ----------------------------------------------------------------

def test_ladder_rows_drops_role_gated():
    """Rule 2: role_gated scenarios make authorisation differ by persona BY
    DESIGN, so pooling them lets legitimate role-gating masquerade as
    deliberation about status."""
    rows = [_row("ceo", "killswitch", 200),
            _row("ceo", "incident_response", 900, family="role_gated")]
    assert [r.reasoning for r in ladder_rows(rows)] == [200]


def test_ladder_rows_drops_external_which_is_not_a_rung():
    rows = [_row("ceo", "k", 1), _row("external", "k", 1)]
    assert {r.persona for r in ladder_rows(rows)} == {"ceo"}
    assert "external" not in LADDER


def test_ladder_rows_keeps_anonymous_on_its_own_condition():
    """`anonymous` rides the shared `anonymised` condition, so a blanket
    `condition == "identified"` filter would silently delete the ladder floor."""
    rows = [_row("anonymous", "k", 50), _row("analyst", "k", 40)]
    assert {r.persona for r in ladder_rows(rows)} == {"anonymous", "analyst"}


def test_ladder_rows_drops_a_persona_on_the_wrong_condition():
    assert ladder_rows([_row("ceo", "k", 1, condition="anonymised")]) == []


# ---- R1/R2/R3 -------------------------------------------------------------

def test_per_turn_is_sample_weighted_not_token_weighted():
    """R2: each sample contributes ONE ratio, so a long episode does not
    outweigh a short one. Token-weighting would give 110/11 = 10.0."""
    rows = [_row("ceo", "a", 100, turns=10), _row("ceo", "b", 10, turns=1)]
    assert REASONING_PER_TURN(rows) == pytest.approx((10.0 + 10.0) / 2)


def test_per_turn_skips_zero_turn_samples_without_dividing_by_zero():
    rows = [_row("ceo", "a", 100, turns=4), _row("ceo", "b", 0, turns=0)]
    assert REASONING_PER_TURN(rows) == pytest.approx(25.0)


def test_contrast_absolute_and_relative():
    rows = [_row("ceo", "a", 200), _row("analyst", "a", 100)]
    c = contrast(rows, "ceo", "analyst", REASONING_PER_SAMPLE)
    assert c["absolute"]["point"] == pytest.approx(100.0)
    assert c["relative"]["point"] == pytest.approx(1.0)
    assert c["n_high"] == 1 and c["n_low"] == 1


def test_contrast_interval_widens_when_the_effect_is_one_scenario_only():
    """Rule 1/10: an effect carried by a single cluster must not get the same
    interval as one present in every cluster. This is the whole point of
    resampling scenarios rather than samples."""
    scenarios = list("abcdefg")
    concentrated = [_row(p, s, 200 if (p == "ceo" and s == "a") else 100)
                    for s in scenarios for p in ("ceo", "analyst")]
    everywhere = [_row(p, s, 200 if p == "ceo" else 100)
                  for s in scenarios for p in ("ceo", "analyst")]
    c1 = contrast(concentrated, "ceo", "analyst", REASONING_PER_SAMPLE)["absolute"]
    c2 = contrast(everywhere, "ceo", "analyst", REASONING_PER_SAMPLE)["absolute"]
    assert (c1["hi"] - c1["lo"]) > (c2["hi"] - c2["lo"])
    assert c1["lo"] <= 0 <= c1["hi"]          # one cluster: not established
    assert c2["lo"] > 0                        # every cluster: excludes zero


def test_contrast_relative_is_nan_when_the_reference_is_zero():
    rows = [_row("ceo", "a", 200), _row("analyst", "a", 0)]
    rel = contrast(rows, "ceo", "analyst", REASONING_PER_SAMPLE)["relative"]["point"]
    assert rel != rel


def test_visible_control_is_not_total_output():
    """If the control were total output it would contain reasoning and rise
    with it automatically. `visible` must be blind to the reasoning column."""
    rows = [_row("ceo", "a", 500, visible=10), _row("analyst", "a", 0, visible=10)]
    assert VISIBLE_PER_SAMPLE(rows) == pytest.approx(10.0)
    assert contrast(rows, "ceo", "analyst", VISIBLE_PER_SAMPLE)["absolute"]["point"] == 0


# ---- R2 sensitivity -------------------------------------------------------

def test_turns_covariate_recovers_a_planted_persona_effect_net_of_turns():
    """reasoning = 10*turns + 50*[persona == ceo]: the fit must attribute the
    50 to the persona and the 10 to turns, not smear one into the other."""
    rows = []
    for s in "abcdefg":
        for t in (1, 2, 3, 4):
            rows.append(_row("analyst", s, 10 * t, turns=t))
            rows.append(_row("ceo", s, 10 * t + 50, turns=t))
    fit = turns_covariate(rows)
    assert fit["available"]
    assert fit["coefficients"]["ceo"]["point"] == pytest.approx(50.0, abs=1e-6)
    assert fit["coefficients"]["turns"]["point"] == pytest.approx(10.0, abs=1e-6)


def test_turns_covariate_attributes_a_pure_turn_effect_to_turns_not_persona():
    """The artefact case: reasoning is 10 per turn for BOTH personas, and ceo
    only looks like it reasons more because it takes more turns on average
    (4 vs 2). The persona coefficient must come back at ~0.

    Turns overlap between the personas on purpose. If each persona sat at a
    single distinct turn count, persona and turns would be perfectly collinear
    and no regression could separate them — the coefficient would be an
    artefact of how `lstsq` splits a degenerate design, not a finding. The real
    logs do have within-persona turn variation, which is what makes this
    sensitivity identifiable there."""
    rows = []
    for s in "abcdefg":
        for t in (1, 2, 3):
            rows.append(_row("analyst", s, 10 * t, turns=t))
        for t in (3, 4, 5):
            rows.append(_row("ceo", s, 10 * t, turns=t))
    fit = turns_covariate(rows)
    assert fit["coefficients"]["ceo"]["point"] == pytest.approx(0.0, abs=1e-6)
    assert fit["coefficients"]["turns"]["point"] == pytest.approx(10.0, abs=1e-6)


def test_turns_covariate_unavailable_without_the_reference_persona():
    fit = turns_covariate([_row("ceo", "a", 1)])
    assert fit["available"] is False


# ---- R4 -------------------------------------------------------------------

def _table(**per_persona):
    return {p: {"reasoning_per_sample": {"point": v}} for p, v in per_persona.items()}


def test_monotonicity_true_when_the_ladder_rises():
    m = monotonicity(_table(anonymous=1, analyst=2, chief_of_staff=3,
                            researcher=4, ceo=5))
    assert m["monotonic"] and m["breaks"] == []


def test_monotonicity_names_the_offending_rung():
    m = monotonicity(_table(anonymous=1, analyst=2, chief_of_staff=9,
                            researcher=4, ceo=10))
    assert not m["monotonic"]
    assert [(b["from"], b["to"]) for b in m["breaks"]] == [("chief_of_staff", "researcher")]


def test_monotonicity_reports_the_ladder_in_rung_order_not_value_order():
    m = monotonicity(_table(ceo=10, analyst=2, anonymous=1))
    assert [p for p, _ in m["ladder"]] == ["anonymous", "analyst", "ceo"]


# ---- R6: the pre-registered verdict table ---------------------------------

def _c(point, lo, hi, rel=None):
    rel = rel or (point, lo, hi)
    return {"absolute": {"point": point, "lo": lo, "hi": hi},
            "relative": {"point": rel[0], "lo": rel[1], "hi": rel[2]}}


def test_verdict_survivor_when_both_gaps_exclude_zero():
    v = verdict(_c(100, 60, 150, rel=(1.0, 0.6, 1.4)),
                _c(29, 18, 43, rel=(0.85, 0.54, 1.25)),
                _c(257, 147, 363, rel=(0.20, 0.11, 0.29)))
    assert v["verdict"] == "survivor"
    assert not v["verbosity_override"]


def test_verdict_artefact_when_the_per_turn_gap_includes_zero():
    v = verdict(_c(100, 60, 150, rel=(1.0, 0.6, 1.4)),
                _c(2, -5, 9, rel=(0.02, -0.05, 0.09)),
                _c(5, -1, 11, rel=(0.05, -0.01, 0.11)))
    assert v["verdict"] == "artefact of episode length"


def test_verdict_not_established_when_the_headline_gap_includes_zero():
    v = verdict(_c(100, -20, 220, rel=(1.0, -0.2, 2.2)),
                _c(29, 18, 43, rel=(0.85, 0.54, 1.25)),
                _c(5, -1, 11, rel=(0.05, -0.01, 0.11)))
    assert v["verdict"] == "not established"


def test_verdict_not_established_outranks_a_significant_per_turn_gap():
    """The rows are ordered: an inconclusive headline is not rescued by its
    own control."""
    v = verdict(_c(1, -100, 100, rel=(0.01, -1.0, 1.0)),
                _c(50, 40, 60, rel=(0.5, 0.4, 0.6)),
                _c(1, -1, 3, rel=(0.01, -0.01, 0.03)))
    assert v["verdict"] == "not established"


def test_verbosity_override_fires_when_visible_output_rises_in_step():
    v = verdict(_c(100, 60, 150, rel=(1.0, 0.6, 1.4)),
                _c(29, 18, 43, rel=(0.85, 0.54, 1.25)),
                _c(90, 55, 140, rel=(0.95, 0.55, 1.35)))
    assert v["verdict"] == "verbosity, not deliberation"
    assert v["verbosity_override"]


def test_no_verbosity_override_when_visible_rises_far_less():
    """The AI-9 shape: reasoning +98.6% against visible +19.5% — the intervals
    do not overlap, so the model is not merely writing more."""
    v = verdict(_c(104, 61, 153, rel=(0.986, 0.611, 1.394)),
                _c(29, 18, 43, rel=(0.845, 0.538, 1.245)),
                _c(257, 147, 363, rel=(0.195, 0.106, 0.289)))
    assert v["verdict"] == "survivor"


def test_verdict_survivor_requires_the_same_sign_on_both_gaps():
    """A per-turn interval that excludes zero in the OPPOSITE direction is not
    an artefact verdict: that label carries the reason "the per-turn gap does
    not exclude zero", which the interval flatly contradicts. It is a state the
    pre-registered table does not cover, and it is reported as one."""
    v = verdict(_c(100, 60, 150, rel=(1.0, 0.6, 1.4)),
                _c(-30, -50, -10, rel=(-0.3, -0.5, -0.1)),
                _c(5, -1, 11, rel=(0.05, -0.01, 0.11)))
    assert v["verdict"] == "per-turn sign reversal — inconclusive"


def test_verdict_handles_a_nan_interval_as_not_established():
    nan = float("nan")
    v = verdict(_c(nan, nan, nan), _c(29, 18, 43), _c(5, -1, 11))
    assert v["verdict"] == "not established"


# ---- R8 + diagnostic ------------------------------------------------------

def test_independent_relative_gap_matches_the_pipeline_path():
    rows = [_row("ceo", "a", 209), _row("ceo", "b", 210),
            _row("analyst", "a", 105), _row("analyst", "b", 106)]
    ind = independent_relative_gap(rows)
    pipeline = contrast(rows, "ceo", "analyst", REASONING_PER_SAMPLE)["relative"]["point"]
    assert ind["relative"] == pytest.approx(pipeline)
    assert ind["sum_high"] == 419 and ind["n_high"] == 2


def test_independent_relative_gap_unavailable_when_a_side_is_missing():
    assert independent_relative_gap([_row("ceo", "a", 1)])["available"] is False


def test_per_scenario_gap_reports_every_scenario_and_leave_one_out():
    rows = [r for s in "abc" for r in
            (_row("ceo", s, 200 if s != "c" else 400), _row("analyst", s, 100))]
    d = per_scenario_gap(rows)
    assert set(d["per_scenario"]) == {"a", "b", "c"}
    assert d["per_scenario"]["c"]["relative"] == pytest.approx(3.0)
    # dropping the outlier scenario must move the pooled relative gap down
    assert d["leave_one_out_relative"]["c"] == pytest.approx(1.0)


# ---- top level ------------------------------------------------------------

def test_report_marks_a_non_reasoning_model_not_measurable():
    """Reporting rule: never imputed, never differenced against a model that
    does expose reasoning tokens."""
    load = _load([_fake_sample("ceo", "k", reasoning=0, output=300, turns=2),
                  _fake_sample("analyst", "k", reasoning=0, output=300, turns=2)])
    block = reasoning_report(load)["models"][BASE]
    assert block["measurable"] is False
    assert "R1_status_gap" not in block
    assert "not measurable" in block["note"]


def test_report_computes_the_full_r_series_for_a_reasoning_model():
    samples = [_fake_sample(p, s, reasoning=200 if p == "ceo" else 100,
                            output=400, turns=2)
               for s in "abcdefg" for p in ("ceo", "analyst")]
    block = reasoning_report(_load(samples))["models"][BASE]
    assert block["measurable"]
    assert block["n_scenarios"] == 7
    assert block["R1_status_gap"]["relative"]["point"] == pytest.approx(1.0)
    assert block["R6_verdict"]["verdict"] in {
        "survivor", "artefact of episode length", "not established",
        "verbosity, not deliberation"}
    assert block["R8_rows"]["relative"] == pytest.approx(
        block["R1_status_gap"]["relative"]["point"])


def test_report_disposition_carries_the_exclusion_counts():
    load = _load([_fake_sample("ceo", "k", reasoning=1, output=2, turns=1, error="x")],
                 status="error")
    assert reasoning_report(load)["disposition"] == {
        "excluded_error": 1, "excluded_limit": 0}


# ---- codex review follow-ups ----------------------------------------------

def test_arm_is_taken_from_the_task_name():
    assert _load([_fake_sample("ceo", "k", reasoning=1, output=2, turns=1)],
                 task="principal_eval").rows[0].arm == "base"
    assert _load([_fake_sample("ceo", "k", reasoning=1, output=2, turns=1)],
                 task="principal_eval_pushback").rows[0].arm == "pushback"


def test_base_and_pushback_are_never_pooled_into_one_block():
    """Plan rule 5: the arms are distinct estimand sets. A directory holding
    both must produce two labelled blocks, not one averaged mean — the pushback
    arm adds a second interaction, so its turns and reasoning move together."""
    base = [_fake_sample(p, s, reasoning=100, output=200, turns=2)
            for s in "abcdefg" for p in ("ceo", "analyst")]
    push = [_fake_sample(p, s, reasoning=900, output=1800, turns=6)
            for s in "abcdefg" for p in ("ceo", "analyst")]
    header_base = SimpleNamespace(
        eval=SimpleNamespace(model="anthropic/claude-opus-5", task="principal_eval",
                             run_id="run-base"), status="success")
    header_push = SimpleNamespace(
        eval=SimpleNamespace(model="anthropic/claude-opus-5", run_id="run-push",
                             task="principal_eval_pushback"), status="success")
    with patch("principal_eval.reasoning.read_eval_log",
               side_effect=[header_base, header_push]), \
         patch("principal_eval.reasoning.read_eval_log_samples",
               side_effect=[iter(base), iter(push)]):
        load = load_reasoning_rows(["base.eval", "push.eval"])
    report = reasoning_report(load)
    assert set(report["models"]) == {BASE, PUSH}
    assert report["models"][BASE]["n_in_scope"] == 14
    assert report["models"][PUSH]["n_in_scope"] == 14
    # and the pushback block says loudly that it is not the headline
    assert "BASE arms" in report["models"][PUSH]["warning"]
    assert "warning" not in report["models"][BASE]


def test_a_model_whose_every_sample_is_excluded_is_still_reported():
    """It must not vanish from a multi-model arm: a silently missing model
    reads as 'not run', which is a different fact from 'every sample died'."""
    load = _load([_fake_sample("ceo", "k", reasoning=1, output=2, turns=1, error="x")],
                 status="error")
    block = reasoning_report(load)["models"][BASE]
    assert block["n_analysable_all_families"] == 0
    assert block["n_excluded"] == 1
    assert block["excluded_by_reason"] == {"error": 1, "limit": 0}
    assert "every sample" in block["note"]


def test_external_is_reported_beside_the_ladder_not_on_it():
    """E4: external varies affiliation as well as status, so it is excluded
    from R1/R4 — but R4 also requires it REPORTED, not deleted."""
    samples = [_fake_sample(p, s, reasoning=100, output=200, turns=2)
               for s in "abcdefg" for p in ("ceo", "analyst", "external")]
    block = reasoning_report(_load(samples))["models"][BASE]
    assert "external" not in block["persona_table"]
    assert block["external_cell"]["n"] == 7
    assert [p for p, _ in block["R4_monotonicity_per_sample"]["ladder"]] == [
        "analyst", "ceo"]


def test_external_cell_is_none_when_the_persona_is_absent():
    samples = [_fake_sample(p, s, reasoning=100, output=200, turns=2)
               for s in "abcdefg" for p in ("ceo", "analyst")]
    assert reasoning_report(_load(samples))["models"][BASE]["external_cell"] is None


def test_external_rows_scope():
    rows = [_row("external", "k", 1),
            _row("external", "k", 1, family="role_gated"),
            _row("ceo", "k", 1)]
    assert len(external_rows(rows)) == 1


def test_cell_carries_the_per_turn_denominator_separately():
    """R0: zero-turn samples are counted separately. Printing the full `n`
    beside a per-turn mean would overstate its denominator."""
    samples = [_fake_sample("ceo", s, reasoning=100, output=200, turns=2)
               for s in "abcdef"]
    samples.append(_fake_sample("ceo", "g", reasoning=0, output=0, turns=0))
    block = reasoning_report(_load(samples))["models"][BASE]
    cell = block["persona_table"]["ceo"]
    assert cell["n"] == 7
    assert cell["n_zero_turn"] == 1
    assert cell["n_per_turn"] == 6


def test_verbosity_override_also_outranks_the_artefact_row():
    """The amendment says the override applies "whatever R2 does". A per-turn
    gap that includes zero must not shield an artefact verdict from it."""
    v = verdict(_c(100, 60, 150, rel=(1.0, 0.6, 1.4)),
                _c(2, -5, 9, rel=(0.02, -0.05, 0.09)),
                _c(90, 55, 140, rel=(0.95, 0.55, 1.35)))
    assert v["verdict"] == "verbosity, not deliberation"
    assert v["verbosity_override"]


def test_verbosity_override_does_not_rescue_a_not_established_verdict():
    """The override text overrides "both rows" — the two where R1 is
    established. There is no effect left to reattribute in the third."""
    v = verdict(_c(1, -100, 100, rel=(0.01, -1.0, 1.0)),
                _c(2, -5, 9, rel=(0.02, -0.05, 0.09)),
                _c(1, -1, 3, rel=(0.01, -0.01, 0.03)))
    assert v["verdict"] == "not established"


def test_independent_path_from_logs_matches_the_pipeline():
    samples = [_fake_sample(p, s, reasoning=200 if p == "ceo" else 100,
                            output=400, turns=2)
               for s in "abcdefg" for p in ("ceo", "analyst")]
    header = SimpleNamespace(
        eval=SimpleNamespace(model="anthropic/claude-opus-5", task="principal_eval",
                             run_id="run-1"), status="success")
    with patch("principal_eval.reasoning.read_eval_log", return_value=header), \
         patch("principal_eval.reasoning.read_eval_log_samples",
               return_value=iter(samples)):
        ind = independent_relative_gap_from_logs(
            ["fake.eval"], "anthropic/claude-opus-5", "base")
    assert ind["relative"] == pytest.approx(1.0)
    assert ind["n_high"] == 7 and ind["n_low"] == 7


def test_independent_path_applies_the_scope_rules_itself():
    """It re-derives the exclusions and the family/condition scope rather than
    inheriting them — otherwise a scoping bug would move both numbers together
    and still reconcile to zero."""
    samples = [
        _fake_sample("ceo", "a", reasoning=200, output=400, turns=2),
        _fake_sample("analyst", "a", reasoning=100, output=200, turns=2),
        # each of these must be dropped by the independent path on its own
        _fake_sample("ceo", "b", reasoning=9_000, output=9_000, turns=2,
                     family="role_gated"),
        _fake_sample("ceo", "c", reasoning=9_000, output=9_000, turns=2,
                     condition="anonymised"),
        _fake_sample("ceo", "d", reasoning=9_000, output=9_000, turns=2, error="x"),
        _fake_sample("ceo", "e", reasoning=9_000, output=9_000, turns=2,
                     limit=SimpleNamespace(type="token")),
    ]
    header = SimpleNamespace(
        eval=SimpleNamespace(model="anthropic/claude-opus-5", task="principal_eval",
                             run_id="run-1"), status="error")
    with patch("principal_eval.reasoning.read_eval_log", return_value=header), \
         patch("principal_eval.reasoning.read_eval_log_samples",
               return_value=iter(samples)):
        ind = independent_relative_gap_from_logs(
            ["fake.eval"], "anthropic/claude-opus-5", "base")
    assert ind["n_high"] == 1 and ind["sum_high"] == 200
    assert ind["relative"] == pytest.approx(1.0)


def test_independent_path_ignores_other_models_and_other_arms():
    samples = [_fake_sample(p, s, reasoning=100, output=200, turns=2)
               for s in "abcdefg" for p in ("ceo", "analyst")]
    header = SimpleNamespace(
        eval=SimpleNamespace(model="anthropic/claude-opus-5", task="principal_eval",
                             run_id="run-1"), status="success")
    with patch("principal_eval.reasoning.read_eval_log", return_value=header), \
         patch("principal_eval.reasoning.read_eval_log_samples",
               return_value=iter(samples)):
        wrong_model = independent_relative_gap_from_logs(
            ["fake.eval"], "openai/gpt-5.6-sol", "base")
    with patch("principal_eval.reasoning.read_eval_log", return_value=header), \
         patch("principal_eval.reasoning.read_eval_log_samples",
               return_value=iter(samples)):
        wrong_arm = independent_relative_gap_from_logs(
            ["fake.eval"], "anthropic/claude-opus-5", "pushback")
    assert wrong_model["available"] is False
    assert wrong_arm["available"] is False


def test_attach_independent_checks_flags_a_discrepancy_rather_than_hiding_it():
    """The whole value of R8 is that it FAILS loudly when the two paths
    disagree. A check that can only ever agree is decoration."""
    samples = [_fake_sample(p, s, reasoning=200 if p == "ceo" else 100,
                            output=400, turns=2)
               for s in "abcdefg" for p in ("ceo", "analyst")]
    report = reasoning_report(_load(samples))
    header = SimpleNamespace(
        eval=SimpleNamespace(model="anthropic/claude-opus-5", task="principal_eval",
                             run_id="run-1"), status="success")

    # honest run: the second path sees the same samples and reconciles
    with patch("principal_eval.reasoning.read_eval_log", return_value=header), \
         patch("principal_eval.reasoning.read_eval_log_samples",
               return_value=iter(samples)):
        attach_independent_checks(report, ["fake.eval"])
    assert report["models"][BASE]["R8_reconciles"] is True

    # corrupted run: the second path sees different tokens and must not agree
    tampered = [_fake_sample(p, s, reasoning=200 if p == "ceo" else 150,
                             output=400, turns=2)
                for s in "abcdefg" for p in ("ceo", "analyst")]
    with patch("principal_eval.reasoning.read_eval_log", return_value=header), \
         patch("principal_eval.reasoning.read_eval_log_samples",
               return_value=iter(tampered)):
        attach_independent_checks(report, ["fake.eval"])
    assert report["models"][BASE]["R8_reconciles"] is False


def test_attach_independent_checks_skips_unmeasurable_blocks():
    load = _load([_fake_sample("ceo", "k", reasoning=0, output=300, turns=2)])
    report = attach_independent_checks(reasoning_report(load), [])
    assert "R8_independent" not in report["models"][BASE]


# ---- codex review, round 2 -------------------------------------------------

def test_separate_runs_of_the_same_model_and_arm_are_refused():
    """`logs/ai9-frontier/` really does hold a 1-epoch smoke run beside the
    20-epoch production run. Same model, same arm, different run — pooling
    them would present the smoke run as part of the arm."""
    prod = [_fake_sample(p, s, reasoning=200, output=400, turns=2)
            for s in "abcdefg" for p in ("ceo", "analyst")]
    smoke = [_fake_sample(p, "a", reasoning=9_000, output=9_000, turns=9)
             for p in ("ceo", "analyst")]
    h_prod = SimpleNamespace(eval=SimpleNamespace(
        model="anthropic/claude-opus-5", task="principal_eval", run_id="prod"),
        status="success")
    h_smoke = SimpleNamespace(eval=SimpleNamespace(
        model="anthropic/claude-opus-5", task="principal_eval", run_id="smoke"),
        status="success")
    with patch("principal_eval.reasoning.read_eval_log",
               side_effect=[h_prod, h_smoke]), \
         patch("principal_eval.reasoning.read_eval_log_samples",
               side_effect=[iter(prod), iter(smoke)]):
        load = load_reasoning_rows(["prod.eval", "smoke.eval"])
    with pytest.raises(ValueError, match="refusing to pool separate runs"):
        reasoning_report(load)
    # ...but pooling stays possible when it is asked for explicitly
    report = reasoning_report(load, allow_mixed_runs=True)
    assert sorted(report["models"][BASE]["run_ids"]) == ["prod", "smoke"]


def test_one_run_per_key_is_not_refused():
    samples = [_fake_sample(p, s, reasoning=100, output=200, turns=2)
               for s in "abcdefg" for p in ("ceo", "analyst")]
    report = reasoning_report(_load(samples))
    assert report["models"][BASE]["run_ids"] == ["run-1"]


def test_exclusion_reasons_are_tracked_per_model_block():
    """A global count cannot distinguish a provider failing outright from
    episodes hitting the runaway cap."""
    load = _load([
        _fake_sample("ceo", "a", reasoning=1, output=2, turns=1, error="x"),
        _fake_sample("ceo", "b", reasoning=1, output=2, turns=1,
                     limit=SimpleNamespace(type="token")),
        _fake_sample("ceo", "c", reasoning=1, output=2, turns=1,
                     limit=SimpleNamespace(type="token")),
    ], status="error")
    block = reasoning_report(load)["models"][BASE]
    assert block["excluded_by_reason"] == {"error": 1, "limit": 2}


def test_incomplete_ladder_is_not_declared_monotonic():
    """A subset of the ladder cannot answer a question about the ladder."""
    m = monotonicity(_table(analyst=2, ceo=5))
    assert m["monotonic"] is None
    assert m["complete"] is False
    assert set(m["missing_rungs"]) == {"anonymous", "chief_of_staff", "researcher"}


def test_non_finite_rung_is_not_silently_monotonic():
    """NaN comparisons are always False, so a non-finite cell would register no
    break and read as monotonic."""
    m = monotonicity(_table(anonymous=1, analyst=2, chief_of_staff=float("nan"),
                            researcher=4, ceo=5))
    assert m["monotonic"] is None
    assert m["non_finite_rungs"] == ["chief_of_staff"]


def test_complete_ladder_still_reports_a_boolean():
    m = monotonicity(_table(anonymous=1, analyst=2, chief_of_staff=3,
                            researcher=4, ceo=5))
    assert m["monotonic"] is True and m["complete"] is True


def test_missing_per_turn_interval_is_not_read_as_an_artefact():
    """An ABSENT control is not a failed one: publishing 'the extra reasoning
    is turns, not depth' off a NaN would be a claim the data never made."""
    nan = float("nan")
    v = verdict(_c(100, 60, 150, rel=(1.0, 0.6, 1.4)),
                _c(nan, nan, nan, rel=(nan, nan, nan)),
                _c(5, -1, 11, rel=(0.05, -0.01, 0.11)))
    assert v["verdict"] == "control unavailable"
    assert "unanswered" in v["reason"]


def test_verbosity_override_still_applies_without_a_usable_control():
    """R1 and R3 alone establish the reattribution, so it does not need R2 --
    which is what "whatever R2 does" means."""
    nan = float("nan")
    v = verdict(_c(100, 60, 150, rel=(1.0, 0.6, 1.4)),
                _c(nan, nan, nan, rel=(nan, nan, nan)),
                _c(90, 55, 140, rel=(0.95, 0.55, 1.35)))
    assert v["verdict"] == "verbosity, not deliberation"


def test_turns_covariate_refuses_a_rank_deficient_design():
    """Turns determined by persona: the effects are not separately
    identifiable and lstsq's minimum-norm split is a property of the solver."""
    rows = []
    for s in "abcdefg":
        rows.append(_row("analyst", s, 20, turns=2))
        rows.append(_row("ceo", s, 40, turns=4))
    fit = turns_covariate(rows)
    assert fit["available"] is False
    assert "rank-deficient" in fit["reason"]


def test_turns_covariate_still_available_when_identified():
    rows = []
    for s in "abcdefg":
        for t in (1, 2, 3):
            rows.append(_row("analyst", s, 10 * t, turns=t))
        for t in (3, 4, 5):
            rows.append(_row("ceo", s, 10 * t + 50, turns=t))
    fit = turns_covariate(rows)
    assert fit["available"]
    assert fit["coefficients"]["ceo"]["point"] == pytest.approx(50.0, abs=1e-6)


# ---- codex review, round 3 -------------------------------------------------

def test_per_turn_contrast_reports_the_denominator_it_actually_used():
    """A per-turn estimate computed from 6 rows must not advertise n=7."""
    rows = [_row("ceo", s, 100, turns=2) for s in "abcdef"]
    rows.append(_row("ceo", "g", 0, turns=0))
    rows += [_row("analyst", s, 50, turns=2) for s in "abcdefg"]
    per_turn = contrast(rows, "ceo", "analyst", REASONING_PER_TURN)
    per_sample = contrast(rows, "ceo", "analyst", REASONING_PER_SAMPLE)
    assert per_turn["n_high"] == 6 and per_turn["n_high_all"] == 7
    assert per_sample["n_high"] == 7 and per_sample["n_high_all"] == 7


def test_a_log_with_no_samples_still_produces_a_block():
    """An eval that died before writing its first sample has a header and no
    rows. Dropping it reads as 'not run', which is a different fact."""
    load = _load([], status="error")
    report = reasoning_report(load)
    assert BASE in report["models"]
    assert "NO samples at all" in report["models"][BASE]["note"]


def test_epoch_count_is_reported_per_block():
    """The amendment's Reporting rule attributes every R-number to its epoch
    count; it cannot be inferred from n_in_scope once cells are unbalanced."""
    samples = []
    for epoch in (1, 2, 3):
        for scenario in "abcdefg":
            for persona in ("ceo", "analyst"):
                smp = _fake_sample(persona, scenario, reasoning=100, output=200, turns=2)
                smp.epoch = epoch
                samples.append(smp)
    block = reasoning_report(_load(samples))["models"][BASE]
    assert block["n_epochs"] == 3


def test_zero_visible_gap_does_not_count_as_the_same_sign():
    """`(a > 0) == (b > 0)` calls a negative gap and a ZERO gap the same sign,
    which would fire the verbosity override on no visible effect at all."""
    v = verdict(_c(-100, -150, -60, rel=(-1.0, -1.4, -0.6)),
                _c(-29, -43, -18, rel=(-0.85, -1.25, -0.54)),
                _c(0, -140, 140, rel=(0.0, -1.4, 1.4)))
    assert not v["verbosity_override"]
    assert v["verdict"] == "survivor"


def test_sign_helper_is_three_valued():
    from principal_eval.reasoning import _sign
    assert (_sign(-2.0), _sign(0.0), _sign(3.0)) == (-1, 0, 1)
    assert _sign(float("nan")) == 0
