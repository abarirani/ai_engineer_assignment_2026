"""Semaphore manager for controlling concurrent job execution.

This module provides a semaphore manager that limits the number of
concurrent jobs running at any given time using asyncio.Semaphore.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class SemaphoreManager:
    """Manages concurrent job execution using asyncio.Semaphore.

    This class manages a semaphore that limits the number of concurrent jobs.
    Jobs must acquire the semaphore before processing and release it when done.

    Attributes:
        _semaphore: asyncio.Semaphore instance for concurrency control.
        _max_concurrent: Maximum number of concurrent jobs allowed.
        _current_count: Current number of jobs being processed.
        _lock: Lock for thread-safe counter updates.
    """

    def __init__(self, max_concurrent: int) -> None:
        """Initialize the semaphore manager.

        Args:
            max_concurrent: Maximum number of concurrent jobs allowed.

        Raises:
            ValueError: If max_concurrent is less than 1.
        """
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._current_count: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()

        logger.info(
            f"SemaphoreManager initialized with max_concurrent_jobs={max_concurrent}"
        )

    async def acquire(self, job_id: str) -> None:
        """Acquire the semaphore for a job.

        Blocks until a slot is available for concurrent execution.

        Args:
            job_id: Unique job identifier for logging purposes.
        """
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
        async with self._lock:
            self._current_count -= 1

        self._semaphore.release()
        logger.info(
            f"Job {job_id} released semaphore (current: {self._current_count}/{self._max_concurrent})"
        )
