"""The real harness: 5-persona status ladder x anonymisation transform x 7 scenarios."""
from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.agent import as_solver, react
from inspect_ai.dataset import MemoryDataset, Sample

from .episode import TRIGGER, setup_episode
from .personas import PERSONA_ORDER
from .scenarios import SCENARIOS
from .scoring import persona_scorer
from .tools import action_tools, cue_tools


def build_dataset() -> MemoryDataset:
    samples: list[Sample] = []
    for scenario in SCENARIOS:
        for persona in PERSONA_ORDER:  # identified: 5 persona-cells
            samples.append(Sample(
                input=TRIGGER,
                metadata={"persona": persona, "condition": "identified",
                          "scenario": scenario.key},
            ))
        samples.append(Sample(  # anonymised: one shared baseline
            input=TRIGGER,
            metadata={"persona": "anonymous", "condition": "anonymised",
                      "scenario": scenario.key},
        ))
    return MemoryDataset(samples)


@task
def principal_eval(judge_model: str = "openai/gpt-4o-mini") -> Task:
    # react() gives anti-premature-termination (nudges the model to decide/submit)
    # WITHOUT retry pressure: attempts=1, and the judge is a post-hoc scorer, never
    # a react retry gate. The dynamic per-model lab system prompt is set at runtime
    # by setup_episode; react's own prompt stays neutral.
    agent = react(tools=cue_tools() + action_tools(), attempts=1)
    return Task(
        dataset=build_dataset(),
        solver=[setup_episode(), as_solver(agent)],
        scorer=persona_scorer(judge_model),
    )
