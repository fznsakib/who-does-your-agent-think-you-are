from principal_eval.real_eval import build_dataset


def test_matrix_is_42_cells():
    samples = list(build_dataset().samples)
    assert len(samples) == 42  # 7 scenarios * (5 identified + 1 anon)


def test_identified_has_five_personas_per_scenario():
    samples = list(build_dataset().samples)
    ident = [s for s in samples if s.metadata["condition"] == "identified"]
    anon = [s for s in samples if s.metadata["condition"] == "anonymised"]
    assert len(ident) == 35
    assert len(anon) == 7
    # each anon cell uses the shared placeholder persona
    assert {s.metadata["persona"] for s in anon} == {"anonymous"}


def test_every_sample_carries_required_metadata():
    for s in build_dataset().samples:
        assert set(s.metadata) >= {"persona", "condition", "scenario"}
