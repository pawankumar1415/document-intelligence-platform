from backend.app.services.extraction_signals import extract_signals


def test_extract_signals_detects_expected_patterns() -> None:
    text = (
        "The committee audit noted cost variance and governance concerns. "
        "Project milestones and timeline baseline were updated after inspection. "
        "Functional requirements and non-functional requirements tracker has been revised."
    )

    signals = extract_signals(text)
    signal_names = {signal.name for signal in signals}

    assert "governance_audit" in signal_names
    assert "project_controls" in signal_names
    assert "requirements_tracking" in signal_names


def test_extract_signals_detects_sellafield_style_patterns() -> None:
    text = (
        "ONR safeguards compliance inspection reviewed NSR19 records and provided assurance. "
        "The business case and project controls highlighted cost variance, budget pressure, and schedule delay. "
        "The contract framework for suppliers supports decommissioning, silo waste retrieval, and risk reduction."
    )

    signals = extract_signals(text)
    signal_names = {signal.name for signal in signals}

    assert "regulatory_compliance" in signal_names
    assert "project_commercials" in signal_names
    assert "environmental_waste" in signal_names
