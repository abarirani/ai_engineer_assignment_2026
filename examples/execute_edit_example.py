"""Example script demonstrating how to call the execute_edit function.

This script shows how to use the execute_edit function from the deep_agent_workflow
module to perform image editing operations using the FLUX.2 klein model.
"""

from app.agents.deep_agent_workflow import execute_edit


def main():
    """Example usage of execute_edit function."""
    # Define the image path and editing prompt
    image_path = "data/input/creative_1.png"  # Path to your input image
    prompt = "Make the image brighter and more vibrant with enhanced colors"

    # Example 1: Basic usage with default priority (1)
    print("Example 1: Basic edit with default priority")
    result = execute_edit(
        prompt=prompt,
        image_path=image_path,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
