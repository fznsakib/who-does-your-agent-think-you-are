"""The real harness: 5-persona status ladder x anonymisation transform x 10 scenarios
(7 status-irrelevant + 3 role-gated calibration)."""
from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.agent import Agent, AgentState, as_solver, react
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageSystem, ChatMessageUser
from inspect_ai.solver import Generate, Solver, TaskState, solver

from principal_eval.episode import TRIGGER, setup_episode
from principal_eval.personas import PERSONA_ORDER
from principal_eval.scenarios import SCENARIOS_BY_KEY, SCENARIOS
from principal_eval.scoring import persona_scorer
from principal_eval.tools import action_tools, cue_tools


def build_dataset() -> MemoryDataset:
    samples: list[Sample] = []
    for scenario in SCENARIOS:
        for persona in PERSONA_ORDER:  # identified: 5 persona-cells
            samples.append(Sample(
                input=TRIGGER,
                metadata={"persona": persona, "condition": "identified",
                          "scenario": scenario.key,
                          "family": scenario.family},
            ))
        samples.append(Sample(  # anonymised: one shared baseline
            input=TRIGGER,
            metadata={"persona": "anonymous", "condition": "anonymised",
                      "scenario": scenario.key,
                      "family": scenario.family},
        ))
    return MemoryDataset(samples)


@task
def principal_eval(judge_model: str = "openai/gpt-4o-mini") -> Task:
    agent = react(tools=cue_tools() + action_tools(), attempts=1)
    return Task(
        dataset=build_dataset(),
        solver=[setup_episode(), as_solver(agent)],
        scorer=persona_scorer(judge_model),
    )


@solver
def pushback_turn(agent: Agent | None = None) -> Solver:
    """Run a second react cycle after appending the scenario's pushback line.

    react()'s execute() unconditionally does `state.messages.insert(0,
    system_message)` on every invocation of the agent, so calling
    `as_solver(react(...))` twice in a row would insert its own system
    message twice (duplicated/conflicting prompts). To avoid that, this
    solver builds ONE react agent instance and invokes it directly (not
    via as_solver) twice:

      1st call: react inserts its system message at index 0, runs one
                cycle, and returns with state.output.completion set to the
                first-turn answer.
      (strip)   we remove that freshly-inserted react system message
                (it sits at index 0, ahead of setup_episode's persona
                system message which was originally at index 0) so it
                isn't duplicated, then append the pushback ChatMessageUser
                (framed as the sender's follow-up).
      2nd call: react inserts a fresh (identical) system message at index
                0 again, runs a second cycle against the pushback, and
                returns with state.output.completion set to the
                post-pushback answer -- which is what persona_scorer grades.

    Net effect: exactly one react system message present in the final
    transcript, the persona/episode system message from setup_episode
    stays untouched, and state.output.completion ends up as the final
    post-pushback response.

    `agent` is injectable for unit testing (defaults to a real react()
    agent); production callers should not pass it.
    """
    agent = agent if agent is not None else react(tools=cue_tools() + action_tools(), attempts=1)

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        scenario = SCENARIOS_BY_KEY[state.metadata["scenario"]]

        agent_state = AgentState(messages=state.messages)
        agent_state = await agent(agent_state)

        # react() inserted its own system message at index 0 of the
        # messages it was handed; remove it before the second call so we
        # don't end up with two copies once react re-inserts on re-entry.
        messages = list(agent_state.messages)
        if messages and isinstance(messages[0], ChatMessageSystem):
            messages.pop(0)
        messages.append(ChatMessageUser(content=scenario.pushback))
        agent_state.messages = messages

        agent_state = await agent(agent_state)

        state.messages = agent_state.messages
        if agent_state.output:
            state.output = agent_state.output
        return state

    return solve


# The pushback arm only makes sense where re-asserted authority should NOT
# change the answer: status-irrelevant scenarios with an unambiguous correct
# response (refuse/escalate). Role-gated scenarios are excluded (authority is
# the very thing being calibrated) and so is the ambiguous surveillance one.
PUSHBACK_SCENARIO_KEYS: list[str] = [
    s.key for s in SCENARIOS
    if s.family == "status_irrelevant" and s.correct in ("refuse", "escalate")
]


def build_pushback_dataset() -> MemoryDataset:
    keys = set(PUSHBACK_SCENARIO_KEYS)
    return MemoryDataset(
        [s for s in build_dataset().samples if s.metadata["scenario"] in keys]
    )


@task
def principal_eval_pushback(judge_model: str = "openai/gpt-4o-mini") -> Task:
    """Pushback arm of the pilot: adds a second react cycle after the
    scenario's pushback follow-up, and the judge grades the FINAL
    post-pushback response. Runs on the 6 refuse/escalate status-irrelevant
    scenarios x 6 conditions = 36 samples (see PUSHBACK_SCENARIO_KEYS); does
    not modify principal_eval's solver, dataset, or metadata contract.
    """
    return Task(
        dataset=build_pushback_dataset(),
        solver=[setup_episode(), pushback_turn()],
        scorer=persona_scorer(judge_model, variant="pushback"),
    )
