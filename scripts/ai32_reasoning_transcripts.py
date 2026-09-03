"""AI-32 R7: pull transcripts for the hand-read content check.

The R-series token counts say *how much* the model deliberated, never *about
what*. R7 of the 2026-09-03 amendment requires hand-reading the highest-reasoning
`ceo` transcripts against `analyst` transcripts and reporting whether the extra
reasoning is about the **requester** at all, or about task difficulty that
happens to correlate with the cell.

**Both frontier providers ship ENCRYPTED reasoning.** In the AI-9 logs every
`ContentReasoning` block from `claude-opus-5` and `gpt-5.6-sol` carries
`redacted=True` and a ciphertext payload — Anthropic's signed thinking blocks and
OpenAI's encrypted reasoning items. The reasoning *text* cannot be read at any
price from these logs, so this script reports that fact per sample rather than
hiding it, and dumps what IS readable: the visible assistant text and the tool
call sequence of the same episodes. A survivor verdict read off token counts
whose content is unreadable is reported as **mechanism unexplained** (R7), not
as evidence of status-sensitivity.

Usage:
    uv run python scripts/ai32_reasoning_transcripts.py <log.eval> --persona ceo [--top 5]
"""
from __future__ import annotations

import sys

sys.path.insert(0, "src")

from inspect_ai.log import read_eval_log, read_eval_log_samples  # noqa: E402

from principal_eval.reasoning import is_subject_usage  # noqa: E402


def arg(flag: str, default: str) -> str:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main() -> None:
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {"--persona", "--top"}
    for f in flags:
        if f in sys.argv:
            positional = [a for a in positional if a != sys.argv[sys.argv.index(f) + 1]]
    if not positional:
        raise SystemExit(__doc__)
    path = positional[0]
    persona = arg("--persona", "ceo")
    top = int(arg("--top", "5"))

    header = read_eval_log(path, header_only=True)
    model = str(header.eval.model)

    picked = []
    for s in read_eval_log_samples(path, all_samples_required=header.status == "success"):
        meta = s.metadata or {}
        if meta.get("persona") != persona or meta.get("family") != "status_irrelevant":
            continue
        if s.error is not None or getattr(s, "limit", None) is not None:
            continue
        reasoning = sum(
            getattr(u, "reasoning_tokens", None) or 0
            for k, u in (s.model_usage or {}).items() if is_subject_usage(k, model)
        )
        picked.append((reasoning, s))
    picked.sort(key=lambda t: -t[0])

    print(f"# {model} — persona={persona} — top {top} by reasoning tokens")
    if len(picked) < top:
        # R7 requires FIVE transcripts per cell. Printing three under a "top 5"
        # header lets an incomplete hand-read look like a completed gate, so
        # this fails loudly rather than quietly under-delivering.
        print(f"!! INCOMPLETE: only {len(picked)} analysable {persona} samples are "
              f"available, fewer than the {top} requested. The R7 content check is "
              f"NOT satisfied by this output.")
    for reasoning, s in picked[:top]:
        meta = s.metadata or {}
        turns = sum(1 for m in s.messages if m.role == "assistant")
        print(f"\n{'=' * 72}")
        print(f"sample {s.id} epoch {s.epoch} scenario={meta.get('scenario')} "
              f"reasoning={reasoning} turns={turns}")
        for m in s.messages:
            if m.role != "assistant":
                continue
            # `content` may be a plain string rather than a multipart list --
            # a valid representation for assistant messages, and the usual one
            # when a provider exposes token counts without ContentReasoning
            # blocks. Iterating an empty list there would print a blank
            # transcript and silently hide the very evidence R7 exists to read.
            if isinstance(m.content, str):
                if m.content.strip():
                    print(f"  [text] {m.content.strip()}")
            for part in (m.content if isinstance(m.content, list) else []):
                kind = type(part).__name__
                if kind == "ContentReasoning":
                    if getattr(part, "redacted", False):
                        print("  [reasoning: ENCRYPTED by provider — content unreadable]")
                    else:
                        print(f"  [reasoning] {getattr(part, 'reasoning', '')}")
                elif kind == "ContentText" and getattr(part, "text", "").strip():
                    print(f"  [text] {part.text.strip()}")
            for tc in (m.tool_calls or []):
                print(f"  [tool] {tc.function}({tc.arguments})")

    if len(picked) < top:
        raise SystemExit(
            f"R7 INCOMPLETE: {len(picked)}/{top} {persona} transcripts available")


if __name__ == "__main__":
    main()
