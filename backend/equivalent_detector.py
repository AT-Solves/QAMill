"""
equivalent_detector.py
3-stage pipeline: rule-based → Z3 solver → LLM judge.
Returns classification: equivalent | real | unknown
"""
import re
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class EquivalenceResult:
    equivalent: bool
    confidence: str      # high | medium | low
    method: str          # rule | z3 | llm | none
    reason: str
    counterexample: Optional[str] = None


# ── Stage 1: Rule-based patterns (instant, free) ───────────────────────────

KNOWN_EQUIVALENT_REWRITES = [
    # Pattern: (find in original, find in mutant) — normalised source strings
    (r"- 1\b",       r"\+ \(-1\)"),   # x - 1  ≡  x + (-1)
    (r"\+ 0\b",      r""),             # x + 0  ≡  x
    (r"\* 1\b",      r""),             # x * 1  ≡  x
    (r"not not ",    r""),             # not not x  ≡  x
    (r"== True\b",   r""),             # x == True  ≡  x (bool context)
    (r"is True\b",   r""),             # x is True  ≡  x
    (r"// 1\b",      r""),             # x // 1  ≡  x (int)
]

# Operators that are always structurally equivalent when swapped here
STRUCTURAL_EQUIV_PAIRS = [
    ("i += 1", "i = i + 1"),
    ("i -= 1", "i = i - 1"),
]


def _normalize(src: str) -> str:
    return " ".join(src.split())


def rule_based_check(original_src: str, mutant_src: str) -> Optional[EquivalenceResult]:
    norm_orig = _normalize(original_src)
    norm_mut  = _normalize(mutant_src)

    # Structural string equivalence after normalization
    for a, b in STRUCTURAL_EQUIV_PAIRS:
        if a in norm_orig and b in norm_mut:
            return EquivalenceResult(
                equivalent=True, confidence="high", method="rule",
                reason=f"Structural rewrite: '{a}' ≡ '{b}'"
            )

    # Regex pattern matching
    for orig_pat, mut_pat in KNOWN_EQUIVALENT_REWRITES:
        if re.search(orig_pat, norm_orig) and re.search(mut_pat, norm_mut):
            return EquivalenceResult(
                equivalent=True, confidence="high", method="rule",
                reason=f"Known equivalent pattern: {orig_pat} ≡ {mut_pat}"
            )

    return None  # Not caught by rules — proceed to next stage


# ── Stage 2: Z3 solver (precise for arithmetic) ────────────────────────────

def z3_check(original_src: str, mutant_src: str) -> Optional[EquivalenceResult]:
    """
    Asks Z3 if two function bodies can produce different results.
    Handles:
      - Simple arithmetic return expressions
      - Single if/else returning constants
      - Comparison-against-literal returns
      - Simple boolean (True/False) returns
    """
    try:
        from z3 import Int, Bool, Solver, unsat, sat, BoolVal, If

        # ── Pattern A: single `return <expr>` ─────────────────────────────
        orig_returns = re.findall(r"\breturn\s+(.+)", original_src)
        mut_returns  = re.findall(r"\breturn\s+(.+)", mutant_src)

        if len(orig_returns) == 1 and len(mut_returns) == 1:
            orig_expr = orig_returns[0].strip()
            mut_expr  = mut_returns[0].strip()

            # Pattern B: returning a plain boolean constant
            bool_map = {"True": True, "False": False}
            if orig_expr in bool_map and mut_expr in bool_map:
                if bool_map[orig_expr] == bool_map[mut_expr]:
                    return EquivalenceResult(
                        equivalent=True, confidence="high", method="z3",
                        reason=f"Both return the same boolean constant {orig_expr}"
                    )
                return EquivalenceResult(
                    equivalent=False, confidence="high", method="z3",
                    reason=f"Return values differ: {orig_expr} vs {mut_expr}",
                    counterexample="any input"
                )

            # Pattern C: arithmetic expression (no keywords, no calls)
            all_tokens = orig_expr + " " + mut_expr
            identifiers = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", all_tokens))
            bad_kw = {"True", "False", "None", "not", "and", "or",
                      "if", "else", "in", "is", "len", "range"}
            if identifiers and not (identifiers & bad_kw):
                z3_vars = {name: Int(name) for name in identifiers}
                try:
                    orig_z3 = eval(orig_expr, {"__builtins__": {}}, dict(z3_vars))
                    mut_z3  = eval(mut_expr,  {"__builtins__": {}}, dict(z3_vars))
                    s = Solver()
                    s.add(orig_z3 != mut_z3)
                    res = s.check()
                    if res == unsat:
                        return EquivalenceResult(
                            equivalent=True, confidence="high", method="z3",
                            reason=f"Z3 proved: '{orig_expr}' == '{mut_expr}' for all inputs"
                        )
                    if res == sat:
                        model = s.model()
                        counter = {str(d): str(model[d]) for d in model}
                        return EquivalenceResult(
                            equivalent=False, confidence="high", method="z3",
                            reason="Z3 found counterexample — mutant is real",
                            counterexample=str(counter)
                        )
                except Exception:
                    pass

        # ── Pattern D: single if/else returning two constants ──────────────
        # Matches: if <cond>:\n    return A\n ... return B
        ifelse = re.search(
            r"if\s+(.+?):\s*\n\s+return\s+(\S+).*?\n.*?return\s+(\S+)",
            original_src, re.DOTALL
        )
        ifelse_m = re.search(
            r"if\s+(.+?):\s*\n\s+return\s+(\S+).*?\n.*?return\s+(\S+)",
            mutant_src, re.DOTALL
        )
        if ifelse and ifelse_m:
            cond_o, ret_o1, ret_o2 = ifelse.groups()
            cond_m, ret_m1, ret_m2 = ifelse_m.groups()
            # If same condition but same pair of return values → equivalent
            if (cond_o.strip() == cond_m.strip() and
                    ret_o1.strip() == ret_m1.strip() and
                    ret_o2.strip() == ret_m2.strip()):
                return EquivalenceResult(
                    equivalent=True, confidence="high", method="z3",
                    reason="if/else returns identical constants under same condition"
                )

        # ── Pattern E: comparison against literal ─────────────────────────
        # e.g.  return n > 0  vs  return n >= 0  — Z3 can disprove equivalence
        cmp_pat = r"return\s+([a-zA-Z_]\w*)\s*([><=!]+)\s*(\d+)"
        orig_cmp = re.search(cmp_pat, original_src)
        mut_cmp  = re.search(cmp_pat, mutant_src)
        if orig_cmp and mut_cmp:
            var_o, op_o, lit_o = orig_cmp.groups()
            var_m, op_m, lit_m = mut_cmp.groups()
            if var_o == var_m:
                v = Int(var_o)
                op_map = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
                          "<": lambda a, b: a < b,  "<=": lambda a, b: a <= b,
                          "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
                if op_o in op_map and op_m in op_map:
                    expr_o = op_map[op_o](v, int(lit_o))
                    expr_m = op_map[op_m](v, int(lit_m))
                    s = Solver()
                    s.add(expr_o != expr_m)
                    res = s.check()
                    if res == unsat:
                        return EquivalenceResult(
                            equivalent=True, confidence="high", method="z3",
                            reason=f"Z3 proved: '{var_o} {op_o} {lit_o}' == '{var_m} {op_m} {lit_m}'"
                        )
                    if res == sat:
                        model = s.model()
                        counter = {str(d): str(model[d]) for d in model}
                        return EquivalenceResult(
                            equivalent=False, confidence="high", method="z3",
                            reason=f"Operators differ: {op_o} vs {op_m} — real mutant",
                            counterexample=str(counter)
                        )

    except Exception:
        pass
    return None


if __name__ == "__main__":
    # ── Test cases proving the upgraded Z3 stage ─────────────────────────────

    print("Z3 stage test cases")
    print("=" * 60)

    # Test 1: arithmetic equivalence (x + 0 == x)
    orig1 = "def f(x):\n    return x + 0\n"
    mut1  = "def f(x):\n    return x\n"
    r1 = z3_check(orig1, mut1)
    print(f"Test 1 - arithmetic (x+0 vs x):     equivalent={r1 and r1.equivalent}  method={r1 and r1.method}")

    # Test 2: boolean constant flip (True vs False)
    orig2 = "def f():\n    return True\n"
    mut2  = "def f():\n    return False\n"
    r2 = z3_check(orig2, mut2)
    print(f"Test 2 - bool constant (True->False): equivalent={r2 and r2.equivalent}  method={r2 and r2.method}")

    # Test 3: comparison against literal — same op, same lit → equiv
    orig3 = "def f(n):\n    return n > 0\n"
    mut3  = "def f(n):\n    return n > 0\n"
    r3 = z3_check(orig3, mut3)
    print(f"Test 3 - same comparison (n>0 vs n>0): equivalent={r3 and r3.equivalent}  method={r3 and r3.method}")

    # Test 4: comparison against literal — different op → real mutant
    orig4 = "def f(n):\n    return n > 0\n"
    mut4  = "def f(n):\n    return n >= 0\n"
    r4 = z3_check(orig4, mut4)
    print(f"Test 4 - different comparison (n>0 vs n>=0): equivalent={r4 and r4.equivalent}  counterexample={r4 and r4.counterexample}")

    print("=" * 60)


# ── Stage 3: LLM semantic judge ────────────────────────────────────────────

LLM_PROMPT = """\
You are a formal program semantics verifier. Determine if two Python functions are equivalent.

ORIGINAL:
```python
{original}
```

MUTANT:
```python
{mutant}
```

EQUIVALENCE DEFINITION:
Two functions are equivalent if and only if for every valid input:
  (a) they return the same value, AND
  (b) they raise the same exceptions under the same conditions, AND
  (c) they have identical observable side effects.

ANALYSIS PROTOCOL — follow these steps in order:
  1. Identify the single syntactic change between original and mutant.
  2. Ask: is there any valid input where this change produces a different output?
  3. If YES → not equivalent. Provide the exact input as counterexample.
  4. If NO  → equivalent. Prove why the change cannot affect any output.

NON-EQUIVALENT PATTERNS — if you recognise any of these, mark equivalent=false:
  - Comparison operator changed (> vs >= vs < vs <=) → differ at boundary value
  - Arithmetic operator changed (+ vs - vs * vs /) → differ for non-zero operands
  - Logical operator changed (and vs or) → differ on (True,False) inputs
  - Equality changed (== vs !=) → always differ
  - Boolean constant flipped (True vs False) → always differ
  - Return value changed to None → always differ unless function never used result

CONFIDENCE GUIDE:
  high   → formal proof or obvious counterexample
  medium → strong reasoning but some edge-case uncertainty
  low    → complex logic, could not fully verify

RESPOND WITH VALID JSON ONLY — no text outside the braces:
{{"equivalent": true|false, "confidence": "high|medium|low", "reason": "one sentence naming the exact change and the input that differs, or why no such input exists", "counterexample_input": "e.g. x=0 or a=1,b=2 — concrete values, or null if equivalent"}}"""


async def llm_check(original_src: str, mutant_src: str,
                    llm_adapter) -> Optional[EquivalenceResult]:
    if llm_adapter is None:
        return None
    try:
        prompt = LLM_PROMPT.format(original=original_src, mutant=mutant_src)
        raw = await llm_adapter.call_async(prompt, max_tokens=300)

        # Strip markdown fences if present
        clean = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(clean)

        return EquivalenceResult(
            equivalent=bool(data.get("equivalent", False)),
            confidence=data.get("confidence", "medium"),
            method="llm",
            reason=data.get("reason", ""),
            counterexample=data.get("counterexample_input"),
        )
    except Exception as e:
        return EquivalenceResult(
            equivalent=False, confidence="low", method="llm",
            reason=f"LLM check failed: {e}"
        )


# ── Orchestrator ───────────────────────────────────────────────────────────

class EquivalentDetector:
    def __init__(self, llm_adapter=None):
        self.llm_adapter = llm_adapter

    async def classify(self, original_src: str,
                       mutant_src: str) -> EquivalenceResult:
        # Stage 1 — rules (sync, instant)
        result = rule_based_check(original_src, mutant_src)
        if result:
            return result

        # Stage 2 — Z3 (sync, arithmetic only)
        result = z3_check(original_src, mutant_src)
        if result:
            return result

        # Stage 3 — LLM (async, complex semantics)
        if self.llm_adapter:
            result = await llm_check(original_src, mutant_src, self.llm_adapter)
            if result:
                return result

        # Conservative fallback — treat as real mutant
        return EquivalenceResult(
            equivalent=False, confidence="low", method="none",
            reason="Could not determine — treated as real mutant"
        )
