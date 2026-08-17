"""
Application-wide logging configuration.
Call configure_logging() once at startup before any other imports.
"""
import logging
import sys


def configure_logging() -> None:
    """Configure the standard Python root logger for the VALORA application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from noisy third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

