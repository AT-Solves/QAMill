"""
test_generator.py
Extends QAMill beyond mutation testing into test *authoring*:

  1. generate_unit_tests(...)   → a complete pytest suite for a source file,
                                  verified to import and pass against the original.
  2. generate_manual_tests(...) → a structured manual QA test suite (human-readable
                                  cases: id, title, preconditions, steps, expected,
                                  priority) for testers who don't run code.

Mirrors auto_healer.py's prompt → LLM → parse → verify pattern, and reuses the
same LLM adapter interface (llm_adapter.create_adapter).
"""
from __future__ import annotations

import ast
import asyncio
import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _llm_err_msg(e: Exception, provider: str) -> str:
    """Turn an opaque LLM/httpx error into actionable guidance."""
    from llm_adapter import LLMProviderError
    if isinstance(e, LLMProviderError):
        return str(e)  # already the user-facing text, e.g. quota vs rate limit
    txt = str(e).lower()
    if provider == "inhouse" and ("timeout" in txt or "timed out" in txt or txt.strip() == ""):
        return ("Local Ollama timed out generating the suite — large test suites are slow on CPU. "
                "Try again, use a smaller file, or switch to Claude/GPT-4o for fast results.")
    if "connect" in txt or "refused" in txt:
        return ("Could not reach the LLM. For Ollama, ensure it is running ('ollama serve'); "
                "for cloud providers, check your API key and internet connection.")
    return f"LLM error while generating tests: {e}" if str(e) else \
           "The LLM did not respond. Try again or switch providers."


# ── Source inspection ────────────────────────────────────────────────────────

def _public_functions(source: str) -> list[str]:
    """Return top-level + class method names worth testing (skip private/dunder)."""
    names: list[str] = []

    # Try Python parsing first
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    names.append(node.name)
        return names
    except SyntaxError:
        pass

    # If Python parsing failed, try JavaScript regex patterns
    # Match: function name(...) { or const/let name = (...) =>
    patterns = [
        r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(',  # function name()
        r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s*)?\(',  # const name = ()
        r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s*)?function',  # const name = function
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, source):
            name = match.group(1)
            if not name.startswith("_"):
                if name not in names:
                    names.append(name)

    return names


# ── Unit test generation ──────────────────────────────────────────────────────

UNIT_PROMPT = """\
You are an expert Python test engineer. Write a COMPLETE pytest unit-test suite
for the module below. Cover every public function with: happy-path cases, edge
cases (empty, zero, negative, boundary), and error cases (invalid input, raises).

MODULE NAME : {module_name}
SOURCE CODE:
```python
{source}
```

FUNCTIONS TO COVER: {functions}

REQUIREMENTS (mandatory):
  - Import everything you test from `{module_name}`:  from {module_name} import ...
  - Use plain pytest — `def test_*()` functions and `assert`. Use
    `pytest.raises(...)` for expected exceptions. No external fixtures or mocking
    unless the code genuinely requires it.
  - Every test must PASS against the ORIGINAL code shown above (use the real
    return values — do not invent behaviour).
  - Use concrete literal inputs and expected values.
  - Group with clear test names: test_<function>_<scenario>.
  - Add a one-line comment above each test stating what it checks.

RESPOND WITH A SINGLE PYTHON CODE BLOCK ONLY — no prose outside it:
```python
import pytest
from {module_name} import ...

def test_...():
    ...
```"""


@dataclass
class UnitTestResult:
    success:    bool
    test_code:  str
    verified:   bool            # True = suite imported and passed against original
    passed:     int = 0
    failed:     int = 0
    message:    str = ""
    module_name: str = ""


class TestGenerator:
    def __init__(self, llm_adapter, project_root: str, user_email: str = "", fallback_llm=None):
        self.llm = llm_adapter
        self.fallback_llm = fallback_llm  # Ollama as fallback if primary fails
        self.project_root = Path(project_root)
        self.user_email = user_email
        # Provider actually used for the last call; set when a fallback runs,
        # so a switch away from the chosen provider is always reported.
        self.provider_used = llm_adapter.name
        self.fallback_reason: Optional[str] = None

    def _record_fallback(self, reason: str) -> None:
        self.provider_used = f"{self.fallback_llm.name} (fallback)"
        self.fallback_reason = f"{self.llm.name} failed: {reason}"

    async def _call_llm_with_fallback(self, prompt: str, max_tokens: int = 500) -> str:
        """Try primary LLM, fall back to Ollama if it fails or returns garbage."""
        import sys
        import asyncio
        print(f"[DEBUG] Calling {self.llm.name} with {len(prompt)} char prompt...", file=sys.stderr, flush=True)

        try:
            # Timeout varies by provider: cloud (30s), local Ollama (300s)
            timeout_seconds = 300.0 if self.llm.name == "inhouse" else 30.0
            try:
                result = await asyncio.wait_for(self.llm.call_async(prompt, max_tokens=max_tokens), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                print(f"[DEBUG] {self.llm.name} TIMEOUT ({timeout_seconds}s) - falling back to Ollama", file=sys.stderr, flush=True)
                raise Exception(f"{self.llm.name} timed out after {timeout_seconds} seconds")
            print(f"[DEBUG] {self.llm.name} returned {len(result)} chars", file=sys.stderr, flush=True)

            # Validate response has actual code/test content
            result_clean = result.strip() if result else ""
            has_code_indicators = any(indicator in result for indicator in ["def ", "```", "import ", "class ", "async def"])
            has_minimum_length = len(result_clean) > 50

            print(f"[DEBUG] Response validation: clean={bool(result_clean)}, code={has_code_indicators}, len={len(result_clean)}", file=sys.stderr, flush=True)

            if result_clean and has_code_indicators and has_minimum_length:
                print(f"[DEBUG] Response valid, returning from {self.llm.name}", file=sys.stderr, flush=True)
                return result

            # Invalid response - try fallback
            if self.fallback_llm and self.fallback_llm.name != self.llm.name:
                print(f"[DEBUG] Response invalid! Falling back to Ollama...", file=sys.stderr, flush=True)
                self._record_fallback("returned an unusable response")
                fallback_result = await self.fallback_llm.call_async(prompt, max_tokens=max_tokens)
                print(f"[DEBUG] Ollama returned {len(fallback_result)} chars", file=sys.stderr, flush=True)
                return fallback_result

            print(f"[DEBUG] No fallback available, returning invalid response", file=sys.stderr, flush=True)
            return result
        except Exception as e:
            print(f"[DEBUG] {self.llm.name} exception: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr, flush=True)
            if self.fallback_llm and self.fallback_llm.name != self.llm.name:
                print(f"[DEBUG] Trying fallback Ollama...", file=sys.stderr, flush=True)
                self._record_fallback(str(e)[:200])
                try:
                    fallback_result = await self.fallback_llm.call_async(prompt, max_tokens=max_tokens)
                    print(f"[DEBUG] Ollama fallback returned {len(fallback_result)} chars", file=sys.stderr, flush=True)
                    return fallback_result
                except Exception as fallback_e:
                    error_msg = f"Primary ({self.llm.name}) and fallback (Ollama) both failed. Primary: {str(e)[:50]}... Ollama: {str(fallback_e)[:50]}..."
                    print(f"[DEBUG] BOTH FAILED: {error_msg}", file=sys.stderr, flush=True)
                    raise Exception(error_msg)
            raise

    # ── Unit tests ───────────────────────────────────────────────────────
    async def generate_unit_tests(self, file_path: str, verify: bool = True) -> UnitTestResult:
        path = Path(file_path)
        source = path.read_text(encoding="utf-8")
        module_name = path.stem
        functions = _public_functions(source)

        if self.llm.name == "none":
            return UnitTestResult(False, "", False,
                message="Select an LLM provider (Claude, GPT-4o, Grok, or Ollama) to generate unit tests.",
                module_name=module_name)
        if not functions:
            return UnitTestResult(False, "", False,
                message="No public functions found to test in this file.",
                module_name=module_name)

        prompt = UNIT_PROMPT.format(
            module_name=module_name, source=source,
            functions=", ".join(functions),
        )
        try:
            raw = await self._call_llm_with_fallback(prompt)
            if self.user_email:
                from usage_tracker import tracker
                tracker.track_usage(self.user_email, self.llm.name, tokens_used=len(prompt.split()), task="unit_tests")
        except Exception as e:
            return UnitTestResult(False, "", False,
                message=(_llm_err_msg(e, self.llm.name)), module_name=module_name)

        test_code = self._extract_code(raw)
        if not test_code:
            return UnitTestResult(False, "", False,
                message="The model did not return a usable test block. Try again.",
                module_name=module_name)

        if not verify:
            return UnitTestResult(True, test_code, False,
                message="Generated (not verified).", module_name=module_name)

        passed, failed, ok = await self._verify_against_original(path, source, test_code)
        return UnitTestResult(
            success=True, test_code=test_code, verified=ok,
            passed=passed, failed=failed, module_name=module_name,
            message=(f"Verified — {passed} passed against the original code."
                     if ok else
                     f"Generated, but {failed} test(s) did not pass against the original — review before committing."),
        )

    def _get_test_file_ext(self, file_path: str) -> str:
        """Determine test file extension based on source file type."""
        if file_path.endswith((".js", ".jsx")):
            return ".test.js"
        elif file_path.endswith((".ts", ".tsx")):
            return ".test.ts"
        else:
            return "_generated.py"  # Python default

    def _get_test_runner(self, file_path: str) -> tuple[str, list[str]]:
        """Get test runner command based on file type."""
        if file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            # Jest for JavaScript/TypeScript
            return "npx", ["jest", "--no-coverage", "--silent"]
        else:
            # pytest for Python
            return "pytest", ["-q", "--tb=no"]

    async def _verify_against_original(self, path: Path, source: str,
                                       test_code: str) -> tuple[int, int, bool]:
        """Run the generated suite against the ORIGINAL source; tests should pass."""
        with tempfile.TemporaryDirectory(prefix="amil_unit_") as tmpdir:
            tmp = Path(tmpdir)
            (tmp / path.name).write_text(source, encoding="utf-8")

            # Determine test file naming based on language
            test_ext = self._get_test_file_ext(str(path))
            if test_ext == "_generated.py":
                test_file = tmp / f"test_{path.stem}_generated.py"
            else:
                test_file = tmp / f"{path.stem}{test_ext}"

            test_file.write_text(test_code, encoding="utf-8")

            try:
                runner_cmd, args = self._get_test_runner(str(path))
                cmd = [runner_cmd] + args + [str(test_file)]

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=str(tmp),
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
                text = out.decode(errors="replace")
                passed = self._count(text, "passed")
                failed = self._count(text, "failed") + self._count(text, "error")
                return passed, failed, (proc.returncode == 0 and passed > 0)
            except Exception:
                return 0, 0, False

    @staticmethod
    def _count(text: str, word: str) -> int:
        m = re.search(rf"(\d+)\s+{word}", text)
        return int(m.group(1)) if m else 0

    # ── Manual test suite ────────────────────────────────────────────────
    async def generate_manual_tests(self, file_path: str, gap_driven: bool = False) -> dict:
        if gap_driven:
            return await self.generate_gap_tests(file_path)
        path = Path(file_path)
        source = path.read_text(encoding="utf-8")
        module_name = path.stem

        if self.llm.name == "none":
            return {"success": False, "cases": [],
                    "message": "Select an LLM provider to generate a manual test suite."}

        prompt = MANUAL_PROMPT.format(module_name=module_name, source=source)
        try:
            # A full manual suite is JSON of 1-2k tokens; the 500-token default
            # cut every response off mid-array.
            raw = await self._call_llm_with_fallback(prompt, max_tokens=MANUAL_TESTS_MAX_TOKENS)
            if self.user_email:
                from usage_tracker import tracker
                tracker.track_usage(self.user_email, self.llm.name, tokens_used=len(prompt.split()), task="manual_tests")
        except Exception as e:
            return self._llm_failure(e)

        cases = self._extract_json_cases(raw)
        if not cases:
            return {"success": False, "cases": [],
                    "message": "The model did not return usable test cases. Try again."}
        # Normalise + assign IDs
        for i, c in enumerate(cases, 1):
            c.setdefault("id", f"TC-{i:03d}")
            c.setdefault("priority", "Medium")
            c.setdefault("preconditions", "")
            c.setdefault("steps", [])
            c.setdefault("expected", "")

        # Format content for display in webview
        content = json.dumps(cases, indent=2)

        return {"success": True, "cases": cases, "module": module_name,
                "content": content, "format": "test_case",
                "message": f"{len(cases)} manual test cases generated."}

    def _llm_failure(self, e: Exception) -> dict:
        """
        Failure result for a provider error. Never switches providers: it only
        reports the error code and whether a local Ollama alternative is ready,
        so the user can decide.
        """
        from llm_adapter import LLMProviderError, ollama_status
        result = {"success": False, "cases": [], "message": _llm_err_msg(e, self.llm.name),
                  "provider": self.llm.name, "error_code": None, "offer_ollama": False}
        if isinstance(e, LLMProviderError):
            result["error_code"] = e.code
            if self.llm.name != "inhouse":  # Ollama is already the alternative
                result["offer_ollama"] = bool(ollama_status().get("available"))
        return result

    async def generate_gap_tests(self, file_path: str) -> dict:
        """
        Gap-driven generation: write tests that would kill the surviving mutants
        recorded by the last mutation analysis of this file.
        Nothing is invented: no gap record means no generation.
        """
        from mutation_gaps import (load_gap_file, existing_test_context,
                                   existing_test_names, normalise_title)
        path = Path(file_path)
        source = path.read_text(encoding="utf-8")
        module_name = path.stem

        if self.llm.name == "none":
            return {"success": False, "cases": [],
                    "message": "Select an LLM provider to generate gap-driven tests."}

        gap_doc = load_gap_file(str(self.project_root), file_path)
        if gap_doc is None:
            return {"success": False, "cases": [],
                    "message": "No mutation analysis results for this file. Run mutation analysis first, then generate gap-driven tests."}
        gaps = gap_doc.get("gaps", [])
        if not gaps:
            return {"success": False, "cases": [],
                    "message": "Mutation analysis found no surviving mutants for this file, so there are no gaps to target."}

        rank = {"high": 0, "medium": 1, "low": 2}
        ordered = sorted(gaps, key=lambda g: rank.get(g.get("priority"), 1))
        batch = ordered[:GAP_BATCH_SIZE]
        valid_ids = {g["mutant_id"] for g in batch}

        prompt = GAP_PROMPT.format(
            module_name=module_name,
            source=source,
            existing_tests=existing_test_context(str(self.project_root)) or "(no existing tests found)",
            gaps=json.dumps(batch, indent=2),
        )
        try:
            raw = await self._call_llm_with_fallback(prompt, max_tokens=MANUAL_TESTS_MAX_TOKENS)
            if self.user_email:
                from usage_tracker import tracker
                tracker.track_usage(self.user_email, self.llm.name, tokens_used=len(prompt.split()), task="gap_tests")
        except Exception as e:
            return self._llm_failure(e)

        candidates = self._extract_json_cases(raw)
        existing = existing_test_names(str(self.project_root))
        seen, kept, duplicates, unlinked = set(), [], 0, 0
        for c in candidates:
            if not isinstance(c, dict):
                continue
            linked = [i for i in (c.get("mutation_ids") or []) if i in valid_ids]
            if not linked:
                unlinked += 1          # not tied to a real surviving mutant
                continue
            key = normalise_title(c.get("title", ""))
            if not key or key in existing or key in seen:
                duplicates += 1        # duplicates an existing or generated test
                continue
            seen.add(key)
            c["mutation_ids"] = linked
            c.setdefault("priority", "Medium")
            c.setdefault("preconditions", "")
            c.setdefault("steps", [])
            c.setdefault("expected", "")
            c.setdefault("objective", "")
            c.setdefault("coverage_gap", "")
            kept.append(c)

        if not kept:
            return {"success": False, "cases": [],
                    "message": f"No usable gap-driven test cases (duplicates: {duplicates}, not linked to a surviving mutation: {unlinked}). Try again."}

        for i, c in enumerate(kept, 1):
            c["id"] = f"TC-{i:03d}"
        return {
            "success": True, "cases": kept, "module": module_name,
            "content": json.dumps(kept, indent=2), "format": "test_case",
            "gap_driven": True,
            "gaps_targeted": len(batch), "gaps_total": len(gaps),
            "provider_used": self.provider_used, "fallback_reason": self.fallback_reason,
            "duplicates_removed": duplicates, "unlinked_removed": unlinked,
            "message": (f"{len(kept)} gap-driven test cases for {len(batch)} of {len(gaps)} surviving mutations"
                        f" (removed: {duplicates} duplicate, {unlinked} not linked to a mutation)."),
        }

    # ── Gherkin (BDD) ────────────────────────────────────────────────────
    async def generate_gherkin(self, file_path: str) -> dict:
        path = Path(file_path); source = path.read_text(encoding="utf-8")
        module_name = path.stem
        if self.llm.name == "none":
            return {"success": False, "content": "", "message": "Select an LLM provider first."}
        try:
            prompt = GHERKIN_PROMPT.format(module_name=module_name, source=source)
            raw = await self._call_llm_with_fallback(prompt)
            if self.user_email:
                from usage_tracker import tracker
                tracker.track_usage(self.user_email, self.llm.name, tokens_used=len(prompt.split()), task="gherkin")
        except Exception as e:
            return {"success": False, "content": "", "message": _llm_err_msg(e, self.llm.name)}
        m = re.search(r"```(?:gherkin)?\s*(.*?)```", raw, re.DOTALL)
        content = (m.group(1).strip() if m else raw.strip())
        if "Feature:" not in content:
            return {"success": False, "content": "", "message": "No valid Gherkin returned. Try again."}
        return {"success": True, "content": content, "module": module_name,
                "message": "Gherkin feature generated."}

    # ── Traceability matrix ──────────────────────────────────────────────
    async def generate_traceability(self, file_path: str) -> dict:
        path = Path(file_path); source = path.read_text(encoding="utf-8")
        module_name = path.stem
        if self.llm.name == "none":
            return {"success": False, "rows": [], "message": "Select an LLM provider first."}
        try:
            prompt = TRACEABILITY_PROMPT.format(module_name=module_name, source=source)
            raw = await self._call_llm_with_fallback(prompt)
            if self.user_email:
                from usage_tracker import tracker
                tracker.track_usage(self.user_email, self.llm.name, tokens_used=len(prompt.split()), task="traceability")
        except Exception as e:
            return {"success": False, "rows": [], "message": _llm_err_msg(e, self.llm.name)}
        rows = self._extract_json_cases(raw)
        if not rows:
            return {"success": False, "rows": [], "message": "No matrix rows returned. Try again."}
        return {"success": True, "rows": rows, "module": module_name,
                "message": f"{len(rows)} traceability rows generated."}

    # ── Unified dispatch by format ───────────────────────────────────────
    async def generate_suite(self, file_path: str, fmt: str, verify: bool = True,
                             gap_driven: bool = False) -> dict:
        """
        Returns a normalised dict the UI can render directly:
          {success, format, lang, content, module, verified?, passed?, failed?, message}
        """
        meta = SUITE_FORMATS.get(fmt, SUITE_FORMATS["test_case"])
        base = {"format": fmt, "lang": meta["lang"], "ext": meta["ext"]}

        if fmt == "unit":
            r = await self.generate_unit_tests(file_path, verify=verify)
            return {**base, "success": r.success, "content": r.test_code,
                    "module": r.module_name, "verified": r.verified,
                    "passed": r.passed, "failed": r.failed, "message": r.message,
                    "filename": f"test_{r.module_name}.py"}

        if fmt == "gherkin":
            r = await self.generate_gherkin(file_path)
            return {**base, "success": r["success"], "content": r.get("content", ""),
                    "module": r.get("module", ""), "message": r["message"],
                    "filename": f"{r.get('module','suite')}.feature"}

        if fmt == "traceability":
            r = await self.generate_traceability(file_path)
            content = traceability_to_markdown(r.get("rows", []), r.get("module", "")) if r["success"] else ""
            return {**base, "success": r["success"], "content": content,
                    "module": r.get("module", ""), "rows": r.get("rows", []),
                    "message": r["message"], "filename": f"traceability-{r.get('module','suite')}.md"}

        # test_case OR table — both come from structured manual cases
        r = await self.generate_manual_tests(file_path, gap_driven=gap_driven)
        if not r["success"]:
            details = {k: r[k] for k in ("provider", "error_code", "offer_ollama") if k in r}
            return {**base, "success": False, "content": "", "message": r["message"], **details}
        if fmt == "table":
            content = manual_cases_to_table(r["cases"], r.get("module", ""))
        else:
            content = manual_cases_to_markdown(r["cases"], r.get("module", ""))
        gap_meta = {k: r[k] for k in ("gap_driven", "gaps_targeted", "gaps_total", "duplicates_removed",
                                       "unlinked_removed", "provider_used", "fallback_reason") if k in r}
        return {**base, "success": True, "content": content,
                "module": r.get("module", ""), "cases": r["cases"], "message": r["message"],
                "filename": f"test-suite-{r.get('module','suite')}.md", **gap_meta}

    # ── Parsing helpers ──────────────────────────────────────────────────
    @staticmethod
    def _extract_code(raw: str) -> Optional[str]:
        import sys
        # Prefer a ```python fence, then any ``` fence — keep the block INTACT
        # (never line-filter; that corrupts multi-line constructs like @parametrize).
        m = re.search(r"```python\s*(.*?)```", raw, re.DOTALL)
        if m:
            code = m.group(1).strip()
        else:
            m2 = re.search(r"```\s*(.*?)```", raw, re.DOTALL)
            if m2:
                code = m2.group(1).strip()
            else:
                # No fence — take from the first code line to the end, verbatim.
                # This handles Ollama and other models that output raw code without fences.
                lines = raw.split("\n")
                code_keywords = ("import ", "from ", "def ", "@", "class ", "async ", "if ", "try ", "with ")
                # Find first non-comment, non-empty code line
                start = None
                for i, l in enumerate(lines):
                    stripped = l.lstrip()
                    if stripped and not stripped.startswith(("#", "//")):
                        if any(stripped.startswith(kw) for kw in code_keywords):
                            start = i
                            break
                if start is not None:
                    code = "\n".join(lines[start:]).strip()
                    print(f"[DEBUG] Extracted code from line {start}, length={len(code)}", file=sys.stderr, flush=True)
                else:
                    # Last resort: take everything non-comment
                    code_lines = [l for l in lines if l.strip() and not l.lstrip().startswith("#")]
                    code = "\n".join(code_lines).strip()
                    print(f"[DEBUG] No clear code start found, using content-based extraction", file=sys.stderr, flush=True)
        if not code:
            print(f"[DEBUG] No code extracted from response", file=sys.stderr, flush=True)
            return None
        # Validate it parses as Python; if not, it's unusable — signal failure.
        try:
            ast.parse(code)
            print(f"[DEBUG] Code parsing successful, {len(code)} chars valid Python", file=sys.stderr, flush=True)
        except SyntaxError as e:
            print(f"[DEBUG] SyntaxError parsing extracted code: {e}", file=sys.stderr, flush=True)
            print(f"[DEBUG] Attempted to parse: {code[:300]}...", file=sys.stderr, flush=True)
            return None
        return code

    @staticmethod
    def _repair_json(blob: str) -> str:
        """
        Repair incomplete/malformed JSON from Ollama using robust multi-strategy approach.
        Uses the JSONRepair class for intelligent repair with multiple fallback strategies.
        """
        import sys
        from json_repair import JSONRepair

        print(f"[DEBUG] Starting robust JSON repair with multiple strategies...", file=sys.stderr, flush=True)

        try:
            # Use robust JSON repair with multiple strategies (up to 5 attempts)
            data, was_repaired = JSONRepair.repair(blob, max_attempts=5)

            if was_repaired:
                print(f"[DEBUG] JSON repaired successfully after multiple attempts", file=sys.stderr, flush=True)
                # Convert back to string for json.loads in calling function
                return json.dumps(data)
            else:
                print(f"[DEBUG] JSON parsed on first try (no repair needed)", file=sys.stderr, flush=True)
                return blob

        except Exception as e:
            print(f"[DEBUG] Robust repair failed with error: {e}", file=sys.stderr, flush=True)
            print(f"[DEBUG] Falling back to simple emergency repair", file=sys.stderr, flush=True)

            # Fallback to simple repair if robust repair fails
            return TestGenerator._simple_repair_json(blob)

    @staticmethod
    def _simple_repair_json(blob: str) -> str:
        """
        Simple fallback repair for emergency cases.
        Only tries basic bracket/brace closing.
        """
        import sys
        blob = blob.strip()

        # Close unclosed brackets
        open_brackets = blob.count('[')
        close_brackets = blob.count(']')
        if open_brackets > close_brackets:
            blob += ']' * (open_brackets - close_brackets)
            print(f"[DEBUG] Added {open_brackets - close_brackets} closing bracket(s)", file=sys.stderr, flush=True)

        # Close unclosed braces
        open_braces = blob.count('{')
        close_braces = blob.count('}')
        if open_braces > close_braces:
            blob += '}' * (open_braces - close_braces)
            print(f"[DEBUG] Added {open_braces - close_braces} closing brace(s)", file=sys.stderr, flush=True)

        # Remove trailing commas
        blob = re.sub(r',(\s*[}\]])', r'\1', blob)

        return blob

    @staticmethod
    def _extract_json_cases(raw: str) -> list[dict]:
        import sys
        from json_repair import JSONRepair

        # Prefer a fenced ```json block, else the first [...] array
        m = re.search(r"```json\s*(.*?)```", raw, re.DOTALL)
        blob = m.group(1).strip() if m else None
        if blob is None:
            # Try any code fence with possible language
            m_fence = re.search(r"```\s*(?:json)?\s*(.*?)```", raw, re.DOTALL)
            blob = m_fence.group(1).strip() if m_fence else None
        if blob is None:
            # Last resort: find [...] array
            m2 = re.search(r"(\[.*)", raw, re.DOTALL)
            blob = m2.group(1) if m2 else None
        if not blob:
            print(f"[DEBUG] No JSON block found in response, raw length={len(raw)}", file=sys.stderr, flush=True)
            return []

        # Try parsing first
        try:
            data = json.loads(blob)
            result = data if isinstance(data, list) else []
            print(f"[DEBUG] Successfully parsed {len(result)} cases from JSON (first try)", file=sys.stderr, flush=True)
            return result
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON parse error (first try): {e}", file=sys.stderr, flush=True)

        # If first try failed, attempt repair
        print(f"[DEBUG] Attempting JSON repair for Ollama incomplete output...", file=sys.stderr, flush=True)
        repaired = TestGenerator._repair_json(blob)
        try:
            data = json.loads(repaired)
            result = data if isinstance(data, list) else []
            print(f"[DEBUG] Successfully parsed {len(result)} cases from repaired JSON", file=sys.stderr, flush=True)
            return result
        except json.JSONDecodeError as e:
            # Never substitute invented cases: keep only objects the model
            # actually completed. An unrecoverable response yields no cases, and
            # the caller reports that to the user as a failure.
            print(f"[DEBUG] JSON parse error (after repair): {e}", file=sys.stderr, flush=True)
            salvaged = TestGenerator._salvage_complete_cases(blob)
            if salvaged:
                print(f"[WARNING] LLM response was truncated; recovered {len(salvaged)} complete test case(s).", file=sys.stderr, flush=True)
                return salvaged
            print(f"[ERROR] Could not parse test cases from LLM response: {e}", file=sys.stderr, flush=True)
            return []

    @staticmethod
    def _salvage_complete_cases(blob: str) -> list[dict]:
        """
        Recover the complete objects from a truncated JSON array.
        Tries each closing brace from the end, closes the array there, and keeps
        the first candidate that parses. Only objects the model finished are kept.
        """
        start = blob.find("[")
        if start == -1:
            return []
        body = blob[start:]
        for end in reversed([m.end() for m in re.finditer(r"\}", body)]):
            candidate = body[:end].rstrip().rstrip(",") + "]"
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                return [c for c in data if isinstance(c, dict)]
        return []


# Output budget for a manual test suite (JSON array of test cases).
MANUAL_TESTS_MAX_TOKENS = 2500
# Surviving mutants sent per gap-driven request (highest priority first).
GAP_BATCH_SIZE = 5

GAP_PROMPT = """\
You are a senior QA engineer. The module "{module_name}" is covered by an existing
test suite, which was run against deliberately mutated copies of the code. Each
mutation listed below SURVIVED: every existing test still passed on the mutated code.

Write NEW test cases that would FAIL on each mutated behaviour and PASS on the
original behaviour. For each gap:
- Target exactly the behaviour that changed (boundary values, negative inputs,
  swapped arguments, changed strings or operators, as the gap describes).
- Do NOT repeat any test that already exists (see EXISTING TESTS).
- Make each step concrete (inputs and the observable result).

Return ONLY a JSON array. Each element has these keys:
  "title", "objective", "priority" (High|Medium|Low), "preconditions",
  "steps" (array of strings), "expected", "coverage_gap",
  "mutation_ids" (array; use only IDs from the GAPS list).

EXISTING TESTS:
{existing_tests}

MODULE SOURCE:
{source}

GAPS (surviving mutations):
{gaps}
"""


MANUAL_PROMPT = """\
You are a senior QA engineer. From the Python module below, produce a MANUAL test
suite a human tester (who cannot read code) could execute. Focus on observable
behaviour, business rules, boundaries, and failure conditions.

MODULE: {module_name}
SOURCE:
```python
{source}
```

Return STRICT JSON — an array of test cases, each with:
  - "id"           : short id like "TC-001"
  - "title"        : what is being verified, plain language
  - "priority"     : "High" | "Medium" | "Low"
  - "preconditions": setup/state required before the steps (string)
  - "steps"        : array of plain-language action strings
  - "expected"     : the expected observable result (string)

Cover happy paths, edge/boundary values, and error conditions. 8-15 cases.

RESPOND WITH A SINGLE JSON CODE BLOCK ONLY:
```json
[
  {{"id":"TC-001","title":"...","priority":"High","preconditions":"...","steps":["...","..."],"expected":"..."}}
]
```"""


GHERKIN_PROMPT = """\
You are a BDD specialist. From the Python module below, write a Gherkin feature
file describing its behaviour as Scenarios using Given / When / Then.

MODULE: {module_name}
SOURCE:
```python
{source}
```

Cover happy paths, edge/boundary values, and error conditions. Use Scenario
Outlines with Examples tables where it reduces repetition.

RESPOND WITH A SINGLE gherkin CODE BLOCK ONLY:
```gherkin
Feature: {module_name}
  As a developer
  I want ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```"""


TRACEABILITY_PROMPT = """\
You are a QA lead building a Requirements Traceability Matrix. Infer the
requirements each function implements, then map them to test cases.

MODULE: {module_name}
SOURCE:
```python
{source}
```

Return STRICT JSON — an array of rows, each with:
  - "req_id"     : like "REQ-01"
  - "requirement": the behaviour/rule in plain language
  - "function"   : the function that implements it
  - "test_id"    : like "TC-01"
  - "test_desc"  : what the test verifies
  - "type"       : "Positive" | "Negative" | "Boundary"
  - "priority"   : "High" | "Medium" | "Low"

One requirement may map to several test rows. 10-20 rows.

RESPOND WITH A SINGLE JSON CODE BLOCK ONLY:
```json
[
  {{"req_id":"REQ-01","requirement":"...","function":"...","test_id":"TC-01","test_desc":"...","type":"Positive","priority":"High"}}
]
```"""


# Friendly format registry — drives the UI selector and dispatch.
SUITE_FORMATS = {
    "unit":         {"label": "Unit Tests (pytest)",   "lang": "python",   "ext": "py"},
    "test_case":    {"label": "Test Case format",       "lang": "markdown", "ext": "md"},
    "table":        {"label": "Table format",           "lang": "markdown", "ext": "md"},
    "gherkin":      {"label": "Gherkin (BDD)",           "lang": "gherkin",  "ext": "feature"},
    "traceability": {"label": "Traceability matrix",     "lang": "markdown", "ext": "md"},
}


def manual_cases_to_table(cases: list[dict], module: str = "") -> str:
    """Render manual cases as a Markdown table."""
    lines = [f"# Test Suite (Table) — {module}", "",
             "| ID | Title | Priority | Preconditions | Steps | Expected |",
             "|----|-------|----------|---------------|-------|----------|"]
    for c in cases:
        steps = "<br>".join(f"{i}. {s}" for i, s in enumerate(c.get("steps", []), 1))
        row = [c.get("id", ""), c.get("title", ""), c.get("priority", "Medium"),
               (c.get("preconditions", "") or "—").replace("|", "\\|"),
               steps.replace("|", "\\|"), (c.get("expected", "") or "").replace("|", "\\|")]
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def traceability_to_markdown(rows: list[dict], module: str = "") -> str:
    """Render a requirements traceability matrix as a Markdown table."""
    lines = [f"# Requirements Traceability Matrix — {module}", "",
             "| Req ID | Requirement | Function | Test ID | Test Description | Type | Priority |",
             "|--------|-------------|----------|---------|------------------|------|----------|"]
    for r in rows:
        cells = [r.get("req_id", ""), r.get("requirement", ""), r.get("function", ""),
                 r.get("test_id", ""), r.get("test_desc", ""), r.get("type", ""), r.get("priority", "")]
        lines.append("| " + " | ".join(str(x).replace("|", "\\|") for x in cells) + " |")
    return "\n".join(lines)


def manual_cases_to_markdown(cases: list[dict], module: str = "") -> str:
    """Render manual cases as a Markdown document for export."""
    lines = [f"# Manual Test Suite — {module}", ""]
    for c in cases:
        lines.append(f"## {c.get('id','')} — {c.get('title','')}")
        lines.append(f"**Priority:** {c.get('priority','Medium')}")
        if c.get("mutation_ids"):
            lines.append(f"**Mutation(s):** {', '.join(c['mutation_ids'])}")
        if c.get("objective"):
            lines.append(f"**Objective:** {c['objective']}")
        if c.get("coverage_gap"):
            lines.append(f"**Coverage gap:** {c['coverage_gap']}")
        if c.get("preconditions"):
            lines.append(f"**Preconditions:** {c['preconditions']}")
        lines.append("**Steps:**")
        for i, s in enumerate(c.get("steps", []), 1):
            # Models often number their own steps; avoid "1. 1. ..." in the output.
            step_text = re.sub(r"^\s*\d+[.)]\s*", "", str(s))
            lines.append(f"{i}. {step_text}")
        lines.append(f"**Expected:** {c.get('expected','')}")
        lines.append("")
    return "\n".join(lines)
