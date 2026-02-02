# -*- coding: utf-8 -*-
"""
Logging configuration for MHFrontier addon.

Provides a configured logger for the addon with appropriate handlers.
"""

import logging
import sys

# Create the addon logger
logger = logging.getLogger("mhfrontier")

# Only configure if not already configured (avoid duplicate handlers)
if not logger.handlers:
    # Set default level (can be changed by users)
    logger.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "[%(name)s] %(levelname)s: %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    # Don't propagate to root logger
    logger.propagate = False


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger for a specific module.

    :param name: Module name (e.g., "fmod", "stage"). If None, returns the root addon logger.
    :return: Configured logger instance.
    """
    if name:
        return logging.getLogger(f"mhfrontier.{name}")
    return logger
