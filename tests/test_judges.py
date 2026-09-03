"""Opposite-provider judge selection (AI-11)."""
import pytest

from principal_eval.judges import (
    ANTHROPIC_JUDGE, FALLBACK_JUDGE, JUDGE_BY_FAMILY, OPENAI_JUDGE,
    model_family, resolve_judge_model,
)

# The only models this harness is ever allowed to pick as a judge, per the
# project budget: frontier models are never a default.
CHEAP_JUDGES = {"anthropic/claude-haiku-4-5", "openai/gpt-4o-mini"}


def test_anthropic_under_test_is_judged_by_openai():
    assert resolve_judge_model("anthropic/claude-haiku-4-5") == "openai/gpt-4o-mini"


def test_openai_under_test_is_judged_by_anthropic():
    assert resolve_judge_model("openai/gpt-4o-mini") == "anthropic/claude-haiku-4-5"


def test_no_model_ever_judges_itself():
    for under_test in ("anthropic/claude-haiku-4-5", "openai/gpt-4o-mini",
                       "anthropic/claude-opus-4-1", "openai/gpt-4o"):
        judge = resolve_judge_model(under_test)
        assert judge != under_test
        assert model_family(judge) != model_family(under_test)


def test_ai5_haiku_runs_stay_comparable():
    # AI-5's completed haiku runs were graded by gpt-4o-mini. The
    # opposite-provider rule must reproduce exactly that, or those logs stop
    # being comparable with anything graded afterwards.
    assert resolve_judge_model("anthropic/claude-haiku-4-5") == "openai/gpt-4o-mini"
    assert JUDGE_BY_FAMILY["anthropic"] == "openai/gpt-4o-mini"


def test_explicit_override_always_wins():
    assert resolve_judge_model(
        "anthropic/claude-haiku-4-5", override="anthropic/claude-haiku-4-5"
    ) == "anthropic/claude-haiku-4-5"
    assert resolve_judge_model(
        "openai/gpt-4o-mini", override="openai/gpt-4o-mini"
    ) == "openai/gpt-4o-mini"
    assert resolve_judge_model("openai/gpt-4o", override="google/gemini") == "google/gemini"


def test_empty_override_is_treated_as_no_override():
    assert resolve_judge_model("openai/gpt-4o-mini", override=None) == ANTHROPIC_JUDGE
    assert resolve_judge_model("openai/gpt-4o-mini", override="") == ANTHROPIC_JUDGE


def test_defaults_are_cheap_models_only():
    assert set(JUDGE_BY_FAMILY.values()) | {FALLBACK_JUDGE} <= CHEAP_JUDGES
    assert {ANTHROPIC_JUDGE, OPENAI_JUDGE} == CHEAP_JUDGES


@pytest.mark.parametrize("model,family", [
    ("anthropic/claude-haiku-4-5", "anthropic"),
    ("openai/gpt-4o-mini", "openai"),
    ("bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0", "anthropic"),
    ("azureai/gpt-4o", "openai"),
    ("mockllm/model", None),
    ("google/gemini-2.0-flash", None),
])
def test_model_family_reads_provider_then_model_id(model, family):
    assert model_family(model) == family


def test_unrecognised_provider_keeps_the_historical_default():
    assert resolve_judge_model("mockllm/model") == FALLBACK_JUDGE == "openai/gpt-4o-mini"
    assert resolve_judge_model("google/gemini-2.0-flash") == "openai/gpt-4o-mini"
