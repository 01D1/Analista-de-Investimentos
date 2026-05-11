"""
errors.py
---------
Exceções estruturadas para falhas de ingestão e chamadas a APIs externas.
"""
from datetime import datetime, timezone


class IngestionError(Exception):
    """Sinaliza exaustão de todas as tentativas de retry em uma operação de ingestão.

    Attributes:
        cause: str representation of the original exception.
        func_name: Name of the decorated function that exhausted retries.
        timestamp: UTC datetime of failure.
    """

    def __init__(self, func_name: str, cause: "str | Exception"):
        self.cause = str(cause)
        self.func_name = func_name
        self.timestamp = datetime.now(tz=timezone.utc)
        super().__init__(f"{func_name} falhou após todas as tentativas: {self.cause}")
