# QAMill Error Handler & Recovery Module
# Handles errors gracefully, logs properly, and prevents fatal crashes

import logging
import traceback
import sys
from typing import Optional, Callable, Any
from functools import wraps
from fastapi import Request
from fastapi.responses import JSONResponse
from health_check import monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend/logs/qamill.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class QAMillException(Exception):
    """Base exception for QAMill"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AnalysisError(QAMillException):
    """Analysis-related errors"""
    pass


class LLMError(QAMillException):
    """LLM API errors"""
    pass


class ValidationError(QAMillException):
    """Validation errors"""
    def __init__(self, message: str):
        super().__init__(message, 400)


class ResourceError(QAMillException):
    """Resource exhaustion errors"""
    pass


async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled errors"""

    error_message = str(exc)
    error_type = type(exc).__name__

    # Log the error with full traceback
    logger.error(
        f"Unhandled exception: {error_type}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        }
    )

    # Record error in monitor
    monitor.record_error(f"{error_type}: {error_message}")

    # Check for critical issues
    critical_issue = monitor.check_critical_issues()
    if critical_issue:
        logger.critical(f"CRITICAL ISSUE DETECTED: {critical_issue}")

    # Determine status code and response
    if isinstance(exc, QAMillException):
        status_code = exc.status_code
        message = exc.message
    else:
        status_code = 500
        message = "Internal server error. Please try again later."

    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "message": message,
            "type": error_type,
            "code": status_code,
        }
    )


def safe_endpoint(func: Callable) -> Callable:
    """Decorator to safely wrap endpoint handlers"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            monitor.record_request()
            result = await func(*args, **kwargs)
            return result
        except QAMillException as e:
            logger.warning(f"Expected error in {func.__name__}: {e.message}")
            monitor.record_error(str(e))
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in {func.__name__}: {str(e)}",
                exc_info=True
            )
            monitor.record_error(f"{type(e).__name__}: {str(e)}")
            raise QAMillException(
                "Internal server error. Check logs for details.",
                500
            )
    return wrapper


def ensure_directory_exists(path: str):
    """Ensure log directory exists"""
    import os
    os.makedirs(path, exist_ok=True)


# Create log directory on import
ensure_directory_exists('backend/logs')

logger.info("Error handler module initialized")
