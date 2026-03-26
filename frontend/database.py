"""SQLite database module for tracking submitted jobs."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

# Database path - stored in the frontend directory
DB_PATH = Path(__file__).parent / "jobs.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Initialize the database and create tables if they don't exist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                message TEXT,
                error TEXT,
                submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                recommendations TEXT,
                brand_guidelines TEXT,
                result_data TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_job(
    job_id: str,
    status: str = "pending",
    recommendations: Optional[str] = None,
    brand_guidelines: Optional[str] = None,
) -> None:
    """Save a new job to the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (job_id, status, recommendations, brand_guidelines)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, status, recommendations, brand_guidelines),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Job already exists, update it instead
        cursor.execute(
            """
            UPDATE jobs SET status = ?, recommendations = ?, brand_guidelines = ?
            WHERE job_id = ?
            """,
            (status, recommendations, brand_guidelines, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_job_status(
    job_id: str,
    status: str,
    progress: Optional[int] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    result_data: Optional[str] = None,
) -> None:
    """Update the status of an existing job."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE jobs
            SET status = ?,
                progress = COALESCE(?, progress),
                message = COALESCE(?, message),
                error = COALESCE(?, error),
                result_data = COALESCE(?, result_data),
                completed_at = CASE WHEN ? = 'completed' OR ? = 'failed'
                                   THEN CURRENT_TIMESTAMP
                                   ELSE completed_at END
            WHERE job_id = ?
            """,
            (status, progress, message, error, result_data, status, status, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get a job by its ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_all_jobs() -> List[Dict[str, Any]]:
    """Get all jobs ordered by submission date (most recent first)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs ORDER BY submitted_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_completed_jobs() -> List[Dict[str, Any]]:
    """Get all completed jobs ordered by submission date (most recent first)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM jobs WHERE status = 'completed' ORDER BY submitted_at DESC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_job(job_id: str) -> bool:
    """Delete a job from the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def clear_all_jobs() -> None:
    """Delete all jobs from the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs")
        conn.commit()
    finally:
        conn.close()
