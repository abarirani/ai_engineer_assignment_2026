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
import json
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader

from app.agents.orchestrator import create_orchestrator
from app.config.settings import settings
from app.services.llm.strategy_factory import LLMStrategyFactory
from app.agents.tools import (  # noqa: F401
    execute_edit,
    evaluate_variant,
    generate_report,
)

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

    async def run_workflow(self, job_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
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
            tools=[generate_report],
            system_prompt=system_prompt,
            subagents=subagents,
            model=self._llm_strategy.get_llm(),
        )

        logger.info(f"Executing Deep Agent workflow for job {job_id}")

        # Invoke the agent
        config = {"configurable": {"job_id": f"{job_id}"}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_message}]}, config=config
        )

        self._generate_markdown_from_messages(result["messages"], job_id, settings.storage.output_dir)

        logger.info(f"Deep Agent workflow completed for job {job_id}")
        return result

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
            f"- [{rec.type.value}] {rec.title}: {rec.description}"
            for rec in request.recommendations
        )

        brand_guidelines_text = ""
        if request.brand_guidelines:
            bg = request.brand_guidelines
            guidelines_parts = ["Brand Guidelines:"]

            if bg.protected_regions:
                guidelines_parts.append("Protected Regions:")
                guidelines_parts.extend(
                    f"- {region}" for region in bg.protected_regions
                )

            if bg.typography:
                guidelines_parts.append(f"Typography: {bg.typography}")

            if bg.aspect_ratio:
                guidelines_parts.append(f"Aspect Ratio: {bg.aspect_ratio}")

            if bg.brand_elements:
                guidelines_parts.append(f"Brand Elements: {bg.brand_elements}")

            brand_guidelines_text = "\n".join(guidelines_parts)

        template_path = Path(settings.prompts.deep_agent_user_message)
        env = Environment(loader=FileSystemLoader(str(template_path.parent)))
        template = env.get_template(template_path.name)
        return template.render(
            image_path=image_path,
            recommendations_text=recommendations_text,
            brand_guidelines_text=brand_guidelines_text,
        )

    def _generate_markdown_from_messages(self, messages, job_id: str, output_dir: str):
        """Format messages and write to a markdown file in the output job folder.

        Args:
            messages: List of messages to format.
            job_id: The job identifier used to create the output folder.
            output_dir: directory to store the markdown file.
        """
        def format_message_content(message):
            """Convert message content to displayable string."""
            parts = []
            tool_calls_processed = False

            # Handle main content
            if isinstance(message.content, str):
                parts.append(message.content)
            elif isinstance(message.content, list):
                # Handle complex content like tool calls (Anthropic format)
                for item in message.content:
                    if item.get("type") == "text":
                        parts.append(item["text"])
                    elif item.get("type") == "tool_use":
                        parts.append(f"\n🔧 Tool Call: {item['name']}")
                        parts.append(f"   Args: {json.dumps(item['input'], indent=2)}")
                        parts.append(f"   ID: {item.get('id', 'N/A')}")
                        tool_calls_processed = True
            else:
                parts.append(str(message.content))

            # Handle tool calls attached to the message (OpenAI format) - only if not already processed
            if (
                not tool_calls_processed
                and hasattr(message, "tool_calls")
                and message.tool_calls
            ):
                for tool_call in message.tool_calls:
                    parts.append(f"\n🔧 Tool Call: {tool_call['name']}")
                    parts.append(f"   Args: {json.dumps(tool_call['args'], indent=2)}")
                    parts.append(f"   ID: {tool_call['id']}")

            return "\n".join(parts)

        output_dir = Path(output_dir) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        markdown_lines = []

        for m in messages:
            msg_type = m.__class__.__name__.replace("Message", "")
            content = format_message_content(m)

            # Map message types to markdown headers
            if msg_type == "Human":
                markdown_lines.append("## 🧑 Human\n")
            elif msg_type == "Ai":
                markdown_lines.append("## 🤖 Assistant\n")
            elif msg_type == "Tool":
                markdown_lines.append("## 🔧 Tool Output\n")
            else:
                markdown_lines.append(f"## 📝 {msg_type}\n")

            markdown_lines.append(content)
            markdown_lines.append("\n---\n")

        # Write to markdown file
        output_file = output_dir / "messages.md"
        output_file.write_text("\n".join(markdown_lines))
