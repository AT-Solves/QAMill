# QAMill Backend Configuration Constants
# Centralized configuration for all hardcoded values

import os
from typing import Dict, Any

# Server Configuration
SERVER_HOST = os.getenv("QAMILL_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("QAMILL_PORT", "8765"))
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

# API Configuration
API_ROUTES = {
    "ANALYZE": "/analyze",
    "ANALYZE_JAVASCRIPT": "/analyze/javascript",
    "STREAM": "/stream",
    "GENERATE_UNIT_TESTS": "/generate/unit-tests/stream",
    "GENERATE_MANUAL_TESTS": "/generate/manual-tests/stream",
    "HEALTH": "/health",
}

# Timeout Configuration (in seconds)
TIMEOUT = {
    "STREAM_EVENT": 10,
    "SMTP": 15,
    "SOCKET": 30,
    "DEFAULT": 30,
}

# LLM Configuration
LLM_CONFIG = {
    "EQUIVALENCE_DETECTION": {
        "MAX_TOKENS": 400,
    },
    "TEST_GENERATION": {
        "OLLAMA": {
            "FAST": 80,
            "NORMAL": 150,
        },
        "CLOUD": {
            "FAST": 100,
            "NORMAL": 180,
        },
        "UNIT_TESTS": {
            "FAST": 150,
            "NORMAL": 250,
        },
        "UNIT_TESTS_CLOUD": {
            "FAST": 100,
            "NORMAL": 180,
        },
        "MANUAL_TESTS": {
            "FAST": 150,
            "NORMAL": 300,
        },
        "MANUAL_TESTS_CLOUD": {
            "FAST": 100,
            "NORMAL": 200,
        },
    },
}

# CORS Configuration
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8765",
    "https://qamill.achieverthoughts.com",
    "*",
]

# SMTP Configuration
SMTP_CONFIG = {
    "HOST": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "PORT": int(os.getenv("SMTP_PORT", "587")),
    "PORT_SSL": int(os.getenv("SMTP_PORT_SSL", "465")),
    "USERNAME": os.getenv("SMTP_USERNAME", ""),
    "PASSWORD": os.getenv("SMTP_PASSWORD", ""),
    "TIMEOUT": TIMEOUT["SMTP"],
}

# Mutation Testing Configuration
MUTATION_CONFIG = {
    "MAX_MUTANTS": 500,
    "BATCH_SIZE": 10,
}

# File Configuration
FILE_CONFIG = {
    "UPLOAD_MAX_SIZE": 10 * 1024 * 1024,  # 10MB
    "TEMP_DIR": os.getenv("TEMP_DIR", "/tmp/qamill"),
}

# Database Configuration (if needed)
DATABASE_CONFIG = {
    "URL": os.getenv("DATABASE_URL", "sqlite:///./qamill.db"),
    "ECHO": os.getenv("DEBUG", "false").lower() == "true",
}

# Logging Configuration
LOGGING_CONFIG = {
    "LEVEL": os.getenv("LOG_LEVEL", "INFO"),
    "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

# Feature Flags
FEATURES = {
    "EQUIVALENCE_DETECTION": True,
    "AUTO_HEALING": True,
    "STREAMING": True,
    "CACHING": True,
}

# Get function for convenient access
def get_config(section: str, key: str = None, default: Any = None) -> Any:
    """
    Get configuration value by section and key.

    Example:
        max_tokens = get_config("LLM_CONFIG", "EQUIVALENCE_DETECTION.MAX_TOKENS")
    """
    try:
        config_dict = globals().get(section)
        if config_dict is None:
            return default

        if key is None:
            return config_dict

        # Handle nested keys with dot notation
        keys = key.split(".")
        value = config_dict
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default
