"""Example script demonstrating how to call the evaluate_variant function.

This script shows how to use the evaluate_variant tool to evaluate an image
variant using a multimodal LLM critic.
"""

from app.agents.tools import evaluate_variant


def main():
    """Example usage of evaluate_variant function."""
    # Path to the variant image you want to evaluate
    variant_path = "output/edited_1774261020.png"

    # Evaluation prompt containing all context for the evaluation
    # This should include:
    # - The original recommendation/brand guidelines
    # - What aspects to evaluate (e.g., color accuracy, composition, style)
    # - Any specific criteria or constraints
    evaluation_prompt = """
    Evaluate this image variant based on the following criteria:

    Brand Guidelines:
    - Primary color: #FF5733 (orange-red)
    - Style: Modern, minimalist, professional
    - Target audience: Tech-savvy professionals aged 25-40

    Evaluation Criteria:
    1. Color accuracy: Does the image use the brand colors appropriately?
    2. Composition: Is the layout balanced and visually appealing?
    3. Style consistency: Does it match the modern, minimalist aesthetic?
    4. Professional quality: Is it suitable for professional use?

    Please provide a score from 0.0 to 1.0 and detailed feedback.
    """

    # Call the evaluate_variant function
    result = evaluate_variant(variant_path=variant_path, prompt=evaluation_prompt)

    # Process the result
    print("Evaluation Result:")
    print("===========================")
    print(result)


if __name__ == "__main__":
    main()
