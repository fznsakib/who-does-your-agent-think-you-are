from principal_eval.personas import lab_for_model


def test_anthropic_model_maps_to_anthropic_lab():
    lab = lab_for_model("anthropic/claude-haiku-4-5")
    assert lab.name == "Anthropic"
    assert lab.domain == "anthropic.com"


def test_openai_model_maps_to_openai_lab():
    lab = lab_for_model("openai/gpt-4o-mini")
    assert lab.name == "OpenAI"


def test_unknown_provider_falls_back_to_neutral_lab():
    lab = lab_for_model("mistral/whatever")
    assert lab.name == "Meridian AI"
