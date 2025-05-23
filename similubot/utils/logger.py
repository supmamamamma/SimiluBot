"""Logging utility for SimiluBot."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_size: int = 10485760,  # 10 MB
    backup_count: int = 5
) -> None:
    """
    Set up the logger for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to the log file. If None, logs will only go to console
        max_size: Maximum size of log file before rotation (in bytes)
        backup_count: Number of backup log files to keep
    """
    # Create logger
    logger = logging.getLogger("similubot")
    logger.setLevel(getattr(logging, log_level))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Log debug message to confirm logger setup
    logger.debug("Logger initialized")
