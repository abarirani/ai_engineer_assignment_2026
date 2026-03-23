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

    # Example 2: Edit with higher priority (better quality, slower)
    print("\nExample 2: Edit with priority 5 (highest quality)")
    result = execute_edit(
        prompt="Add a professional gradient background",
        image_path=image_path,
        priority=5,
    )
    print(f"Result: {result}")

    # Example 3: Edit with lower priority (faster, lower quality)
    print("\nExample 3: Edit with priority 1 (fastest)")
    result = execute_edit(
        prompt="Slightly increase contrast",
        image_path=image_path,
        priority=1,
    )
    print(f"Result: {result}")

    # Example 4: Handling the result
    print("\nExample 4: Proper result handling")
    result = execute_edit(
        prompt="Make the text more prominent",
        image_path=image_path,
        priority=3,
    )

    if result["success"]:
        print("Edit successful!")
        print(f"Output image saved to: {result['image_path']}")
        if result["metadata"]:
            print(f"Metadata: {result['metadata']}")
    else:
        print(f"Edit failed: {result['error']}")


if __name__ == "__main__":
    main()
