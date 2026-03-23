"""Example script demonstrating how to use the DeepAgentWorkflow.

This script shows how to use the DeepAgentWorkflow class to process image editing
jobs using the Deep Agents framework. The workflow orchestrates multiple tools
(analyze_recommendation, build_prompt, execute_edit, evaluate_variant) to generate
image variants based on recommendations and brand guidelines.
"""

import asyncio
from app.utils import generate_unique_id
from app.agents.deep_agent_workflow import DeepAgentWorkflow
from app.models.schemas import BrandGuidelines, ProcessRequest, Recommendation, RecommendationType


async def main():
    """Example usage of DeepAgentWorkflow.process_job()."""
    # Initialize the DeepAgentWorkflow
    workflow = DeepAgentWorkflow()

    # Define the image path
    image_path = "data/input/creative_1.png"

    # Example 1: Basic job with a single recommendation
    print("=" * 60)
    print("Basic job with 3 recommendations and 1 brand guideline")
    print("=" * 60)

    job_id = generate_unique_id()
    job = {
        "request": ProcessRequest(
            recommendations=[
                Recommendation(
                    id="rec-002",
                    title="Add a professional gradient background",
                    description="Apply a subtle gradient background to enhance visual appeal and create depth",
                    type=RecommendationType.COLOUR_MOOD,
                ),
                Recommendation(
                    id="rec-003",
                    title="Increase contrast and sharpness",
                    description="Enhance image clarity by boosting contrast and applying selective sharpening",
                    type=RecommendationType.CONTRAST_SALIENCE,
                ),
                Recommendation(
                    id="rec-004",
                    title="Make the text more prominent and readable",
                    description="Improve text visibility through better contrast and typography adjustments",
                    type=RecommendationType.COPY_MESSAGING,
                ),
            ],
            brand_guidelines=BrandGuidelines(
                protected_regions=[
                    "Do not modify or remove the brand logo",
                    "Do not alter the model's face"
                ],
                typography="Maintain existing font style and hierarchy for all text elements",
                aspect_ratio="Maintain original aspect ratio (1572x1720)",
                brand_elements="Ensure logo remains visible and legible at all times"
            )
        ),
        "image_path": image_path,
    }

    result = await workflow.process_job(job_id=job_id, job=job)
    print(f"Job ID: {result['job_id']}")
    print(f"Status: {result['status']}")
    print(f"Number of variants generated: {len(result['variants'])}")
    for variant in result["variants"]:
        print(
            f"  - Recommendation {variant['recommendation_id']}: "
            f"score={variant['evaluation_score']:.2f}, "
            f"iterations={variant['iterations']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
