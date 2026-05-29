"""
difficulty_ranker.py
Standalone module for classifying how hard a survived mutant is to kill.
Used by AutoHealer; can also be imported directly for batch ranking.
"""
import re
import json
from dataclasses import dataclass

from mutation_engine import Mutant


DIFFICULTY_PROMPT = """\
You are a mutation testing expert classifying a survived mutant.

MUTATION UNDER ANALYSIS:
  Function  : {function_name}
  Change    : {description}

Original (correct behaviour):
```python
{original}
```

Mutant (the bug that survived):
```python
{mutant}
```

CLASSIFICATION TASK:
How hard is it for a developer to write a test that distinguishes mutant from original?

DIFFICULTY DEFINITIONS — use exactly one:
  low    → A standard happy-path test already covers the affected input range.
            The mutation survived only because a basic case was never written.
            Example: add(2, 3) was never asserted after + was changed to -.
  medium → A specific boundary value or targeted edge case is required.
            The developer must study the mutation to design the right input.
            Example: is_positive(0) needed after > 0 changed to >= 0.
  high   → Requires deep algorithmic knowledge, a rare input combination, or
            understanding of how multiple conditions interact.
            Example: a compound boolean in a loop that only triggers on step N.

RISK SCALE 1–10 (independent of difficulty):
  1–3  Low    — cosmetic, obvious in code review, unlikely production impact.
  4–6  Medium — wrong output in edge cases, likely noticed in testing.
  7–10 High   — silent wrong output, security implication, or data corruption.

SELF-CHECK before writing your JSON:
  [ ] Does my reason name the specific change ({description})?
  [ ] Does my difficulty reflect the actual code, not a generic statement?
  [ ] Is risk_score consistent with production impact, not just code complexity?

RESPOND WITH VALID JSON ONLY — no text before or after the braces:
{{"difficulty": "low|medium|high", "reason": "one sentence referencing {description} and why it is hard or easy to catch", "risk_score": <integer 1-10>}}"""


@dataclass
class DifficultyResult:
    difficulty: str      # low | medium | high
    reason: str
    risk_score: int      # 1–10


class DifficultyRanker:
    async def rank(self, mutant: Mutant, llm_adapter) -> DifficultyResult:
        """
        Classify difficulty and risk of a survived mutant.
        Falls back to medium/5 when LLM is unavailable.
        """
        if llm_adapter is None or llm_adapter.name == "none":
            return DifficultyResult(
                difficulty="medium",
                reason="No LLM configured — defaulting to medium",
                risk_score=5,
            )
        try:
            prompt = DIFFICULTY_PROMPT.format(
                function_name=mutant.function_name,
                description=mutant.description,
                original=mutant.original_src,
                mutant=mutant.mutant_src,
            )
            raw = await llm_adapter.call_async(prompt, max_tokens=200)
            clean = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(clean)
            return DifficultyResult(
                difficulty=data.get("difficulty", "medium"),
                reason=data.get("reason", ""),
                risk_score=int(data.get("risk_score", 5)),
            )
        except Exception:
            return DifficultyResult(
                difficulty="medium",
                reason="Could not classify difficulty",
                risk_score=5,
            )
