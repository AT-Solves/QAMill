"""
test_runner.py
Applies a mutant to a temp copy of the file, runs the existing
test suite, captures result. Original source is NEVER modified.
"""
import ast
import os
import re
import json
import shutil
import tempfile
import subprocess
import asyncio
from pathlib import Path
from mutation_engine import Mutant


class TestRunner:
    def __init__(self, project_root: str, test_command: str = None):
        self.project_root = Path(project_root)
        self.test_command = test_command or self._detect_test_command()

    def _detect_test_command(self) -> str:
        root = self.project_root
        if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
            return "pytest --tb=no -q --json-report --json-report-file=.amil_report.json"
        if (root / "package.json").exists():
            return "npm test -- --json"
        if (root / "pom.xml").exists():
            return "mvn test -q"
        if (root / "build.gradle").exists():
            return "gradle test"
        # Default to pytest
        return "pytest --tb=no -q --json-report --json-report-file=.amil_report.json"

    async def run_mutant(self, mutant: Mutant) -> str:
        """
        Returns: "killed" | "survived" | "error"
        Creates temp dir, injects mutant, runs tests, cleans up.
        """
        with tempfile.TemporaryDirectory(prefix="amil_") as tmpdir:
            # Copy entire project to temp dir (read-only original preserved)
            tmp_project = Path(tmpdir) / "project"
            shutil.copytree(self.project_root, tmp_project,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                          ".git", "node_modules"))

            # Inject mutant into the copied file
            rel_path = Path(mutant.file_path).relative_to(self.project_root)
            target_file = tmp_project / rel_path

            self._inject_mutant(target_file, mutant)

            # Run test suite
            return await self._execute_tests(tmp_project)

    def _inject_mutant(self, target_file: Path, mutant: Mutant):
        """
        Replace the target function in the file with the mutant version.

        Strategy:
          1. Direct string match (works when source == astor output)
          2. AST-guided line-range replacement (works when astor reformats code)
          3. No-op fallback so the file remains valid (mutant will survive)
        """
        source = target_file.read_text(encoding="utf-8")

        # Strategy 1 — direct match
        if mutant.original_src in source:
            target_file.write_text(
                source.replace(mutant.original_src, mutant.mutant_src, 1),
                encoding="utf-8",
            )
            return

        # Strategy 2 — locate function by name using AST, replace its line range
        try:
            tree = ast.parse(source)
            lines = source.splitlines(keepends=True)
            for node in ast.walk(tree):
                if (isinstance(node, ast.FunctionDef) and
                        node.name == mutant.function_name):
                    start = node.lineno - 1          # 0-indexed, inclusive
                    end   = node.end_lineno          # 0-indexed, exclusive
                    mutant_text = mutant.mutant_src
                    if not mutant_text.endswith("\n"):
                        mutant_text += "\n"
                    new_lines = lines[:start] + [mutant_text] + lines[end:]
                    target_file.write_text("".join(new_lines), encoding="utf-8")
                    return
        except Exception:
            pass

        # Strategy 3 — leave unchanged (safe fallback; mutant will survive)

    async def _execute_tests(self, project_dir: Path) -> str:
        cmd = self.test_command.split()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=60
            )

            # Non-zero exit = at least one test failed = mutant KILLED
            if proc.returncode != 0:
                return "killed"

            # All tests passed = mutant SURVIVED
            return "survived"

        except asyncio.TimeoutError:
            return "error"
        except Exception:
            return "error"

    async def run_baseline(self) -> bool:
        """Run tests on original code — must pass before mutation starts."""
        cmd = self.test_command.split()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        return proc.returncode == 0
