"""
auto_healer.py
Game Changer 2: Takes a survived mutant, asks LLM to write a test
that kills it, verifies the test actually kills it, returns the
validated test ready to commit.
"""
import re
import json
import asyncio
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from mutation_engine import Mutant
from difficulty_ranker import DifficultyRanker


EXPLAIN_PROMPT = """\
You are QAMill, a mutation testing expert assistant.

A mutation testing tool found this SURVIVED MUTANT — the existing tests did NOT catch this change.

Original function (correct):
```python
{original_src}
```

Mutant (the change that was not caught):
```python
{mutant_src}
```

Mutation applied: {description}

In 2-3 sentences explain:
1. What this mutation represents as a real-world bug a developer could ship
2. Why the existing tests missed it (what input or condition they never checked)
3. What specific input value would expose this bug

Be specific and practical. Reference the actual code. No jargon."""


HEAL_PROMPT = """\
You are an expert Python test engineer. Write one pytest test that kills a specific mutant.

ORIGINAL FUNCTION (correct — your test must PASS against this):
```python
{original}
```

MUTANT FUNCTION (the bug — your test must FAIL against this):
```python
{mutant}
```

THE CHANGE : {description}
FUNCTION   : {fn_name}
MODULE     : {module_name}
TEST NAME  : test_{fn_name}_kills_{mutant_id}

DESIGN PROCESS — work through this before writing:
  1. What exactly changed? ({description})
  2. Find one concrete input where original and mutant return different values.
  3. What does the original return for that input? That is your expected value.
  4. Write the assert using those exact values.

REQUIREMENTS (all are mandatory):
  - Import  : from {module_name} import {fn_name}
  - Name    : def test_{fn_name}_kills_{mutant_id}():
  - Input   : concrete literals only — no variables, no fixtures, no mocking
  - Assert  : exactly one assertion
  - Verify  : original({your_input}) == {your_expected} PASS
              mutant({your_input})   == {your_expected} FAIL

RESPOND WITH A SINGLE PYTHON CODE BLOCK — no explanation outside the block:
```python
from {module_name} import {fn_name}

def test_{fn_name}_kills_{mutant_id}():
    assert {fn_name}(...) == ...
```"""


@dataclass
class HealResult:
    success: bool
    test_code: str
    verified: bool       # True = test was confirmed to kill the mutant
    message: str


class AutoHealer:
    def __init__(self, llm_adapter, project_root: str):
        self.llm = llm_adapter
        self.project_root = Path(project_root)

    async def explain(self, mutant: Mutant) -> str:
        """Ask LLM to explain what the survived mutant means as a real bug."""
        if self.llm.name == "none":
            return ""
        try:
            prompt = EXPLAIN_PROMPT.format(
                original_src=mutant.original_src,
                mutant_src=mutant.mutant_src,
                description=mutant.description,
            )
            return await self.llm.call_async(prompt, max_tokens=300)
        except Exception:
            return ""

    async def rank_difficulty(self, mutant: Mutant) -> dict:
        """Delegate to DifficultyRanker. Returns dict with difficulty + reason."""
        result = await DifficultyRanker().rank(mutant, self.llm)
        return {"difficulty": result.difficulty, "reason": result.reason}

    async def heal(self, mutant: Mutant, max_attempts: int = 3) -> HealResult:
        """
        Attempt up to max_attempts times to generate a verified killing test.
        """
        for attempt in range(1, max_attempts + 1):
            test_code = await self._generate_test(mutant)
            if not test_code:
                continue

            verified = await self._verify_test_kills_mutant(mutant, test_code)
            if verified:
                return HealResult(
                    success=True,
                    test_code=test_code,
                    verified=True,
                    message=f"Verified on attempt {attempt}"
                )

        # Return last generated test even if unverified
        test_code = await self._generate_test(mutant)
        return HealResult(
            success=True,
            test_code=test_code or "",
            verified=False,
            message="Generated but not verified — review before committing"
        )

    async def _generate_test(self, mutant: Mutant) -> Optional[str]:
        try:
            module_name = Path(mutant.file_path).stem
            prompt = HEAL_PROMPT.format(
                original=mutant.original_src,
                mutant=mutant.mutant_src,
                description=mutant.description,
                fn_name=mutant.function_name,
                mutant_id=mutant.id.lower(),
                module_name=module_name,
            )
            raw = await self.llm.call_async(prompt, max_tokens=600)

            # Extract code block
            match = re.search(r"```python\s*(.*?)```", raw, re.DOTALL)
            if match:
                return match.group(1).strip()

            # Fallback: if no fences, take all lines starting with def/import
            lines = [l for l in raw.split("\n")
                     if l.strip().startswith(("def ", "import ", "from ", "assert", "    "))]
            return "\n".join(lines).strip() or None

        except Exception:
            return None

    async def _verify_test_kills_mutant(self, mutant: Mutant,
                                        test_code: str) -> bool:
        """
        Run the generated test against the mutant source.
        If the test fails (exit != 0) → it kills the mutant → verified.
        """
        with tempfile.TemporaryDirectory(prefix="amil_verify_") as tmpdir:
            tmp = Path(tmpdir)

            # Write the mutant version of the file
            rel_path = Path(mutant.file_path).relative_to(self.project_root)
            module_file = tmp / rel_path.name
            module_file.write_text(mutant.mutant_src)

            # Write the generated test file
            test_file = tmp / f"test_amil_{mutant.id}.py"
            # Patch import to use local module
            module_name = rel_path.stem
            patched = test_code.replace(
                f"from {rel_path.parent}.{module_name} import",
                f"from {module_name} import"
            ).replace(
                f"from {module_name} import",
                f"from {module_name} import"
            )
            test_file.write_text(patched)

            try:
                proc = await asyncio.create_subprocess_exec(
                    "pytest", str(test_file), "--tb=no", "-q",
                    cwd=str(tmp),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                # Non-zero = test failed against mutant = test kills the mutant
                return proc.returncode != 0
            except Exception:
                return False
