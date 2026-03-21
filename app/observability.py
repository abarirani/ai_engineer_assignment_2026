"""OpenTelemetry observability configuration for local tracing.

This module provides minimal OpenTelemetry setup for automatic tracing
of LangGraph/LangChain workflows without requiring external services.
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource

from openinference.instrumentation.langchain import LangChainInstrumentor


def init_observability() -> None:
    """Initialize OpenTelemetry tracing.

    This function:
    1. Creates a tracer provider with service metadata
    2. Adds a console exporter to output traces to stdout
    3. Instruments LangChain/LangGraph for automatic tracing

    All LangGraph nodes (orchestrator, worker, synthesizer) will be
    automatically traced with inputs, outputs, and timing information.
    """
    # Create tracer provider with service metadata
    provider = TracerProvider(
        resource=Resource.create({"service.name": "image-editing-agent"})
    )

    # Export traces to console (stdout)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    # Auto-instrument LangChain/LangGraph
    LangChainInstrumentor().instrument()
