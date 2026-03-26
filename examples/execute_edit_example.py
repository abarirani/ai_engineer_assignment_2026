"""Example script demonstrating how to call the execute_edit function.

This script shows how to use the execute_edit function from the deep_agent_workflow
module to perform image editing operations using the FLUX.2 klein model.
"""

from langchain.tools import ToolRuntime
from langchain_core.runnables import RunnableConfig

from app.agents.tools import execute_edit
from app.utils import generate_unique_id


def create_tool_runtime(job_id: str = "example_job") -> ToolRuntime:
    """Create a ToolRuntime instance simulating LangChain tool calling.

    This function creates a ToolRuntime with the necessary parameters that would
    normally be provided by LangChain during tool invocation.

    Args:
        job_id: The job identifier for organizing output files.

    Returns:
        ToolRuntime: A configured ToolRuntime instance ready for use.
    """
    config = RunnableConfig(configurable={"job_id": job_id})
    tool_call_id = generate_unique_id()

    return ToolRuntime(
        state={},
        context={},
        config=config,
        stream_writer=None,
        tool_call_id=tool_call_id,
        store=None,
    )


def main():
    """Example usage of execute_edit function."""
    # Define the image path and editing prompt
    image_path = "data/input/creative_1.png"  # Path to your input image
    prompt = "Make the image brighter and more vibrant with enhanced colors"

    # Create a ToolRuntime instance simulating LangChain tool calling
    runtime = create_tool_runtime(job_id=generate_unique_id())

    # Example 1: Basic usage
    print("Example 1: Basic edit")
    result = execute_edit(
        prompt=prompt,
        image_path=image_path,
        runtime=runtime,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
