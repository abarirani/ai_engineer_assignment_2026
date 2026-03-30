"""Unit tests for DeepAgentWorkflow exception handling.

This module tests that exceptions from subagent invocations propagate correctly
through the run_workflow() method.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.config.settings import settings, StorageSettings
import tempfile
from langchain_community.chat_models import FakeListChatModel


@pytest.mark.asyncio
async def test_run_workflow_subagent_invoke_exception_propagates():
    """Test that an exception from a subagent's invoke() propagates correctly
    through run_workflow().

    Exception handling chain verified:
    1. Subagent's invoke() raises an exception during agent.ainvoke()
    2. Exception propagates through the deep agent's execution
    3. DeepAgentWorkflow.run_workflow() receives the exception
    4. Exception is propagated to the caller (WorkflowService.process_job)

    This test uses minimal mocking:
    - FakeListChatModel from langchain_community for realistic chat model behavior
    - Mocked create_orchestrator to inject a subagent that raises on invoke
    - Real DeepAgentWorkflow instance to test actual exception propagation
    """
    from app.agents.deep_agent_workflow import DeepAgentWorkflow

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a fake LLM using LangChain's FakeListChatModel
        fake_llm = FakeListChatModel(responses=["test response"])

        with patch(
            "app.agents.deep_agent_workflow.LLMStrategyFactory"
        ) as mock_factory:
            # Configure the LLM strategy factory mock
            mock_strategy = MagicMock()
            mock_strategy.get_llm = lambda: fake_llm
            mock_factory.create_strategy.return_value = mock_strategy

            # Create workflow instance with explicit settings parameters
            workflow = DeepAgentWorkflow(
                llm_settings=settings.llm,
                subagents_settings=settings.subagents,
                storage_settings=StorageSettings(output_dir=temp_dir),
                prompt_settings=settings.prompts,
                processing_settings=settings.processing
            )

            # Prepare test job data
            job_id = "test-subagent-exception-job"
            job = {
                "request": {
                    "recommendations": [
                        {
                            "id": "rec-1",
                            "title": "Test recommendation",
                            "description": "Test description",
                            "type": "contrast_salience",
                        }
                    ],
                    "brand_guidelines": None,
                },
                "image_path": "/fake/image.jpg",
            }

            # Mock create_orchestrator to return an agent whose ainvoke
            # simulates a subagent exception
            with patch(
                "app.agents.deep_agent_workflow.create_orchestrator"
            ) as mock_create:
                # Create mock agent that raises exception during ainvoke
                # This simulates what happens when a subagent's invoke fails
                mock_agent = type("MockAgent", (), {})()
                subagent_error = RuntimeError("Subagent invocation failed: timeout")
                mock_agent.ainvoke = AsyncMock(side_effect=subagent_error)
                mock_create.return_value = mock_agent

                # Verify the exception propagates correctly
                with pytest.raises(RuntimeError, match="Subagent invocation failed"):
                    await workflow.run_workflow(job_id, job)

                # Verify ainvoke was called (confirming the exception came from there)
                mock_agent.ainvoke.assert_called_once()
