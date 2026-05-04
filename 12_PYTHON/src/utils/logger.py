import sys
from pathlib import Path

from loguru import logger as _logger

_configured = False


def configure_logging(logs_dir: Path, level: str = "INFO") -> None:
    global _configured
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

    # Arquivo — rotação diária, retenção 30 dias
    logs_dir.mkdir(parents=True, exist_ok=True)
    _logger.add(
        logs_dir / "intelligence_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name} — {message}",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
    )

    _configured = True


def get_logger(name: str):
    return _logger.bind(name=name)
