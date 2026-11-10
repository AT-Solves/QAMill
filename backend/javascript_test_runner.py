"""
JavaScript Test Runner - Execute Jest tests and track mutation kill/survive status
"""
import asyncio
import subprocess
import json
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from language_adapters.base_adapter import Mutant


class JestTestRunner:
    """Execute Jest tests for mutation testing"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.temp_dir = None
        # Extra environment for test processes (e.g. NODE_PATH pointing at the
        # original node_modules when running in an isolated copy).
        self.extra_env: Optional[Dict[str, str]] = None

    @staticmethod
    def _jest_command() -> List[str]:
        """
        Build the command that launches Jest.

        Running the npm shim (jest.CMD on Windows) goes through cmd.exe and then
        node. A timeout kill only stops cmd.exe, so grandchildren keep the output
        pipes open and subprocess.run blocks forever. Running Jest's entry script
        directly under node lets the timeout kill the real process.
        """
        jest_path = shutil.which("jest")
        node_path = shutil.which("node")
        if jest_path and node_path:
            candidate = Path(jest_path).parent / "node_modules" / "jest" / "bin" / "jest.js"
            if not candidate.exists():
                real = Path(os.path.realpath(jest_path))
                candidate = real if real.suffix == ".js" else None
            if candidate is not None and candidate.exists():
                return [node_path, str(candidate)]
        return [jest_path or "jest"]

    def run_tests(
        self, test_files: List[str] = None, coverage: bool = False
    ) -> Dict:
        """
        Run Jest tests.
        Returns: {
            "status": "success" | "failed" | "error",
            "passed": int,
            "failed": int,
            "total": int,
            "error": Optional[str],
            "coverage": Optional[Dict]
        }
        """
        try:
            cmd = self._jest_command() + ["--json", "--runInBand"]

            if coverage:
                cmd.append("--coverage")

            if test_files:
                cmd.extend(test_files)

            # Output goes to a temp file, not a pipe. If the timeout kills Jest
            # while a child still holds a pipe open, subprocess.run would block
            # forever and freeze the whole backend event loop.
            with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as out_file:
                result = subprocess.run(
                    cmd,
                    cwd=str(self.project_path),
                    stdout=out_file,
                    stderr=subprocess.DEVNULL,
                    env={**os.environ, **self.extra_env} if self.extra_env else None,
                    timeout=60,
                )
                out_file.seek(0)
                stdout_text = out_file.read()

            # Parse Jest JSON output
            try:
                data = json.loads(stdout_text)
                return {
                    "status": "success" if result.returncode == 0 else "failed",
                    "passed": data.get("numPassedTests", 0),
                    "failed": data.get("numFailedTests", 0),
                    "total": data.get("numTotalTests", 0),
                    "suites": data.get("numTotalTestSuites", 0),
                    "duration": data.get("testResults", [{}])[0].get("perfStats", {}).get(
                        "end", 0
                    ),
                    "error": None,
                }
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                    "error": f"Jest output parsing failed: {stdout_text[:200]}",
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "error": "Jest tests timed out (60s limit)",
            }
        except FileNotFoundError:
            return {
                "status": "error",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "error": "Jest not found. Install: npm install --save-dev jest",
            }
        except Exception as e:
            return {
                "status": "error",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "error": str(e),
            }

    async def test_mutant(
        self, mutant: Mutant, test_files: List[str]
    ) -> Dict:
        """
        Apply mutant and test against it.
        Returns: {
            "status": "killed" | "survived" | "error",
            "test_result": Dict (from run_tests),
            "error": Optional[str]
        }
        """
        # Create temp file for mutant
        temp_file = None
        try:
            # Backup original
            backup_path = Path(mutant.file_path)
            backup_content = backup_path.read_text()

            # Write mutant
            backup_path.write_text(mutant.mutant_src)

            # Validate syntax
            valid, syntax_error = self._validate_syntax(mutant.mutant_src)
            if not valid:
                backup_path.write_text(backup_content)
                return {
                    "status": "error",
                    "test_result": {
                        "status": "error",
                        "passed": 0,
                        "failed": 0,
                        "total": 0,
                        "error": f"Syntax error in mutant: {syntax_error}",
                    },
                    "error": syntax_error,
                }

            # Run tests against mutant
            # Run Jest in a worker thread: the blocking subprocess call would
            # otherwise freeze the server's event loop for the whole job.
            result = await asyncio.to_thread(self.run_tests, test_files)

            # Restore original
            backup_path.write_text(backup_content)

            # A runner failure (Jest missing, timeout, unparseable output) is an
            # execution error, not evidence that the tests missed the mutant.
            if result.get("status") == "error":
                return {
                    "status": "error",
                    "test_result": result,
                    "error": result.get("error"),
                }

            # Determine if mutant was killed
            mutant_status = "survived" if result.get("failed", 0) == 0 else "killed"

            return {
                "status": mutant_status,
                "test_result": result,
                "error": None,
            }

        except Exception as e:
            # Restore original on error
            if Path(mutant.file_path).exists():
                try:
                    Path(mutant.file_path).write_text(backup_content)
                except:
                    pass

            return {
                "status": "error",
                "test_result": {
                    "status": "error",
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                    "error": str(e),
                },
                "error": str(e),
            }

    def _validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate JavaScript syntax"""
        try:
            result = subprocess.run(
                ["node", "-c"],
                input=code,
                capture_output=True,
                timeout=5,
                text=True,
            )
            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr or "Syntax error"
        except:
            return True, None  # Continue if validation fails (assume OK)


class VitestTestRunner:
    """Execute Vitest tests (modern, Vite-native)"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def run_tests(self, test_files: List[str] = None) -> Dict:
        """Run Vitest tests"""
        try:
            cmd = ["vitest", "run", "--reporter=json"]

            if test_files:
                cmd.extend(test_files)

            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                timeout=60,
                text=True,
            )

            try:
                data = json.loads(result.stdout)
                return {
                    "status": "success" if result.returncode == 0 else "failed",
                    "passed": data.get("numPassedTests", 0),
                    "failed": data.get("numFailedTests", 0),
                    "total": data.get("numTotalTests", 0),
                    "error": None,
                }
            except:
                return {
                    "status": "error",
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                    "error": "Vitest output parsing failed",
                }

        except FileNotFoundError:
            return {
                "status": "error",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "error": "Vitest not found. Install: npm install --save-dev vitest",
            }
        except Exception as e:
            return {
                "status": "error",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "error": str(e),
            }


class MochaTestRunner:
    """Execute Mocha tests"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def run_tests(self, test_files: List[str] = None) -> Dict:
        """Run Mocha tests"""
        try:
            cmd = ["mocha", "--reporter", "json"]

            if test_files:
                cmd.extend(test_files)

            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                timeout=60,
                text=True,
            )

            try:
                data = json.loads(result.stdout)
                return {
                    "status": "success" if result.returncode == 0 else "failed",
                    "passed": data.get("stats", {}).get("passes", 0),
                    "failed": data.get("stats", {}).get("failures", 0),
                    "total": data.get("stats", {}).get("tests", 0),
                    "error": None,
                }
            except:
                return {
                    "status": "error",
                    "passed": 0,
                    "failed": 0,
                    "total": 0,
                    "error": "Mocha output parsing failed",
                }

        except FileNotFoundError:
            return {
                "status": "error",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "error": "Mocha not found. Install: npm install --save-dev mocha",
            }
        except Exception as e:
            return {
                "status": "error",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "error": str(e),
            }
