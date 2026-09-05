from loguru import logger
import sys
from pathlib import Path
import json

# Create the log directory. Path("logs") refers to the "logs" directory under the current working directory. If the application is started from a different working directory, the location of the logs directory will also change accordingly.
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Remove the default console logger.
logger.remove()

# Add console logging.
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Add file logging.
logger.add(
    "logs/app.log",  # General application log file
    rotation="500 MB",  # Rotate the log file when it exceeds 500 MB
    retention="10 days",  # Keep log files for 10 days
    compression="zip",  # Compress rotated log files
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    encoding="utf-8"
)

# Store error logs in a separate file.
logger.add(
    "logs/error.log",  # Error log file
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    encoding="utf-8"
)

def get_logger(service: str):
    """Return a logger bound to a specific service."""
    return logger.bind(service=service)

def log_structured(event_type: str, data: dict):
    """Record structured log data."""
    logger.info({"event_type": event_type, "data": data})