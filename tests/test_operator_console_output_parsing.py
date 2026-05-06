from pathlib import Path


HTML_PATH = Path("ui/static/operator_console.html")
CSS_PATH = Path("ui/static/operator_console.css")


def _html() -> str:
    return HTML_PATH.read_text()


def _css() -> str:
    return CSS_PATH.read_text()


def test_operator_console_syncs_state_panel_from_rendered_output():
    html = _html()

    assert "function outputStateFromSections(output)" in html
    assert "function syncStatePanelFromOutput(output)" in html
    assert "function buildLatestRunState(derived)" in html
    assert "function renderLatestRunState(derived)" in html
    assert 'valueFromSection(sections, "Execution Readiness", ["level"])' in html
    assert 'valueFromSection(sections, "Operator Workflow", ["state"])' in html
    assert 'valueFromSection(sections, "Handoff Summary", ["blockers"])' in html


def test_operator_console_labels_state_sources_separately():
    html = _html()

    assert "Clarification Session State" in html
    assert "Latest Run State" in html
    assert "Raw clarification/session state" in html
    assert "<h2>Raw State</h2>" not in html
    assert "latestRunStateRaw" in html


def test_operator_console_latest_run_state_uses_output_source():
    html = _html()

    helper_start = html.index("function buildLatestRunState(derived)")
    helper_end = html.index("function renderLatestRunState(derived)", helper_start)
    helper_block = html[helper_start:helper_end]

    assert "workflow_state: normalizeStateToken(derived.workflowStateValue" in helper_block
    assert 'workflow_state: "unknown"' in helper_block
    assert "readiness_level: normalizeStateToken(derived.readinessLevel" in helper_block
    assert "approval_state: \"not_requested\"" in helper_block
    assert "requires_human_approval: requiresHumanApproval" in helper_block
    assert "execution_prep_eligible: executionPrepEligible" in helper_block
    assert "blockers" in helper_block


def test_operator_console_set_output_syncs_after_rendering_output():
    html = _html()

    set_output_start = html.index("function setOutput(output)")
    set_output_end = html.index("function renderState(state)", set_output_start)
    set_output_block = html[set_output_start:set_output_end]

    assert "renderSectionedOutput(normalizedOutput);" in set_output_block
    assert "updateBriefFromOutput(normalizedOutput);" in set_output_block
    assert "syncStatePanelFromOutput(normalizedOutput);" in set_output_block
    assert "renderState(data.state);" not in set_output_block

    assert set_output_block.index("renderSectionedOutput(normalizedOutput);") < set_output_block.index(
        "syncStatePanelFromOutput(normalizedOutput);"
    )


def test_operator_console_does_not_mix_execution_block_details_with_raw_blocks():
    html = _html()

    helper_start = html.index("function outputStateFromSections(output)")
    helper_end = html.index("function syncStatePanelFromOutput(output)", helper_start)
    helper_block = html[helper_start:helper_end]

    assert 'const executionBlocks = sections.find((item) => item.title === "Execution Blocks");' in helper_block
    assert 'const executionBlockDetails = sections.find((item) => item.title === "Execution Block Details");' in helper_block
    assert "if (executionBlocks && executionBlocks.lines.length)" in helper_block
    assert "} else if (executionBlockDetails && executionBlockDetails.lines.length)" in helper_block


def test_operator_console_displays_boolean_approval_as_operator_language():
    html = _html()

    assert 'approvalState.textContent = "Not Required";' in html
    assert 'approvalState.textContent = "Required";' in html
    assert 'normalizedApproval === "false"' in html
    assert 'normalizedApproval === "true"' in html


def test_operator_console_prefers_raw_execution_blocks_over_block_details():
    html = _html()

    helper_start = html.index("function outputStateFromSections(output)")
    helper_end = html.index("function syncStatePanelFromOutput(output)", helper_start)
    helper_block = html[helper_start:helper_end]

    assert 'const executionBlocks = sections.find((item) => item.title === "Execution Blocks");' in helper_block
    assert 'const executionBlockDetails = sections.find((item) => item.title === "Execution Block Details");' in helper_block
    assert "if (executionBlocks && executionBlocks.lines.length)" in helper_block
    assert "} else if (executionBlockDetails && executionBlockDetails.lines.length)" in helper_block
    assert "blockLines.push(...executionBlocks.lines);" in helper_block
    assert "blockLines.push(...executionBlockDetails.lines);" in helper_block


def test_operator_console_recognizes_draft_itinerary_as_own_section():
    html = _html()

    assert '"Draft Itinerary:"' in html
    assert '"Draft Itinerary": "list"' in html


def test_operator_console_visually_separates_draft_itinerary_section():
    css = _css()

    assert ".output-section.draft-itinerary" in css
    assert "margin-top: 10px;" in css
