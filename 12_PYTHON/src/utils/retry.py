import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from src.utils.logger import get_logger

log = get_logger(__name__)
F = TypeVar("F", bound=Callable)


def retry(
    attempts: int = 3, delay: float = 2.0, backoff: float = 2.0, exceptions: tuple = (Exception,)
):
    """Decorator de retry com backoff exponencial."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == attempts:
                        log.error(f"{func.__name__} falhou após {attempts} tentativas: {exc}")
                        raise
                    log.warning(
                        f"{func.__name__} tentativa {attempt}/{attempts} falhou: {exc}. Aguardando {wait:.1f}s"
                    )
                    time.sleep(wait)
                    wait *= backoff

        return wrapper  # type: ignore

    return decorator
