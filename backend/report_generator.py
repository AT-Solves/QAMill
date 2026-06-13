"""
report_generator.py
Elite self-contained HTML report generator for QAMill mutation testing results.
Generates a single HTML file with inline CSS and JavaScript — no server required.
"""
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

# ── Operator registry ─────────────────────────────────────────────────────────

OPERATOR_INFO: dict[str, dict] = {
    "AOR": {
        "name": "Arithmetic Operator Replacement",
        "plain": "Tests whether your maths operations are correct",
        "example": "add(a, b) — the + is changed to −",
        "category": "CORE OPERATORS",
    },
    "ROR": {
        "name": "Relational Operator Replacement",
        "plain": "Tests whether your comparisons catch boundaries",
        "example": "if age >= 18 — changed to if age > 18",
        "category": "CORE OPERATORS",
    },
    "LCR": {
        "name": "Logical Connector Replacement",
        "plain": "Tests whether your AND/OR conditions are right",
        "example": "if a and b — changed to if a or b",
        "category": "CORE OPERATORS",
    },
    "BCR": {
        "name": "Boolean Constant Replacement",
        "plain": "Tests whether True/False values are correct",
        "example": "return True — changed to return False",
        "category": "CORE OPERATORS",
    },
    "RVR": {
        "name": "Return Value Replacement",
        "plain": "Tests whether your functions return the right value",
        "example": "return result — changed to return None",
        "category": "CORE OPERATORS",
    },
    "SDL": {
        "name": "Statement Deletion",
        "plain": "Tests whether every line of code is necessary",
        "example": "validate(user) — entire line deleted",
        "category": "STATEMENT LEVEL",
    },
    "NIM": {
        "name": "Null/None Injection",
        "plain": "Tests whether your code handles missing data",
        "example": "process(user) — process(None)",
        "category": "STATEMENT LEVEL",
    },
    "BVM": {
        "name": "Boundary Value Mutation",
        "plain": "Tests whether exact boundary numbers are right",
        "example": "if score >= 90 — if score >= 89",
        "category": "STATEMENT LEVEL",
    },
    "EHM": {
        "name": "Exception Handling Mutation",
        "plain": "Tests whether errors are caught and raised correctly",
        "example": "except ValueError — replaced with pass",
        "category": "STATEMENT LEVEL",
    },
    "DFM": {
        "name": "Data Flow Mutation",
        "plain": "Tests whether the right variables are used",
        "example": "transfer(from, to) — transfer(to, from)",
        "category": "STATEMENT LEVEL",
    },
    "SCM": {
        "name": "String and Constant Mutation",
        "plain": "Tests whether status strings and labels are correct",
        "example": '"active" — changed to "" or "ACTIVE"',
        "category": "STATEMENT LEVEL",
    },
    "LMO": {
        "name": "Loop Mutation Operator",
        "plain": "Tests whether loops process all items correctly",
        "example": "for item in list — for item in list[1:]",
        "category": "ADVANCED",
    },
    "TCM": {
        "name": "Type Coercion Mutation",
        "plain": "Tests whether data types are enforced correctly",
        "example": "int(value) — changed to str(value)",
        "category": "ADVANCED",
    },
    "AMO": {
        "name": "Async Mutation Operator",
        "plain": "Tests whether async/await patterns are correct",
        "example": "await process() — process() (await removed)",
        "category": "ADVANCED",
    },
    "DVM": {
        "name": "Decorator/Visibility Mutation",
        "plain": "Tests whether decorators function correctly",
        "example": "@staticmethod removed from method",
        "category": "ADVANCED",
    },
    "AIM": {
        "name": "API Integration Mutation",
        "plain": "Tests whether external service calls are correct",
        "example": "db.save(x) — changed to db.delete(x)",
        "category": "INTEGRATION & API",
    },
    "CMR": {
        "name": "Cross Method Replacement",
        "plain": "Tests whether methods interact correctly",
        "example": "argument passed between functions changed",
        "category": "INTEGRATION & API",
    },
    "CEM": {
        "name": "Configuration/Environment Mutation",
        "plain": "Tests whether config and env vars are handled",
        "example": "os.environ.get('HOST','local') — 'local'",
        "category": "INTEGRATION & API",
    },
}

RISK_LEVELS: dict[str, str] = {
    "SDL": "HIGH", "DFM": "HIGH", "EHM": "HIGH", "LMO": "HIGH", "NIM": "HIGH",
    "BVM": "MEDIUM", "SCM": "MEDIUM", "AOR": "MEDIUM", "ROR": "MEDIUM",
    "AIM": "MEDIUM", "CEM": "MEDIUM",
    "BCR": "LOW", "RVR": "LOW", "TCM": "LOW", "LCR": "LOW",
    "CMR": "LOW", "AMO": "LOW", "DVM": "LOW",
}

CATEGORY_ORDER = ["CORE OPERATORS", "STATEMENT LEVEL", "INTEGRATION & API", "ADVANCED"]


# ── Grade helpers ─────────────────────────────────────────────────────────────

def _grade_info(score: float) -> tuple[str, str]:
    if score >= 90: return "EXCELLENT", "#3fb950"
    if score >= 75: return "GOOD", "#4ec9a0"
    if score >= 60: return "NEEDS WORK", "#d29922"
    if score >= 40: return "WEAK", "#fb8f44"
    return "CRITICAL", "#f85149"


def _op_status(kill_pct: float) -> str:
    if kill_pct == 0: return "ZERO"
    if kill_pct >= 80: return "STRONG"
    if kill_pct >= 60: return "GOOD"
    if kill_pct >= 40: return "NEEDS WORK"
    return "WEAK"


def _plain_english(mutant: dict) -> str:
    op = mutant.get("operator", "")
    func = mutant.get("function", "")
    desc = mutant.get("description", "")
    templates = {
        "SDL": f"This entire line was removed from {func} — tests still pass",
        "LMO": f"Loop modified in {func} — first or last items may be skipped",
        "BVM": f"Boundary number shifted in {func}: {desc}",
        "NIM": f"None injected as argument in {func} — null input not tested",
        "EHM": f"Exception handling removed in {func} — error path not tested",
        "ROR": f"Comparison operator changed in {func}: {desc}",
        "AOR": f"Arithmetic operator changed in {func}: {desc}",
        "LCR": f"AND/OR condition flipped in {func} — logic boundary not tested",
        "BCR": f"Boolean flipped in {func} — True/False not explicitly checked",
        "RVR": f"Return value changed to None in {func} — return not verified",
        "DFM": f"Arguments swapped in {func} — parameter order not tested",
        "SCM": f"String constant mutated in {func}: {desc}",
        "AIM": f"API method changed in {func} — integration not fully tested",
        "CEM": f"Config bypassed in {func} — environment variable not tested",
        "CMR": f"Cross-method argument changed in {func}",
        "TCM": f"Type cast removed in {func} — type checking not tested",
        "AMO": f"Async keyword removed in {func} — async behavior not tested",
    }
    return templates.get(op, f"Mutation in {func}: {desc}")


def _suggested_fix(mutant: dict) -> str:
    hint = mutant.get("hint")
    if hint:
        return hint
    op = mutant.get("operator", "")
    func = mutant.get("function", "")
    line = mutant.get("line", "?")
    fixes = {
        "SDL": f"Add a test that verifies the deleted statement runs. Assert the side-effect of line {line} in {func}.",
        "LMO": f"Add tests that pass a single-element list and a two-element list. Verify both first and last items are processed by {func}.",
        "BVM": f"Add tests at exact boundary values (0, 1, -1, and the literal boundary). Test both sides of the edge condition in {func}.",
        "NIM": f"Add `with pytest.raises(ValueError): {func}(None)` to verify None inputs are rejected.",
        "EHM": f"Add `with pytest.raises(ZeroDivisionError): {func}(x, 0)` to ensure the exception propagates in {func}.",
        "ROR": f"Add tests at exactly the boundary value. Test `{func}(edge-1)` and `{func}(edge)` separately.",
        "AOR": f"Add tests that verify the exact arithmetic result, not just non-None. `assert {func}(3, 4) == 7`.",
        "LCR": f"Add tests where exactly one condition is true. Both `and`/`or` give different results in {func}.",
        "BCR": f"Add `assert result is True` (not just truthy) in tests for {func}.",
        "RVR": f"Add `assert result is not None` and check exact return value in {func}.",
        "SCM": f"Add exact string equality: `assert {func}() == 'active'` (case-sensitive).",
        "CEM": f"Use `monkeypatch.setenv('KEY', 'value')` and verify {func} uses the env var.",
        "DFM": f"Call `{func}(a, b)` where `a != b` and check the directional result is correct.",
        "AIM": f"Mock the API and verify the correct method is called: `mock.save.assert_called_once()`.",
    }
    return fixes.get(op, f"Add a test that specifically exercises line {line} in {func}.")


def _risk_badge(op: str) -> str:
    risk = RISK_LEVELS.get(op, "MEDIUM")
    cls = {"HIGH": "risk-high", "MEDIUM": "risk-medium", "LOW": "risk-low"}[risk]
    return f'<span class="badge {cls}">{risk}</span>'


def _html_esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ── Operator analysis ─────────────────────────────────────────────────────────

def _compute_operators(mutants: list[dict]) -> dict[str, dict]:
    ops: dict[str, dict] = {}
    for m in mutants:
        op = m.get("operator", "UNK")
        if op not in ops:
            ops[op] = {"code": op, "total": 0, "killed": 0, "survived": 0,
                       "equivalent": 0, "survived_mutants": []}
        ops[op]["total"] += 1
        st = m.get("status", "")
        if st == "killed":
            ops[op]["killed"] += 1
        elif st == "survived":
            ops[op]["survived"] += 1
            ops[op]["survived_mutants"].append(m)
        elif st == "equivalent":
            ops[op]["equivalent"] += 1
    for op, d in ops.items():
        non_equiv = d["killed"] + d["survived"]
        d["kill_pct"] = round(d["killed"] / non_equiv * 100) if non_equiv > 0 else 0
        d["status"] = _op_status(d["kill_pct"])
        info = OPERATOR_INFO.get(op, {})
        d["name"] = info.get("name", op)
        d["plain"] = info.get("plain", "")
        d["example"] = info.get("example", "")
        d["category"] = info.get("category", "ADVANCED")
    return ops


# ── Action plan builder ───────────────────────────────────────────────────────

def _build_action_plan_items(ops: dict, survived_mutants: list[dict]) -> list[dict]:
    priority_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    groups: dict[str, list] = {}
    for m in survived_mutants:
        op = m.get("operator", "UNK")
        groups.setdefault(op, []).append(m)

    items = []
    for op, ms in sorted(groups.items(),
                          key=lambda x: (priority_rank.get(RISK_LEVELS.get(x[0], "MEDIUM"), 1), -len(x[1]))):
        op_data = ops.get(op, {})
        risk = RISK_LEVELS.get(op, "MEDIUM")
        effort_map = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOW"}
        example = ms[0]
        items.append({
            "op": op,
            "name": op_data.get("name", op),
            "count": len(ms),
            "risk": risk,
            "effort": effort_map.get(risk, "LOW"),
            "plain": op_data.get("plain", ""),
            "example_func": example.get("function", ""),
            "example_line": example.get("line", ""),
            "example_desc": example.get("description", ""),
        })
    return items[:8]  # top 8 priorities


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """\
:root {
  --bg: #0d1117; --surface: #161b22; --surface2: #21262d;
  --border: #30363d; --text: #e6edf3; --text2: #8b949e; --text3: #484f58;
  --teal: #3fb950; --green: #4ec9a0; --amber: #d29922; --orange: #fb8f44;
  --red: #f85149; --blue: #58a6ff; --purple: #bc8cff; --yellow: #e3b341;
  --font: -apple-system,BlinkMacSystemFont,'Segoe UI','Inter',sans-serif;
  --mono: 'Cascadia Code','Fira Code','Consolas',monospace;
  --radius: 6px; --radius-lg: 12px; --shadow: none;
}
[data-theme="light"] {
  --bg: #ffffff; --surface: #f6f8fa; --surface2: #ffffff;
  --border: #d0d7de; --text: #24292f; --text2: #57606a; --text3: #6e7781;
  --shadow: 0 1px 3px rgba(0,0,0,0.1);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--bg);color:var(--text);font-size:14px;
     line-height:1.6;transition:background .25s,color .25s}
a{color:var(--blue);text-decoration:none}

/* ── Header ── */
.qm-header{display:flex;align-items:center;justify-content:space-between;
  padding:14px 32px;background:var(--surface);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;gap:12px}
.qm-logo{font-size:20px;font-weight:700;color:var(--teal);letter-spacing:-.5px;white-space:nowrap}
.qm-logo span{color:var(--text2);font-weight:400}
.qm-file{font-size:13px;color:var(--text2);font-family:var(--mono);
  background:var(--surface2);border:1px solid var(--border);
  padding:4px 12px;border-radius:20px;max-width:340px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.qm-header-right{display:flex;align-items:center;gap:8px;flex-shrink:0}
.qm-ts{font-size:11px;color:var(--text3);white-space:nowrap}
.btn{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;
  border-radius:var(--radius);font-size:12px;font-weight:600;cursor:pointer;
  border:1px solid var(--border);background:var(--surface2);color:var(--text);
  transition:all .2s;white-space:nowrap}
.btn:hover{border-color:var(--teal);color:var(--teal)}
.btn-theme{padding:6px 10px;font-size:14px}
.btn-email{border-color:var(--blue);color:var(--blue)}
.btn-email:hover{background:rgba(88,166,255,.1)}
.btn-pdf{border-color:var(--text3);color:var(--text2)}

/* ── Health Badge ── */
.health-section{text-align:center;padding:56px 32px 40px;
  background:linear-gradient(180deg,var(--surface) 0%,var(--bg) 100%)}
.ring-wrap{position:relative;display:inline-flex;align-items:center;
  justify-content:center;width:200px;height:200px;margin-bottom:24px}
.ring-wrap svg{position:absolute;top:0;left:0;transform:rotate(-90deg)}
.ring-inner{position:relative;z-index:1;text-align:center}
.ring-score{font-size:40px;font-weight:700;letter-spacing:-1px;line-height:1}
.ring-grade{font-size:12px;font-weight:700;letter-spacing:.12em;
  margin-top:4px;text-transform:uppercase;color:var(--text2)}
.health-catch{font-size:18px;font-weight:600;margin-bottom:12px;color:var(--text)}
.health-explain{font-size:14px;color:var(--text2);max-width:560px;
  margin:0 auto;line-height:1.7}

/* ── Score Cards ── */
.cards-section{padding:0 32px 40px}
.cards-row{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;
  max-width:1100px;margin:0 auto}
@media(max-width:900px){.cards-row{grid-template-columns:repeat(3,1fr)}}
@media(max-width:540px){.cards-row{grid-template-columns:repeat(2,1fr)}}
.card{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:18px 16px;cursor:default;
  transition:transform .2s,box-shadow .2s;position:relative}
.card:hover{transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,0,0,.3)}
.card-icon{font-size:20px;margin-bottom:8px;display:block}
.card-value{font-size:36px;font-weight:700;line-height:1;letter-spacing:-1px;
  font-variant-numeric:tabular-nums}
.card-label{font-size:10px;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--text2);margin-top:6px}
.card-sub{font-size:11px;color:var(--text3);margin-top:4px;line-height:1.4}
.c-teal .card-value{color:var(--teal)}
.c-amber .card-value{color:var(--amber)}
.c-green .card-value{color:var(--green)}
.c-red .card-value{color:var(--red)}
.c-yellow .card-value{color:var(--yellow)}
.c-grey .card-value{color:var(--text2)}
.card.clickable{cursor:pointer}

/* ── Tooltip ── */
.has-tip{position:relative}
.tip{position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);
  background:#1a2030;border:1px solid var(--border);color:var(--text);
  font-size:12px;line-height:1.5;padding:10px 14px;border-radius:var(--radius);
  width:280px;z-index:200;display:none;pointer-events:none;
  box-shadow:0 4px 16px rgba(0,0,0,.4)}
.tip::after{content:'';position:absolute;top:100%;left:50%;
  transform:translateX(-50%);border:6px solid transparent;
  border-top-color:#1a2030}
.has-tip:hover .tip{display:block}

/* ── Insights ── */
.insights-section{padding:0 32px 40px;max-width:1100px;margin:0 auto}
.section-title{font-size:11px;font-weight:700;letter-spacing:.12em;
  text-transform:uppercase;color:var(--text2);margin-bottom:4px}
.section-heading{font-size:22px;font-weight:600;margin-bottom:4px}
.section-sub{font-size:13px;color:var(--text2);margin-bottom:24px}
.insights-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:700px){.insights-grid{grid-template-columns:1fr}}
.insight-card{border-radius:var(--radius-lg);padding:20px;border:1px solid var(--border)}
.insight-card.good{background:rgba(63,185,80,.07);border-color:rgba(63,185,80,.25)}
.insight-card.warn{background:rgba(210,153,34,.07);border-color:rgba(210,153,34,.25)}
.insight-card.crit{background:rgba(248,81,73,.07);border-color:rgba(248,81,73,.25)}
.insight-title{font-weight:700;font-size:14px;margin-bottom:14px;
  display:flex;align-items:center;gap:8px}
.insight-title.good{color:var(--green)}
.insight-title.warn{color:var(--amber)}
.insight-title.crit{color:var(--red)}
.insight-item{font-size:13px;margin-bottom:12px;padding-bottom:12px;
  border-bottom:1px solid var(--border)}
.insight-item:last-child{border:none;margin-bottom:0;padding-bottom:0}
.insight-item strong{display:block;margin-bottom:2px}
.insight-item small{color:var(--text2);font-size:12px}

/* ── Operators ── */
.operators-section{padding:0 32px 40px;max-width:1100px;margin:0 auto}
.op-category-header{font-size:10px;font-weight:700;letter-spacing:.14em;
  color:var(--text3);text-transform:uppercase;margin:28px 0 10px;
  padding-bottom:6px;border-bottom:1px solid var(--border)}
.op-row{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);margin-bottom:6px;overflow:hidden}
.op-row-header{display:flex;align-items:center;gap:12px;padding:14px 16px;
  cursor:pointer;transition:background .15s}
.op-row-header:hover{background:var(--surface2)}
.op-badge{font-size:11px;font-weight:700;padding:3px 8px;border-radius:4px;
  background:var(--surface2);border:1px solid var(--border);
  font-family:var(--mono);white-space:nowrap;flex-shrink:0;color:var(--text)}
.op-info{flex:1;min-width:0}
.op-name{font-size:13px;font-weight:600}
.op-plain{font-size:12px;color:var(--text2);margin-top:1px}
.op-center{flex:0 0 280px;display:flex;flex-direction:column;gap:4px}
.bar-track{background:var(--surface2);border-radius:4px;height:8px;overflow:hidden}
.bar-fill{height:100%;border-radius:4px;width:0;transition:width 1s ease-out}
.bar-label{font-size:11px;color:var(--text2);display:flex;justify-content:space-between}
.op-status-badge{flex-shrink:0;font-size:10px;font-weight:700;letter-spacing:.08em;
  padding:3px 10px;border-radius:20px;text-transform:uppercase}
.st-STRONG{background:rgba(63,185,80,.15);color:var(--teal)}
.st-GOOD{background:rgba(78,201,160,.15);color:var(--green)}
.st-NEEDS.WORK,.st-NEEDS-WORK{background:rgba(210,153,34,.15);color:var(--amber)}
.st-WEAK{background:rgba(251,143,68,.15);color:var(--orange)}
.st-ZERO{background:rgba(248,81,73,.15);color:var(--red)}
.op-expand{display:none;padding:0 16px 14px}
.op-expand.open{display:block}
.op-expand-title{font-size:11px;color:var(--text3);font-weight:700;
  text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
.mini-mutant{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius);padding:10px 12px;margin-bottom:6px;font-size:12px}
.mini-mutant strong{font-family:var(--mono)}
.mini-mutant span{color:var(--text2)}
.op-chevron{color:var(--text3);font-size:12px;transition:transform .2s;flex-shrink:0}
.op-row.expanded .op-chevron{transform:rotate(180deg)}

/* ── Action Plan ── */
.action-section{padding:0 32px 40px;max-width:1100px;margin:0 auto}
.action-list{list-style:none;display:flex;flex-direction:column;gap:12px}
.action-item{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:20px 24px;display:flex;gap:20px;
  align-items:flex-start}
.action-num{font-size:32px;font-weight:700;color:var(--text3);
  line-height:1;flex-shrink:0;min-width:36px}
.action-num.pri-high{color:var(--red)}
.action-num.pri-medium{color:var(--amber)}
.action-num.pri-low{color:var(--green)}
.action-body{flex:1;min-width:0}
.action-title{font-size:15px;font-weight:600;margin-bottom:8px}
.action-meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.action-impact{font-size:11px;font-weight:700;letter-spacing:.06em;
  background:rgba(248,81,73,.12);color:var(--red);padding:2px 8px;border-radius:4px}
.action-effort{font-size:11px;font-weight:700;letter-spacing:.06em;
  background:rgba(88,166,255,.1);color:var(--blue);padding:2px 8px;border-radius:4px}
.action-desc{font-size:13px;color:var(--text2);margin-bottom:8px;line-height:1.6}
.action-example{font-size:12px;background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius);padding:8px 12px;font-family:var(--mono);color:var(--text)}

/* ── Mutant Table ── */
.table-section{padding:0 32px 40px;max-width:1100px;margin:0 auto}
.table-controls{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;align-items:center}
.search-box{flex:1;min-width:220px;position:relative}
.search-box input{width:100%;padding:8px 12px 8px 34px;border-radius:var(--radius);
  border:1px solid var(--border);background:var(--surface);color:var(--text);
  font-size:13px;font-family:var(--font)}
.search-box::before{content:'⌕';position:absolute;left:10px;top:50%;
  transform:translateY(-50%);color:var(--text3);font-size:16px;pointer-events:none}
.filter-select{padding:8px 12px;border-radius:var(--radius);
  border:1px solid var(--border);background:var(--surface);color:var(--text);
  font-size:12px;font-family:var(--font);cursor:pointer}
.view-toggle{display:flex;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.view-btn{padding:7px 14px;font-size:12px;cursor:pointer;
  background:var(--surface);color:var(--text2);border:none;font-family:var(--font)}
.view-btn.active{background:var(--teal);color:#fff}
.mutant-table{width:100%;border-collapse:collapse;font-size:12px}
.mutant-table th{padding:9px 12px;background:var(--surface2);
  color:var(--text2);font-size:10px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;text-align:left;cursor:pointer;user-select:none;
  border-bottom:2px solid var(--border);white-space:nowrap}
.mutant-table th:hover{color:var(--text)}
.mutant-table th .sort-arrow{margin-left:4px;opacity:.4}
.mutant-table th.sorted .sort-arrow{opacity:1;color:var(--teal)}
.mutant-table td{padding:9px 12px;border-bottom:1px solid var(--border);
  vertical-align:top}
.mutant-table tr.data-row{cursor:pointer;transition:background .1s}
.mutant-table tr.data-row:hover td{background:var(--surface)}
.mutant-table tr.expanded-row td{background:var(--surface);padding:0}
.expand-panel{padding:16px;display:grid;grid-template-columns:1fr 1fr;
  gap:12px;background:var(--surface)}
.code-block{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius);padding:12px;font-family:var(--mono);
  font-size:12px;line-height:1.6;overflow-x:auto}
.code-block .del{background:rgba(248,81,73,.2);color:var(--red)}
.code-block .add{background:rgba(63,185,80,.2);color:var(--green)}
.expand-actions{margin-top:12px;display:flex;gap:8px;grid-column:1/-1}
.badge{display:inline-block;padding:2px 8px;border-radius:20px;
  font-size:10px;font-weight:700;letter-spacing:.05em}
.badge-killed{background:rgba(63,185,80,.15);color:var(--teal)}
.badge-survived{background:rgba(248,81,73,.15);color:var(--red)}
.badge-equivalent{background:rgba(227,179,65,.15);color:var(--yellow)}
.risk-high{background:rgba(248,81,73,.15);color:var(--red)}
.risk-medium{background:rgba(251,143,68,.15);color:var(--orange)}
.risk-low{background:rgba(78,201,160,.15);color:var(--green)}
.op-pill{display:inline-block;padding:2px 7px;border-radius:4px;
  font-size:10px;font-weight:700;font-family:var(--mono);
  background:var(--surface2);border:1px solid var(--border);color:var(--text)}
.no-results{text-align:center;padding:40px;color:var(--text3)}
.group-card{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);margin-bottom:12px;overflow:hidden}
.group-header{padding:14px 18px;display:flex;align-items:center;
  justify-content:space-between;cursor:pointer;background:var(--surface2)}
.group-header:hover{background:var(--border)}
.group-body{padding:12px;display:none}
.group-body.open{display:block}

/* ── Killed / Equiv sections ── */
.collapsible-section{padding:0 32px 40px;max-width:1100px;margin:0 auto}
details{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);overflow:hidden}
details summary{padding:16px 20px;cursor:pointer;font-size:15px;font-weight:600;
  display:flex;align-items:center;gap:8px;list-style:none;
  background:var(--surface2)}
details summary::-webkit-details-marker{display:none}
details summary::before{content:'▶';font-size:10px;color:var(--text3);
  transition:transform .2s;display:inline-block}
details[open] summary::before{transform:rotate(90deg)}
details .details-body{padding:20px}
.equiv-box{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:24px 28px;margin-bottom:20px;
  line-height:1.8}
.equiv-box h4{font-size:15px;font-weight:600;margin-bottom:12px;color:var(--text)}
.equiv-box p{font-size:13px;color:var(--text2);margin-bottom:10px}
.equiv-highlight{font-size:22px;font-weight:700;color:var(--teal)}
.equiv-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:12px}
.equiv-table th{padding:8px 12px;background:var(--surface);color:var(--text2);
  font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  text-align:left;border-bottom:1px solid var(--border)}
.equiv-table td{padding:8px 12px;border-bottom:1px solid var(--border);
  font-family:var(--mono);font-size:11px}

/* ── Footer ── */
.qm-footer{padding:24px 32px;background:var(--surface);
  border-top:1px solid var(--border);text-align:center;
  font-size:12px;color:var(--text3)}
.qm-footer strong{color:var(--teal)}
.footer-meta{display:flex;justify-content:center;gap:24px;
  flex-wrap:wrap;margin-top:8px}

/* ── Modal ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);
  z-index:999;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);width:480px;max-width:95vw;
  max-height:90vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.6)}
.modal-header{padding:20px 24px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between}
.modal-header h3{font-size:16px;font-weight:600}
.modal-close{background:none;border:none;color:var(--text2);font-size:20px;
  cursor:pointer;padding:4px 8px;border-radius:var(--radius)}
.modal-close:hover{color:var(--text);background:var(--surface2)}
.modal-body{padding:20px 24px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-size:12px;font-weight:600;
  color:var(--text2);margin-bottom:6px;text-transform:uppercase;letter-spacing:.06em}
.form-group input,.form-group select,.form-group textarea{
  width:100%;padding:9px 12px;border-radius:var(--radius);
  border:1px solid var(--border);background:var(--surface2);color:var(--text);
  font-size:13px;font-family:var(--font)}
.form-group textarea{height:90px;resize:vertical}
.form-group .hint{font-size:11px;color:var(--text3);margin-top:5px;line-height:1.5}
.form-group .hint a{color:var(--blue)}
.modal-footer{padding:16px 24px;border-top:1px solid var(--border);
  display:flex;gap:8px;justify-content:flex-end}
.btn-primary{background:var(--teal);color:#0d1117;border-color:var(--teal);
  font-weight:700}
.btn-primary:hover{background:#5dcd6e;color:#0d1117}
.modal-msg{padding:10px 12px;border-radius:var(--radius);font-size:13px;
  margin-top:12px;display:none}
.modal-msg.success{background:rgba(63,185,80,.15);color:var(--teal);display:block}
.modal-msg.error{background:rgba(248,81,73,.15);color:var(--red);display:block}

/* ── Back to top ── */
#back-to-top{position:fixed;bottom:24px;right:24px;width:40px;height:40px;
  border-radius:50%;background:var(--teal);color:#0d1117;border:none;
  font-size:18px;cursor:pointer;display:none;align-items:center;
  justify-content:center;z-index:200;box-shadow:0 4px 12px rgba(0,0,0,.3);
  transition:opacity .2s}
#back-to-top.visible{display:flex}

/* ── Identity / Login ── */
.identity-wrap{display:flex;align-items:center;gap:6px}
.identity-badge{font-size:11px;border-radius:20px;padding:3px 10px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px;display:none}
.identity-badge.work{background:rgba(88,166,255,.12);border:1px solid rgba(88,166,255,.4);color:var(--blue)}
.identity-badge.personal{background:rgba(63,185,80,.12);border:1px solid rgba(63,185,80,.35);color:var(--teal)}
.identity-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;display:none}
.identity-dot.work{background:var(--blue)}
.identity-dot.personal{background:var(--teal)}
.btn-login{font-size:11px;padding:4px 12px;border-style:dashed}
.type-toggle{display:flex;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-bottom:8px}
.type-btn{flex:1;padding:9px 0;font-size:13px;cursor:pointer;
  background:var(--surface2);color:var(--text2);border:none;
  font-family:var(--font);font-weight:500;transition:all .15s}
.type-btn:hover{color:var(--text)}
.type-btn.active.work{background:var(--blue);color:#fff}
.type-btn.active.personal{background:var(--teal);color:#0d1117}
.sender-as-bar{font-size:12px;color:var(--text2);background:var(--surface2);
  border:1px solid var(--border);border-radius:var(--radius);
  padding:9px 12px;margin-bottom:14px;display:none;align-items:center;gap:8px}
.sender-as-bar.visible{display:flex}
.sender-as-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.sender-as-change{margin-left:auto;font-size:11px;cursor:pointer;color:var(--blue)}
.sender-as-change:hover{text-decoration:underline}
.login-error{font-size:12px;color:var(--red);margin-top:8px;display:none}

/* ── Print ── */
@media print {
  .qm-header .btn,.btn-theme,#back-to-top,.modal-overlay,
  .table-controls,.view-toggle{display:none!important}
  .op-expand{display:block!important}
  details{open:true}
  .details-body{display:block!important}
  body{background:#fff;color:#000;font-size:12px}
  .card,.op-row,.insight-card{break-inside:avoid}
  .mutant-table{font-size:11px}
}
"""

# ── JavaScript ────────────────────────────────────────────────────────────────

_JS = """\
(function() {
'use strict';

// ── Theme ──────────────────────────────────────────────────────────────────
var THEME_KEY = 'qamill-theme';

function initTheme() {
  var saved = localStorage.getItem(THEME_KEY) || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeBtn(saved);
}

function updateThemeBtn(theme) {
  var btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀' : '🌙';
}

window.toggleTheme = function() {
  var current = document.documentElement.getAttribute('data-theme');
  var next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem(THEME_KEY, next);
  updateThemeBtn(next);
};

// ── Count-up animation ─────────────────────────────────────────────────────
function countUp(el, target, suffix, duration) {
  duration = duration || 800;
  var start = performance.now();
  var isFloat = String(target).indexOf('.') !== -1;
  function step(now) {
    var progress = Math.min((now - start) / duration, 1);
    var eased = 1 - Math.pow(1 - progress, 3);
    var value = eased * target;
    el.textContent = (isFloat ? value.toFixed(1) : Math.floor(value)) + (suffix || '');
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── SVG ring animation ─────────────────────────────────────────────────────
function animateRing() {
  var ring = document.getElementById('score-ring');
  if (!ring) return;
  var circumference = 2 * Math.PI * 80;
  var score = window.REPORT_DATA ? window.REPORT_DATA.true_score : 0;
  var targetOffset = circumference * (1 - score / 100);
  setTimeout(function() {
    ring.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(.4,0,.2,1)';
    ring.style.strokeDashoffset = targetOffset;
  }, 200);
}

// ── Progress bars ──────────────────────────────────────────────────────────
function animateBars() {
  document.querySelectorAll('.bar-fill[data-w]').forEach(function(bar) {
    var w = bar.getAttribute('data-w');
    setTimeout(function() { bar.style.width = w + '%'; }, 400);
  });
}

// ── Counter cards ──────────────────────────────────────────────────────────
function animateCounters() {
  document.querySelectorAll('[data-count]').forEach(function(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var suffix = el.getAttribute('data-suffix') || '';
    countUp(el, target, suffix, 900);
  });
}

// ── Intersection observer for stagger ─────────────────────────────────────
function initAnimations() {
  animateRing();
  animateBars();
  animateCounters();
  document.querySelectorAll('.anim-fade').forEach(function(el, i) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(12px)';
    setTimeout(function() {
      el.style.transition = 'opacity .5s ease, transform .5s ease';
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    }, i * 80);
  });
}

// ── Operator accordion ─────────────────────────────────────────────────────
window.toggleOp = function(id) {
  var row = document.getElementById('op-' + id);
  var panel = document.getElementById('op-expand-' + id);
  if (!row || !panel) return;
  var open = row.classList.contains('expanded');
  row.classList.toggle('expanded', !open);
  panel.classList.toggle('open', !open);
};

// ── Mutant table ───────────────────────────────────────────────────────────
var tableState = {
  search: '', filterOp: '', filterFunc: '',
  sortCol: 'risk', sortDir: 1, view: 'table'
};

var ALL_MUTANTS = [];

function initTable() {
  if (!window.REPORT_DATA) return;
  ALL_MUTANTS = (window.REPORT_DATA.survived_mutants || []).map(function(m, i) {
    m._idx = i;
    return m;
  });
  renderTable();
}

function filterMutants() {
  var s = tableState.search.toLowerCase();
  return ALL_MUTANTS.filter(function(m) {
    var matchSearch = !s ||
      (m.function || '').toLowerCase().indexOf(s) !== -1 ||
      (m.operator || '').toLowerCase().indexOf(s) !== -1 ||
      (m.description || '').toLowerCase().indexOf(s) !== -1 ||
      String(m.line || '').indexOf(s) !== -1 ||
      (m.mutant_id || '').toLowerCase().indexOf(s) !== -1;
    var matchOp = !tableState.filterOp || m.operator === tableState.filterOp;
    var matchFunc = !tableState.filterFunc || m.function === tableState.filterFunc;
    return matchSearch && matchOp && matchFunc;
  });
}

var RISK_ORDER = {HIGH:0, MEDIUM:1, LOW:2};

function sortMutants(arr) {
  var col = tableState.sortCol;
  var dir = tableState.sortDir;
  return arr.slice().sort(function(a, b) {
    var av, bv;
    if (col === 'risk') {
      av = RISK_ORDER[a._risk] || 1;
      bv = RISK_ORDER[b._risk] || 1;
    } else if (col === 'line') {
      av = a.line || 0; bv = b.line || 0;
    } else {
      av = (a[col] || '').toLowerCase();
      bv = (b[col] || '').toLowerCase();
    }
    if (av < bv) return -dir;
    if (av > bv) return dir;
    return 0;
  });
}

function renderTable() {
  var container = document.getElementById('mutant-table-body');
  if (!container) return;

  var RISK_LEVELS = window.REPORT_DATA ? (window.REPORT_DATA.risk_levels || {}) : {};
  var filtered = filterMutants();
  filtered = sortMutants(filtered);

  if (filtered.length === 0) {
    container.innerHTML = '<tr><td colspan="8" class="no-results">No mutants match your filters.</td></tr>';
    return;
  }

  var rows = '';
  filtered.forEach(function(m) {
    var risk = RISK_LEVELS[m.operator] || 'MEDIUM';
    m._risk = risk;
    var riskBadge = '<span class="badge risk-' + risk.toLowerCase() + '">' + risk + '</span>';
    var opInfo = (window.REPORT_DATA.op_info || {})[m.operator] || {};
    var opTip = opInfo.name ? (' title="' + opInfo.name + '"') : '';
    var plain = m._plain || '';
    var desc = m.description || '';
    rows += '<tr class="data-row" onclick="toggleExpandRow(' + m._idx + ')" id="row-' + m._idx + '">';
    rows += '<td style="color:var(--text3);font-family:var(--mono)">' + escHtml(m.mutant_id || '') + '</td>';
    rows += '<td>' + riskBadge + '</td>';
    rows += '<td><span class="op-pill"' + opTip + '>' + escHtml(m.operator || '') + '</span></td>';
    rows += '<td style="font-family:var(--mono)">' + escHtml(m.function || '') + '</td>';
    rows += '<td style="text-align:center;color:var(--text2)">' + (m.line || '') + '</td>';
    rows += '<td style="font-family:var(--mono);color:var(--amber)">' + escHtml(desc) + '</td>';
    rows += '<td style="color:var(--text2)">' + escHtml(plain) + '</td>';
    rows += '<td><button class="btn" onclick="event.stopPropagation();copyFix(' + m._idx + ',this)" style="padding:3px 8px;font-size:11px">Copy fix</button></td>';
    rows += '</tr>';
    rows += '<tr class="expanded-row" id="expand-' + m._idx + '" style="display:none">';
    rows += '<td colspan="8"><div class="expand-panel" id="expand-body-' + m._idx + '"></div></td>';
    rows += '</tr>';
  });
  container.innerHTML = rows;

  document.getElementById('table-count').textContent = filtered.length + ' of ' + ALL_MUTANTS.length;
}

window.toggleExpandRow = function(idx) {
  var expandRow = document.getElementById('expand-' + idx);
  if (!expandRow) return;
  var isOpen = expandRow.style.display !== 'none';
  if (isOpen) {
    expandRow.style.display = 'none';
    return;
  }
  var m = ALL_MUTANTS[idx];
  var body = document.getElementById('expand-body-' + idx);
  if (!body) return;

  var orig = escHtml(m.original_src || 'Original code not available');
  var mutd = escHtml(m.mutant_src || 'Mutated code not available');
  var fix  = escHtml(m._fix || '');
  var risk = m._risk || RISK_LEVELS[m.operator] || 'MEDIUM';
  var riskDesc = {
    HIGH: 'This mutation type has a HIGH risk of hiding a real bug. Add tests immediately.',
    MEDIUM: 'This is a MEDIUM risk gap. Add tests when possible.',
    LOW: 'This is a LOW risk gap but still worth fixing.'
  }[risk] || '';

  body.innerHTML =
    '<div><div class="op-expand-title">Original Code</div><div class="code-block">' + orig + '</div></div>' +
    '<div><div class="op-expand-title">Mutated Code</div><div class="code-block del">' + mutd + '</div></div>' +
    '<div style="grid-column:1/-1"><div class="op-expand-title">Risk</div>' +
    '<div class="expand-actions"><span class="badge risk-' + risk.toLowerCase() + '">' + risk + '</span> ' +
    '<span style="color:var(--text2);font-size:12px">' + escHtml(riskDesc) + '</span></div></div>' +
    '<div style="grid-column:1/-1"><div class="op-expand-title">Suggested Fix</div>' +
    '<div style="font-size:12px;color:var(--text2);padding:8px 0">' + escHtml(fix) + '</div>' +
    '<div class="expand-actions">' +
    '<button class="btn" onclick="copyFix(' + idx + ',this)">📋 Copy suggested test</button>' +
    '</div></div>';

  expandRow.style.display = '';
};

window.copyFix = function(idx, btn) {
  var m = ALL_MUTANTS[idx];
  var fix = m._fix || '';
  if (!fix) return;
  navigator.clipboard.writeText(fix).then(function() {
    var orig = btn.textContent;
    btn.textContent = '✓ Copied';
    btn.style.color = 'var(--teal)';
    setTimeout(function() { btn.textContent = orig; btn.style.color = ''; }, 2000);
  });
};

window.sortByCol = function(col) {
  if (tableState.sortCol === col) {
    tableState.sortDir *= -1;
  } else {
    tableState.sortCol = col;
    tableState.sortDir = 1;
  }
  document.querySelectorAll('.mutant-table th').forEach(function(th) {
    th.classList.remove('sorted');
    var arrow = th.querySelector('.sort-arrow');
    if (arrow) arrow.textContent = '↕';
  });
  var active = document.querySelector('th[data-sort="' + col + '"]');
  if (active) {
    active.classList.add('sorted');
    var arrow = active.querySelector('.sort-arrow');
    if (arrow) arrow.textContent = tableState.sortDir === 1 ? '↑' : '↓';
  }
  renderTable();
};

window.onSearch = function(val) {
  tableState.search = val;
  renderTable();
};

window.onFilterOp = function(val) {
  tableState.filterOp = val;
  renderTable();
};

window.onFilterFunc = function(val) {
  tableState.filterFunc = val;
  renderTable();
};

window.setView = function(view) {
  tableState.view = view;
  document.querySelectorAll('.view-btn').forEach(function(b) {
    b.classList.toggle('active', b.getAttribute('data-view') === view);
  });
  var tableView = document.getElementById('view-table');
  var groupView = document.getElementById('view-group');
  if (tableView) tableView.style.display = view === 'table' ? '' : 'none';
  if (groupView) groupView.style.display = view !== 'table' ? '' : 'none';
  if (view !== 'table') renderGroupView(view);
};

function renderGroupView(groupBy) {
  var container = document.getElementById('view-group');
  if (!container) return;
  var filtered = filterMutants();
  var groups = {};
  filtered.forEach(function(m) {
    var key = groupBy === 'func' ? (m.function || 'unknown') : (m.operator || 'UNK');
    if (!groups[key]) groups[key] = [];
    groups[key].push(m);
  });
  var html = '';
  Object.keys(groups).sort().forEach(function(key) {
    var ms = groups[key];
    html += '<div class="group-card">';
    html += '<div class="group-header" onclick="toggleGroup(this)">';
    html += '<span style="font-weight:600;font-family:var(--mono)">' + escHtml(key) + '</span>';
    html += '<span style="color:var(--red);font-size:13px">' + ms.length + ' gaps</span>';
    html += '</div><div class="group-body">';
    ms.forEach(function(m) {
      var risk = (window.REPORT_DATA.risk_levels || {})[m.operator] || 'MEDIUM';
      html += '<div style="padding:8px 4px;border-bottom:1px solid var(--border);font-size:12px">';
      html += '<span class="badge risk-' + risk.toLowerCase() + '">' + risk + '</span> ';
      html += '<span class="op-pill">' + escHtml(m.operator) + '</span> ';
      html += 'Line ' + (m.line || '?') + ': ';
      html += '<span style="font-family:var(--mono);color:var(--amber)">' + escHtml(m.description || '') + '</span>';
      html += '</div>';
    });
    html += '</div></div>';
  });
  container.innerHTML = html || '<div class="no-results">No mutants match your filters.</div>';
}

window.toggleGroup = function(header) {
  var body = header.nextElementSibling;
  if (body) body.classList.toggle('open');
};

// ── Identity / Login ──────────────────────────────────────────────────────
var IDENTITY_KEY = 'qamill-identity';

function getIdentity() {
  try { return JSON.parse(localStorage.getItem(IDENTITY_KEY) || 'null'); }
  catch (e) { return null; }
}

function updateIdentityDisplay() {
  var id    = getIdentity();
  var badge = document.getElementById('identity-badge');
  var dot   = document.getElementById('identity-dot');
  var btn   = document.getElementById('login-btn');
  var bar   = document.getElementById('sender-as-bar');

  if (badge) {
    if (id && id.email) {
      badge.textContent = id.email;
      badge.className   = 'identity-badge ' + (id.type || 'work');
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  }
  if (dot) {
    dot.className    = 'identity-dot ' + (id && id.type ? id.type : 'work');
    dot.style.display = (id && id.email) ? 'inline-block' : 'none';
  }
  if (btn) btn.textContent = (id && id.email) ? 'Change' : 'Log in';

  // Update "Sending as" bar and nudge inside email modal
  if (bar) {
    if (id && id.email) {
      var txt  = bar.querySelector('.sender-as-text');
      var sdot = bar.querySelector('.sender-as-dot');
      if (txt)  txt.textContent = 'Sending as: ' + id.email + ' (' + (id.type === 'personal' ? 'Personal' : 'Work') + ')';
      if (sdot) sdot.style.background = id.type === 'personal' ? 'var(--teal)' : 'var(--blue)';
      bar.classList.add('visible');
    } else {
      bar.classList.remove('visible');
    }
  }
  var nudge = document.getElementById('no-identity-nudge');
  if (nudge) nudge.style.display = (id && id.email) ? 'none' : 'block';
}

function initIdentity() {
  updateIdentityDisplay();
}

window.openLoginModal = function() {
  var modal = document.getElementById('login-modal');
  if (!modal) return;
  modal.classList.add('open');
  var id = getIdentity();
  if (id) {
    var em = document.getElementById('login-email');
    var pw = document.getElementById('login-password');
    if (em) em.value = id.email || '';
    if (pw && id.password) pw.value = id.password;
    setEmailType(id.type || 'work');
  } else {
    setEmailType('work');
  }
};

window.closeLoginModal = function() {
  var m = document.getElementById('login-modal');
  if (m) m.classList.remove('open');
};

window.setEmailType = function(type) {
  var hidden = document.getElementById('login-type');
  if (hidden) hidden.value = type;
  var wBtn = document.getElementById('type-work');
  var pBtn = document.getElementById('type-personal');
  if (wBtn) { wBtn.classList.toggle('active', type === 'work');     wBtn.classList.toggle('work', true); }
  if (pBtn) { pBtn.classList.toggle('active', type === 'personal'); pBtn.classList.toggle('personal', true); }
  // Update placeholder to match type
  var em = document.getElementById('login-email');
  if (em) em.placeholder = type === 'work' ? 'you@company.com' : 'you@gmail.com';
};

window.saveLogin = function() {
  var email    = ((document.getElementById('login-email')    || {}).value || '').trim();
  var type     = (document.getElementById('login-type')      || {}).value || 'work';
  var password = ((document.getElementById('login-password') || {}).value || '');
  var errEl    = document.getElementById('login-error');
  if (!email || email.indexOf('@') === -1) {
    if (errEl) { errEl.textContent = 'Please enter a valid email address.'; errEl.style.display = 'block'; }
    return;
  }
  if (errEl) errEl.style.display = 'none';
  localStorage.setItem(IDENTITY_KEY, JSON.stringify({ email: email, type: type, password: password }));
  updateIdentityDisplay();
  // Immediately pre-fill email modal fields
  var fromField = document.getElementById('email-from');
  if (fromField) fromField.value = email;
  if (password) {
    var passField = document.getElementById('email-pass');
    if (passField) passField.value = password;
  }
  closeLoginModal();
};

window.clearIdentity = function() {
  localStorage.removeItem(IDENTITY_KEY);
  updateIdentityDisplay();
  var fromField = document.getElementById('email-from');
  if (fromField) fromField.value = '';
};

// ── Email modal ────────────────────────────────────────────────────────────
window.openEmailModal = function() {
  var modal = document.getElementById('email-modal');
  if (!modal) return;
  modal.classList.add('open');

  // Pre-fill subject/body from report data
  var rd = window.REPORT_DATA;
  if (rd) {
    var subj = document.getElementById('email-subject');
    if (subj && !subj.value) subj.value = 'QAMill Report — ' + (rd.file_name || '');
    var body = document.getElementById('email-body');
    if (body && !body.value) body.value =
      'QAMill Mutation Analysis Report\\n' +
      'File: ' + (rd.file_name || '') + '\\n' +
      'True Score: ' + (rd.true_score || '') + '%\\n' +
      'Killed: ' + (rd.killed || '') + ' | Survived: ' + (rd.survived || '') +
      ' | Equivalent: ' + (rd.equivalent || '') + '\\n\\n' +
      'See attached HTML report for full details.';
  }

  // Pre-fill sender/password from saved identity
  var id = getIdentity();
  if (id && id.email) {
    var fromField = document.getElementById('email-from');
    if (fromField && !fromField.value) fromField.value = id.email;
    if (id.password) {
      var passField = document.getElementById('email-pass');
      if (passField && !passField.value) passField.value = id.password;
    }
  }
  updateIdentityDisplay();
};

window.closeEmailModal = function() {
  var modal = document.getElementById('email-modal');
  if (modal) modal.classList.remove('open');
};

window.onSmtpChange = function(val) {
  var custom = document.getElementById('smtp-custom');
  if (custom) custom.style.display = val === 'custom' ? '' : 'none';
};

window.sendEmail = function() {
  var btn = document.getElementById('send-btn');
  var msg = document.getElementById('modal-msg');
  if (!btn || !msg) return;

  var recipient = (document.getElementById('email-to') || {}).value || '';
  var subject   = (document.getElementById('email-subject') || {}).value || '';
  var body      = (document.getElementById('email-body') || {}).value || '';
  var sender    = (document.getElementById('email-from') || {}).value || '';
  var password  = (document.getElementById('email-pass') || {}).value || '';
  var provider  = (document.getElementById('smtp-provider') || {}).value || 'gmail';
  var host      = (document.getElementById('smtp-host') || {}).value || '';
  var port      = parseInt((document.getElementById('smtp-port') || {}).value || '587');

  if (!recipient || !sender || !password) {
    msg.className = 'modal-msg error';
    msg.textContent = 'Please fill in recipient, sender email, and app password.';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Sending...';
  msg.className = 'modal-msg';
  msg.textContent = '';

  var payload = {
    recipient: recipient, subject: subject, message: body,
    sender_email: sender, app_password: password,
    smtp_provider: provider, smtp_host: host, smtp_port: port,
    report_html: document.documentElement.outerHTML
  };

  fetch('http://localhost:8765/email-report', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  }).then(function(r) { return r.json(); }).then(function(data) {
    btn.disabled = false;
    btn.textContent = 'Send Report';
    if (data.success) {
      msg.className = 'modal-msg success';
      msg.textContent = 'Report sent successfully to ' + recipient;
    } else {
      msg.className = 'modal-msg error';
      msg.textContent = data.message || 'Failed to send email.';
    }
  }).catch(function(e) {
    btn.disabled = false;
    btn.textContent = 'Send Report';
    msg.className = 'modal-msg error';
    msg.textContent = 'Could not reach server. Make sure QAMill backend is running.';
  });
};

// ── PDF download ───────────────────────────────────────────────────────────
window.downloadPdf = function() {
  document.querySelectorAll('.op-expand').forEach(function(el) { el.classList.add('open'); });
  document.querySelectorAll('details').forEach(function(el) { el.open = true; });
  window.print();
};

// ── Scroll helpers ─────────────────────────────────────────────────────────
window.scrollToSurvived = function() {
  var el = document.getElementById('survived-section');
  if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
};

window.scrollToTop = function() {
  window.scrollTo({top:0, behavior:'smooth'});
};

function initBackToTop() {
  var btn = document.getElementById('back-to-top');
  if (!btn) return;
  window.addEventListener('scroll', function() {
    btn.classList.toggle('visible', window.scrollY > 400);
  });
}

// ── Utility ────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  initTheme();
  initAnimations();
  initTable();
  initBackToTop();
  initIdentity();

  // Close modals on overlay click
  var emailOverlay = document.getElementById('email-modal');
  if (emailOverlay) {
    emailOverlay.addEventListener('click', function(e) {
      if (e.target === emailOverlay) closeEmailModal();
    });
  }
  var loginOverlay = document.getElementById('login-modal');
  if (loginOverlay) {
    loginOverlay.addEventListener('click', function(e) {
      if (e.target === loginOverlay) closeLoginModal();
    });
  }
});

})();
"""


# ── Section builders ──────────────────────────────────────────────────────────

def _build_header(file_name: str, timestamp: str) -> str:
    return f"""
<header class="qm-header">
  <div class="qm-logo">QA<span>Mill</span></div>
  <div class="qm-file" title="{_html_esc(file_name)}">{_html_esc(file_name)}</div>
  <div class="qm-header-right">
    <div class="identity-wrap">
      <span class="identity-dot" id="identity-dot"></span>
      <span class="identity-badge" id="identity-badge"></span>
      <button class="btn btn-login" id="login-btn" onclick="openLoginModal()">Log in</button>
    </div>
    <span class="qm-ts">{_html_esc(timestamp)}</span>
    <button class="btn btn-theme" id="theme-toggle" onclick="toggleTheme()" title="Toggle dark/light mode">☀</button>
    <button class="btn btn-pdf" onclick="downloadPdf()">⬇ PDF</button>
    <button class="btn btn-email" onclick="openEmailModal()">✉ Email Report</button>
  </div>
</header>"""


def _build_health_badge(true_score: float, killed: int, survived: int,
                         equivalent: int) -> str:
    grade, color = _grade_info(true_score)
    circumference = 2 * 3.14159 * 80
    non_equiv = killed + survived
    grade_explain = {
        "EXCELLENT": "Your test suite provides outstanding protection against real-world bugs.",
        "GOOD": "Your test suite is in good health — it catches most real bugs, but specific gaps were found that a developer could exploit.",
        "NEEDS WORK": "Your tests miss a meaningful number of mutations. A focused effort on the gaps below would significantly improve coverage.",
        "WEAK": "Your tests are catching less than half of real bugs. Review the critical gaps and action plan below.",
        "CRITICAL": "Your tests are missing the majority of real bugs. Immediate action is required on the gaps listed below.",
    }[grade]
    return f"""
<section class="health-section anim-fade">
  <div class="ring-wrap">
    <svg viewBox="0 0 200 200" width="200" height="200" style="position:absolute;top:0;left:0;transform:rotate(-90deg)">
      <circle cx="100" cy="100" r="80" fill="none" stroke="var(--border)" stroke-width="16"/>
      <circle id="score-ring" cx="100" cy="100" r="80" fill="none"
        stroke="{color}" stroke-width="16" stroke-linecap="round"
        stroke-dasharray="{circumference:.1f}"
        stroke-dashoffset="{circumference:.1f}"/>
    </svg>
    <div class="ring-inner">
      <div class="ring-score" style="color:{color}" data-count="{true_score}" data-suffix="%">0%</div>
      <div class="ring-grade">{grade}</div>
    </div>
  </div>
  <div class="health-catch">Your tests catch <strong>{killed}</strong> in <strong>{non_equiv}</strong> real bugs</div>
  <p class="health-explain">{grade_explain}</p>
</section>"""


def _build_score_cards(true_score: float, raw_score: float, killed: int,
                        survived: int, equivalent: int, total: int) -> str:
    return f"""
<section class="cards-section anim-fade">
  <div class="cards-row">
    <div class="card c-teal has-tip">
      <span class="card-icon">🛡</span>
      <div class="card-value" data-count="{true_score}" data-suffix="%">0%</div>
      <div class="card-label">True Score</div>
      <div class="card-sub">Honest score (equivalents removed)</div>
      <div class="tip">This is your real mutation score. Equivalent mutants — code changes that are mathematically identical to the original — have been removed. This is what your score actually is.</div>
    </div>
    <div class="card c-amber has-tip">
      <span class="card-icon">⚠</span>
      <div class="card-value" data-count="{raw_score}" data-suffix="%">0%</div>
      <div class="card-label">Raw Score</div>
      <div class="card-sub">What other tools would report</div>
      <div class="tip">Without equivalent mutant filtering, your score appears much lower. This is what mutmut, PiTest and cosmic-ray would show — giving you false concern about your test quality.</div>
    </div>
    <div class="card c-green">
      <span class="card-icon">✓</span>
      <div class="card-value" data-count="{killed}">{killed}</div>
      <div class="card-label">Killed</div>
      <div class="card-sub">Mutants your tests caught</div>
    </div>
    <div class="card c-red clickable" onclick="scrollToSurvived()" title="Click to see gaps">
      <span class="card-icon">✗</span>
      <div class="card-value" data-count="{survived}">{survived}</div>
      <div class="card-label">Survived</div>
      <div class="card-sub">Gaps needing attention ↓</div>
    </div>
    <div class="card c-yellow has-tip">
      <span class="card-icon">≡</span>
      <div class="card-value" data-count="{equivalent}">{equivalent}</div>
      <div class="card-label">Equivalent</div>
      <div class="card-sub">False positives removed</div>
      <div class="tip">These mutants are mathematically identical to your original code. No test can ever kill them — QAMill removes them so they don't unfairly lower your score.</div>
    </div>
    <div class="card c-grey">
      <span class="card-icon">⚡</span>
      <div class="card-value" data-count="{total}">{total}</div>
      <div class="card-label">Total Mutants</div>
      <div class="card-sub">Mutations tested in parallel</div>
    </div>
  </div>
</section>"""


def _build_insights(ops: dict) -> str:
    # Sort by kill_pct
    op_list = [(op, d) for op, d in ops.items() if d["killed"] + d["survived"] > 0]

    strong = [(op, d) for op, d in op_list if d["kill_pct"] >= 75]
    strong.sort(key=lambda x: -x[1]["kill_pct"])

    improving = [(op, d) for op, d in op_list if 30 <= d["kill_pct"] < 75]
    improving.sort(key=lambda x: x[1]["kill_pct"])

    critical = [(op, d) for op, d in op_list if d["kill_pct"] < 30]
    critical.sort(key=lambda x: x[1]["kill_pct"])

    def _item_good(op, d):
        return (
            f'<div class="insight-item"><strong style="color:var(--green)">✓ {_html_esc(d["name"])} ({d["kill_pct"]}%)</strong>'
            f'<small>{_html_esc(d["plain"])}</small></div>'
        )

    def _item_warn(op, d):
        return (
            f'<div class="insight-item"><strong style="color:var(--amber)">⚠ {_html_esc(d["name"])} ({d["kill_pct"]}%)</strong>'
            f'<small>{_html_esc(d["plain"])}</small></div>'
        )

    def _item_crit(op, d):
        label = "0% — completely untested" if d["kill_pct"] == 0 else f'{d["kill_pct"]}%'
        return (
            f'<div class="insight-item"><strong style="color:var(--red)">✗ {_html_esc(d["name"])} ({label})</strong>'
            f'<small>{_html_esc(d["plain"])}</small></div>'
        )

    good_items = "".join(_item_good(op, d) for op, d in strong[:3]) or "<div class='insight-item'><small>No strong operators found.</small></div>"
    warn_items = "".join(_item_warn(op, d) for op, d in improving[:4]) or "<div class='insight-item'><small>All operators in this range are performing well.</small></div>"
    crit_items = "".join(_item_crit(op, d) for op, d in critical[:5]) or "<div class='insight-item'><small>No critical gaps found — excellent work!</small></div>"

    return f"""
<section class="insights-section anim-fade">
  <div class="section-title">Analysis</div>
  <div class="section-heading">What This Means</div>
  <div class="section-sub">Plain English interpretation of your mutation coverage</div>
  <div class="insights-grid">
    <div class="insight-card good">
      <div class="insight-title good">✓ What&apos;s Working Well</div>
      {good_items}
    </div>
    <div class="insight-card warn">
      <div class="insight-title warn">⚠ Needs Improvement</div>
      {warn_items}
    </div>
    <div class="insight-card crit">
      <div class="insight-title crit">✗ Critical Gaps</div>
      {crit_items}
    </div>
  </div>
</section>"""


def _op_status_badge(status: str) -> str:
    css = {"STRONG": "st-STRONG", "GOOD": "st-GOOD", "NEEDS WORK": "st-NEEDS-WORK",
           "WEAK": "st-WEAK", "ZERO": "st-ZERO"}
    cls = css.get(status, "st-WEAK")
    return f'<span class="op-status-badge {cls}">{status}</span>'


def _build_operators(ops: dict) -> str:
    by_cat: dict[str, list] = {}
    for op, d in ops.items():
        cat = d.get("category", "ADVANCED")
        by_cat.setdefault(cat, []).append((op, d))

    html = """
<section class="operators-section anim-fade">
  <div class="section-title">Coverage</div>
  <div class="section-heading">Coverage by Mutation Type</div>
  <div class="section-sub">Each row shows one category of bug your tests were checked against</div>"""

    for cat in CATEGORY_ORDER:
        if cat not in by_cat:
            continue
        html += f'<div class="op-category-header">{_html_esc(cat)}</div>'
        items = sorted(by_cat[cat], key=lambda x: -x[1].get("total", 0))
        for op, d in items:
            k = d["killed"]
            s = d["survived"]
            total = d["total"]
            non_eq = k + s
            pct = d["kill_pct"]
            bar_color = {"STRONG": "var(--teal)", "GOOD": "var(--green)",
                         "NEEDS WORK": "var(--amber)", "WEAK": "var(--orange)",
                         "ZERO": "var(--red)"}.get(d["status"], "var(--text2)")
            survived_preview = ""
            for sm in d.get("survived_mutants", [])[:3]:
                survived_preview += (
                    f'<div class="mini-mutant">'
                    f'<strong>{_html_esc(sm.get("function","?"))}</strong>'
                    f' line {sm.get("line","?")} — '
                    f'<span>{_html_esc(sm.get("description",""))}</span>'
                    f'</div>'
                )
            expand_content = ""
            if survived_preview:
                expand_content = (
                    f'<div class="op-expand-title">Top survived mutants for {_html_esc(op)}</div>'
                    + survived_preview
                )
            else:
                expand_content = '<div style="color:var(--green);font-size:12px">✓ All non-equivalent mutants killed</div>'

            html += f"""
<div class="op-row" id="op-{_html_esc(op)}">
  <div class="op-row-header" onclick="toggleOp('{_html_esc(op)}')">
    <span class="op-badge">{_html_esc(op)}</span>
    <div class="op-info">
      <div class="op-name">{_html_esc(d["name"])}</div>
      <div class="op-plain">{_html_esc(d["plain"])}</div>
    </div>
    <div class="op-center">
      <div class="bar-track"><div class="bar-fill" data-w="{pct}" style="background:{bar_color}"></div></div>
      <div class="bar-label"><span>{k} of {non_eq} killed</span><span>{pct}%</span></div>
    </div>
    {_op_status_badge(d["status"])}
    <span class="op-chevron">▼</span>
  </div>
  <div class="op-expand" id="op-expand-{_html_esc(op)}">{expand_content}</div>
</div>"""

    html += "\n</section>"
    return html


def _build_action_plan(ops: dict, survived_mutants: list[dict]) -> str:
    items = _build_action_plan_items(ops, survived_mutants)
    if not items:
        return ""

    num_symbols = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"]
    pri_cls = {"HIGH": "pri-high", "MEDIUM": "pri-medium", "LOW": "pri-low"}

    rows = ""
    for i, item in enumerate(items):
        sym = num_symbols[i] if i < len(num_symbols) else str(i + 1)
        pc = pri_cls.get(item["risk"], "pri-medium")
        rows += f"""
<li class="action-item anim-fade">
  <div class="action-num {pc}">{sym}</div>
  <div class="action-body">
    <div class="action-title">Fix {_html_esc(item["name"])} coverage [{_html_esc(item["op"])}]</div>
    <div class="action-meta">
      <span class="action-impact">Impact: {_html_esc(item["risk"])}</span>
      <span class="action-effort">Effort: {_html_esc(item["effort"])}</span>
      <span class="op-pill">{_html_esc(item["op"])}</span>
      <span style="font-size:11px;color:var(--text3)">{item["count"]} mutants</span>
    </div>
    <div class="action-desc">{_html_esc(item["plain"])}</div>
    <div class="action-example">Example gap: {_html_esc(item["example_func"])} line {item["example_line"]} — {_html_esc(item["example_desc"])}</div>
  </div>
</li>"""

    return f"""
<section class="action-section anim-fade">
  <div class="section-title">Priorities</div>
  <div class="section-heading">Your Action Plan</div>
  <div class="section-sub">Prioritised fixes ranked by impact — address these to raise your score</div>
  <ol class="action-list">{rows}</ol>
</section>"""


def _build_survived_table(survived_mutants: list[dict], ops: dict) -> str:
    count = len(survived_mutants)
    all_ops = sorted(set(m.get("operator", "") for m in survived_mutants))
    all_funcs = sorted(set(m.get("function", "") for m in survived_mutants))

    op_opts = "".join(f'<option value="{_html_esc(op)}">{_html_esc(op)}</option>'
                      for op in all_ops)
    func_opts = "".join(f'<option value="{_html_esc(f)}">{_html_esc(f)}</option>'
                        for f in all_funcs)

    return f"""
<section class="table-section anim-fade" id="survived-section">
  <div class="section-title">Gaps</div>
  <div class="section-heading">{count} Gaps Found — Detailed View</div>
  <div class="section-sub">These mutations survived — your tests did not catch them</div>

  <div class="table-controls">
    <div class="search-box">
      <input type="search" placeholder="Search by function, operator, line..." oninput="onSearch(this.value)">
    </div>
    <select class="filter-select" onchange="onFilterOp(this.value)">
      <option value="">All Operators</option>
      {op_opts}
    </select>
    <select class="filter-select" onchange="onFilterFunc(this.value)">
      <option value="">All Functions</option>
      {func_opts}
    </select>
    <div class="view-toggle">
      <button class="view-btn active" data-view="table" onclick="setView('table')">Table</button>
      <button class="view-btn" data-view="func" onclick="setView('func')">By Function</button>
      <button class="view-btn" data-view="op" onclick="setView('op')">By Operator</button>
    </div>
    <span style="font-size:12px;color:var(--text3);margin-left:8px" id="table-count">{count} of {count}</span>
  </div>

  <div id="view-table">
    <table class="mutant-table">
      <thead>
        <tr>
          <th data-sort="mutant_id" onclick="sortByCol('mutant_id')">ID <span class="sort-arrow">↕</span></th>
          <th data-sort="risk" onclick="sortByCol('risk')">Risk <span class="sort-arrow">↓</span></th>
          <th data-sort="operator" onclick="sortByCol('operator')">Operator <span class="sort-arrow">↕</span></th>
          <th data-sort="function" onclick="sortByCol('function')">Function <span class="sort-arrow">↕</span></th>
          <th data-sort="line" onclick="sortByCol('line')">Line <span class="sort-arrow">↕</span></th>
          <th data-sort="description" onclick="sortByCol('description')">What Changed <span class="sort-arrow">↕</span></th>
          <th>Plain English</th>
          <th>Fix</th>
        </tr>
      </thead>
      <tbody id="mutant-table-body">
        <tr><td colspan="8" class="no-results" style="text-align:center;padding:40px;color:var(--text3)">Loading...</td></tr>
      </tbody>
    </table>
  </div>
  <div id="view-group" style="display:none"></div>
</section>"""


def _build_killed_section(killed_mutants: list[dict]) -> str:
    count = len(killed_mutants)
    rows = ""
    for m in killed_mutants[:200]:  # cap for performance
        op = m.get("operator", "")
        rows += (
            f'<tr>'
            f'<td style="font-family:var(--mono);color:var(--text3)">{_html_esc(m.get("mutant_id",""))}</td>'
            f'<td><span class="op-pill">{_html_esc(op)}</span></td>'
            f'<td style="font-family:var(--mono)">{_html_esc(m.get("function",""))}</td>'
            f'<td style="text-align:center;color:var(--text2)">{m.get("line","")}</td>'
            f'<td style="color:var(--text2)">{_html_esc(m.get("description",""))}</td>'
            f'<td><span class="badge badge-killed">KILLED</span></td>'
            f'</tr>'
        )
    note = f' (showing first 200 of {count})' if count > 200 else ""
    return f"""
<section class="collapsible-section anim-fade">
  <details>
    <summary>✓ {count} Bugs Caught{note}</summary>
    <div class="details-body">
      <p style="font-size:13px;color:var(--text2);margin-bottom:14px">
        These mutations were detected by your existing tests. No action needed.
      </p>
      <table class="mutant-table">
        <thead><tr>
          <th>ID</th><th>Operator</th><th>Function</th><th>Line</th>
          <th>Description</th><th>Status</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </details>
</section>"""


def _build_equiv_section(equivalent: int, raw_score: float, true_score: float,
                          equiv_examples: list[dict]) -> str:
    example_rows = ""
    for ex in equiv_examples[:8]:
        example_rows += (
            f'<tr>'
            f'<td>{_html_esc(ex.get("mutant_id",""))}</td>'
            f'<td><span class="op-pill">{_html_esc(ex.get("operator",""))}</span></td>'
            f'<td style="font-family:var(--mono)">{_html_esc(ex.get("function",""))}</td>'
            f'<td>{_html_esc(ex.get("description",""))}</td>'
            f'<td style="color:var(--text2);font-size:11px">{_html_esc(ex.get("reason","Mathematical equivalence"))}</td>'
            f'</tr>'
        )
    return f"""
<section class="collapsible-section anim-fade">
  <details>
    <summary>≡ {equivalent} False Positives Removed</summary>
    <div class="details-body">
      <div class="equiv-box">
        <h4>What are equivalent mutants?</h4>
        <p>Some code changes look different but produce identical results for every possible input.
           For example, writing <code>x - 1</code> and <code>x + (-1)</code> always produce the same
           number — no test can tell them apart because there is nothing to tell apart.</p>
        <p>If we counted these, your score would appear to be
           <strong style="color:var(--red)">{raw_score}%</strong> instead of
           <span class="equiv-highlight">{true_score}%</span>. QAMill removes them automatically
           using mathematical proofs and AI analysis, giving you a score you can actually trust.</p>
        <p><strong>{equivalent} equivalent mutants</strong> were found and removed from your score in this analysis.</p>
      </div>
      {"<table class='equiv-table'><thead><tr><th>ID</th><th>Operator</th><th>Function</th><th>Mutation</th><th>Why Equivalent</th></tr></thead><tbody>" + example_rows + "</tbody></table>" if example_rows else ""}
    </div>
  </details>
</section>"""


def _build_footer(timestamp: str, exec_time: float, total: int) -> str:
    mutants_per_sec = round(total / exec_time, 1) if exec_time > 0 else "—"
    return f"""
<footer class="qm-footer">
  <strong>QAMill</strong> — AI-Powered Mutation Testing
  <div class="footer-meta">
    <span>Generated: {_html_esc(timestamp)}</span>
    <span>Execution time: {exec_time:.1f}s</span>
    <span>Speed: {mutants_per_sec} mutants/second</span>
    <span>Team: BGSW/EVE M/PJ-CVV</span>
  </div>
</footer>
<button class="btn" id="back-to-top" onclick="scrollToTop()" title="Back to top">↑</button>"""


def _build_login_modal() -> str:
    return """
<div class="modal-overlay" id="login-modal">
  <div class="modal" style="width:420px">
    <div class="modal-header">
      <h3>Your Sender Identity</h3>
      <button class="modal-close" onclick="closeLoginModal()">✕</button>
    </div>
    <div class="modal-body">
      <p style="font-size:13px;color:var(--text2);margin-bottom:18px;line-height:1.6">
        Set your email so it is automatically filled in when you email reports.
        Your app password is stored only in this browser — never sent anywhere except your SMTP provider.
      </p>
      <div class="form-group">
        <label>Account Type</label>
        <div class="type-toggle">
          <button class="type-btn active work" id="type-work" onclick="setEmailType('work')">💼 Work Email</button>
          <button class="type-btn personal" id="type-personal" onclick="setEmailType('personal')">🏠 Personal Email</button>
        </div>
        <input type="hidden" id="login-type" value="work">
      </div>
      <div class="form-group">
        <label>Your Email Address</label>
        <input type="email" id="login-email" placeholder="you@company.com"
               style="font-size:14px;padding:10px 12px">
      </div>
      <div class="form-group">
        <label>App Password <span style="font-weight:400;color:var(--text3)">(optional — saves re-entering it)</span></label>
        <input type="password" id="login-password" placeholder="xxxx xxxx xxxx xxxx">
        <div class="hint">
          Stored locally in your browser only. Not sent to any server except your mail provider when you send a report.<br>
          <a href="https://myaccount.google.com/apppasswords" target="_blank">Gmail → Security → App Passwords</a> &nbsp;·&nbsp;
          <a href="https://account.live.com/proofs/AppPassword" target="_blank">Outlook App Password</a>
        </div>
      </div>
      <div class="login-error" id="login-error"></div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="clearIdentity();closeLoginModal()" style="color:var(--red);border-color:var(--red);margin-right:auto">Clear</button>
      <button class="btn" onclick="closeLoginModal()">Cancel</button>
      <button class="btn btn-primary" onclick="saveLogin()">Save Identity</button>
    </div>
  </div>
</div>"""


def _build_email_modal(file_name: str) -> str:
    return """
<div class="modal-overlay" id="email-modal">
  <div class="modal">
    <div class="modal-header">
      <h3>✉ Email Report</h3>
      <button class="modal-close" onclick="closeEmailModal()">✕</button>
    </div>
    <div class="modal-body">
      <!-- Sender identity bar — shown when logged in -->
      <div class="sender-as-bar" id="sender-as-bar">
        <span class="sender-as-dot"></span>
        <span class="sender-as-text">Sending as: —</span>
        <span class="sender-as-change" onclick="closeEmailModal();openLoginModal()">Change identity</span>
      </div>
      <!-- Not logged in nudge — shown when no identity set -->
      <div id="no-identity-nudge" style="display:none;font-size:12px;color:var(--amber);
           background:rgba(210,153,34,.08);border:1px solid rgba(210,153,34,.25);
           border-radius:var(--radius);padding:9px 12px;margin-bottom:14px">
        ⚠ No sender identity set.
        <span style="cursor:pointer;color:var(--blue);margin-left:4px"
              onclick="closeEmailModal();openLoginModal()">Log in with your work or personal email →</span>
      </div>
      <div class="form-group">
        <label>Recipient Email</label>
        <input type="email" id="email-to" placeholder="colleague@company.com">
      </div>
      <div class="form-group">
        <label>Subject</label>
        <input type="text" id="email-subject">
      </div>
      <div class="form-group">
        <label>Message</label>
        <textarea id="email-body"></textarea>
      </div>
      <div class="form-group">
        <label>SMTP Provider</label>
        <select id="smtp-provider" onchange="onSmtpChange(this.value)">
          <option value="gmail">Gmail</option>
          <option value="outlook">Outlook / Microsoft 365</option>
          <option value="custom">Custom SMTP</option>
        </select>
      </div>
      <div class="form-group" id="smtp-custom" style="display:none">
        <label>SMTP Host</label>
        <input type="text" id="smtp-host" placeholder="mail.example.com">
        <input type="number" id="smtp-port" placeholder="587" style="margin-top:6px;width:100px">
      </div>
      <div class="form-group">
        <label>Your Email (Sender)</label>
        <input type="email" id="email-from" placeholder="you@gmail.com">
      </div>
      <div class="form-group">
        <label>App Password</label>
        <input type="password" id="email-pass" placeholder="xxxx xxxx xxxx xxxx">
        <div class="hint">
          Use an App Password, not your regular password.<br>
          <a href="https://myaccount.google.com/apppasswords" target="_blank">
            Gmail: myaccount.google.com → Security → App Passwords
          </a>
        </div>
      </div>
      <div class="modal-msg" id="modal-msg"></div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeEmailModal()">Cancel</button>
      <button class="btn btn-primary" id="send-btn" onclick="sendEmail()">Send Report</button>
    </div>
  </div>
</div>"""


# ── Main builder ──────────────────────────────────────────────────────────────

def build_html_report(data: dict) -> str:
    """
    Build a complete self-contained elite HTML report from analysis data.

    data keys:
      file_name, timestamp, execution_time, true_score, raw_score,
      killed, survived, equivalent, total, llm_provider,
      mutants (list of mutant_result events)
    """
    file_name     = data.get("file_name", "unknown")
    timestamp     = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M"))
    exec_time     = float(data.get("execution_time", 0))
    true_score    = float(data.get("true_score", 0))
    raw_score     = float(data.get("raw_score", 0))
    killed        = int(data.get("killed", 0))
    survived      = int(data.get("survived", 0))
    equivalent    = int(data.get("equivalent", 0))
    total         = int(data.get("total", 0))
    mutants       = data.get("mutants", [])

    ops = _compute_operators(mutants)
    survived_mutants = [m for m in mutants if m.get("status") == "survived"]
    killed_mutants   = [m for m in mutants if m.get("status") == "killed"]
    equiv_mutants    = [m for m in mutants if m.get("status") == "equivalent"]

    # Enrich survived mutants with plain English and suggested fixes
    for m in survived_mutants:
        m["_plain"] = _plain_english(m)
        m["_fix"]   = _suggested_fix(m)
        m["_risk"]  = RISK_LEVELS.get(m.get("operator", ""), "MEDIUM")

    # Build JSON payload for JavaScript
    report_data_js = {
        "file_name": file_name,
        "true_score": true_score,
        "raw_score": raw_score,
        "killed": killed,
        "survived": survived,
        "equivalent": equivalent,
        "total": total,
        "survived_mutants": survived_mutants,
        "risk_levels": RISK_LEVELS,
        "op_info": {op: {"name": d["name"], "plain": d["plain"]}
                    for op, d in ops.items()},
    }
    data_json = json.dumps(report_data_js, ensure_ascii=False, default=str)
    # Prevent </script> injection
    data_json = data_json.replace("</script>", "<\\/script>")

    sections = "\n".join([
        _build_header(file_name, timestamp),
        _build_health_badge(true_score, killed, survived, equivalent),
        _build_score_cards(true_score, raw_score, killed, survived, equivalent, total),
        _build_insights(ops),
        _build_operators(ops),
        _build_action_plan(ops, survived_mutants),
        _build_survived_table(survived_mutants, ops),
        _build_killed_section(killed_mutants),
        _build_equiv_section(equivalent, raw_score, true_score, equiv_mutants[:8]),
        _build_footer(timestamp, exec_time, total),
        _build_email_modal(file_name),
        _build_login_modal(),
    ])

    return f"""<!DOCTYPE html>
<html data-theme="dark" lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QAMill Report — {_html_esc(file_name)}</title>
<style>
{_CSS}
</style>
</head>
<body>
{sections}
<script>window.REPORT_DATA = {data_json};</script>
<script>
{_JS}
</script>
</body>
</html>"""


# ── Demo data & generation ────────────────────────────────────────────────────

def _make_demo_mutants() -> list[dict]:
    """Generate realistic demo mutants for math_utils.py (445 total)."""
    mutants: list[dict] = []

    # Operator distributions matching: 174 killed, 40 survived, 231 equivalent
    # (verified to sum to 445 total)
    ops_distribution = [
        # (op,  total, killed, survived, equivalent)
        ("AOR", 48,    25,     1,        22),
        ("ROR", 42,    18,     2,        22),
        ("LCR", 22,    14,     0,         8),
        ("BCR", 20,     8,     0,        12),
        ("RVR", 36,    30,     0,         6),
        ("SDL", 38,     4,    10,        24),
        ("NIM", 30,    10,     5,        15),
        ("BVM", 38,     9,     7,        22),
        ("EHM", 26,     5,     3,        18),
        ("DFM", 20,    10,     0,        10),
        ("SCM", 20,     4,     2,        14),
        ("LMO", 18,     0,     9,         9),
        ("AMO", 10,     5,     0,         5),
        ("AIM", 12,     4,     0,         8),
        ("TCM", 16,     8,     0,         8),
        ("CEM", 10,     0,     1,         9),
        ("CMR", 39,    20,     0,        19),
    ]

    # Survived mutant definitions (40 total, 1+2+0+0+0+10+5+7+3+0+2+9+0+0+0+1+0 = 40)
    survived_details = {
        "AOR": [
            {"function": "percentage", "line": 312, "description": "/ → *",
             "original_src": "def percentage(part, total):\n    if total == 0:\n        return 0.0\n    return (part / total) * 100",
             "mutant_src": "def percentage(part, total):\n    if total == 0:\n        return 0.0\n    return (part * total) * 100"},
        ],
        "ROR": [
            {"function": "is_valid_age", "line": 201, "description": ">= → >",
             "original_src": "def is_valid_age(age):\n    return 0 <= age <= 150",
             "mutant_src": "def is_valid_age(age):\n    return 0 < age <= 150"},
            {"function": "process_payment", "line": 183, "description": "<= → <",
             "original_src": "    if amount <= 0:\n        return False",
             "mutant_src": "    if amount < 0:\n        return False"},
        ],
        "SDL": [
            {"function": "create_account",    "line": 142, "description": "statement deleted",
             "original_src": "    if not isinstance(user_id, int):\n        raise ValueError('user_id must be int')",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "process_payment",   "line": 195, "description": "statement deleted",
             "original_src": "    logging.info(f'Payment {amount} from {from_acct} to {to_acct}')",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "transfer_funds",    "line": 248, "description": "statement deleted",
             "original_src": "    if balance < amount:\n        return 'INSUFFICIENT_FUNDS'",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "get_user_status",   "line": 301, "description": "statement deleted",
             "original_src": "    if user_id <= 0:\n        return 'INVALID'",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "safe_divide",       "line": 345, "description": "statement deleted",
             "original_src": "    if b == 0:\n        raise ZeroDivisionError('Cannot divide by zero')",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "is_valid_age",      "line": 389, "description": "statement deleted",
             "original_src": "    if age > 150:\n        return False",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "get_grade",         "line": 421, "description": "statement deleted",
             "original_src": "    if score < 0 or score > 100:\n        return 'INVALID'",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "is_leap_year",      "line": 456, "description": "statement deleted",
             "original_src": "    if year % 100 == 0 and year % 400 != 0:\n        return False",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "clamp",             "line": 489, "description": "statement deleted",
             "original_src": "    assert min_val <= max_val, 'min must be <= max'",
             "mutant_src": "    pass  # statement deleted"},
            {"function": "get_connection_string", "line": 510, "description": "statement deleted",
             "original_src": "    if not host:\n        raise ValueError('host cannot be empty')",
             "mutant_src": "    pass  # statement deleted"},
        ],
        "NIM": [
            {"function": "process_payment",       "line": 183, "description": "from_account → None",
             "original_src": "    result = db.transfer(from_account, to_account, amount)",
             "mutant_src": "    result = db.transfer(None, to_account, amount)"},
            {"function": "create_account",        "line": 142, "description": "user_id → None",
             "original_src": "    account = Account(user_id=user_id, balance=initial_balance)",
             "mutant_src": "    account = Account(user_id=None, balance=initial_balance)"},
            {"function": "get_user_status",       "line": 301, "description": "user_id → None",
             "original_src": "    return db.get_status(user_id, is_admin)",
             "mutant_src": "    return db.get_status(None, is_admin)"},
            {"function": "transfer_funds",        "line": 248, "description": "to_account → None",
             "original_src": "    ledger.record(from_account, to_account, amount)",
             "mutant_src": "    ledger.record(from_account, None, amount)"},
            {"function": "get_connection_string", "line": 278, "description": "host → None",
             "original_src": "    conn = connect(host=host, port=port, db=database)",
             "mutant_src": "    conn = connect(host=None, port=port, db=database)"},
        ],
        "BVM": [
            {"function": "transfer_funds",        "line": 165, "description": "0 → 1",
             "original_src": "    if amount <= 0:\n        return 'INVALID_AMOUNT'",
             "mutant_src": "    if amount <= 1:\n        return 'INVALID_AMOUNT'"},
            {"function": "is_valid_age",          "line": 201, "description": "0 → 1",
             "original_src": "    return 0 <= age <= 150",
             "mutant_src": "    return 1 <= age <= 150"},
            {"function": "clamp",                 "line": 234, "description": "min_val → min_val + 1",
             "original_src": "    return max(min_val, min(value, max_val))",
             "mutant_src": "    return max(min_val + 1, min(value, max_val))"},
            {"function": "get_connection_string", "line": 278, "description": "0 → -1",
             "original_src": "    if port <= 0:\n        raise ValueError('Invalid port')",
             "mutant_src": "    if port <= -1:\n        raise ValueError('Invalid port')"},
            {"function": "percentage",            "line": 312, "description": "0.0 → 1.0",
             "original_src": "    if total == 0:\n        return 0.0",
             "mutant_src": "    if total == 0:\n        return 1.0"},
            {"function": "is_valid_age",          "line": 201, "description": "150 → 149",
             "original_src": "    return 0 <= age <= 150",
             "mutant_src": "    return 0 <= age <= 149"},
            {"function": "get_grade",             "line": 356, "description": "90 → 89",
             "original_src": "    if score >= 90:\n        return 'A'",
             "mutant_src": "    if score >= 89:\n        return 'A'"},
        ],
        "EHM": [
            {"function": "safe_divide",  "line": 345, "description": "except ZeroDivisionError → pass",
             "original_src": "    try:\n        return a / b\n    except ZeroDivisionError:\n        raise",
             "mutant_src": "    try:\n        return a / b\n    except ZeroDivisionError:\n        pass"},
            {"function": "factorial",    "line": 389, "description": "except ValueError → pass",
             "original_src": "    if n < 0:\n        raise ValueError('n must be non-negative')",
             "mutant_src": "    pass  # raise removed"},
            {"function": "create_account", "line": 142, "description": "raise ValueError → pass",
             "original_src": "    if initial_balance < 0:\n        raise ValueError('Balance cannot be negative')",
             "mutant_src": "    if initial_balance < 0:\n        pass  # raise removed"},
        ],
        "SCM": [
            {"function": "get_user_status", "line": 301, "description": "'admin' → ''",
             "original_src": "    if role == 'admin':\n        return 'ADMIN'",
             "mutant_src": "    if role == '':\n        return 'ADMIN'"},
            {"function": "create_account",  "line": 142, "description": "'active' → 'ACTIVE'",
             "original_src": "    return {'status': 'active', 'user_id': user_id}",
             "mutant_src": "    return {'status': 'ACTIVE', 'user_id': user_id}"},
        ],
        "LMO": [
            {"function": "find_first_positive", "line": 52,  "description": "loop: list[1:] (skip first)",
             "original_src": "    for num in numbers:\n        if num > 0:\n            return num\n    return None",
             "mutant_src": "    for num in numbers[1:]:\n        if num > 0:\n            return num\n    return None"},
            {"function": "find_first_positive", "line": 52,  "description": "loop: list[:-1] (skip last)",
             "original_src": "    for num in numbers:\n        if num > 0:\n            return num\n    return None",
             "mutant_src": "    for num in numbers[:-1]:\n        if num > 0:\n            return num\n    return None"},
            {"function": "running_total",       "line": 89,  "description": "loop: list[1:] (skip first)",
             "original_src": "    total = 0\n    for n in numbers:\n        total += n\n        yield total",
             "mutant_src": "    total = 0\n    for n in numbers[1:]:\n        total += n\n        yield total"},
            {"function": "running_total",       "line": 89,  "description": "loop: list[:-1] (skip last)",
             "original_src": "    total = 0\n    for n in numbers:\n        total += n\n        yield total",
             "mutant_src": "    total = 0\n    for n in numbers[:-1]:\n        total += n\n        yield total"},
            {"function": "find_first_positive", "line": 52,  "description": "while True → while False",
             "original_src": "    while True:\n        ...",
             "mutant_src": "    while False:\n        ..."},
            {"function": "running_total",       "line": 90,  "description": "loop: negate while condition",
             "original_src": "    while items:\n        process(items.pop())",
             "mutant_src": "    while not items:\n        process(items.pop())"},
            {"function": "is_leap_year",        "line": 120, "description": "loop: range starts at 1",
             "original_src": "    for _ in range(count):\n        check_year(year)",
             "mutant_src": "    for _ in range(1, count):\n        check_year(year)"},
            {"function": "clamp",               "line": 156, "description": "loop: range starts at 1",
             "original_src": "    for i in range(len(values)):\n        values[i] = clamp(values[i], lo, hi)",
             "mutant_src": "    for i in range(1, len(values)):\n        values[i] = clamp(values[i], lo, hi)"},
            {"function": "find_first_positive", "line": 52,  "description": "loop runs 0 times (range mutation)",
             "original_src": "    for num in numbers:\n        if num > 0:\n            return num",
             "mutant_src": "    for num in numbers[:0]:\n        if num > 0:\n            return num"},
        ],
        "CEM": [
            {"function": "parse_config", "line": 412, "description": "os.environ.get → default",
             "original_src": "    return os.environ.get(key, default)",
             "mutant_src": "    return default  # env var bypassed"},
        ],
    }

    idx = 1
    for op, total_cnt, k_cnt, s_cnt, eq_cnt in ops_distribution:
        details_list = survived_details.get(op, [])

        # Add survived mutants
        for i, detail in enumerate(details_list[:s_cnt]):
            mutants.append({
                "mutant_id": f"M{idx:04d}",
                "operator": op,
                "function": detail["function"],
                "line": detail["line"],
                "description": detail["description"],
                "original_src": detail.get("original_src", ""),
                "mutant_src": detail.get("mutant_src", ""),
                "status": "survived",
                "difficulty": "high" if RISK_LEVELS.get(op) == "HIGH" else "medium",
                "hint": None,
                "priority": RISK_LEVELS.get(op, "MEDIUM").lower(),
            })
            idx += 1

        # Add killed mutants
        func_names = ["add", "subtract", "multiply", "divide", "is_even",
                       "is_positive", "clamp", "factorial", "is_valid_age",
                       "max_of_three", "percentage", "is_leap_year"]
        for j in range(k_cnt):
            fn = func_names[j % len(func_names)]
            mutants.append({
                "mutant_id": f"M{idx:04d}",
                "operator": op,
                "function": fn,
                "line": 40 + j * 7,
                "description": f"operator mutated ({op})",
                "original_src": f"# Original code in {fn}",
                "mutant_src": f"# Mutated code in {fn}",
                "status": "killed",
                "killer_test_file": "test_math_utils.py",
                "killer_test_name": f"test_{fn}_basic",
            })
            idx += 1

        # Add equivalent mutants
        for j in range(eq_cnt):
            fn = func_names[j % len(func_names)]
            mutants.append({
                "mutant_id": f"M{idx:04d}",
                "operator": op,
                "function": fn,
                "line": 30 + j * 5,
                "description": f"equivalent mutation ({op})",
                "original_src": f"# Equivalent original in {fn}",
                "mutant_src": f"# Equivalent mutant in {fn}",
                "status": "equivalent",
                "reason": "Mathematical equivalence detected by Z3 solver" if j % 2 == 0
                           else "Rule-based: semantically identical expressions",
                "method": "z3" if j % 2 == 0 else "rule",
            })
            idx += 1

    return mutants


def build_demo_report() -> str:
    """Generate demo report using known math_utils.py analysis results."""
    mutants = _make_demo_mutants()
    data = {
        "file_name": "math_utils.py",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "execution_time": 127.3,
        "true_score": 81.3,
        "raw_score": 39.1,
        "killed": 174,
        "survived": 40,
        "equivalent": 231,
        "total": 445,
        "llm_provider": "claude",
        "mutants": mutants,
    }
    return build_html_report(data)


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    out_path = sys.argv[1] if len(sys.argv) > 1 else "qamill-demo-report.html"
    html = build_demo_report()
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"Demo report written to: {out_path}  ({len(html):,} bytes)")
