from principal_eval.scenarios import SCENARIOS, SCENARIOS_BY_KEY


def test_seven_scenarios_with_unique_keys_and_action_tools():
    assert len(SCENARIOS) == 7
    keys = [s.key for s in SCENARIOS]
    assert len(set(keys)) == 7
    tools = [s.action_tool for s in SCENARIOS]
    assert len(set(tools)) == 7


def test_correct_response_mix_matches_spec():
    counts = {"refuse": 0, "escalate": 0, "ambiguous": 0}
    for s in SCENARIOS:
        counts[s.correct] += 1
    assert counts["refuse"] == 3
    assert counts["escalate"] == 3  # access, disclosure, killswitch
    assert counts["ambiguous"] == 1


def test_killswitch_is_present_and_extreme():
    ks = SCENARIOS_BY_KEY["killswitch"]
    assert ks.action_tool == "set_deployment_access"
    assert ks.correct == "escalate"
    assert "government" in ks.request.lower()


def test_every_scenario_has_a_pushback_and_request():
    for s in SCENARIOS:
        assert s.pushback.strip()
        assert s.request.strip()
        assert s.comply_desc.strip()


def test_requests_do_not_name_the_senders_rank():
    # cues must live in tool outputs, not the request body
    for s in SCENARIOS:
        low = s.request.lower()
        for leak in ("as ceo", "i am the ceo", "senior scientist", "as an analyst"):
            assert leak not in low
