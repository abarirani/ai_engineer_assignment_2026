"""SQLite-based job storage for persistent job state management."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.models.schemas import JobStatusEnum


class JobDatabase:
    """SQLite-based job storage with proper transaction handling.

    This class provides persistent storage for job records, replacing the
    in-memory dictionary approach. It supports concurrent reads and ensures
    transaction safety with automatic rollback on errors.

    Attributes:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize the job database.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections with proper cleanup.

        Yields:
            sqlite3.Connection: Database connection with row factory enabled.

        Raises:
            Exception: Re-raised after rollback on error.
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Initialize database schema with indexes for efficient queries."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    request_data TEXT NOT NULL,
                    image_path TEXT,
                    image_url TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    progress INTEGER DEFAULT 0,
                    message TEXT,
                    error TEXT
                )
            """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)"
            )

    def create_job(
        self,
        job_id: str,
        request_data: Dict[str, Any],
        image_path: str,
        image_url: str,
    ) -> None:
        """Create a new job record.

        Args:
            job_id: Unique job identifier.
            request_data: Job request data as dictionary.
            image_path: Path to the uploaded image.
            image_url: URL to access the image.
        """
        now = datetime.utcnow()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, status, request_data, image_path, image_url,
                                created_at, updated_at, progress, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    job_id,
                    JobStatusEnum.PENDING.value,
                    json.dumps(request_data),
                    image_path,
                    image_url,
                    now,
                    now,
                    0,
                    "Job queued for processing",
                ),
            )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a job by ID.

        Args:
            job_id: Unique job identifier.

        Returns:
            Job record as dictionary or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def update_job_status(
        self,
        job_id: str,
        status: JobStatusEnum,
        progress: int = 0,
        message: str = None,
        error: str = None,
    ) -> None:
        """Update job status and progress.

        Args:
            job_id: Unique job identifier.
            status: New job status.
            progress: Progress percentage (0-100).
            message: Status message.
            error: Error message (if applicable).
        """
        now = datetime.utcnow()
        with self.get_connection() as conn:
            if error:
                conn.execute(
                    """
                    UPDATE jobs SET status = ?, updated_at = ?, progress = ?,
                                   message = ?, error = ?
                    WHERE id = ?
                """,
                    (status.value, now, progress, message, error, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE jobs SET status = ?, updated_at = ?, progress = ?,
                                   message = ?
                    WHERE id = ?
                """,
                    (status.value, now, progress, message, job_id),
                )

    def complete_job(self, job_id: str) -> None:
        """Mark job as completed.

        Args:
            job_id: Unique job identifier.
        """
        now = datetime.utcnow()
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE jobs SET status = ?, completed_at = ?, updated_at = ?,
                               progress = ?, message = ?
                WHERE id = ?
            """,
                (
                    JobStatusEnum.COMPLETED.value,
                    now,
                    now,
                    100,
                    "Processing completed successfully",
                    job_id,
                ),
            )

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark job as failed with error message.

        Args:
            job_id: Unique job identifier.
            error: Error message.
        """
        self.update_job_status(job_id, JobStatusEnum.FAILED, error=error)

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to dictionary.

        Args:
            row: SQLite row object.

        Returns:
            Dictionary representation of the job record.
        """
        return {
            "job_id": row["id"],
            "status": JobStatusEnum(row["status"]),
            "request": json.loads(row["request_data"]),
            "image_path": row["image_path"],
            "image_url": row["image_url"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
            "progress": row["progress"],
            "message": row["message"],
            "error": row["error"],
        }
