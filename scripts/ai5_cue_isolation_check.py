"""AI-5 validation: verify the cue-isolation invariant in real transcripts.

Invariant (CLAUDE.md): identity cues reach the model ONLY through tool outputs -
never in the system message or the user message. The system prompt carries lab
framing only, and the episode trigger is byte-identical across personas.

This reads N sampled transcripts per log and asserts:
  1. the system message contains no persona-identifying string
  2. every user message is the shared TRIGGER (or a scenario pushback line)
  3. the persona's identifying strings DO appear in tool outputs (i.e. the cue
     actually reached the model by the sanctioned channel)

Usage:
    uv run python scripts/ai5_cue_isolation_check.py <log.eval> [--n 3]
"""
from __future__ import annotations

import sys

from inspect_ai.log import read_eval_log, read_eval_log_samples

sys.path.insert(0, "src")
from principal_eval.episode import TRIGGER, build_episode_context  # noqa: E402
from principal_eval.scenarios import SCENARIOS_BY_KEY  # noqa: E402


def identity_strings(model: str, persona: str, condition: str, scenario: str) -> list[str]:
    """Identity-bearing strings for this episode.

    Compound records (the full email address, the pipe-delimited directory entry,
    a whole calendar line) are NOT sufficient probes: a system or user message could
    leak an atomic fragment - "Alex Rivera", "Chief Executive Officer", the email
    signature - without containing any complete record, and the check would pass.
    So split the compound records into their atomic fields and probe those too.
    """
    ctx = build_episode_context(model, persona, condition, scenario)
    parts: list[str] = [ctx.identity_email, ctx.directory_entry, *ctx.calendar]
    # atomic fields out of the directory entry: "Name | Title | Team | reports to: X"
    for seg in (ctx.directory_entry or "").split("|"):
        seg = seg.strip()
        if seg.lower().startswith("reports to:"):
            seg = seg.split(":", 1)[1].strip()
        parts.append(seg)
    # the email local-part on its own ("a.rivera"), and the signature block
    if ctx.identity_email and "@" in ctx.identity_email:
        parts.append(ctx.identity_email.split("@", 1)[0])
    parts.extend(seg.strip() for line in ctx.calendar for seg in line.split("-"))
    # de-dupe, drop empties and anything too short to be a meaningful probe
    seen, out = set(), []
    for p in parts:
        p = (p or "").strip()
        if len(p) > 4 and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out


def check_sample(sample, model: str) -> list[str]:
    meta = sample.metadata or {}
    persona = meta.get("persona")
    condition = meta.get("condition")
    scenario_key = meta.get("scenario")
    scenario = SCENARIOS_BY_KEY[scenario_key]
    failures: list[str] = []

    sys_msgs = [m for m in sample.messages if m.role == "system"]
    user_msgs = [m for m in sample.messages if m.role == "user"]
    tool_msgs = [m for m in sample.messages if m.role == "tool"]

    probes = identity_strings(model, persona, condition, scenario_key)
    ctx_email = probes[0]
    # Every probe (compound record AND atomic field) must be absent from the system
    # and user channels. Only the email address is required to be PRESENT in a tool
    # output - the directory entry and calendar appear solely if the agent chose to
    # call lookup_directory / read_calendar.

    sys_blob = " ".join(m.text for m in sys_msgs).lower()
    tool_blob = " ".join(m.text for m in tool_msgs).lower()

    for p in probes:
        if p.lower() in sys_blob:
            failures.append(f"LEAK: identity string in SYSTEM message: {p!r}")

    # The user turns must carry no identity. Beyond the shared TRIGGER and the
    # scenario pushback line, react() injects its own continuation prompt -
    # framework text, identical across personas, so it is allowed. What is NOT
    # allowed is any identity string appearing in a user turn.
    allowed_user = {TRIGGER.strip().lower(), scenario.pushback.strip().lower()}
    for m in user_msgs:
        text = m.text.strip().lower()
        if text in allowed_user:
            continue
        if "please proceed to the next step" in text:  # react() continuation
            continue
        failures.append(f"UNEXPECTED user message: {m.text[:120]!r}")
    user_blob = " ".join(m.text for m in user_msgs).lower()
    for p in probes:
        if p.lower() in user_blob:
            failures.append(f"LEAK: identity string in USER message: {p!r}")

    # Positive control: for identified episodes the sender's address must have
    # reached the model through a tool output, else the manipulation never landed.
    if condition == "identified":
        if ctx_email.lower() not in tool_blob:
            failures.append(f"NO CUE DELIVERED: {ctx_email!r} absent from all tool outputs")

    return failures


def main() -> None:
    argv = sys.argv[1:]
    n = 3
    args: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--n":
            n = int(argv[i + 1])
            i += 2
            continue
        args.append(argv[i])
        i += 1
    if not args:
        raise SystemExit(__doc__)

    total_failures = 0
    total_checked = 0
    for path in args:
        print(f"\n=== {path} ===")
        # The provider-qualified model string from the header is what
        # setup_episode saw (str(state.model)); sample.output.model drops the
        # provider prefix, which changes which lab identity is built.
        header = read_eval_log(path, header_only=True)
        log_model = str(header.eval.model)
        checked = 0
        all_failures = 0
        seen_personas: set[str] = set()
        for sample in read_eval_log_samples(path, all_samples_required=False):
            if sample.error is not None:
                continue
            meta = sample.metadata or {}
            persona = meta.get("persona")
            # spread the spot-check over distinct personas
            if persona in seen_personas:
                continue
            seen_personas.add(persona)
            failures = check_sample(sample, log_model)
            status = "OK" if not failures else "FAIL"
            print(f"[{status}] persona={persona} condition={meta.get('condition')} "
                  f"scenario={meta.get('scenario')} epoch={sample.epoch}")
            for f in failures:
                print(f"       {f}")
            all_failures += len(failures)
            checked += 1
            if checked >= n:
                break
        print(f"-- checked {checked} transcripts, {all_failures} invariant violations")
        total_failures += all_failures
        total_checked += checked

    # Exit non-zero so CI and shell pipelines cannot silently accept a FAIL. A run
    # that sampled no transcripts at all is also a failure: it validated nothing.
    if total_failures:
        print(f"\nFAILED: {total_failures} cue-isolation violations across {total_checked} transcripts")
        raise SystemExit(1)
    if total_checked == 0:
        print("\nFAILED: no transcripts were checked")
        raise SystemExit(1)
    print(f"\nOK: {total_checked} transcripts, 0 violations")


if __name__ == "__main__":
    main()
