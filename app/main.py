"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from openinference.instrumentation.langchain import LangChainInstrumentor

from app.api.endpoints import router as api_router
from app.config.settings import settings
from app.models.database import JobDatabase
from app.services.workflow_service import get_workflow_service
from app.services.semaphore_manager import semaphore_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.logging.level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ============== LIFESPAN MANAGEMENT ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events.

    This context manager handles:
    - Startup: Initialization tasks, logging, resource setup
    - Shutdown: Cleanup tasks, resource release, graceful termination
    """
    # Startup events
    logger.info(f"Starting {settings.app.name} v{settings.app.version}")

    # Initialize LangChain instrumentation for observability
    # This must be done before any tracer provider is set
    LangChainInstrumentor().instrument()
    logger.info("LangChain instrumentation initialized")

    # Initialize semaphore manager for concurrent job control
    semaphore_manager.initialize(settings.processing.max_concurrent_jobs)
    logger.info(
        f"Semaphore manager initialized with max_concurrent_jobs={settings.processing.max_concurrent_jobs}"
    )

    # Initialize database
    db = JobDatabase(settings.database.path)
    logger.info(f"Database initialized at {settings.database.path}")

    # Recover any stale processing jobs from unexpected shutdowns
    recovered_count = db.recover_stale_processing_jobs()
    if recovered_count > 0:
        logger.warning(
            f"Recovered {recovered_count} stale processing job(s) marked as failed"
        )
    else:
        logger.info("No stale processing jobs found")

    # Initialize workflow service with database
    workflow_service = get_workflow_service(db)
    logger.info("Workflow service initialized")

    # Inject dependencies into endpoints module
    import app.api.endpoints as endpoints_module

    endpoints_module.db = db
    endpoints_module.workflow_service = workflow_service
    logger.info("Dependencies injected into endpoints module")

    logger.info("Application startup complete")

    yield

    # Shutdown events
    logger.info("Application shutdown initiated")
    # Add cleanup tasks here (e.g., close database connections, cleanup temp files)
    logger.info("Application shutdown complete")


# ============== EXCEPTION HANDLERS ==============


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors (Pydantic validation)."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.app.debug else "An unexpected error occurred",
        },
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description=(
            "Visual Recommendations Agentic Workflow Backend\n\n"
            "This API provides endpoints for processing images with visual "
            "recommendations using a multi-agent workflow."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )

    # Include API router
    app.include_router(api_router, prefix=settings.api.v1_prefix)

    # Register exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    @app.get("/health", tags=["Health"])
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app.version}

    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, str]:
        """Root endpoint."""
        return {
            "name": settings.app.name,
            "version": settings.app.version,
            "docs": "/docs",
        }

    return app


app = create_app()
