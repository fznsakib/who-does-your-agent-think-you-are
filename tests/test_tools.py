from principal_eval.tools import ACTION_TOOLS, cue_tools, action_tools
from principal_eval.scenarios import SCENARIOS


def test_action_registry_covers_every_scenario():
    for s in SCENARIOS:
        assert s.action_tool in ACTION_TOOLS


def test_four_cue_tools_and_seven_action_tools():
    assert len(cue_tools()) == 4
    assert len(action_tools()) == 7


def test_action_registry_has_exactly_the_seven_tools():
    assert set(ACTION_TOOLS) == {
        "send_external", "deploy_checkpoint", "edit_audit_log", "grant_access",
        "post_public", "read_user_messages", "set_deployment_access",
    }
