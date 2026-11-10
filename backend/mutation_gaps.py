"""
mutation_gaps.py
Mutation gap records: the bridge from mutation analysis to test generation.

After a mutation job finishes, its surviving mutants are written to
  <project>/qamill-reports/mutation-gaps-<file stem>.json
Test generation (gap-driven mode) reads that file and asks the LLM for tests that
would kill each surviving mutant. Only real survivors are ever written here.
"""
import difflib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from test_runner import mutation_hint, mutation_priority

_SKIP_DIRS = {"node_modules", "qamill-reports", ".git", "__pycache__", ".pytest_cache"}
_TEST_PATTERNS = ("test_*.py", "*_test.py", "*.test.js", "*.spec.js", "*.test.ts", "*.spec.ts")
_WHY_SURVIVED = (
    "Every existing test passed against this mutated code, so no assertion "
    "distinguishes the original behaviour from the mutated behaviour."
)
MAX_CONTEXT_CHARS = 6000


def gap_file_path(project_root: str, file_path: str) -> Path:
    stem = Path(file_path).stem
    return Path(project_root) / "qamill-reports" / f"mutation-gaps-{stem}.json"


def _changed_lines(original: str, mutated: str, limit: int = 3) -> tuple[str, str]:
    """Return the first changed original and mutated lines (the actual edit)."""
    orig_lines, mut_lines = original.splitlines(), mutated.splitlines()
    matcher = difflib.SequenceMatcher(a=orig_lines, b=mut_lines, autojunk=False)
    old_out, new_out = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        old_out.extend(orig_lines[i1:i2])
        new_out.extend(mut_lines[j1:j2])
        if len(old_out) >= limit and len(new_out) >= limit:
            break
    return "\n".join(old_out[:limit]).strip(), "\n".join(new_out[:limit]).strip()


def build_gap_records(survived: Iterable, source: str) -> list[dict]:
    """Turn surviving Mutant objects into gap records (no invented content)."""
    records = []
    source_lines = source.count("\n")
    for m in survived:
        # JS mutants hold the whole mutated file; Python mutants hold only the
        # mutated function. Compare against the matching original text.
        if abs(m.mutant_src.count("\n") - source_lines) <= 2:
            original_code, mutated_code = _changed_lines(source, m.mutant_src)
        else:
            original_code, mutated_code = _changed_lines(m.original_src, m.mutant_src)
        hint = mutation_hint(m.operator, m.description)
        records.append({
            "mutant_id": m.id,
            "operator": m.operator,
            "function": m.function_name,
            "line": m.line_no,
            "change": m.description,
            "original_code": original_code[:600],
            "mutated_code": mutated_code[:600],
            "priority": mutation_priority(m.operator),
            "why_survived": _WHY_SURVIVED,
            "missing_assertion": hint,
            "expected_behaviour": (
                f"A test must fail when line {m.line_no} changes from "
                f"'{original_code[:200]}' to '{mutated_code[:200]}'."
            ),
        })
    return records


def write_gap_file(project_root: str, file_path: str, job_id: str, total: int,
                   killed: int, records: list[dict]) -> Path:
    path = gap_file_path(project_root, file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "file": Path(file_path).name,
        "job_id": job_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": total,
        "killed": killed,
        "survived": len(records),
        "gaps": records,
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def load_gap_file(project_root: str, file_path: str) -> Optional[dict]:
    path = gap_file_path(project_root, file_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _test_files(project_root: Path) -> list[Path]:
    found = []
    for pattern in _TEST_PATTERNS:
        for p in project_root.rglob(pattern):
            if not any(part in _SKIP_DIRS for part in p.parts):
                found.append(p)
    return sorted(set(found))


def existing_test_context(project_root: str) -> str:
    """Existing test source, truncated, used as coverage context for the LLM."""
    root = Path(project_root)
    chunks, used = [], 0
    for p in _test_files(root):
        text = p.read_text(encoding="utf-8", errors="replace")
        block = f"# {p.relative_to(root)}\n{text}\n"
        if used + len(block) > MAX_CONTEXT_CHARS:
            block = block[: max(0, MAX_CONTEXT_CHARS - used)]
        chunks.append(block)
        used += len(block)
        if used >= MAX_CONTEXT_CHARS:
            break
    return "\n".join(chunks)


def existing_test_names(project_root: str) -> set[str]:
    """Normalised names of tests that already exist (for duplicate detection)."""
    names = set()
    for p in _test_files(Path(project_root)):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"def\s+test_(\w+)", text):
            names.add(normalise_title(m.group(1)))
        for m in re.finditer(r"\b(?:it|test)\s*\(\s*(['\"`])(.+?)\1", text):
            names.add(normalise_title(m.group(2)))
    return names


def normalise_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(title).lower())
