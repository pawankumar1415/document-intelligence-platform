from backend.app.services.extraction_signals import extract_signals


def test_extract_signals_detects_expected_patterns() -> None:
    text = (
        "The architecture has API and service components for document processing. "
        "Functional requirements and non-functional requirements were defined with acceptance criteria. "
        "Project timeline and implementation plan include phased delivery milestones."
    )

    signals = extract_signals(text)
    signal_names = {signal.name for signal in signals}

    assert "solution_architecture" in signal_names
    assert "delivery_planning" in signal_names
    assert "project_requirements" in signal_names


def test_extract_signals_detects_sellafield_style_patterns() -> None:
    text = (
        "ONR safeguards compliance inspection reviewed NSR19 records and provided assurance. "
        "The business case highlighted cost variance, budget pressure, and schedule delay. "
        "The contract framework for suppliers supports decommissioning, silo waste retrieval, and risk reduction."
    )

    signals = extract_signals(text)
    signal_names = {signal.name for signal in signals}

    assert "regulatory_compliance" in signal_names
    assert "commercial_value" in signal_names
    assert "decommissioning_environment" in signal_names
