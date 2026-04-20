import asyncio
import logging
from typing import Callable, TypeVar, Any

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    RetryCallState,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ThrottledError(Exception):
    def __init__(self, retry_after: float = 30.0):
        self.retry_after = retry_after
        super().__init__(f"Graph API throttled, retry after {retry_after}s")


class GraphApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Graph API error {status_code}: {message}")


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ThrottledError):
        return True
    if isinstance(exc, GraphApiError):
        return exc.status_code in (429, 500, 502, 503, 504)
    return False


def build_retry_decorator(attempts: int, backoff_seconds: float):
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=backoff_seconds, min=backoff_seconds, max=120),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


async def handle_throttle_sleep(exc: ThrottledError) -> None:
    logger.warning("Throttled by Graph API, sleeping %.1fs", exc.retry_after)
    await asyncio.sleep(exc.retry_after)
