"""OpenTelemetry observability configuration for local tracing.

This module provides minimal OpenTelemetry setup for automatic tracing
of LangGraph/LangChain workflows without requiring external services.

Note: LangChain instrumentation must be initialized at application startup
before this module is used. See app/main.py for instrumentation setup.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace import ReadableSpan


def _timestamp_to_iso(timestamp: Optional[int]) -> Optional[str]:
    """Convert OpenTelemetry timestamp (nanoseconds since epoch) to ISO format.

    Args:
        timestamp: Timestamp in nanoseconds since epoch, or None.

    Returns:
        ISO 8601 formatted string, or None if timestamp is None.
    """
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp / 1e9, tz=timezone.utc).isoformat()


class FileSpanExporter(SpanExporter):
    """Custom span exporter that writes traces to a JSON file.

    This exporter collects spans and writes them to a specified file path
    in JSON format, making it easy to inspect traces locally.

    Attributes:
        file_path: Path to the output file for trace data.
        _spans: List of collected spans before export.
    """

    def __init__(self, file_path: str):
        """Initialize the file exporter with an output path.

        Args:
            file_path: Path to the JSON file where traces will be written.
        """
        self.file_path = Path(file_path)
        self._spans: list[dict] = []
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        """Export a batch of spans to the internal list.

        Args:
            spans: List of spans to export.

        Returns:
            SpanExportResult.SUCCESS if export was successful.
        """
        for span in spans:
            span_data = self._span_to_dict(span)
            self._spans.append(span_data)
        return SpanExportResult.SUCCESS

    def _span_to_dict(self, span: ReadableSpan) -> dict:
        """Convert a span to a dictionary representation.

        Args:
            span: The span to convert.

        Returns:
            Dictionary representation of the span.
        """
        span_dict = {
            "name": span.name,
            "context": {
                "trace_id": (
                    format(span.get_span_context().trace_id, "x")
                    if span.get_span_context().trace_id
                    else None
                ),
                "span_id": (
                    format(span.get_span_context().span_id, "x")
                    if span.get_span_context().span_id
                    else None
                ),
            },
            "kind": span.kind.name,
            "start_time": _timestamp_to_iso(span.start_time),
            "end_time": _timestamp_to_iso(span.end_time),
            "status": {
                "status_code": span.status.status_code.name,
                "description": span.status.description,
            },
            "attributes": dict(span.attributes) if span.attributes else {},
            "events": [
                {
                    "name": event.name,
                    "timestamp": _timestamp_to_iso(event.timestamp),
                    "attributes": dict(event.attributes) if event.attributes else {},
                }
                for event in span.events
            ],
            "links": [
                {
                    "context": {
                        "trace_id": format(link.context.trace_id, "x"),
                        "span_id": format(link.context.span_id, "x"),
                    },
                    "attributes": dict(link.attributes) if link.attributes else {},
                }
                for link in span.links
            ],
        }
        return span_dict

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Flush all collected spans to the file.

        Args:
            timeout_millis: Timeout in milliseconds (not used).

        Returns:
            True if flush was successful.
        """
        try:
            with open(self.file_path, "w") as f:
                json.dump({"traces": self._spans}, f, indent=2)
            return True
        except Exception:
            return False

    def shutdown(self, timeout_millis: int = 30000) -> None:
        """Shutdown the exporter and flush remaining spans.

        Args:
            timeout_millis: Timeout in milliseconds (not used).
        """
        self.force_flush()


# Global tracer provider for job-specific tracing
_job_tracer_provider: Optional[TracerProvider] = None
_job_file_exporter: Optional[FileSpanExporter] = None


def init_observability_for_job(job_id: str, output_dir: str = "data/output") -> None:
    """Initialize OpenTelemetry tracing for a specific job with file export.

    This function creates a job-specific tracer that exports traces to a JSON file
    in the same directory as the job output.

    Args:
        job_id: Unique identifier for the job.
        output_dir: Base output directory (default: "data/output").

    The traces will be written to: {output_dir}/{job_id}/traces.json
    """
    global _job_tracer_provider, _job_file_exporter

    # Clean up previous job's tracer if exists
    if _job_tracer_provider is not None:
        _job_tracer_provider.shutdown()

    # Create job-specific output path
    job_output_dir = Path(output_dir) / job_id
    trace_file_path = job_output_dir / "traces.json"

    # Create file exporter
    _job_file_exporter = FileSpanExporter(str(trace_file_path))

    # Create tracer provider with service metadata
    _job_tracer_provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": "image-editing-agent",
                "job.id": job_id,
            }
        )
    )

    # Create span processor with file exporter
    span_processor = SimpleSpanProcessor(_job_file_exporter)
    _job_tracer_provider.add_span_processor(span_processor)

    # Set as global tracer provider
    # Note: LangChain instrumentation must have been initialized at app startup
    trace.set_tracer_provider(_job_tracer_provider)


def flush_job_traces() -> bool:
    """Flush all collected traces for the current job to file.

    Returns:
        True if flush was successful, False otherwise.
    """
    global _job_file_exporter
    if _job_file_exporter is not None:
        return _job_file_exporter.force_flush()
    return False


def shutdown_job_observability() -> None:
    """Shutdown the job-specific observability and clean up resources.

    This should be called after job processing is complete to ensure
    all traces are flushed to disk.
    """
    global _job_tracer_provider, _job_file_exporter

    if _job_tracer_provider is not None:
        _job_tracer_provider.shutdown()
        _job_tracer_provider = None
        _job_file_exporter = None
