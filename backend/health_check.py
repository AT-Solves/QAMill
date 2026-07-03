# QAMill Health Check Module
# Monitors backend health, provides status endpoints, and triggers recovery

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import psutil
import os

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors backend health and provides status information"""

    def __init__(self):
        self.start_time = datetime.now()
        self.last_error: Optional[str] = None
        self.error_count = 0
        self.request_count = 0
        self.process = psutil.Process(os.getpid())

    def record_request(self):
        """Increment request counter"""
        self.request_count += 1

    def record_error(self, error: str):
        """Record an error"""
        self.last_error = error
        self.error_count += 1
        logger.error(f"Error recorded: {error}")

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system resource usage"""
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()

            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / 1024 / 1024,
                "memory_percent": memory_percent,
                "threads": self.process.num_threads(),
            }
        except Exception as e:
            logger.warning(f"Failed to get system stats: {e}")
            return {}

    def get_health_status(self) -> Dict[str, Any]:
        """Get complete health status"""
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        uptime_minutes = uptime_seconds / 60
        uptime_hours = uptime_minutes / 60

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": {
                "seconds": int(uptime_seconds),
                "minutes": int(uptime_minutes),
                "hours": int(uptime_hours),
            },
            "requests": self.request_count,
            "errors": self.error_count,
            "last_error": self.last_error,
            "system": self.get_system_stats(),
        }

        # Check if unhealthy
        if self.error_count > 100 or self.get_system_stats().get("memory_percent", 0) > 90:
            health_status["status"] = "degraded"

        if self.error_count > 500:
            health_status["status"] = "unhealthy"

        return health_status

    def check_critical_issues(self) -> Optional[str]:
        """Check for critical issues that need recovery"""
        stats = self.get_system_stats()

        # Check memory
        if stats.get("memory_percent", 0) > 95:
            return "Memory usage critical (>95%)"

        # Check error rate (more than 10 errors in last batch)
        if self.error_count > 50:
            return f"High error count: {self.error_count}"

        return None

    def reset_stats(self):
        """Reset stats for new monitoring period"""
        self.error_count = 0
        self.request_count = 0
        self.last_error = None


# Global monitor instance
monitor = HealthMonitor()
