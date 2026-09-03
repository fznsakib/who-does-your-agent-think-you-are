"""The frontier projection has to budget the paired scorer's second judge call
(AI-24). The projection gates real spend, so an understated request count is a
gate failure, not a cosmetic one. Loaded by path — scripts aren't a package.
"""
import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "ai5_projection", Path(__file__).resolve().parents[1] / "scripts" / "ai5_frontier_projection.py"
)
proj = importlib.util.module_from_spec(_SPEC)
sys.modules["ai5_projection"] = proj
_SPEC.loader.exec_module(proj)


def test_pushback_sample_budgets_two_judge_requests():
    # since AI-18 the scorer grades the first-turn answer as well as the final
    # one, so every pushback sample costs two judge calls
    assert proj.sample_profile("pushback")["judge_reqs"] == 2
    assert proj.sample_profile("base")["judge_reqs"] == 1


def test_pushback_sample_budgets_two_sets_of_judge_tokens():
    base = proj.sample_profile("base")
    push = proj.sample_profile("pushback")
    assert push["judge_in"] == 2 * base["judge_in"]
    assert push["judge_out"] == 2 * base["judge_out"]


def test_projected_openai_requests_include_the_second_judge_call():
    # an Anthropic model under test sends only its judge calls to OpenAI:
    # 600 base x1 + 360 pushback x2 = 1,320, not the pre-AI-18 960
    row = proj.project_model("anthropic/claude-opus-5")
    assert row["openai_reqs_fixed"] == proj.BASE_SAMPLES + 2 * proj.PUSHBACK_SAMPLES
    assert row["openai_reqs_fixed"] == 1320


def test_agent_request_count_is_untouched_by_the_judge_fix():
    assert proj.sample_profile("base")["agent_reqs"] == proj.AGENT_REQS_PER_SAMPLE
    assert proj.sample_profile("pushback")["agent_reqs"] == proj.PUSHBACK_AGENT_REQS_PER_SAMPLE
