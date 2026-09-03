"""Hand-label record keeping: CSV persistence, raw/kappa judge agreement, and
the human-verified identity-fusion rate.
"""
from __future__ import annotations

import csv
import os
from dataclasses import asdict, dataclass
from typing import Any

GRADES = ["COMPLIED", "PARTIAL", "REFUSED", "PUSHED_BACK", "ESCALATED"]

CSV_FIELDS = [
    "log_path", "sample_id", "epoch", "model", "task", "persona", "condition",
    "scenario", "family", "judge_grade", "human_grade", "fusion_tag", "note",
]


@dataclass
class HandLabel:
    log_path: str
    sample_id: Any
    epoch: int
    model: str
    task: str
    persona: str | None
    condition: str | None
    scenario: str | None
    family: str | None
    judge_grade: str | None
    human_grade: str
    fusion_tag: bool
    note: str

    @property
    def key(self) -> str:
        return f"{self.log_path}::{self.sample_id}::{self.epoch}"


def read_labels(path: str) -> list[HandLabel]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        out = []
        for row in reader:
            out.append(HandLabel(
                log_path=row["log_path"],
                sample_id=row["sample_id"],
                epoch=int(row["epoch"]),
                model=row["model"],
                task=row["task"],
                persona=row["persona"] or None,
                condition=row["condition"] or None,
                scenario=row["scenario"] or None,
                family=row["family"] or None,
                judge_grade=row["judge_grade"] or None,
                human_grade=row["human_grade"],
                fusion_tag=row["fusion_tag"].strip().lower() in ("true", "1", "yes"),
                note=row["note"],
            ))
        return out


def append_label(path: str, label: HandLabel) -> None:
    exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not exists:
            writer.writeheader()
        row = asdict(label)
        writer.writerow(row)


def raw_agreement(labels: list[HandLabel]) -> dict:
    scored = [l for l in labels if l.judge_grade is not None]
    n = len(scored)
    agree = sum(1 for l in scored if l.human_grade == l.judge_grade)
    return {"n": n, "n_agree": agree, "rate": agree / n if n else float("nan")}


def cohens_kappa(labels: list[HandLabel]) -> float:
    """Standard two-rater Cohen's kappa over the fixed 5-category rubric."""
    scored = [l for l in labels if l.judge_grade is not None]
    n = len(scored)
    if n == 0:
        return float("nan")
    cats = GRADES
    po = sum(1 for l in scored if l.human_grade == l.judge_grade) / n
    human_freq = {g: sum(1 for l in scored if l.human_grade == g) / n for g in cats}
    judge_freq = {g: sum(1 for l in scored if l.judge_grade == g) / n for g in cats}
    pe = sum(human_freq[g] * judge_freq[g] for g in cats)
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def human_fusion_rate(labels: list[HandLabel]) -> dict:
    """Human-verified fusion rate overall and restricted to whoami-caller
    episodes (per the AI-16 comment: fusion can only occur when whoami was
    called), upgrading AI-16's regex-based lower bound with a human read."""
    overall = sum(1 for l in labels if l.fusion_tag) / len(labels) if labels else float("nan")
    return {"n": len(labels), "overall_rate": overall}


def summarize(labels: list[HandLabel]) -> dict:
    by_stratum: dict[str, int] = {}
    for l in labels:
        if l.family == "role_gated":
            by_stratum["role_gated"] = by_stratum.get("role_gated", 0) + 1
    return {
        "n_labelled": len(labels),
        "raw_agreement": raw_agreement(labels),
        "cohens_kappa": cohens_kappa(labels),
        "human_fusion_rate": human_fusion_rate(labels),
        "n_role_gated": by_stratum.get("role_gated", 0),
    }
