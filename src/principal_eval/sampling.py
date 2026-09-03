"""Stratified sampling for a hand-labelling pass over eval logs.

Don't sample uniformly at random — deliberately include whoami-calling
episodes (the only ones where identity fusion can occur) and role-gated
cells (where a ceo-gate-inversion-style lead would live), and oversample
PARTIAL grades and judge/harmful-action-predicate disagreements, since those
are the cells where the judge is least trustworthy and a uniform sample
would barely touch them.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass
from math import ceil
from typing import Any

from inspect_ai.log import list_eval_logs, read_eval_log, read_eval_log_sample_summaries

# Candidate metadata key for AI-20's harmful-action predicate, mirrored from
# analysis.HARMFUL_ACTION_KEYS. Kept local (rather than imported) so this
# module has no dependency on analysis's Row/bootstrap machinery.
HARMFUL_ACTION_KEYS = ("harmful_action_occurred",)

# Default stratum quotas as a fraction of the target sample size. Strata are
# applied in this order and a sample already picked by an earlier stratum is
# not double-counted against a later one's quota.
DEFAULT_QUOTAS: dict[str, float] = {
    "harmful_disagreement": 0.20,  # 0 until AI-20 lands; redistributed below
    "role_gated": 0.15,
    "whoami_caller": 0.15,
    "partial_grade": 0.25,
}


def _first_present(meta: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in meta:
            return meta[k]
    return None


@dataclass(frozen=True)
class Candidate:
    log_path: str
    sample_id: Any
    epoch: int
    model: str
    task: str
    persona: str | None
    condition: str | None
    scenario: str | None
    family: str | None
    grade: str | None
    judge_model: str | None
    cues_read: tuple[str, ...]
    harmful_action_occurred: bool | None  # None until AI-20 lands

    @property
    def key(self) -> str:
        return f"{self.log_path}::{self.sample_id}::{self.epoch}"

    def strata(self) -> set[str]:
        s = set()
        if self.family == "role_gated":
            s.add("role_gated")
        if "whoami" in self.cues_read:
            s.add("whoami_caller")
        if self.grade == "PARTIAL":
            s.add("partial_grade")
        if self.harmful_action_occurred is not None:
            disagree = (self.grade == "COMPLIED") != bool(self.harmful_action_occurred)
            if disagree:
                s.add("harmful_disagreement")
        return s


def load_candidates(paths: list[str]) -> list[Candidate]:
    """Cheap load: sample summaries only (no transcripts), per the
    reading-logs skill's "which samples..." decision tree."""
    files: list[str] = []
    for p in paths:
        if p.endswith(".eval") or p.endswith(".json"):
            files.append(p)
        else:
            files.extend(info.name for info in list_eval_logs(p, recursive=True))

    out: list[Candidate] = []
    for path in files:
        header = read_eval_log(path, header_only=True)
        task = header.eval.task
        model = str(header.eval.model)
        for summary in read_eval_log_sample_summaries(path):
            if summary.error is not None or not summary.scores:
                continue
            score = next(iter(summary.scores.values()))
            meta = score.metadata or {}
            smeta = summary.metadata or {}
            harmful = _first_present(meta, HARMFUL_ACTION_KEYS)
            out.append(Candidate(
                log_path=path,
                sample_id=summary.id,
                epoch=summary.epoch,
                model=model,
                task=task,
                persona=meta.get("persona", smeta.get("persona")),
                condition=meta.get("condition", smeta.get("condition")),
                scenario=meta.get("scenario", smeta.get("scenario")),
                family=meta.get("family", smeta.get("family")),
                grade=meta.get("grade"),
                judge_model=meta.get("judge_model"),
                cues_read=tuple(meta.get("cues_read", []) or []),
                harmful_action_occurred=bool(harmful) if harmful is not None else None,
            ))
    return out


def stratified_sample(
    candidates: list[Candidate],
    n: int,
    quotas: dict[str, float] | None = None,
    seed: int = 6,
) -> list[Candidate]:
    """Fills stratum quotas first (each capped by availability), then tops up
    the remainder by round-robining over (model, scenario, persona,
    condition) cells so coverage stays broad rather than clumping on
    whichever cell happens to sort first. Deterministic for a given
    `candidates` order and `seed`.
    """
    rng = random.Random(seed)
    quotas = dict(quotas or DEFAULT_QUOTAS)

    # A quota with no eligible candidates (e.g. harmful_disagreement before
    # AI-20 lands) redistributes its share to the remaining active quotas
    # rather than shrinking the total sample.
    pools = {name: [c for c in candidates if name in c.strata()] for name in quotas}
    active = {name: frac for name, frac in quotas.items() if pools[name]}
    dead_frac = sum(frac for name, frac in quotas.items() if not pools[name])
    if active:
        bump = dead_frac / len(active)
        active = {name: frac + bump for name, frac in active.items()}

    picked: dict[str, Candidate] = {}
    for name, frac in active.items():
        pool = [c for c in pools[name] if c.key not in picked]
        rng.shuffle(pool)
        quota_n = min(len(pool), ceil(n * frac))
        for c in pool[:quota_n]:
            picked[c.key] = c

    # Each stratum independently rounds UP (`ceil`), so for a small `n` or
    # quotas whose rounded shares happen to sum past 1, the strata combined
    # can already exceed the requested `n` before any top-up runs. Trim back
    # down rather than silently over-returning.
    if len(picked) > n:
        keys = list(picked)
        rng.shuffle(keys)
        picked = {k: picked[k] for k in keys[:n]}

    # Top up the remainder for coverage breadth: round-robin over distinct
    # (model, scenario, persona, condition) cells not yet represented.
    remaining_needed = max(0, n - len(picked))
    if remaining_needed:
        remainder_pool = [c for c in candidates if c.key not in picked]
        rng.shuffle(remainder_pool)
        by_cell: dict[tuple, list[Candidate]] = {}
        for c in remainder_pool:
            by_cell.setdefault((c.model, c.scenario, c.persona, c.condition), []).append(c)
        cells = list(by_cell.values())
        rng.shuffle(cells)
        i = 0
        while remaining_needed and any(by_cell.values()):
            cell = cells[i % len(cells)]
            if cell:
                c = cell.pop()
                if c.key not in picked:
                    picked[c.key] = c
                    remaining_needed -= 1
            i += 1
            if i > 100_000:  # pools exhausted; avoid an infinite loop
                break

    return list(picked.values())


def write_manifest(candidates: list[Candidate], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump([asdict(c) for c in candidates], f, indent=2, default=str)


def read_manifest(path: str) -> list[Candidate]:
    with open(path) as f:
        raw = json.load(f)
    return [Candidate(**{**r, "cues_read": tuple(r["cues_read"])}) for r in raw]
