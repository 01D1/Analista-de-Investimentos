import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

from loguru import logger as _logger

_configured = False


def configure_logging(logs_dir: Path, level: str = "INFO") -> None:
    global _configured, _logger
    if _configured:
        return

    _logger.remove()

    # Console — colorido e legível
    _logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> — {message}",
        colorize=True,
    )

    # Arquivo — rotação diária, retenção 7 dias
    logs_dir.mkdir(parents=True, exist_ok=True)
    _logger.add(
        logs_dir / "intelligence_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name} | run={extra[run_id]:8} — {message}",
        rotation="1 day",
        retention="7 days",
        encoding="utf-8",
    )

    # Prevents KeyError when run_id not in context (e.g., direct CLI calls outside scheduler)
    _logger = _logger.patch(lambda r: r["extra"].setdefault("run_id", "-"))

    _configured = True


def get_logger(name: str):
    return _logger.bind(name=name)


@contextmanager
def bind_run_id(prefix: str = "run"):
    """Context manager: bind a short unique run_id to all log calls within scope.

    Generates run_id as "{prefix}-{8 hex chars from uuid4}".
    Outside this context, run_id defaults to "-" (set by the patcher in configure_logging).

    Usage in scheduler job functions:
        with bind_run_id("pipeline") as run_id:
            log.info(f"[scheduler] job iniciado — run_id={run_id}")

    Args:
        prefix: String prefix for the run_id. Default "run".

    Yields:
        run_id: The generated run_id string (e.g., "pipeline-a3f19c2d").
    """
    run_id = f"{prefix}-{uuid.uuid4().hex[:8]}"
    with _logger.contextualize(run_id=run_id):
        yield run_id
