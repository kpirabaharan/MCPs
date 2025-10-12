"""
Logger configuration for MCP AIDA Debug Journals
"""

import logging
import os
import sys
from datetime import datetime


def setup_logger(name: str = "weather_mcp_server") -> logging.Logger:
    """
    Set up a logger with console and date-based file handlers

    Args:
        name: Logger Name

    Returns:
        Configured Logger Instance
    """

    logger = logging.getLogger(name)

    logger.handlers.clear()

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"weather_mcp_server_{date_str}.log"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.abspath(os.path.join(base_dir, "..", "logs"))

    # Create logs directory
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file_path = os.path.join(log_dir, log_filename)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "weather_mcp_server") -> logging.Logger:
    """
    Get a logger with console and date-based file handlers

    Args:
        name: Logger Name

    Returns:
        Configured Logger Instance
    """

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger = setup_logger(name)

    return logger
