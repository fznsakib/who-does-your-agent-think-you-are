from principal_eval.ai6_sampling import Candidate, stratified_sample


def _cand(key_id, family="status_irrelevant", grade="REFUSED", cues=(), harmful=None,
          persona="ceo", condition="identified", scenario="exfiltration", model="m"):
    return Candidate(
        log_path="x.eval", sample_id=key_id, epoch=1, model=model, task="t",
        persona=persona, condition=condition, scenario=scenario, family=family,
        grade=grade, judge_model="j", cues_read=cues, harmful_action_occurred=harmful,
    )


def test_strata_detects_role_gated_whoami_and_partial():
    role_gated = _cand(1, family="role_gated")
    whoami = _cand(2, cues=("whoami",))
    partial = _cand(3, grade="PARTIAL")
    plain = _cand(4)
    assert role_gated.strata() == {"role_gated"}
    assert whoami.strata() == {"whoami_caller"}
    assert partial.strata() == {"partial_grade"}
    assert plain.strata() == set()


def test_strata_detects_harmful_disagreement_only_when_field_present():
    no_field = _cand(1, grade="COMPLIED", harmful=None)
    agrees = _cand(2, grade="COMPLIED", harmful=True)
    disagrees = _cand(3, grade="COMPLIED", harmful=False)
    assert "harmful_disagreement" not in no_field.strata()
    assert "harmful_disagreement" not in agrees.strata()
    assert "harmful_disagreement" in disagrees.strata()


def test_stratified_sample_oversamples_partial_and_role_gated():
    candidates = (
        [_cand(f"p{i}", grade="PARTIAL") for i in range(5)]
        + [_cand(f"g{i}", family="role_gated") for i in range(5)]
        + [_cand(f"n{i}", scenario=f"scn{i}") for i in range(50)]
    )
    sample = stratified_sample(candidates, n=20, seed=1)
    assert len(sample) == 20
    partial_n = sum(1 for c in sample if c.grade == "PARTIAL")
    gated_n = sum(1 for c in sample if c.family == "role_gated")
    # with only 5 available in each pool, the quota should pull in most/all of them
    assert partial_n >= 3
    assert gated_n >= 3


def test_stratified_sample_is_deterministic_for_a_fixed_seed():
    candidates = [_cand(i, scenario=f"scn{i % 10}") for i in range(100)]
    a = stratified_sample(candidates, n=30, seed=42)
    b = stratified_sample(candidates, n=30, seed=42)
    assert {c.key for c in a} == {c.key for c in b}


def test_stratified_sample_never_returns_more_than_available():
    candidates = [_cand(i) for i in range(5)]
    sample = stratified_sample(candidates, n=30, seed=1)
    assert len(sample) == 5


def test_stratified_sample_has_no_duplicates():
    candidates = (
        [_cand(f"p{i}", grade="PARTIAL", family="role_gated") for i in range(10)]
        + [_cand(f"n{i}") for i in range(40)]
    )
    sample = stratified_sample(candidates, n=25, seed=3)
    keys = [c.key for c in sample]
    assert len(keys) == len(set(keys))
