"""Example script demonstrating how to use the DeepAgentWorkflow.

This script shows how to use the DeepAgentWorkflow class to process image editing
jobs using the Deep Agents framework. The workflow orchestrates multiple tools
(analyze_recommendation, build_prompt, execute_edit, evaluate_variant) to generate
image variants based on recommendations and brand guidelines.
"""

import asyncio
import logging
from app.config.settings import settings
from app.agents.deep_agent_workflow import DeepAgentWorkflow
from app.models.schemas import BrandGuidelines, ProcessRequest, Recommendation

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.logging.level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    """Example usage of DeepAgentWorkflow.process_job()."""
    # Initialize the DeepAgentWorkflow
    workflow = DeepAgentWorkflow()

    # Define the image path
    image_path = "data/input/creative_1.png"

    # Example 1: Basic job with a single recommendation
    print("=" * 60)
    print("Example 1: Basic job with a single recommendation")
    print("=" * 60)

    job_id_1 = "job-001"
    job_1 = {
        "request": ProcessRequest(
            recommendations=[
                Recommendation(
                    id="rec-001",
                    text="Make the image brighter and more vibrant with enhanced colors",
                    priority=3,
                    category="color",
                )
            ]
        ),
        "image_path": image_path,
    }

    result_1 = await workflow.process_job(job_id=job_id_1, job=job_1)
    print(f"Job ID: {result_1['job_id']}")
    print(f"Status: {result_1['status']}")
    print(f"Variants: {result_1['variants']}")

    # Example 2: Job with multiple recommendations
    print("\n" + "=" * 60)
    print("Example 2: Job with multiple recommendations")
    print("=" * 60)

    job_id_2 = "job-002"
    job_2 = {
        "request": ProcessRequest(
            recommendations=[
                Recommendation(
                    id="rec-002",
                    text="Add a professional gradient background",
                    priority=4,
                    category="background",
                ),
                Recommendation(
                    id="rec-003",
                    text="Increase contrast and sharpness",
                    priority=2,
                    category="enhancement",
                ),
                Recommendation(
                    id="rec-004",
                    text="Make the text more prominent and readable",
                    priority=5,
                    category="text",
                ),
            ]
        ),
        "image_path": image_path,
    }

    result_2 = await workflow.process_job(job_id=job_id_2, job=job_2)
    print(f"Job ID: {result_2['job_id']}")
    print(f"Status: {result_2['status']}")
    print(f"Number of variants generated: {len(result_2['variants'])}")
    for variant in result_2["variants"]:
        print(
            f"  - Recommendation {variant['recommendation_id']}: "
            f"score={variant['evaluation_score']:.2f}, "
            f"iterations={variant['iterations']}"
        )

    # Example 3: Job with brand guidelines
    print("\n" + "=" * 60)
    print("Example 3: Job with brand guidelines")
    print("=" * 60)

    job_id_3 = "job-003"
    job_3 = {
        "request": ProcessRequest(
            recommendations=[
                Recommendation(
                    id="rec-005",
                    text="Apply a modern, professional color scheme",
                    priority=4,
                    category="color",
                )
            ],
            brand_guidelines=BrandGuidelines(
                primary_colors=["#1a73e8", "#34a853", "#ea4335"],
                do_not_use_colors=["#ff0000", "#00ff00"],
                additional_rules=[
                    "Maintain clean, minimalist aesthetic",
                    "Ensure good contrast for accessibility",
                    "Use rounded corners for UI elements",
                ],
            ),
        ),
        "image_path": image_path,
    }

    result_3 = await workflow.process_job(job_id=job_id_3, job=job_3)
    print(f"Job ID: {result_3['job_id']}")
    print(f"Status: {result_3['status']}")
    print(f"Variants: {result_3['variants']}")

    # Example 4: Job with image URL (if pre-uploaded)
    print("\n" + "=" * 60)
    print("Example 4: Job with image URL")
    print("=" * 60)

    job_id_4 = "job-004"
    job_4 = {
        "request": ProcessRequest(
            recommendations=[
                Recommendation(
                    id="rec-006",
                    text="Optimize for social media sharing",
                    priority=3,
                    category="composition",
                )
            ],
            image_id="pre-uploaded-image-123",
        ),
        "image_path": image_path,
        "image_url": "https://example.com/images/creative_1.png",
    }

    result_4 = await workflow.process_job(job_id=job_id_4, job=job_4)
    print(f"Job ID: {result_4['job_id']}")
    print(f"Status: {result_4['status']}")
    print(f"Input image URL: {result_4['input_image_url']}")
    print(f"Variants: {result_4['variants']}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
