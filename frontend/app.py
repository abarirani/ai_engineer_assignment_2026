"""Streamlit frontend for the AI Image Processing Application."""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

from database import init_database, save_job, update_job_status, get_all_jobs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = st.secrets.get("api.api_base_url", "http://localhost:5050/api/v1")


def get_recommendation_types() -> List[str]:
    """Get available recommendation types."""
    return [
        "contrast_salience",
        "composition",
        "colour_mood",
        "copy_messaging",
    ]


def get_recommendation_type_label(rec_type: str) -> str:
    """Get human-readable label for recommendation type."""
    labels = {
        "contrast_salience": "Contrast & Salience",
        "composition": "Composition",
        "colour_mood": "Colour & Mood",
        "copy_messaging": "Copy & Messaging",
    }
    return labels.get(rec_type, rec_type)


def add_recommendation() -> None:
    """Add a new recommendation to session state."""
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []

    st.session_state.recommendations.append(
        {
            "id": f"rec_{len(st.session_state.recommendations) + 1}",
            "title": "",
            "description": "",
            "type": "contrast_salience",
        }
    )


def remove_recommendation(index: int) -> None:
    """Remove a recommendation by index."""
    if "recommendations" in st.session_state:
        st.session_state.recommendations.pop(index)


def edit_recommendation(index: int, field: str, value: str) -> None:
    """Edit a specific field of a recommendation."""
    if "recommendations" in st.session_state and index < len(
        st.session_state.recommendations
    ):
        st.session_state.recommendations[index][field] = value


def submit_job() -> Optional[str]:
    """Submit a job to the API and return the job ID."""
    if (
        "recommendations" not in st.session_state
        or len(st.session_state.recommendations) == 0
    ):
        st.error("Please add at least one recommendation.")
        return None

    if (
        "uploaded_file" not in st.session_state
        or st.session_state.uploaded_file is None
    ):
        st.error("Please upload an image.")
        return None

    # Build recommendations list
    recommendations = []
    for rec in st.session_state.recommendations:
        if rec["title"].strip() and rec["description"].strip():
            recommendations.append(rec)
        else:
            st.warning(
                f"Recommendation '{rec['title']}' is incomplete and will be skipped."
            )

    if len(recommendations) == 0:
        st.error("Please complete at least one recommendation.")
        return None

    # Build brand guidelines
    brand_guidelines = {}
    if st.session_state.protected_regions:
        brand_guidelines["protected_regions"] = (
            st.session_state.protected_regions.split("\n")
        )
    if st.session_state.typography:
        brand_guidelines["typography"] = st.session_state.typography
    if st.session_state.aspect_ratio:
        brand_guidelines["aspect_ratio"] = st.session_state.aspect_ratio
    if st.session_state.brand_elements:
        brand_guidelines["brand_elements"] = st.session_state.brand_elements

    if not brand_guidelines:
        brand_guidelines = None

    # Submit to API
    url = f"{API_BASE_URL}/process"
    files = {
        "image": (
            st.session_state.uploaded_file.name,
            st.session_state.uploaded_file.getvalue(),
            st.session_state.uploaded_file.type,
        )
    }
    data = {
        "recommendations": json.dumps(recommendations),
        "brand_guidelines": json.dumps(brand_guidelines) if brand_guidelines else "",
    }

    # Log the request
    logger.info(f"Submitting job to API: {url}")
    logger.info(f"Image file: {st.session_state.uploaded_file.name}")
    logger.info(f"Recommendations: {json.dumps(recommendations, indent=2)}")
    logger.info(
        f"Brand guidelines: {json.dumps(brand_guidelines, indent=2) if brand_guidelines else 'None'}"
    )

    try:
        response = requests.post(url, files=files, data=data, timeout=30)
        logger.info(f"API response status: {response.status_code}")
        logger.info(f"API response body: {response.text}")
        if response.status_code == 202:
            result = response.json()
            job_id = result.get("job_id")
            logger.info(f"Job submitted successfully with ID: {job_id}")
            # Save job to database
            save_job(
                job_id=job_id,
                status="pending",
                recommendations=json.dumps(recommendations),
                brand_guidelines=(
                    json.dumps(brand_guidelines) if brand_guidelines else None
                ),
            )
            return job_id
        else:
            st.error(f"API error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to API: {e}")
        st.error(f"Failed to connect to API: {e}")
        return None


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a job from the API."""
    url = f"{API_BASE_URL}/status/{job_id}"
    logger.info(f"Getting job status from API: {url}")
    try:
        response = requests.get(url, timeout=10)
        logger.info(f"Job status API response status: {response.status_code}")
        logger.info(f"Job status API response body: {response.text}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.warning(f"Job not found: {job_id}")
            return None
        else:
            st.error(f"API error: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get job status: {e}")
        st.error(f"Failed to get job status: {e}")
        return None


def get_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Get the result of a completed job from the API."""
    url = f"{API_BASE_URL}/result/{job_id}"
    logger.info(f"Getting job result from API: {url}")
    try:
        response = requests.get(url, timeout=30)
        logger.info(f"Job result API response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Job result retrieved successfully for job: {job_id}")
            return result
        else:
            logger.warning(
                f"Failed to get job result: {response.status_code} - {response.text}"
            )
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get job result: {e}")
        st.error(f"Failed to get job result: {e}")
        return None


def display_recommendation_form(index: int, rec: Dict[str, str]) -> None:
    """Display a form for editing a single recommendation."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_input(
            "Title",
            value=rec["title"],
            key=f"rec_title_{index}",
            placeholder="Enter recommendation title",
        )
    with col2:
        st.selectbox(
            "Type",
            options=get_recommendation_types(),
            index=get_recommendation_types().index(rec["type"]),
            key=f"rec_type_{index}",
            format_func=get_recommendation_type_label,
        )

    st.text_area(
        "Description",
        value=rec["description"],
        key=f"rec_desc_{index}",
        placeholder="Enter detailed description of the recommendation",
        height=100,
    )

    # Update session state from form values
    edit_recommendation(index, "title", st.session_state.get(f"rec_title_{index}", ""))
    edit_recommendation(index, "type", st.session_state.get(f"rec_type_{index}", ""))
    edit_recommendation(
        index, "description", st.session_state.get(f"rec_desc_{index}", "")
    )

    # Remove button
    if st.button("Remove", key=f"remove_rec_{index}"):
        remove_recommendation(index)
        st.rerun()


def display_brand_guidelines_form() -> None:
    """Display the brand guidelines form."""
    st.header("Brand Guidelines")
    st.info("Specify brand guidelines that should be respected during image editing.")

    col1, col2 = st.columns(2)

    with col1:
        st.session_state.protected_regions = st.text_area(
            "Protected Regions",
            value=st.session_state.get("protected_regions", ""),
            key="brand_protected_regions",
            placeholder="List regions or elements that should not be modified (one per line)",
            height=100,
        )
        st.session_state.typography = st.text_area(
            "Typography Guidelines",
            value=st.session_state.get("typography", ""),
            key="brand_typography",
            placeholder="Typography guidelines for text elements",
            height=100,
        )

    with col2:
        st.session_state.aspect_ratio = st.text_input(
            "Aspect Ratio",
            value=st.session_state.get("aspect_ratio", ""),
            key="brand_aspect_ratio",
            placeholder="e.g., 16:9, 4:3, 1:1",
        )
        st.session_state.brand_elements = st.text_area(
            "Brand Elements",
            value=st.session_state.get("brand_elements", ""),
            key="brand_brand_elements",
            placeholder="Guidelines for brand elements visibility and placement",
            height=100,
        )


def display_job_status(job_id: str) -> None:
    """Display the current job status with progress bar."""
    status = get_job_status(job_id)

    if status is None:
        st.error("Job not found.")
        return

    # Update job status in database
    update_job_status(
        job_id=job_id,
        status=status["status"],
        progress=status.get("progress"),
        message=status.get("message"),
        error=status.get("error"),
    )

    status_map = {
        "pending": ("⏳ Pending", "secondary"),
        "processing": ("⚙️ Processing", "primary"),
        "completed": ("✅ Completed", "success"),
        "failed": ("❌ Failed", "error"),
    }

    status_label, status_type = status_map.get(
        status["status"], ("❓ Unknown", "secondary")
    )

    st.subheader(f"Job Status: {status_label}")

    if status["progress"] is not None:
        st.progress(status["progress"] / 100)

    if status["message"]:
        st.info(status["message"])

    if status["error"]:
        st.error(f"Error: {status['error']}")

    # Poll for updates if processing
    if status["status"] == "processing":
        st.markdown("*Polling for updates...*")
        time.sleep(2)
        st.rerun()

    # Show results if completed
    if status["status"] == "completed":
        display_job_results(job_id)


def display_job_results(job_id: str) -> None:
    """Display the results of a completed job."""
    st.success("Job completed! Showing results...")

    result = get_job_result(job_id)

    if result is None:
        st.error("Failed to retrieve job results.")
        return

    # Update job status in database with result data
    update_job_status(
        job_id=job_id,
        status="completed",
        result_data=json.dumps(result),
    )

    # Display input image
    if result.get("input_image_url"):
        st.subheader("Input Image")
        st.image(result["input_image_url"])

    # Display variants
    if result.get("variants"):
        st.subheader("Generated Variants")

        for variant in result["variants"]:
            with st.expander(
                f"Variant for: {variant.get('recommendation_id', 'Unknown')}"
            ):
                st.image(variant["variant_url"])
                st.metric("Evaluation Score", f"{variant['evaluation_score']:.2f}/10")
                st.metric("Iterations", variant["iterations"])

    # Display report content
    if result.get("report_content"):
        with st.expander("Report Details"):
            st.json(result["report_content"])

    # Display messages
    if result.get("messages_content"):
        with st.expander("Processing Messages"):
            st.markdown(result["messages_content"])


def display_job_history() -> None:
    """Display the job history from the database with latest status from server."""
    st.header("Job History")

    jobs = get_all_jobs()

    if not jobs:
        st.info("No jobs found in the database.")
        return

    for job in jobs:
        # Fetch latest status from server
        latest_status = get_job_status(job["job_id"])

        # Use server status if available, otherwise fall back to database status
        display_status = latest_status if latest_status else job

        # Update local database with latest status if server returned data
        if latest_status:
            update_job_status(
                job_id=job["job_id"],
                status=latest_status["status"],
                progress=latest_status.get("progress"),
                message=latest_status.get("message"),
                error=latest_status.get("error"),
            )

        # Use the latest status for display
        status = display_status

        with st.expander(
            f"Job {job['job_id']} - {status['status'].upper()}",
            expanded=False,
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Status", status["status"].upper())
                st.metric("Submitted", job["submitted_at"])
                if job["completed_at"]:
                    st.metric("Completed", job["completed_at"])
            with col2:
                if status.get("progress") is not None:
                    st.metric("Progress", f"{status['progress']}%")
                if status.get("message"):
                    st.info(status["message"])
                if status.get("error"):
                    st.error(status["error"])

            if job["recommendations"]:
                with st.expander("Recommendations"):
                    st.json(json.loads(job["recommendations"]))

            if job["brand_guidelines"]:
                with st.expander("Brand Guidelines"):
                    st.json(json.loads(job["brand_guidelines"]))

            if job["result_data"]:
                with st.expander("Result Data"):
                    st.json(json.loads(job["result_data"]))

            st.divider()


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="AI Image Processing",
        page_icon="🎨",
        layout="wide",
    )

    # Initialize database
    init_database()

    st.title("🎨 AI Image Processing Application")
    st.markdown(
        """
        Upload an image and provide visual recommendations to generate edited variants.
        The system will process your image while respecting your brand guidelines.
        """
    )

    # Initialize session state
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None
    if "job_id" not in st.session_state:
        st.session_state.job_id = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "New Processing"

    # Sidebar for navigation
    with st.sidebar:
        st.header("Navigation")
        pages = ["New Processing", "Job Status", "Job History"]
        st.session_state.current_page = st.radio(
            "Go to",
            pages,
            index=pages.index(st.session_state.current_page),
        )

    # Main content based on current page
    if st.session_state.current_page == "Job History":
        display_job_history()
    elif st.session_state.current_page == "Job Status":
        if st.session_state.job_id:
            display_job_status(st.session_state.job_id)
        else:
            st.info("No active job. Start a new processing to track job status.")
    elif st.session_state.current_page == "New Processing":
        # Clear job_id when switching to New Processing to ensure clean state
        if st.session_state.job_id is not None:
            st.session_state.job_id = None
            st.rerun()
        # Image upload
        st.header("1. Upload Image")
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=["jpg", "jpeg", "png", "gif", "bmp"],
            help="Supported formats: JPG, JPEG, PNG, GIF, BMP",
        )
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            st.success(f"Uploaded: {uploaded_file.name}")
            # Display preview
            st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

        st.divider()

        # Recommendations section
        st.header("2. Add Recommendations")
        st.info(
            "Add visual recommendations that describe how you want the image to be edited."
        )

        # Display existing recommendations
        for i, rec in enumerate(st.session_state.recommendations):
            with st.container():
                st.markdown(f"**Recommendation {i + 1}**")
                display_recommendation_form(i, rec)
                st.divider()

        # Add new recommendation button
        st.button(
            "+ Add Recommendation",
            on_click=add_recommendation,
            use_container_width=True,
        )

        st.divider()

        # Brand guidelines section
        display_brand_guidelines_form()

        st.divider()

        # Submit button
        st.header("3. Submit for Processing")
        if st.button("Submit Job", type="primary", use_container_width=True):
            job_id = submit_job()
            if job_id:
                st.session_state.job_id = job_id
                st.rerun()


if __name__ == "__main__":
    main()
