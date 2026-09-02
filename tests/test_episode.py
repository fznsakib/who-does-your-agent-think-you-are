from principal_eval.episode import build_episode_context, compose_email
from principal_eval.personas import build_identity, lab_for_model
from principal_eval.scenarios import SCENARIOS_BY_KEY

MODEL = "anthropic/claude-haiku-4-5"


def test_identified_context_names_the_self_referential_lab():
    ctx = build_episode_context(MODEL, "ceo", "identified", "exfiltration")
    assert "Anthropic" in ctx.system_prompt
    assert "Chief Executive Officer" in ctx.email_text  # signature leaked via email
    assert ctx.identity_email.endswith("@anthropic.com")


def test_anonymised_context_is_persona_independent():
    a = build_episode_context(MODEL, "ceo", "anonymised", "exfiltration")
    b = build_episode_context(MODEL, "external", "anonymised", "exfiltration")
    assert a.email_text == b.email_text
    assert a.directory_entry == b.directory_entry
    assert "Chief Executive Officer" not in a.email_text


def test_email_contains_request_and_from_header():
    scen = SCENARIOS_BY_KEY["killswitch"]
    idn = build_identity("ceo", lab_for_model(MODEL))
    email = compose_email(idn, scen)
    assert "From:" in email
    assert "government" in email.lower()
    assert idn.signature in email  # identified → signature present


def test_openai_model_yields_openai_lab_in_prompt():
    ctx = build_episode_context("openai/gpt-4o-mini", "ceo", "identified", "exfiltration")
    assert "OpenAI" in ctx.system_prompt
