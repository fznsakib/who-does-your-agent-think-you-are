from types import SimpleNamespace
from unittest.mock import patch

from principal_eval.labels import HandLabel, cohens_kappa, human_fusion_rate, raw_agreement, summarize


def _label(human, judge, fusion=False, family=None):
    return HandLabel(
        log_path="x.eval", sample_id=1, epoch=1, model="m", task="t",
        persona="ceo", condition="identified", scenario="killswitch", family=family,
        judge_grade=judge, human_grade=human, fusion_tag=fusion, note="",
    )


def test_raw_agreement_counts_matches():
    labels = [_label("COMPLIED", "COMPLIED"), _label("REFUSED", "COMPLIED"), _label("REFUSED", "REFUSED")]
    agg = raw_agreement(labels)
    assert agg == {"n": 3, "n_agree": 2, "rate": 2 / 3}


def test_cohens_kappa_is_one_on_perfect_agreement():
    labels = [_label(g, g) for g in ["COMPLIED", "PARTIAL", "REFUSED", "PUSHED_BACK", "ESCALATED"]]
    assert cohens_kappa(labels) == 1.0


def test_cohens_kappa_is_zero_on_chance_level_agreement():
    # human always says COMPLIED, judge always says REFUSED: no overlap, kappa <= 0
    labels = [_label("COMPLIED", "REFUSED") for _ in range(10)]
    assert cohens_kappa(labels) <= 0.0


def test_cohens_kappa_is_undefined_when_both_raters_are_homogeneous():
    # both raters said COMPLIED every time -- po == pe == 1, no variability
    # to measure agreement over. This is mathematically undefined (0/0), not
    # "perfect chance-adjusted agreement".
    labels = [_label("COMPLIED", "COMPLIED") for _ in range(5)]
    k = cohens_kappa(labels)
    assert k != k  # NaN


def test_cohens_kappa_below_one_when_raters_disagree_sometimes():
    labels = (
        [_label("COMPLIED", "COMPLIED")] * 7
        + [_label("REFUSED", "REFUSED")] * 1
        + [_label("COMPLIED", "REFUSED")] * 2
    )
    k = cohens_kappa(labels)
    assert 0.0 < k < 1.0


def test_human_fusion_rate_is_the_fraction_tagged():
    labels = [_label("COMPLIED", "COMPLIED", fusion=True),
              _label("COMPLIED", "COMPLIED", fusion=False),
              _label("COMPLIED", "COMPLIED", fusion=False),
              _label("COMPLIED", "COMPLIED", fusion=True)]
    assert human_fusion_rate(labels)["overall_rate"] == 0.5


def _fake_summary(id_, epoch, cues):
    score = SimpleNamespace(metadata={"cues_read": cues})
    return SimpleNamespace(id=id_, epoch=epoch, scores={"persona_scorer": score})


def test_human_fusion_rate_matches_ids_across_str_vs_int_types():
    # CSV round-trips sample_id as a string (read_labels does NOT cast it,
    # unlike epoch); read_eval_log_sample_summaries returns int ids for an
    # int-keyed dataset. The match must not silently fail on that alone.
    label = HandLabel(
        log_path="x.eval", sample_id="46", epoch=8, model="m", task="t",
        persona="ceo", condition="identified", scenario="killswitch", family="status_irrelevant",
        judge_grade="COMPLIED", human_grade="COMPLIED", fusion_tag=False, note="",
    )
    with patch("principal_eval.labels.read_eval_log_sample_summaries",
               return_value=[_fake_summary(46, 8, ["whoami", "read_email"])]):
        out = human_fusion_rate([label])
    assert out["n_whoami_callers"] == 1
    assert out["whoami_conditioned_rate"] == 0.0


def test_summarize_counts_role_gated():
    labels = [_label("COMPLIED", "COMPLIED", family="role_gated"),
              _label("COMPLIED", "COMPLIED", family="status_irrelevant")]
    s = summarize(labels)
    assert s["n_labelled"] == 2
    assert s["n_role_gated"] == 1
