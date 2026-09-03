"""The real harness: 5-persona status ladder x anonymisation transform x 10 scenarios
(7 status-irrelevant + 3 role-gated calibration)."""
from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.agent import Agent, AgentState, as_solver, react
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, GenerateConfig
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import store

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


# Per-sample bounds against submit-loop runaways (AI-17): the AI-15 gpt-5-nano
# base run had 5/600 samples (~0.8%) spin in a submit loop -- 20+ consecutive
# `model` events with no tool call and no submit -- burning up to 1.07M tokens
# and 149 messages before being cancelled by hand. A normal sample is ~9
# messages/~10k tokens (pushback ~2x that, and the calibrated pushback-arm
# limits of message_limit=40/token_limit=150_000 were never hit by any
# sample there). message_limit=50 and token_limit=150_000 sit comfortably
# above every observed legitimate episode (including pushback) while capping
# a runaway at roughly 10-15% of its worst observed cost. Set on the Task
# itself (not a CLI flag) so every invocation is bounded by construction and
# a limit-hit sample yields a normal `limit`/`limit_reason`-tagged sample
# outcome instead of an unbounded run or a run-killing error.
MESSAGE_LIMIT = 50
TOKEN_LIMIT = 150_000


# Reasoning depth, pinned rather than inherited (AI-9). Every run before this one
# recorded `DEFAULT`, and the defaults are NOT symmetric across providers: the
# AI-15 gpt-5-nano base arm spent 4,501 reasoning tokens per sample (79% of its
# output) while the haiku-4.5 arm spent zero. That makes the completed
# cross-provider comparison a deliberating model against a non-deliberating one
# -- provider confounded with reasoning mode, the same class of error AI-15
# retired gpt-4o-mini for (provider confounded with generation).
#
# `reasoning_effort` is the only knob both providers accept, so it is the only
# setting in which parity is even expressible. "off" is not an option to choose:
# Claude 4.7+ (including Opus 5) is always in adaptive thinking and the provider
# rejects reasoning_effort="none". "medium" is the middle rung and the closest
# to what a deployed agent actually runs, which is what this eval is about.
#
# Nominal parity is NOT actual parity -- "medium" buys different amounts of
# computation from different vendors. The readout therefore reports the REALISED
# reasoning tokens per sample alongside this setting, so a reader can judge
# comparability instead of taking the label on trust.
#
# This reaches the model under test only. Inspect merges the full active generate
# config into a model only when it is the active model (`Model._resolve_config`);
# every other model -- here, the opposite-provider judge -- inherits operational
# config alone (connections/retries/timeout/cache). So a non-reasoning judge like
# gpt-4o-mini never receives `reasoning_effort` and cannot 400 on it.
REASONING_EFFORT = "medium"

GENERATE_CONFIG = GenerateConfig(reasoning_effort=REASONING_EFFORT)


# Recorded in the task metadata of every log so a reader knows which rule
# produced the judge named in each sample's score metadata.
JUDGE_POLICY = (
    "opposite-provider: the judge comes from the other provider to the model "
    "under test (anthropic -> openai/gpt-4o-mini, openai -> "
    "anthropic/claude-haiku-4-5); -T judge_model=... overrides it. "
    "The judge actually used is in each score's metadata under 'judge_model'."
)


def _judge_metadata(judge_model: str | None) -> dict[str, str | None]:
    return {"judge_policy": JUDGE_POLICY, "judge_model_override": judge_model}


@task
def principal_eval(judge_model: str | None = None) -> Task:
    """Base arm: 60 cells (10 scenarios x 5 personas + 1 anonymised baseline).

    Args:
      judge_model: pin a specific judge for the run. Omitted by default, in
        which case the judge is chosen per sample from the opposite provider
        to the model under test (see `principal_eval.judges`) so no model
        grades its own output and one provider's rate limit does not carry
        both the agent and the judge calls.
    """
    agent = react(tools=cue_tools() + action_tools(), attempts=1)
    return Task(
        dataset=build_dataset(),
        solver=[setup_episode(), as_solver(agent)],
        scorer=persona_scorer(judge_model),
        metadata=_judge_metadata(judge_model),
        message_limit=MESSAGE_LIMIT,
        token_limit=TOKEN_LIMIT,
        config=GENERATE_CONFIG,
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

        # Capture the pre-pushback answer so the scorer can judge it with the
        # same blind judge it uses on the final one. Grading both ends of the
        # SAME trajectory is what makes the flip rate a paired measurement
        # (AI-18): matching base-arm epoch N against pushback-arm epoch N
        # compares two independent generations, so sampling variance is
        # indistinguishable from the pushback effect.
        if agent_state.output:
            store().set("first_turn_answer", agent_state.output.completion)

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
def principal_eval_pushback(judge_model: str | None = None) -> Task:
    """Pushback arm of the pilot: adds a second react cycle after the
    scenario's pushback follow-up. The judge grades BOTH ends of each
    trajectory -- the first-turn answer captured into the store by
    `pushback_turn` and the final post-pushback response -- so the flip is
    measured within a transcript rather than across two independent runs
    (AI-18). The score value remains the final answer's compliance. Runs on the 6 refuse/escalate status-irrelevant
    scenarios x 6 conditions = 36 samples (see PUSHBACK_SCENARIO_KEYS); does
    not modify principal_eval's solver, dataset, or metadata contract.

    Args:
      judge_model: pin a specific judge for the run; defaults to the same
        opposite-provider selection as `principal_eval`.
    """
    return Task(
        dataset=build_pushback_dataset(),
        solver=[setup_episode(), pushback_turn()],
        scorer=persona_scorer(judge_model, variant="pushback"),
        metadata=_judge_metadata(judge_model),
        message_limit=MESSAGE_LIMIT,
        token_limit=TOKEN_LIMIT,
        config=GENERATE_CONFIG,
    )
