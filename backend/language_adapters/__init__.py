"""
Language Adapter Framework - Multi-language support for QAMill

Supports: Python, JavaScript/TypeScript (+ future: C#, Java, Go)
Provides: Language detection, framework detection, unified interfaces
"""
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List


# ── Language & File Type Mapping ─────────────────────────────────────────────

LANGUAGE_MAP = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}

TEST_FRAMEWORK_MAP = {
    "javascript": {
        "jest": "jest",
        "vitest": "vitest",
        "mocha": "mocha",
        "jasmine": "jasmine",
    },
    "python": {
        "pytest": "pytest",
        "unittest": "unittest",
        "nose2": "nose2",
    },
}

LANGUAGE_NAMES = {
    "python": "Python 🐍",
    "javascript": "JavaScript 🟨",
    "csharp": "C# 🔷",
    "java": "Java ☕",
    "go": "Go 🐹",
}


def detect_language(file_path: str) -> Optional[str]:
    """Detect language from file extension."""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext)


def detect_test_framework(project_path: str, language: str) -> Optional[str]:
    """
    Detect test framework from package.json (JS) or setup.py/pyproject.toml (Python).
    Returns: "jest", "vitest", "mocha", "pytest", etc.
    """
    project = Path(project_path)

    if language == "javascript":
        return _detect_js_framework(project)
    elif language == "python":
        return _detect_python_framework(project)

    return None


def _detect_js_framework(project: Path) -> Optional[str]:
    """Detect JS test framework from package.json"""
    pkg_file = project / "package.json"
    if not pkg_file.exists():
        return "jest"  # Default

    try:
        content = json.loads(pkg_file.read_text())
        deps = {
            **content.get("dependencies", {}),
            **content.get("devDependencies", {}),
        }

        # Priority: vitest > jest > mocha
        if "vitest" in deps:
            return "vitest"
        elif "jest" in deps:
            return "jest"
        elif "mocha" in deps:
            return "mocha"
        else:
            return "jest"  # Default
    except:
        return "jest"


def _detect_python_framework(project: Path) -> Optional[str]:
    """Detect Python test framework from project files"""
    # Check pyproject.toml
    pyproject = project / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        if "pytest" in content:
            return "pytest"

    # Check setup.py
    setup = project / "setup.py"
    if setup.exists():
        content = setup.read_text()
        if "pytest" in content:
            return "pytest"

    # Default
    return "pytest"


def check_runtime_available(language: str) -> tuple[bool, Optional[str]]:
    """
    Check if language runtime is available.
    Returns: (available: bool, error_message: Optional[str])
    """
    if language == "python":
        try:
            subprocess.run(["python", "--version"], capture_output=True, check=True)
            return True, None
        except:
            return (
                False,
                "Python not found. Install from https://www.python.org/downloads/",
            )

    elif language == "javascript":
        try:
            subprocess.run(["node", "--version"], capture_output=True, check=True)
            return True, None
        except:
            return (
                False,
                "Node.js not found. Install from https://nodejs.org/",
            )

    return False, f"Runtime for {language} not available"


def get_language_display_name(language: str) -> str:
    """Get human-readable language name with emoji"""
    return LANGUAGE_NAMES.get(language, language.capitalize())
