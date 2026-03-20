# Visual Recommendations Agentic Workflow

A containerized, asynchronous backend service that implements a multi-agent workflow for generating visual recommendations on marketing creatives.

## Project Status

**Phase 1: Foundation** - ✅ Complete

## Overview

This system processes input images, applies textual recommendations while respecting brand guidelines, and evaluates the results through an iterative generation-evaluation-refinement loop.

## Architecture

```
graph TB
    A[Client Request] --> B[FastAPI Backend]
    B --> C[Orchestrator Agent]
    C --> D[Planner Agent]
    D --> E[Task Decomposition]
    E --> F[Editor Agent]
    F --> G[Image Generation Tools]
    G --> H[Critic Agent]
    H --> I{Evaluation Pass?}
    I -->|No| J[Refiner Agent]
    J --> K[Prompt/Parameter Adjustment]
    K --> F
    I -->|Yes| L[Output Assembly]
    L --> M[Audit Trail Generation]
    M --> N[Response to Client]
```

## Technology Stack

- **Backend Framework**: FastAPI (async support)
- **Agentic Framework**: LangGraph (Phase 2+)
- **Image Generation**: FLUX.2 [klein] 4B (Phase 3+)
- **Vision-Language Model**: Qwen3.5 27B (Phase 4+)
- **Containerization**: Docker + docker-compose

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)

### Local Development

1. **Create and activate virtual environment:**

```bash
bash setup-venv.sh
source .venv/bin/activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Configure environment (optional):**

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
python -m app.main
```

By default, this will run on:
- **Development** (`APP_ENV=development`): `http://0.0.0.0:5050`
- **Production** (`APP_ENV=production`): `http://0.0.0.0:8000`

You can override the environment by setting `APP_ENV`:

```bash
export APP_ENV=production
python -m app.main
```

5. **Access the API documentation:**

- Swagger UI: http://localhost:5050/docs (development)
- ReDoc: http://localhost:5050/redoc (development)

### Docker Development

```bash
# Build and run with docker-compose
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

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

## Project Structure

```
ai_engineer_assignment_2026/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py        # API endpoint definitions
│   ├── agents/                 # (Phase 2+)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic schemas
│   ├── services/               # (Phase 2+)
│   ├── utils/                  # (Phase 2+)
│   └── config/
│       ├── __init__.py
│       ├── settings.py         # Configuration management
│       ├── base.yaml           # Base configuration
│       ├── development.yaml    # Development environment config
│       └── production.yaml     # Production environment config
├── data/
│   ├── input/                  # Uploaded images
│   └── output/                 # Generated outputs
├── docker/
│   └── Dockerfile.backend      # Backend Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Foundation: FastAPI setup, API endpoints, Pydantic models, Docker config |
| Phase 2 | ⏳ Pending | Agent Core: Base classes, Orchestrator, Planner, audit trail |
| Phase 3 | ⏳ Pending | Image Processing: FLUX integration, Editor agent, protected regions |
| Phase 4 | ⏳ Pending | Evaluation Loop: Qwen3.5 integration, Critic, Refiner agents |
| Phase 5 | ⏳ Pending | Polish & Testing: Error handling, logging, tests, documentation |
| Phase 6 | ⏳ Optional | Frontend: Streamlit interface |

## License

Apache 2.0
