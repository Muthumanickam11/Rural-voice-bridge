import time
import asyncio
import threading
from typing import Any, Callable, Optional, Dict
from utils.logger import logger

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_time_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker tripped to OPEN! Threshold {self.failure_threshold} reached.")

    def is_available(self) -> bool:
        with self._lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_time_seconds:
                    self.state = "HALF_OPEN"
                    return True
                return False
            return True


def _backoff(attempt: int, delay_seconds: float) -> float:
    return delay_seconds * (2 ** attempt)


def call_with_retry(
    fn: Callable[[], Any],
    max_retries: int = 2,
    delay_seconds: float = 0.5,
    circuit_breaker: Optional[CircuitBreaker] = None
) -> Any:
    """
    Blocking retry helper. MUST NOT be called directly from an `async def`
    request handler - use `acall_with_retry` there, or the event loop stalls
    for every concurrent request while this sleeps.
    """
    if circuit_breaker and not circuit_breaker.is_available():
        raise RuntimeError("Circuit breaker is OPEN for this provider")

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            result = fn()
            if circuit_breaker:
                circuit_breaker.record_success()
            return result
        except Exception as e:
            last_err = e
            logger.warning(f"Call attempt {attempt + 1}/{max_retries + 1} failed: {e}")
            if attempt < max_retries:
                time.sleep(_backoff(attempt, delay_seconds))

    if circuit_breaker:
        circuit_breaker.record_failure()
    raise last_err


async def acall_with_retry(
    fn: Callable[[], Any],
    max_retries: int = 2,
    delay_seconds: float = 0.5,
    circuit_breaker: Optional[CircuitBreaker] = None
) -> Any:
    """
    Async-safe retry helper. `fn` is a blocking callable; it is offloaded to a
    worker thread so the event loop keeps serving other requests, and the
    backoff uses `asyncio.sleep` instead of blocking `time.sleep`.
    """
    if circuit_breaker and not circuit_breaker.is_available():
        raise RuntimeError("Circuit breaker is OPEN for this provider")

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            result = await asyncio.to_thread(fn)
            if circuit_breaker:
                circuit_breaker.record_success()
            return result
        except Exception as e:
            last_err = e
            logger.warning(f"Call attempt {attempt + 1}/{max_retries + 1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(_backoff(attempt, delay_seconds))

    if circuit_breaker:
        circuit_breaker.record_failure()
    raise last_err
