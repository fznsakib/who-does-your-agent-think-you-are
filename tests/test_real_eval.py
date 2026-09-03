import asyncio

from inspect_ai.model import ChatMessageAssistant, ChatMessageSystem, ChatMessageUser

from principal_eval.real_eval import (
    MESSAGE_LIMIT, PUSHBACK_SCENARIO_KEYS, TOKEN_LIMIT, build_dataset,
    build_pushback_dataset, principal_eval, principal_eval_pushback,
    pushback_turn,
)
from principal_eval.scenarios import SCENARIOS_BY_KEY


def test_matrix_is_60_cells():
    samples = list(build_dataset().samples)
    assert len(samples) == 60  # 10 scenarios * (5 identified + 1 anon)


def test_identified_has_five_personas_per_scenario():
    samples = list(build_dataset().samples)
    ident = [s for s in samples if s.metadata["condition"] == "identified"]
    anon = [s for s in samples if s.metadata["condition"] == "anonymised"]
    assert len(ident) == 50
    assert len(anon) == 10
    # each anon cell uses the shared placeholder persona
    assert {s.metadata["persona"] for s in anon} == {"anonymous"}


def test_every_sample_carries_required_metadata():
    for s in build_dataset().samples:
        assert set(s.metadata) >= {"persona", "condition", "scenario", "family"}
        assert s.metadata["family"] in ("status_irrelevant", "role_gated")
        assert (
            s.metadata["family"]
            == SCENARIOS_BY_KEY[s.metadata["scenario"]].family
        )


def test_pushback_dataset_is_the_six_unambiguous_scenarios_by_six_conditions():
    expected_keys = {
        "exfiltration", "safety_bypass", "records_tampering",
        "access_escalation", "external_disclosure", "killswitch",
    }
    assert set(PUSHBACK_SCENARIO_KEYS) == expected_keys
    samples = list(build_pushback_dataset().samples)
    assert len(samples) == 36  # 6 scenarios * (5 identified + 1 anon)
    assert {s.metadata["scenario"] for s in samples} == expected_keys
    # role-gated and ambiguous scenarios are excluded
    for s in samples:
        assert s.metadata["family"] == "status_irrelevant"
        assert s.metadata["scenario"] != "surveillance"


def test_both_tasks_bound_runaway_samples_with_message_and_token_limits():
    # AI-17: submit-loop samples ran unbounded (up to 1.07M tokens) in the
    # AI-15 base run because no limit was set anywhere. Both tasks must
    # carry an explicit ceiling so a limit-hit sample yields a gradeable
    # `limit`-tagged outcome instead of running indefinitely.
    for task in (principal_eval(), principal_eval_pushback()):
        assert task.message_limit == MESSAGE_LIMIT
        assert task.token_limit == TOKEN_LIMIT


def test_pushback_task_builds_with_the_36_sample_dataset():
    task = principal_eval_pushback()
    samples = list(task.dataset.samples)
    assert len(samples) == 36
    for s in samples:
        assert set(s.metadata) >= {"persona", "condition", "scenario"}


def test_pushback_task_uses_two_solvers_setup_then_pushback_turn():
    task = principal_eval_pushback()
    # setup_episode() + pushback_turn(): base task's own solver/dataset/
    # metadata contract is untouched (a separate @task/@solver pair).
    assert len(task.solver) == 2


def test_pushback_turn_appends_scenario_pushback_and_avoids_duplicate_system_msgs():
    from inspect_ai.agent import AgentState

    # Fake a minimal react-like agent (matches react()'s documented
    # behavior: it unconditionally inserts its own ChatMessageSystem at
    # index 0 of whatever messages it's handed, then appends one assistant
    # reply) to isolate pushback_turn's message-composition logic without
    # hitting a real model.
    calls: list[list] = []

    async def fake_agent(agent_state: AgentState) -> AgentState:
        messages = list(agent_state.messages)
        calls.append(list(messages))  # snapshot before mutating
        messages.insert(0, ChatMessageSystem(content="react system prompt"))
        messages.append(ChatMessageAssistant(content=f"reply #{len(calls)}"))
        agent_state.messages = messages
        return agent_state

    solver = pushback_turn(agent=fake_agent)

    class FakeState:
        def __init__(self):
            self.messages = [ChatMessageSystem(content="persona system prompt")]
            self.output = None
            self.metadata = {"scenario": "exfiltration"}

    state = FakeState()
    result = asyncio.run(solver(state, generate=None))

    # exactly two agent invocations: first cycle + pushback cycle
    assert len(calls) == 2

    # first call was handed the untouched persona system message (no
    # react system message yet -- that only gets inserted by the agent)
    assert [m.content for m in calls[0]] == ["persona system prompt"]
    assert all(isinstance(m, ChatMessageSystem) for m in calls[0])

    # second call was NOT handed a duplicated react system message: the
    # one inserted by the first call was stripped before the pushback
    # user message was appended
    second_call_messages = calls[1]
    system_msgs = [m for m in second_call_messages if isinstance(m, ChatMessageSystem)]
    assert len(system_msgs) == 1
    assert system_msgs[0].content == "persona system prompt"

    # the pushback line was appended as a user message, after the first
    # cycle's assistant reply, before the second agent call
    assert isinstance(second_call_messages[-1], ChatMessageUser)
    assert second_call_messages[-1].content == SCENARIOS_BY_KEY["exfiltration"].pushback

    # final result reflects the SECOND (post-pushback) cycle's messages:
    # exactly one persona system message + one react system message (the
    # single copy re-inserted by the second call) -- not duplicated.
    final_system_msgs = [m for m in result.messages if isinstance(m, ChatMessageSystem)]
    assert [m.content for m in final_system_msgs] == ["react system prompt", "persona system prompt"]
    assert isinstance(result.messages[-1], ChatMessageAssistant)
    assert result.messages[-1].content == "reply #2"


def test_pushback_lines_exist_for_every_scenario():
    for key, scenario in SCENARIOS_BY_KEY.items():
        assert scenario.pushback and isinstance(scenario.pushback, str)


# --- judge selection is visible in the log (AI-11) --------------------------

def test_tasks_record_the_judge_policy_in_task_metadata():
    # task.metadata is merged into the log header's EvalSpec metadata, so a
    # reader of any log can see which rule picked the judge named in each
    # sample's score metadata.
    from principal_eval.real_eval import JUDGE_POLICY, principal_eval

    for build in (principal_eval, principal_eval_pushback):
        metadata = build().metadata
        assert metadata["judge_policy"] == JUDGE_POLICY
        assert metadata["judge_model_override"] is None


def test_judge_model_override_is_recorded_and_still_accepted_positionally():
    # backwards compatible: `-T judge_model=...` and positional callers both
    # still work, and the pinned judge is visible in the log header.
    from principal_eval.real_eval import principal_eval

    task = principal_eval("openai/gpt-4o-mini")
    assert task.metadata["judge_model_override"] == "openai/gpt-4o-mini"
    task = principal_eval_pushback(judge_model="anthropic/claude-haiku-4-5")
    assert task.metadata["judge_model_override"] == "anthropic/claude-haiku-4-5"


def test_judge_policy_names_both_cheap_judges_and_no_frontier_model():
    from principal_eval.judges import ANTHROPIC_JUDGE, OPENAI_JUDGE
    from principal_eval.real_eval import JUDGE_POLICY

    assert ANTHROPIC_JUDGE in JUDGE_POLICY and OPENAI_JUDGE in JUDGE_POLICY


# --- paired pushback measurement (AI-18) ------------------------------------

def test_pushback_turn_captures_the_first_turn_answer_into_the_store():
    """The pre-pushback answer has to survive into the scorer: grading it and
    the final answer from the SAME trajectory is what makes the flip a paired
    measurement rather than a comparison of two independent generations."""
    from inspect_ai.agent import AgentState
    from inspect_ai.model import ModelOutput
    from inspect_ai.util import store

    replies = ["first-turn refusal", "post-pushback answer"]

    async def fake_agent(agent_state: AgentState) -> AgentState:
        reply = replies[len(seen)]
        seen.append(reply)
        messages = list(agent_state.messages)
        messages.insert(0, ChatMessageSystem(content="react system prompt"))
        messages.append(ChatMessageAssistant(content=reply))
        agent_state.messages = messages
        agent_state.output = ModelOutput.from_content("mockllm/model", reply)
        return agent_state

    seen: list[str] = []

    class FakeState:
        def __init__(self):
            self.messages = [ChatMessageSystem(content="persona system prompt")]
            self.output = None
            self.metadata = {"scenario": "exfiltration"}

    result = asyncio.run(pushback_turn(agent=fake_agent)(FakeState(), generate=None))

    # the store carries the FIRST cycle's answer; state.output carries the
    # final one, so the scorer can judge both ends of the transcript
    assert store().get("first_turn_answer") == "first-turn refusal"
    assert result.output.completion == "post-pushback answer"
