"""Async runner for executing coroutines from synchronous context.

Provides a shared event loop to avoid the overhead of creating a new event loop
for each asyncio.run() call. Uses a single thread pool executor with one worker
to serialize async operations.
"""
import asyncio
import atexit
import concurrent.futures
import signal
import sys
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


class AsyncRunner:
    """Singleton async executor for running coroutines from sync context."""

    def __init__(self, max_workers: int = 1, timeout: float = 30.0):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._loop = asyncio.new_event_loop()
        self._running = True
        self._timeout = timeout

        # Start the loop in a background thread
        self._future = self._executor.submit(self._run_loop)

        # Register cleanup handlers
        atexit.register(self.shutdown)
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _run_loop(self):
        """Run the event loop indefinitely."""
        asyncio.set_event_loop(self._loop)
        while self._running:
            self._loop.run_until_complete(asyncio.sleep(0.5))

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.shutdown(wait=True)
        sys.exit(0)

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run coroutine in shared event loop and return result.

        Args:
            coro: Coroutine to execute

        Returns:
            Result from the coroutine

        Raises:
            concurrent.futures.TimeoutError: If operation exceeds timeout
            Exception: Re-raises any exception from the coroutine
        """
        if not self._running:
            raise RuntimeError("AsyncRunner has been shut down")

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=self._timeout)

    def shutdown(self, wait: bool = True):
        """Shutdown the async runner gracefully.

        Args:
            wait: If True, wait for running tasks to complete
        """
        self._running = False
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._executor.shutdown(wait=wait)
        self._loop.close()


# Global singleton instance
_async_runner: AsyncRunner | None = None


def get_async_runner() -> AsyncRunner:
    """Get the global AsyncRunner instance (lazy initialization)."""
    global _async_runner
    if _async_runner is None:
        _async_runner = AsyncRunner(max_workers=1, timeout=30.0)
    return _async_runner


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run coroutine in the shared event loop.

    This is the main entry point - use this instead of asyncio.run().

    Args:
        coro: Coroutine to execute

    Returns:
        Result from the coroutine
    """
    return get_async_runner().run(coro)


def shutdown_async_runner():
    """Shutdown the global AsyncRunner instance."""
    global _async_runner
    if _async_runner is not None:
        _async_runner.shutdown()
        _async_runner = None


__all__ = ["run_async", "get_async_runner", "shutdown_async_runner", "AsyncRunner"]