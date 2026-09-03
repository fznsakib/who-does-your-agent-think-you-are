"""Render an Inspect sample's messages into a simple, JSON-serialisable
transcript for the hand-labelling UI. Never shows the judge's grade or
explanation -- callers must not pass those in."""
from __future__ import annotations

from typing import Any


def render_transcript(sample: Any) -> list[dict]:
    segments: list[dict] = []
    for m in sample.messages:
        role = m.role
        text = getattr(m, "text", None) or ""
        tool_calls = getattr(m, "tool_calls", None) or []
        if role == "tool":
            fn = getattr(m, "function", None) or "tool"
            segments.append({"role": "tool_result", "tool": fn, "text": text})
            continue
        if text:
            segments.append({"role": role, "text": text})
        for tc in tool_calls:
            args = getattr(tc, "arguments", {}) or {}
            segments.append({
                "role": "tool_call",
                "tool": getattr(tc, "function", "?"),
                "args": args,
            })
    return segments
