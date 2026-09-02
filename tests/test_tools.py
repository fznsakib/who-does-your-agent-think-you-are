import asyncio

from inspect_ai.util import store

from principal_eval.tools import (
    ACTION_TOOLS, cue_tools, action_tools,
    read_email, whoami, lookup_directory, read_calendar,
    send_external,
)
from principal_eval.scenarios import SCENARIOS


def test_action_registry_covers_every_scenario():
    for s in SCENARIOS:
        assert s.action_tool in ACTION_TOOLS


def test_four_cue_tools_and_ten_action_tools():
    assert len(cue_tools()) == 4
    assert len(action_tools()) == 10


def test_action_registry_has_exactly_the_ten_tools():
    assert set(ACTION_TOOLS) == {
        "send_external", "deploy_checkpoint", "edit_audit_log", "grant_access",
        "post_public", "read_user_messages", "set_deployment_access",
        "authorize_exception", "grant_dataset_access", "approve_statement",
    }


def test_every_cue_tool_records_its_read_in_the_store():
    store().set("cues_read", [])
    store().set("identity_email", "user@example.com")
    asyncio.run(read_email()())
    asyncio.run(whoami()())
    asyncio.run(lookup_directory()("user@example.com"))
    asyncio.run(read_calendar()())
    assert store().get("cues_read") == [
        "read_email", "whoami", "lookup_directory", "read_calendar",
    ]


def test_tool_events_records_cues_and_actions_in_invocation_order():
    store().set("tool_events", [])
    store().set("identity_email", "user@example.com")
    asyncio.run(whoami()())
    asyncio.run(send_external()(to="ext@example.com", contents="data"))
    asyncio.run(read_calendar()())
    assert store().get("tool_events") == [
        {"kind": "cue", "tool": "whoami"},
        {"kind": "action", "tool": "send_external"},
        {"kind": "cue", "tool": "read_calendar"},
    ]
