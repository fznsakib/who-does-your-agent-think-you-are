"""Persona fixtures and per-model self-referential lab config."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabConfig:
    name: str
    domain: str


LABS: dict[str, LabConfig] = {
    "anthropic": LabConfig(name="Anthropic", domain="anthropic.com"),
    "openai": LabConfig(name="OpenAI", domain="openai.com"),
}
DEFAULT_LAB = LabConfig(name="Meridian AI", domain="meridian.ai")


def lab_for_model(model_name: str) -> LabConfig:
    """Map an Inspect model string (e.g. 'anthropic/claude-haiku-4-5') to its lab."""
    provider = model_name.split("/", 1)[0].lower()
    return LABS.get(provider, DEFAULT_LAB)
