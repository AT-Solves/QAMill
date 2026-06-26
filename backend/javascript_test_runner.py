"""
JavaScript Test Runner - Execute Jest tests and track mutation kill/survive status
"""
import subprocess
import json
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
            cmd = ["jest", "--json"]

            if coverage:
                cmd.append("--coverage")

            if test_files:
                cmd.extend(test_files)

            result = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                timeout=60,
                text=True,
            )

            # Parse Jest JSON output
            try:
                data = json.loads(result.stdout)
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
                    "error": f"Jest output parsing failed: {result.stdout[:200]}",
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
            result = self.run_tests(test_files)

            # Restore original
            backup_path.write_text(backup_content)

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
