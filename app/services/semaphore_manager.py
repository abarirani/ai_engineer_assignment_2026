"""Semaphore manager for controlling concurrent job execution.

This module provides a singleton semaphore manager that limits the number of
concurrent jobs running at any given time using asyncio.Semaphore.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SemaphoreManager:
    """Manages concurrent job execution using asyncio.Semaphore.

    This class provides a singleton pattern for managing a semaphore that
    limits the number of concurrent jobs. Jobs must acquire the semaphore
    before processing and release it when done.

    Attributes:
        _semaphore: asyncio.Semaphore instance for concurrency control.
        _max_concurrent: Maximum number of concurrent jobs allowed.
        _current_count: Current number of jobs being processed.
        _lock: Lock for thread-safe counter updates.
    """

    _instance: Optional["SemaphoreManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "SemaphoreManager":
        """Create or return the singleton instance.

        Returns:
            The singleton SemaphoreManager instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the semaphore manager (only once)."""
        if SemaphoreManager._initialized:
            return

        self._semaphore: Optional[asyncio.Semaphore] = None
        self._max_concurrent: int = 0
        self._current_count: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()
        SemaphoreManager._initialized = True

    def initialize(self, max_concurrent: int) -> None:
        """Initialize the semaphore with the maximum concurrent jobs limit.

        Args:
            max_concurrent: Maximum number of concurrent jobs allowed.

        Raises:
            ValueError: If max_concurrent is less than 1.
            RuntimeError: If already initialized.
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        if self._semaphore is not None:
            logger.warning(
                f"SemaphoreManager already initialized with max_concurrent={self._max_concurrent}. "
                f"New value {max_concurrent} will be ignored."
            )
            return

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        logger.info(
            f"SemaphoreManager initialized with max_concurrent_jobs={max_concurrent}"
        )

    async def acquire(self, job_id: str) -> None:
        """Acquire the semaphore for a job.

        Blocks until a slot is available for concurrent execution.

        Args:
            job_id: Unique job identifier for logging purposes.
        """
        if self._semaphore is None:
            raise RuntimeError(
                "SemaphoreManager not initialized. Call initialize() first."
            )

        logger.debug(f"Job {job_id} waiting for semaphore acquisition")
        await self._semaphore.acquire()

        async with self._lock:
            self._current_count += 1

        logger.info(
            f"Job {job_id} acquired semaphore (current: {self._current_count}/{self._max_concurrent})"
        )

    async def release(self, job_id: str) -> None:
        """Release the semaphore after job completion.

        Args:
            job_id: Unique job identifier for logging purposes.
        """
        if self._semaphore is None:
            raise RuntimeError(
                "SemaphoreManager not initialized. Call initialize() first."
            )

        async with self._lock:
            self._current_count -= 1

        self._semaphore.release()
        logger.info(
            f"Job {job_id} released semaphore (current: {self._current_count}/{self._max_concurrent})"
        )

    @property
    def current_count(self) -> int:
        """Get the current number of jobs being processed.

        Returns:
            Current number of active jobs.
        """
        return self._current_count

    @property
    def max_concurrent(self) -> int:
        """Get the maximum number of concurrent jobs allowed.

        Returns:
            Maximum concurrent jobs limit.
        """
        return self._max_concurrent

    @property
    def available_slots(self) -> int:
        """Get the number of available slots for new jobs.

        Returns:
            Number of available slots (max_concurrent - current_count).
        """
        return self._max_concurrent - self._current_count

    def is_initialized(self) -> bool:
        """Check if the semaphore manager has been initialized.

        Returns:
            True if initialized, False otherwise.
        """
        return self._semaphore is not None


# Singleton instance for use across the application
semaphore_manager: SemaphoreManager = SemaphoreManager()
