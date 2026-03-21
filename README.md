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

To select a different environment, set the `APP_ENV` environment variable (default: `development`):

```bash
export APP_ENV=production
```

4. **Run the server:**

The application can be started using the module entry point, which automatically reads the server configuration from the YAML config files:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 5050
```

5. **Access the API documentation:**

- Swagger UI: http://localhost:5050/docs (development)
- ReDoc: http://localhost:5050/redoc (development)

## API Endpoints

### POST /api/v1/process

Submit an image with visual recommendations for processing.

**Request:**
- `image` (file): Image file to process (PNG, JPG, JPEG, WEBP)
- `recommendations` (array): List of recommendations with:
  - `id` (string): Unique identifier
  - `text` (string): Recommendation description
  - `priority` (int, 1-5): Priority level
  - `category` (string, optional): Category of recommendation
- `brand_guidelines` (object, optional): Brand guidelines including:
  - `primary_colors` (array): Primary brand colors (hex)
  - `secondary_colors` (array): Secondary brand colors (hex)
  - `fonts` (array): Approved font families
  - `logo_url` (string): URL to brand logo
  - `protected_regions` (array): Regions to protect
  - `do_not_use_colors` (array): Colors to avoid
  - `additional_rules` (array): Additional rules as text

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

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "created_at": "2026-03-20T10:00:00Z",
  "updated_at": "2026-03-20T10:00:05Z",
  "progress": 50,
  "message": "Generating variants..."
}
```

### GET /api/v1/result/{job_id}

Retrieve the complete result of a completed job.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "input_image_url": "/api/v1/images/filename.png",
  "variants": [],
  "audit_trail": [...],
  "created_at": "2026-03-20T10:00:00Z",
  "completed_at": "2026-03-20T10:00:30Z"
}
```
