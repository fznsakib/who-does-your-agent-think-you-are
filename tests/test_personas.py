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


from principal_eval.personas import (
    PERSONAS,
    PERSONA_ORDER,
    build_identity,
    neutral_identity,
    lab_for_model as _lab,
)

LAB = _lab("anthropic/claude-haiku-4-5")


def test_persona_order_is_importance_ranked():
    assert PERSONA_ORDER == [
        "ceo",
        "researcher",
        "mid_high_prox",
        "mid_low_prox",
        "external",
    ]
    assert set(PERSONA_ORDER) == set(PERSONAS)


def test_ceo_identity_leaks_rank_through_channels():
    idn = build_identity("ceo", LAB)
    assert "anthropic.com" in idn.email
    assert "Chief Executive Officer" in idn.signature
    assert "Chief Executive Officer" in idn.directory_entry
    # rank is NOT in a bare user message — only in these channel strings
    assert "Anthropic" in idn.signature


def test_proximity_pair_shares_rank_but_differs_only_on_calendar():
    hi = build_identity("mid_high_prox", LAB)
    lo = build_identity("mid_low_prox", LAB)
    # same rank/title in the directory
    assert "Data Analyst" in hi.directory_entry
    assert "Data Analyst" in lo.directory_entry
    # proximity shows up only via calendar
    hi_cal = "\n".join(hi.calendar).lower()
    lo_cal = "\n".join(lo.calendar).lower()
    assert "ceo" in hi_cal or "founder" in hi_cal
    assert "ceo" not in lo_cal and "founder" not in lo_cal


def test_external_is_marked_non_affiliated():
    idn = build_identity("external", LAB)
    assert "anthropic.com" not in idn.email
    assert "External" in idn.directory_entry


def test_neutral_identity_is_persona_independent():
    n1 = neutral_identity(LAB)
    n2 = neutral_identity(LAB)
    assert n1 == n2
    assert n1.signature == ""
    assert "No title" in n1.directory_entry
    # neutral baseline leaks no rank/proximity terms
    blob = (n1.signature + n1.directory_entry + " ".join(n1.calendar)).lower()
    for term in ("ceo", "executive", "analyst", "founder", "contractor"):
        assert term not in blob
