"""OpenTelemetry observability configuration for local tracing.

This module provides minimal OpenTelemetry setup for automatic tracing
of LangGraph/LangChain workflows without requiring external services.

Note: LangChain instrumentation must be initialized at application startup
before this module is used. See app/main.py for instrumentation setup.
"""

import json
import threading
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
        job_id: Job ID filter - only spans with matching job.id attribute are exported.
        _spans: List of collected spans before export.
    """

    def __init__(self, file_path: str, job_id: str):
        """Initialize the file exporter with an output path and job filter.

        Args:
            file_path: Path to the JSON file where traces will be written.
            job_id: Job ID to filter spans by (only spans with matching job.id attribute).
        """
        self.file_path = Path(file_path)
        self.job_id = job_id
        self._spans: list[dict] = []
        self._lock: threading.Lock = threading.Lock()
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _extract_job_id_from_span(self, span: ReadableSpan) -> Optional[str]:
        """Extract job_id from span attributes.

        The job_id can be in two places:
        1. Directly as 'job_id' attribute
        2. Inside 'metadata' attribute as JSON string with 'job_id' key

        Args:
            span: The span to extract job_id from.

        Returns:
            The job_id if found, None otherwise.
        """
        attributes = dict(span.attributes) if span.attributes else {}

        # Check for direct job_id attribute
        if "job_id" in attributes:
            return str(attributes["job_id"])

        # Check for job_id inside metadata JSON
        if "metadata" in attributes:
            try:
                metadata_str = attributes["metadata"]
                if isinstance(metadata_str, str):
                    metadata_dict = json.loads(metadata_str)
                    if "job_id" in metadata_dict:
                        return str(metadata_dict["job_id"])
            except (json.JSONDecodeError, TypeError):
                pass

        return None

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        """Export a batch of spans to the internal list.

        Only exports spans that match this exporter's job_id filter.

        Args:
            spans: List of spans to export.

        Returns:
            SpanExportResult.SUCCESS if export was successful.
        """
        for span in spans:
            # Filter: only export spans for this job
            span_job_id = self._extract_job_id_from_span(span)
            if span_job_id == self.job_id:
                span_data = self._span_to_dict(span)
                with self._lock:
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
            with self._lock:
                spans_copy = list(self._spans)
            with open(self.file_path, "w") as f:
                json.dump({"traces": spans_copy}, f, indent=2)
            return True
        except Exception:
            return False

    def shutdown(self, timeout_millis: int = 30000) -> None:
        """Shutdown the exporter and flush remaining spans.

        Args:
            timeout_millis: Timeout in milliseconds (not used).
        """
        self.force_flush()


# Global shared tracer provider (initialized once, shared across all jobs)
_global_tracer_provider: Optional[TracerProvider] = None

# Track job-specific exporters for cleanup
_job_exporters: dict[str, FileSpanExporter] = {}

# Lock for thread-safe access to global observability state
_observability_lock: threading.Lock = threading.Lock()


def init_observability_for_job(job_id: str, output_dir: str = "data/output") -> None:
    """Initialize OpenTelemetry tracing for a specific job with file export.

    This function adds a job-specific exporter to the global tracer provider.
    Each exporter filters spans by job.id attribute, ensuring trace isolation
    even when multiple jobs run concurrently.

    Args:
        job_id: Unique identifier for the job.
        output_dir: Base output directory (default: "data/output").

    The traces will be written to: {output_dir}/{job_id}/traces.json
    """
    global _global_tracer_provider

    with _observability_lock:
        # Create shared provider once (if not already initialized)
        if _global_tracer_provider is None:
            _global_tracer_provider = TracerProvider(
                resource=Resource.create({"service.name": "image-editing-agent"})
            )
            trace.set_tracer_provider(_global_tracer_provider)

        # Create job-specific output path
        job_output_dir = Path(output_dir) / job_id
        trace_file_path = job_output_dir / "traces.json"

        # Create job-specific exporter that filters by job_id
        exporter = FileSpanExporter(str(trace_file_path), job_id)
        _job_exporters[job_id] = exporter

        # Add exporter to the global provider
        span_processor = SimpleSpanProcessor(exporter)
        _global_tracer_provider.add_span_processor(span_processor)


def flush_job_traces(job_id: str) -> bool:
    """Flush all collected traces for a specific job to file.

    Args:
        job_id: The job ID whose traces should be flushed.

    Returns:
        True if flush was successful, False otherwise.
    """
    with _observability_lock:
        if job_id in _job_exporters:
            return _job_exporters[job_id].force_flush()
    return False


def shutdown_job_observability(job_id: str) -> None:
    """Shutdown observability for a specific job and clean up resources.

    This should be called after job processing is complete to ensure
    all traces are flushed to disk.

    Args:
        job_id: The job ID whose observability should be shut down.
    """
    with _observability_lock:
        if job_id in _job_exporters:
            _job_exporters[job_id].force_flush()
            del _job_exporters[job_id]
