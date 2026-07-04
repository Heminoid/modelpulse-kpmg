"""Loguru logging configuration for ModelPulse."""

import sys

from loguru import logger


def setup_logging(debug: bool = True) -> None:
    """Configure loguru logger with appropriate format and level."""
    logger.remove()  # Remove default handler
    log_level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
    )
    logger.info("Logging configured at {} level", log_level)
