"""Unit tests for WorkflowService exception handling.

This module tests that exceptions from agent.ainvoke() propagate correctly
through the workflow service, resulting in jobs being marked as FAILED.
"""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile

from langchain_community.chat_models import FakeListChatModel

from app.services.workflow_service import WorkflowService
from app.models.schemas import JobStatusEnum
from app.config.settings import (
    ProcessingSettings,
    DatabaseSettings,
    StorageSettings,
    LLMSettings,
    SubagentsSettings,
    PromptsSettings,
)


@pytest.mark.asyncio
async def test_process_job_agent_invoke_exception_propagates():
    """Test that an exception from agent.ainvoke() propagates correctly through
    run_workflow() to process_job(), resulting in the job being marked as FAILED.

    Exception handling chain verified:
    1. agent.ainvoke() raises an exception
    2. DeepAgentWorkflow.run_workflow() propagates the exception
    3. WorkflowService.process_job() catches it in try/except (line 170-172)
    4. JobDatabase.fail_job() is called with the error message
    5. Job status is updated to FAILED with the error message

    This test uses minimal mocking:
    - Real JobDatabase to verify actual job status update in SQLite
    - Real SemaphoreManager to ensure proper acquire/release behavior
    - Real settings objects (ProcessingSettings, DatabaseSettings, StorageSettings)
    - FakeListChatModel (LangChain's mock LLM) to avoid API key requirements
    - Mocked create_orchestrator to inject controlled exception
    - Mocked observability functions to avoid file I/O side effects
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_jobs.db"

        # Create real settings objects instead of mocking
        processing_settings = ProcessingSettings(max_concurrent_jobs=1)
        database_settings = DatabaseSettings(path=str(db_path))
        storage_settings = StorageSettings(output_dir=temp_dir)
        llm_settings = LLMSettings()
        subagents_settings = SubagentsSettings()
        prompt_settings = PromptsSettings()

        # Use LangChain's FakeListChatModel
        mock_llm = FakeListChatModel(responses=[])

        mock_llm_strategy = MagicMock()
        mock_llm_strategy.get_llm = MagicMock(return_value=mock_llm)

        with patch("app.agents.deep_agent_workflow.LLMStrategyFactory") as mock_factory:
            mock_factory.create_strategy = MagicMock(return_value=mock_llm_strategy)

            service = WorkflowService(
                storage_settings=storage_settings,
                db_settings=database_settings,
                processing_settings=processing_settings,
                llm_settings=llm_settings,
                subagents_settings=subagents_settings,
                prompt_settings=prompt_settings,
            )
            service._db.create_job(
                "test-job",
                {
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
                "/fake/image.jpg",
                "/images/test.jpg",
            )

            # Patch at agent creation level to inject exception
            with patch(
                "app.agents.deep_agent_workflow.create_orchestrator"
            ) as mock_create:
                mock_agent = MagicMock()
                mock_agent.ainvoke = AsyncMock(
                    side_effect=Exception("Agent invocation failed")
                )
                mock_create.return_value = mock_agent

                with (
                    patch("app.services.workflow_service.init_observability_for_job"),
                    patch("app.services.workflow_service.flush_job_traces"),
                    patch("app.services.workflow_service.shutdown_job_observability"),
                ):

                    await service.process_job("test-job")

                    job = service._db.get_job("test-job")
                    assert job["status"] == JobStatusEnum.FAILED
                    assert "Agent invocation failed" in job["error"]


@pytest.mark.asyncio
async def test_api_key_error_propagates_to_workflow_service():
    """Test that missing API key error propagates through WorkflowService.

    Exception handling chain verified:
    1. ChatOpenAI raises an error when OPENAI_API_KEY is missing (401 error)
    2. The error propagates through DeepAgentWorkflow.run_workflow()
    3. WorkflowService.process_job() catches it and marks job as FAILED

    Minimal mocking approach:
    - Real settings objects (ProcessingSettings, DatabaseSettings, etc.)
    - Real JobDatabase to verify actual job status updates
    - Real LLMStrategyFactory to create a real OpenAICompatibleStrategy
    - Only mock observability functions to avoid file I/O side effects
    - The real ChatOpenAI will raise an error when invoked without API key
    """
    # Ensure API key is NOT set (simulate missing API key)
    os.environ.pop("OPENAI_API_KEY", None)

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_jobs.db"

        # Create real settings objects
        processing_settings = ProcessingSettings(max_concurrent_jobs=1)
        database_settings = DatabaseSettings(path=str(db_path))
        storage_settings = StorageSettings(output_dir=temp_dir)
        llm_settings = LLMSettings(
            enabled=True,
            provider="openai_compatible",
            base_url="http://localhost:7878/v1",
            model_name="test-model",
            temperature=0.7,
        )
        subagents_settings = SubagentsSettings()
        prompt_settings = PromptsSettings()

        service = WorkflowService(
            storage_settings=storage_settings,
            db_settings=database_settings,
            processing_settings=processing_settings,
            llm_settings=llm_settings,
            subagents_settings=subagents_settings,
            prompt_settings=prompt_settings,
        )

        # Create a test job
        service._db.create_job(
            "test-api-key-job",
            {
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
            "/fake/image.jpg",
            "/images/test.jpg",
        )

        with (
            patch(
                "app.services.workflow_service.init_observability_for_job"
            ),
            patch("app.services.workflow_service.flush_job_traces"),
            patch(
                "app.services.workflow_service.shutdown_job_observability"
            ),
        ):
            # Process the job - should fail with API key error
            # process_job -> run_workflow -> get_llm -> API key error
            # The real ChatOpenAI will be invoked and raise an error
            # which should result in job failing
            await service.process_job("test-api-key-job")

            # Verify the job was marked as FAILED
            job = service._db.get_job("test-api-key-job")
            assert job["status"] == JobStatusEnum.FAILED
            assert "OPENAI_API_KEY" in job["error"] or "api_key" in job["error"]
