"""
ai_mutant_generator.py
AI-powered semantic mutant generator.
Goes beyond AST operator swapping — asks the LLM to invent
realistic bugs a developer might accidentally introduce.
Operator prefix: AI
"""
import ast
import json
import re
from typing import List

import astor

from mutation_engine import Mutant

_PROMPT_TEMPLATE = """\
You are a mutation testing expert. Here is a Python function:

{function_source}

Generate 5 realistic mutations that represent bugs a developer might accidentally introduce.
These should be SEMANTIC bugs, not just operator swaps. Focus on:
- Wrong boundary conditions (off-by-one: n-1, n, n+1)
- Incorrect variable usage (swapping parameter names)
- Missing edge case handling (removing a guard clause)
- Logic inversions (flipping a condition)
- Wrong return value (returning a related but incorrect expression)

GROUNDING RULES:
- Every original_line MUST be an exact line that appears in the function source above.
- Every mutated_line must be a plausible accidental change to that exact line.
- line_no must be the actual line number within the function (1 = def line).
- Do NOT invent lines that do not exist in the function.

For each mutation respond with a JSON array (no other text):
[
  {{
    "description": "plain English description of what changed",
    "original_line": "the exact original line as it appears above",
    "mutated_line": "the mutated version of that line",
    "operator": "AI",
    "line_no": <integer>
  }}
]

Respond with ONLY the JSON array, nothing else."""


class AIMutantGenerator:
    async def generate(self, file_path: str, llm_adapter) -> List[Mutant]:
        """
        For each function in file_path, ask the LLM to produce semantic mutants.
        Returns a list of Mutant objects ready for the analysis pipeline.
        """
        if llm_adapter is None or llm_adapter.name == "none":
            return []

        with open(file_path) as f:
            source = f.read()

        tree = ast.parse(source)
        mutants: List[Mutant] = []
        counter = 0

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            fn_src = astor.to_source(node)
            items = await self._query_llm(fn_src, llm_adapter)

            for item in items:
                mutant_src = self._apply_mutation(
                    fn_src,
                    item.get("original_line", ""),
                    item.get("mutated_line", ""),
                )
                if mutant_src is None:
                    continue

                counter += 1
                mutants.append(Mutant(
                    id=f"AI{counter:04d}",
                    file_path=file_path,
                    function_name=node.name,
                    line_no=node.lineno + item.get("line_no", 1) - 1,
                    operator="AI",
                    description=item.get("description", "AI semantic mutation"),
                    original_src=fn_src,
                    mutant_src=mutant_src,
                ))

        return mutants

    async def _query_llm(self, fn_src: str, llm_adapter) -> list:
        try:
            prompt = _PROMPT_TEMPLATE.format(function_source=fn_src)
            raw = await llm_adapter.call_async(prompt, max_tokens=800)
            clean = re.sub(r"```json|```", "", raw).strip()
            # Find the JSON array in the response
            match = re.search(r"\[.*\]", clean, re.DOTALL)
            if not match:
                return []
            data = json.loads(match.group(0))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _apply_mutation(
        self, fn_src: str, original_line: str, mutated_line: str
    ) -> str | None:
        """Replace the first occurrence of original_line with mutated_line."""
        orig = original_line.strip()
        mut = mutated_line.strip()
        if not orig or not mut or orig == mut:
            return None

        lines = fn_src.split("\n")
        for i, line in enumerate(lines):
            if line.strip() == orig:
                indent = len(line) - len(line.lstrip())
                lines[i] = " " * indent + mut
                return "\n".join(lines)

        return None
