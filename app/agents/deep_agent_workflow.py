"""Simplified Deep Agents workflow for image editing.

This module provides a simplified agent-based workflow using LangChain's
Deep Agents library, replacing the complex LangGraph multi-agent setup.

Key simplifications:
- Single agent instead of orchestrator + worker + synthesizer nodes
- Built-in task planning via write_todos tool
- Built-in subagent spawning for parallel variant generation
- Python functions as tools instead of verbose JSON schemas
- Filesystem-based context management instead of TypedDict state schemas
"""

import logging
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader

from app.agents.orchestrator import create_orchestrator
from app.config.settings import settings
from app.services.llm.strategy_factory import LLMStrategyFactory
from app.agents.tools import execute_edit, evaluate_variant  # noqa: F401
from app.agents.reporting import generate_report

logger = logging.getLogger(__name__)


class DeepAgentWorkflow:
    """Workflow using Deep Agents for image editing.

    Attributes:
        _llm_strategy: The LLM strategy for model invocation.
    """

    def __init__(self):
        """Initialize the Deep Agent workflow.

        Args:
            llm_strategy: The LLM strategy for model invocation.
        """
        self._llm_strategy = LLMStrategyFactory.create_strategy(settings.llm)
        logger.info("DeepAgentWorkflow initialized")

    async def process_job(self, job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a job using the Deep Agent.

        This method orchestrates the complete image editing workflow:
        1. Prepare the task description for the agent
        2. Invoke the Deep Agent with the task
        3. Format and return the results

        Args:
            job_id: Unique job identifier.
            job: Job data containing request and image path.

        Returns:
            Workflow result dictionary containing:
            - job_id: The job identifier
            - status: Job completion status
            - input_image_url: URL of the input image
            - variants: List of generated variants with evaluation scores
        """
        # Build the system prompt
        system_prompt = self._build_system_prompt()

        # Build the user message with job details
        user_message = self._build_user_message(job)

        # Create the Deep Agent with our tools
        subagents = settings.subagents.to_list()
        for subagent in subagents:
            if subagent["model"] == "":
                subagent["model"] = self._llm_strategy.get_llm()
            for i, tool in enumerate(subagent["tools"]):
                subagent["tools"][i] = globals()[tool]

        agent = create_orchestrator(
            tools=[],
            system_prompt=system_prompt,
            subagents=subagents,
            model=self._llm_strategy.get_llm(),
        )

        logger.info(f"Executing Deep Agent workflow for job {job_id}")

        # Invoke the agent
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_message}]}
        )

        generate_report(result["messages"])

        # Format the result
        formatted_result = self._format_result(job_id, job, result)

        logger.info(f"Deep Agent workflow completed for job {job_id}")
        return formatted_result

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the Deep Agent.

        Returns:
            System prompt string.
        """
        prompt_path = Path(settings.prompts.deep_agent_system)
        return prompt_path.read_text()

    def _build_user_message(self, job: Dict[str, Any]) -> str:
        """Build the user message for the Deep Agent.

        Args:
            job: Job data containing request and image path.

        Returns:
            User message string.
        """
        request = job["request"]
        image_path = job["image_path"]

        recommendations_text = "\n".join(
            f"- [{rec.priority}] {rec.text}" for rec in request.recommendations
        )

        brand_guidelines_text = ""
        if request.brand_guidelines:
            bg = request.brand_guidelines
            brand_guidelines_text = "\n".join(
                [
                    "Brand Guidelines:",
                    (
                        f"- Primary colors: {bg.primary_colors}"
                        if bg.primary_colors
                        else ""
                    ),
                    (
                        f"- Avoid colors: {bg.do_not_use_colors}"
                        if bg.do_not_use_colors
                        else ""
                    ),
                ]
                + [f"- {rule}" for rule in bg.additional_rules or []]
            )
            brand_guidelines_text = "\n".join(filter(None, brand_guidelines_text))

        template_path = Path(settings.prompts.deep_agent_user_message)
        env = Environment(loader=FileSystemLoader(str(template_path.parent)))
        template = env.get_template(template_path.name)
        return template.render(
            image_path=image_path,
            recommendations_text=recommendations_text,
            brand_guidelines_text=brand_guidelines_text,
        )

    def _format_result(
        self, job_id: str, job: Dict[str, Any], agent_result: Any
    ) -> Dict[str, Any]:
        """Format the agent result into the expected response format.

        Args:
            job_id: Unique job identifier.
            job: Original job data.
            agent_result: Result from the Deep Agent.

        Returns:
            Formatted result dictionary.
        """
        # Extract variants from agent result
        # The agent should return structured data with variants
        variants = []

        # For now, return a basic structure
        # In production, you'd parse the agent's output more carefully
        for rec in job["request"].recommendations:
            variants.append(
                {
                    "recommendation_id": rec.id,
                    "variant_url": "",  # Would be populated from agent output
                    "evaluation_score": 0.0,
                    "iterations": 1,
                }
            )

        return {
            "job_id": job_id,
            "status": "completed",
            "input_image_url": job.get("image_url"),
            "variants": variants,
        }
