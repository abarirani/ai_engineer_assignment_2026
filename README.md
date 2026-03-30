# Visual Recommendations Agentic Workflow

A containerized, asynchronous backend service that implements a multi-agent workflow for generating visual recommendations on marketing creatives.

## Overview

This system processes input images, applies textual recommendations while respecting brand guidelines, and evaluates the results through an iterative generation-evaluation-refinement loop.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker

### Local Development

1. **Create and activate virtual environment:**

```bash
bash setup-venv.sh
source .venv/bin/activate
```

2. **Install dependencies (developement):**

```bash
pip install -e .[testing]
```

3. **Configure environment:**

The application uses YAML-based configuration files for managing different environments:
- `app/config/base.yaml` - Base configuration (common settings)
- `app/config/development.yaml` - Development environment overrides
- `app/config/production.yaml` - Production environment overrides

The following settings in [`app/config/development.yaml`](app/config/development.yaml) should be configured to point to an OpenAI-compatible endpoint:

| Setting | Description | Default | Recommended Value |
|---------|-------------|---------|------------------------------|
| `llm.provider` | LLM provider | `openai_compatible` | `openai_compatible` |
| `llm.base_url` | LLM API endpoint | `https://api.openai.com/v1` | Your LLM endpoint |
| `llm.model_name` | LLM model | `gpt-4o` | Your preferred model |
| `evaluation.base_url` | Evaluation API endpoint | `https://api.openai.com/v1` | Your evaluation endpoint |
| `evaluation.model_name` | Evaluation model | `gpt-4o` | Your preferred vision-LLM model |

The following environment variables must be set before running the backend (see [.env-example](.env.example)):

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM services | Required |
| `GEMINI_API_KEY` | Gemini API key for Image editing and Vision-LLM services | Required |

4. **Run the backend:**

The backend can be started using the module entry point, which automatically reads the server configuration from the YAML config files:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 5050
```

5. **Access the API documentation:**

- Swagger UI: http://localhost:5050/docs (development)
- ReDoc: http://localhost:5050/redoc (development)

6. **Run the frontend:**

Follow instructions from the [REARME](frontend/README.md).

## API Endpoints

### POST /api/v1/process

Submit an image with visual recommendations for processing. The system will generate variants based on the recommendations while respecting brand guidelines.

**Request:**
- `image` (file, required): Image file to process (PNG, JPG, JPEG, WEBP)
- `recommendations` (string, required): JSON string containing an array of recommendations, each with:
  - `id` (string): Unique identifier for the recommendation
  - `title` (string): Title/summary of the recommendation
  - `description` (string): Detailed description of the recommendation
  - `type` (string): Type of recommendation - one of: `contrast_salience`, `composition`, `colour_mood`, `copy_messaging`
- `brand_guidelines` (string, optional): JSON string containing brand guidelines:
  - `protected_regions` (array, optional): List of regions or elements that should not be modified
  - `typography` (string, optional): Typography guidelines for text elements
  - `aspect_ratio` (string, optional): Required aspect ratio to maintain
  - `brand_elements` (string, optional): Guidelines for brand elements visibility and placement

**Response:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Job queued for processing"
}
```

### GET /api/v1/status/{job_id}

Check the current status of a processing job.

**Path Parameters:**
- `job_id` (string): Unique job identifier

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "created_at": "2026-03-20T10:00:00Z",
  "updated_at": "2026-03-20T10:00:05Z",
  "progress": 50,
  "message": "Generating variants...",
  "error": null
}
```

**Status Values:**
- `pending`: Job is queued for processing
- `processing`: Job is currently being processed
- `completed`: Job has finished successfully
- `failed`: Job failed with an error

### GET /api/v1/result/{job_id}

Retrieve the complete result of a completed job including generated variants and audit trail.

**Path Parameters:**
- `job_id` (string): Unique job identifier

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "input_image_url": "/images/abc-123/upload/input.png",
  "variants": [
    {
      "recommendation_id": "rec-1",
      "variant_url": "/images/abc-123/variant/output.png",
      "evaluation_score": 8.5,
      "iterations": 2
    }
  ],
  "report_content": {...},
  "messages_content": "...",
  "trace_content": {...},
  "created_at": "2026-03-20T10:00:00Z",
  "completed_at": "2026-03-20T10:00:30Z"
}
```

**Variant Fields:**
- `recommendation_id` (string): Original recommendation ID
- `variant_url` (string): URL to the generated variant image
- `evaluation_score` (float): Quality evaluation score (0-10 scale)
- `iterations` (int): Number of iterations performed

### GET /api/v1/images/{job_id}/{image_type}/{filename}

Retrieve an image by job ID, type, and filename.

**Path Parameters:**
- `job_id` (string): The job ID associated with the image
- `image_type` (string): Type of image - `upload` for input images, `variant` for generated variants
- `filename` (string): The filename of the image

**Response:**
- Returns the image file (PNG, JPG, JPEG, WEBP)

**Example:**
```
GET /api/v1/images/abc-123/upload/input.png
GET /api/v1/images/abc-123/variant/output.png
```

## Docker Compose Deployment

### Prerequisites

- Docker
- Docker Compose

### Quick Start

1. **Set environment variables:**

Ensure required [environment variables](#local-development) are set before performing docker compose deployment:

2. **Build and start services:**

```bash
docker-compose up --build
```

3. **Access the application:**

- Frontend (Streamlit): http://localhost:8501
- Backend API: http://localhost:5050
- API Documentation: http://localhost:5050/docs

### Docker Compose Commands

```bash
# Start services
docker-compose up

# Start services in detached mode
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild and restart
docker-compose up --build --force-recreate

# Execute commands in container
docker-compose exec backend bash
docker-compose exec frontend bash
```
