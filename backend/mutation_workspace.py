"""
mutation_workspace.py
Isolated, disposable copies of a project for mutation execution.

Mutants are written into the copy only. The original project is never
modified, so an interrupted or killed job cannot leave a mutant in a source
file. Each job gets its own temporary directory, so parallel jobs never share
files.
"""
import os
import shutil
import tempfile
from pathlib import Path

_IGNORE = shutil.ignore_patterns(
    ".git", "node_modules", "qamill-reports", "__pycache__",
    ".pytest_cache", "*.pyc",
)


class IsolatedProject:
    """A temporary copy of a project. Call cleanup() when the job ends."""

    def __init__(self, source_root: Path, workspace: Path):
        self.source_root = source_root
        self.workspace = workspace
        self.root = workspace / "project"

    def file_in_copy(self, file_path: str) -> Path:
        """Map a file inside the original project to its copy."""
        original = Path(file_path).resolve()
        relative = original.relative_to(self.source_root)  # ValueError if outside
        return self.root / relative

    def node_path(self) -> str | None:
        """Original node_modules, exposed to the copy via NODE_PATH (not copied)."""
        modules = self.source_root / "node_modules"
        return str(modules) if modules.is_dir() else None

    def cleanup(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)


def isolated_copy(project_root: str) -> IsolatedProject:
    source = Path(project_root).resolve()
    if not source.is_dir():
        raise ValueError(f"Project root not found: {project_root}")
    workspace = Path(tempfile.mkdtemp(prefix="qamill_job_"))
    try:
        shutil.copytree(source, workspace / "project", ignore=_IGNORE, dirs_exist_ok=True)
    except Exception:
        shutil.rmtree(workspace, ignore_errors=True)
        raise
    return IsolatedProject(source, workspace)
