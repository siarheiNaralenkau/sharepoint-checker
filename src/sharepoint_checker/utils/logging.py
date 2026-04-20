import logging
import sys
from typing import Optional


def configure_logging(level: str = "INFO", run_id: Optional[str] = None) -> None:
    fmt = "%(asctime)s %(levelname)-8s %(name)s"
    if run_id:
        fmt += f" run_id={run_id}"
    fmt += " %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stderr,
    )

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("msal").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
