"""
test_runner.py
Parallel mutant testing with a WorkerPool.
Each worker gets its own persistent project copy — copytree runs once per worker,
not once per mutant. Captures the exact test that killed each mutant.
"""
import ast
import os
import re
import shutil
import tempfile
import asyncio
from pathlib import Path
from typing import Optional
from mutation_engine import Mutant

# ── Tuning constants ────────────────────────────────────────────────────────
MUTANT_TIMEOUT = 20                           # seconds per mutant pytest run
MAX_WORKERS    = min(4, max(1, (os.cpu_count() or 2)))  # cap at 4 parallel slots

# ── Mutation operator → actionable hint (no LLM required) ──────────────────
_HINTS: dict[str, str] = {
    "AOR": "Test with values where {desc} gives a different result — pick inputs that distinguish +, -, and * outcomes.",
    "ROR": "Test the EXACT threshold. For '{desc}': write one test on each side and one at the boundary value itself.",
    "LCR": "Test where both conditions disagree (one True, one False) — this exposes an and/or swap.",
    "BCR": "Explicitly assert True or False; don't rely on truthiness — the mutant flips the boolean.",
    "RVR": "Assert the return value equals a specific expected value, not just that it is not None.",
    "SDL": "Verify the deleted statement's side-effect happened — state change, call occurred, exception raised.",
    "BVM": "Test N-1, N, and N+1 for '{desc}'. Off-by-one bugs are caught only at the exact boundary.",
    "NIM": "Call with None for this argument and assert that TypeError or ValueError is raised.",
    "EHM": "Assert the correct exception type is raised and the message is correct.",
    "DFM": "Use clearly distinct values for each parameter to expose argument-swap bugs.",
    "SCM": "Assert the exact string value case-sensitively; also test empty string and the opposite status.",
    "LMO": "Test with empty list, single-item list, and multi-item list; verify first and last are included.",
    "AMO": "Use pytest-asyncio; assert the awaited result is correct, not the coroutine object.",
    "AIM": "Mock the external call and assert the correct method (.get/.post/.save) is invoked with correct args.",
    "TCM": "Test with a value where type conversion changes the result — e.g. int(3/2)=1 vs 3/2=1.5.",
    "DVM": "Test the function with and without the decorator applied to verify it changes behaviour.",
    "CEM": "Test with the env var both set and unset; verify the correct default is used when unset.",
    "CMR": "Use distinct values for each pair of parameters to expose cross-method argument swaps.",
}

_PRIORITY: dict[str, str] = {
    "AOR": "high",   "ROR": "high",   "SDL": "high",   "BVM": "high",
    "LCR": "medium", "BCR": "medium", "RVR": "medium", "NIM": "medium",
    "EHM": "medium", "DFM": "medium", "LMO": "medium", "AIM": "medium",
    "TCM": "medium", "CMR": "medium",
    "SCM": "low",    "AMO": "low",    "DVM": "low",    "CEM": "low",
}


def mutation_hint(operator: str, description: str) -> str:
    template = _HINTS.get(operator, "Write a test that specifically exercises the '{desc}' change.")
    return template.format(desc=description)


def mutation_priority(operator: str) -> str:
    return _PRIORITY.get(operator, "medium")


# ── Worker pool ─────────────────────────────────────────────────────────────

class WorkerPool:
    """
    Maintains N persistent project copies.
    Workers are acquired before running a mutant and released after.
    copytree is called once per worker at setup, not once per mutant.
    """

    def __init__(self, project_root: Path, n: int):
        self.project_root = project_root
        self.n = n
        self._queue: asyncio.Queue = asyncio.Queue()
        self._roots: list[str] = []

    async def setup(self):
        """Create all worker directories in parallel (I/O bound)."""
        loop = asyncio.get_event_loop()
        roots = await asyncio.gather(
            *[loop.run_in_executor(None, self._make_copy) for _ in range(self.n)]
        )
        for r in roots:
            self._roots.append(r)
            self._queue.put_nowait(Path(r))

    def _make_copy(self) -> str:
        tmp = tempfile.mkdtemp(prefix="qamill_")
        shutil.copytree(
            str(self.project_root), tmp,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".git", "node_modules",
                ".pytest_cache", "*.egg-info", "*.dist-info",
            ),
        )
        return tmp

    async def acquire(self) -> Path:
        return await self._queue.get()

    def release(self, path: Path):
        self._queue.put_nowait(path)

    def teardown(self):
        for d in self._roots:
            shutil.rmtree(d, ignore_errors=True)
        self._roots.clear()


# ── Test runner ─────────────────────────────────────────────────────────────

class TestRunner:
    def __init__(self, project_root: str, test_command: str | None = None):
        self.project_root = Path(project_root)
        self.test_command  = test_command  # not used directly; we call pytest
        self._pool: Optional[WorkerPool] = None

    # ── Pool lifecycle ───────────────────────────────────────────────────────

    async def setup_pool(self, n_workers: int):
        self._pool = WorkerPool(self.project_root, n_workers)
        await self._pool.setup()

    def teardown_pool(self):
        if self._pool:
            self._pool.teardown()
            self._pool = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def run_baseline(self) -> bool:
        """Run the test suite on the original code. Must pass before mutation."""
        proc = await asyncio.create_subprocess_exec(
            "pytest", "--tb=no", "-q",
            cwd=str(self.project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(proc.communicate(), timeout=120)
            return proc.returncode == 0
        except asyncio.TimeoutError:
            return False

    async def run_mutant(self, mutant: Mutant) -> tuple[str, dict | None]:
        """
        Acquire a worker slot, inject mutant, run tests, restore, release.
        Returns (status, killer_info | None).
        """
        if not self._pool:
            raise RuntimeError("WorkerPool not initialised — call setup_pool() first")
        worker = await self._pool.acquire()
        try:
            return await self._run_in(mutant, worker)
        finally:
            self._pool.release(worker)

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _run_in(self, mutant: Mutant, worker: Path) -> tuple[str, dict | None]:
        rel    = Path(mutant.file_path).relative_to(self.project_root)
        target = worker / rel
        backup = target.read_text(encoding="utf-8")
        try:
            self._inject(target, mutant)
            return await self._execute(worker)
        finally:
            target.write_text(backup, encoding="utf-8")  # always restore

    def _inject(self, target: Path, mutant: Mutant):
        """
        Replace the mutated function in the copied file.
        Strategy 1: direct string replacement.
        Strategy 2: AST-guided line-range replacement.
        Strategy 3: no-op (mutant survives safely).
        """
        source = target.read_text(encoding="utf-8")

        if mutant.original_src in source:
            target.write_text(
                source.replace(mutant.original_src, mutant.mutant_src, 1),
                encoding="utf-8",
            )
            return

        try:
            tree  = ast.parse(source)
            lines = source.splitlines(keepends=True)
            for node in ast.walk(tree):
                if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name == mutant.function_name):
                    s  = node.lineno - 1
                    e  = node.end_lineno
                    mt = mutant.mutant_src
                    if not mt.endswith("\n"):
                        mt += "\n"
                    target.write_text("".join(lines[:s] + [mt] + lines[e:]), encoding="utf-8")
                    return
        except Exception:
            pass  # strategy 3: leave unchanged

    async def _execute(self, project_dir: Path) -> tuple[str, dict | None]:
        """
        Run pytest with verbose output so we can extract the killer test name.
        -x  : stop after first failure (fastest kill confirmation)
        -v  : verbose test IDs in output
        --tb=line : one-line traceback (enough to parse test name)
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "pytest", "-x", "--tb=line", "-v", "--no-header", "-q",
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(), timeout=MUTANT_TIMEOUT + 5
            )
            if proc.returncode != 0:
                return "killed", self._parse_killer(stdout.decode(errors="replace"))
            return "survived", None
        except asyncio.TimeoutError:
            return "error", None
        except Exception:
            return "error", None

    @staticmethod
    def _parse_killer(output: str) -> dict | None:
        """Extract the test that failed from pytest -v output."""
        for line in output.splitlines():
            # "FAILED tests/test_foo.py::test_name" or "FAILED tests/test_foo.py::test_name - msg"
            m = re.match(r"FAILED\s+([\w./\\-]+\.py)::([\w\[\]-]+)", line.strip())
            if m:
                return {
                    "test_file": Path(m.group(1)).name,
                    "test_name": m.group(2),
                }
        # looser fallback — any line containing FAILED and ::
        for line in output.splitlines():
            if "FAILED" in line and "::" in line:
                for token in line.strip().split():
                    if "::" in token:
                        parts = token.split("::")
                        return {
                            "test_file": Path(parts[0]).name,
                            "test_name": parts[-1].split()[0],
                        }
        return None
