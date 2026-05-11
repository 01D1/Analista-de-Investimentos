import random
import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from src.utils.logger import get_logger

log = get_logger(__name__)
F = TypeVar("F", bound=Callable)


def retry(
    attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    jitter: float = 0.5,
):
    """Decorator de retry com backoff exponencial e jitter.

    Args:
        attempts: Number of total attempts (including first). Default 3.
        delay: Initial wait time in seconds. Default 2.0.
        backoff: Multiplier applied to wait after each failure. Default 2.0.
        exceptions: Tuple of exception types to catch and retry. Default (Exception,).
        jitter: Max random seconds added to each wait to avoid thundering herd. Default 0.5.

    Raises:
        IngestionError: When all attempts are exhausted.
        Exception: Non-matching exceptions propagate immediately without retry.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == attempts:
                        log.error(
                            f"{func.__name__} falhou após {attempts} tentativas: {exc}"
                        )
                        from src.utils.errors import IngestionError  # deferred — avoids circular
                        raise IngestionError(func.__name__, exc) from exc
                    actual_wait = wait + random.uniform(0, jitter)
                    log.warning(
                        f"{func.__name__} tentativa {attempt}/{attempts} falhou: {exc}. "
                        f"Aguardando {actual_wait:.1f}s"
                    )
                    time.sleep(actual_wait)
                    wait *= backoff
        return wrapper  # type: ignore
    return decorator
