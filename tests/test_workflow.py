"""Test the agent workflow with pytest.

This module provides pytest-based tests to verify the LangGraph
workflow implementation works correctly.
"""

import pytest
from app.agents import compile_workflow


@pytest.fixture
def workflow():
    """Fixture that compiles and returns the workflow."""
    return compile_workflow()


@pytest.fixture
def mock_input_state():
    """Fixture that provides mock input state for workflow testing."""
    return {
        "job_id": "test-job-123",
        "input_image": "/path/to/test/image.jpg",
        "recommendations": [
            {
                "id": "rec-1",
                "text": "Make the background brighter",
                "priority": 3,
                "category": "color",
            },
            {
                "id": "rec-2",
                "text": "Add more contrast to the main subject",
                "priority": 4,
                "category": "contrast",
            },
            {
                "id": "rec-3",
                "text": "Adjust the color temperature to be warmer",
                "priority": 2,
                "category": "color",
            },
        ],
        "brand_guidelines": {
            "primary_colors": ["#FF5733", "#33FF57"],
            "secondary_colors": ["#3357FF"],
            "fonts": ["Arial", "Helvetica"],
            "logo_url": "https://example.com/logo.png",
        },
        "tasks": [],
        "variants": [],
        "audit_trail": [],
        "completed": False,
    }


def test_workflow_compilation():
    """Test that the workflow compiles successfully."""
    workflow = compile_workflow()
    assert workflow is not None


@pytest.mark.asyncio
async def test_workflow_execution(workflow, mock_input_state):
    """Test workflow execution with mock data."""
    final_state = await workflow.ainvoke(mock_input_state)

    # Verify workflow completed
    assert final_state is not None
    assert final_state.get("job_id") == "test-job-123"
    assert final_state.get("completed") is True

    # Verify tasks were created
    tasks = final_state.get("tasks", [])
    assert len(tasks) > 0

    # Verify variants were generated
    variants = final_state.get("variants", [])
    assert len(variants) > 0

    # Verify audit trail was populated
    audit_trail = final_state.get("audit_trail", [])
    assert len(audit_trail) > 0


@pytest.mark.asyncio
async def test_workflow_creates_tasks_from_recommendations(workflow, mock_input_state):
    """Test that workflow creates tasks for each recommendation."""
    num_recommendations = len(mock_input_state["recommendations"])
    final_state = await workflow.ainvoke(mock_input_state)

    tasks = final_state.get("tasks", [])
    assert len(tasks) == num_recommendations


@pytest.mark.asyncio
async def test_workflow_generates_variants(workflow, mock_input_state):
    """Test that workflow generates variants with proper structure."""
    final_state = await workflow.ainvoke(mock_input_state)

    variants = final_state.get("variants", [])
    for variant in variants:
        assert "recommendation_id" in variant
        assert "status" in variant
        assert "evaluation_score" in variant
        assert "iterations" in variant


@pytest.mark.asyncio
async def test_workflow_audit_trail(workflow, mock_input_state):
    """Test that workflow maintains an audit trail."""
    final_state = await workflow.ainvoke(mock_input_state)

    audit_trail = final_state.get("audit_trail", [])
    for entry in audit_trail:
        assert "agent" in entry
        assert "action" in entry
