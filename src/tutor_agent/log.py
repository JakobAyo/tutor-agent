"""The tutor log file. Every record passes a filter that masks known secrets."""

import logging
from logging.handlers import RotatingFileHandler

from tutor_agent import paths

LOGGER_NAME = "tutor_agent"
_MASK = "***"


class SecretFilter(logging.Filter):
    """Replaces registered secret values in the final message, including args and tracebacks."""

    def __init__(self) -> None:
        super().__init__()
        self.secrets: set[str] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.secrets:
            return True
        message = record.getMessage()
        if record.exc_info:
            message += "\n" + logging.Formatter().formatException(record.exc_info)
            record.exc_info = None
            record.exc_text = None
        for secret in self.secrets:
            message = message.replace(secret, _MASK)
        record.msg, record.args = message, None
        return True


_secret_filter = SecretFilter()


def register_secret(value: str) -> None:
    """Never let `value` reach the log. Call this as soon as a secret is loaded."""
    if value:
        _secret_filter.secrets.add(value)


class TutorFileHandler(RotatingFileHandler):
    """Marks the handler `get_logger` installs, so other handlers (e.g. pytest's) don't count."""


def get_logger() -> logging.Logger:
    """The tutor logger, writing to the data directory. Set up once per process."""
    logger = logging.getLogger(LOGGER_NAME)
    if not any(isinstance(h, TutorFileHandler) for h in logger.handlers):
        handler = TutorFileHandler(
            paths.log_file(), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(process)d %(levelname)s %(message)s"))
        handler.addFilter(_secret_filter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
