"""Provider-aware judge selection.

The judge is drawn from the **opposite provider** to the model under test, for
two reasons found in the AI-5 dress rehearsal
(docs/pilots/2026-09-02-dress-rehearsal.md §5.1, §5.3):

1. *Self-grading.* With a hardcoded `openai/gpt-4o-mini` judge, the gpt-4o-mini
   run graded its own output — a self-preference risk, and asymmetric across the
   matrix (the haiku run was graded by a different model).
2. *Rate-limit contention.* A hardcoded OpenAI judge puts an OpenAI call behind
   every sample of every run, so the openai-under-test run spent its account
   budget on both agent and judge calls and starved the parallel run.

Under the opposite-provider rule an anthropic model under test still gets
`openai/gpt-4o-mini` as its judge, so the completed AI-5 haiku runs stay valid
and directly comparable to anything graded after this change.

Judges are deliberately the two cheap models — never a frontier model, whatever
is under test. Judging is one short classification call per sample; paying
frontier rates for it is not in the budget (see PLAN.md).
"""
from __future__ import annotations

__all__ = [
    "ANTHROPIC_JUDGE",
    "OPENAI_JUDGE",
    "FALLBACK_JUDGE",
    "JUDGE_BY_FAMILY",
    "model_family",
    "resolve_judge_model",
]

# The only two judge models this harness may pick on its own. Both cheap.
ANTHROPIC_JUDGE = "anthropic/claude-haiku-4-5"
OPENAI_JUDGE = "openai/gpt-4o-mini"

# family of the model UNDER TEST -> judge from the OPPOSITE provider
JUDGE_BY_FAMILY: dict[str, str] = {
    "anthropic": OPENAI_JUDGE,
    "openai": ANTHROPIC_JUDGE,
}

# Anything we can't place (mockllm, google, a local model) keeps the historical
# default so behaviour never silently changes for providers we haven't reasoned
# about.
FALLBACK_JUDGE = OPENAI_JUDGE

_FAMILY_BY_API: dict[str, str] = {"anthropic": "anthropic", "openai": "openai"}


def model_family(model: str) -> str | None:
    """Provider family of a `provider/model` string, or None if unrecognised.

    Prefers the Inspect provider prefix; falls back to the model id itself so
    gateway-prefixed names (`bedrock/anthropic.claude-...`, `azureai/gpt-4o`)
    still land in the right family.
    """
    api, _, rest = model.partition("/")
    family = _FAMILY_BY_API.get(api.lower())
    if family is not None:
        return family
    low = model.lower()
    if "claude" in low or "anthropic" in low:
        return "anthropic"
    if "gpt" in low or "openai" in low:
        return "openai"
    return None


def resolve_judge_model(model_under_test: str, override: str | None = None) -> str:
    """Pick the judge for a run.

    An explicit `override` always wins, so a caller can pin any judge for a
    one-off run. Otherwise the judge comes from the opposite provider to
    `model_under_test`, falling back to `FALLBACK_JUDGE` for unrecognised
    providers.
    """
    if override:
        return override
    family = model_family(str(model_under_test))
    return JUDGE_BY_FAMILY.get(family, FALLBACK_JUDGE) if family else FALLBACK_JUDGE
