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

## Docker Compose Deployment

### Prerequisites

- Docker
- Docker Compose

### Quick Start

1. **Copy environment file and configure:**

```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

2. **Build and start services:**

```bash
docker-compose up --build
```

3. **Access the application:**

- Frontend (Streamlit): http://localhost:8501
- Backend API: http://localhost:5050
- API Documentation: http://localhost:5050/docs

### Development Mode

For development with hot-reload:

```bash
docker-compose up --build
```

The `docker-compose.override.yml` file enables:
- Source code volume mounting for hot-reload
- Development environment configuration

### Production Deployment

For production deployment:

```bash
docker-compose --profile production up --build -d
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | development |
| `OPENAI_API_KEY` | OpenAI API key for LLM services | Required |
| `BACKEND_PORT` | Backend service port | 5050 |
| `FRONTEND_PORT` | Frontend service port | 8501 |

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
