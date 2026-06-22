"""
report_generator.py
Elite self-contained HTML report generator for QAMill mutation testing results.
Generates a single HTML file with inline CSS and JavaScript — no server required.
"""
import base64
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

# ── Logo / favicon loader ─────────────────────────────────────────────────────

_ASSETS = Path(__file__).parent / "assets"

def _load_logo_b64() -> str:
    """Return base64 PNG data URI for the QAMill logo, or '' if not yet saved."""
    f = _ASSETS / "qamill-logo-b64.txt"
    return f.read_text().strip() if f.exists() else ""

def _load_favicon_b64() -> str:
    f = _ASSETS / "qamill-favicon-b64.txt"
    return f.read_text().strip() if f.exists() else _load_logo_b64()

def _logo_img(height: str = "32px") -> str:
    b64 = _load_logo_b64()
    if b64:
        return f'<img src="data:image/png;base64,{b64}" alt="QAMill" style="height:{height};vertical-align:middle">'
    # Fallback: text mark
    return '<span style="font-size:22px;font-weight:800;color:var(--teal)">QAMill</span>'

def _favicon_tag() -> str:
    b64 = _load_favicon_b64()
    if b64:
        return f'<link rel="icon" type="image/png" href="data:image/png;base64,{b64}">'
    return '<link rel="icon" href="data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 100 100\'><text y=\'.9em\' font-size=\'90\'>⚗</text></svg>">'

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

/* ── Auth Modal (elite) ── */
.am-overlay{position:fixed;inset:0;background:rgba(0,0,0,.75);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
  z-index:999;display:none;align-items:center;justify-content:center;
  padding:16px}
@keyframes amFadeIn{from{opacity:0}to{opacity:1}}
.am-card{background:var(--surface);border:1px solid var(--border);
  border-radius:16px;width:460px;max-width:100%;max-height:90vh;
  overflow-y:auto;box-shadow:0 32px 80px rgba(0,0,0,.6);
  animation:amSlideUp .25s cubic-bezier(.34,1.2,.64,1)}
@keyframes amSlideUp{from{transform:translateY(24px);opacity:0}to{transform:none;opacity:1}}
.am-header{display:flex;align-items:center;justify-content:space-between;
  padding:20px 22px 0}
.am-header-left{display:flex;flex-direction:column;gap:2px}
.am-logo{font-size:18px;font-weight:700;color:var(--teal);letter-spacing:-.3px}
.am-tagline{font-size:12px;color:var(--text3)}
.am-close{background:none;border:none;color:var(--text2);font-size:18px;
  cursor:pointer;padding:4px 8px;border-radius:6px;line-height:1;
  transition:all .15s}
.am-close:hover{background:var(--surface2);color:var(--text)}
/* Primary identity banner */
.am-identity{display:flex;align-items:center;gap:12px;
  background:rgba(63,185,80,.07);border:1px solid rgba(63,185,80,.2);
  border-radius:10px;padding:12px 14px;margin:14px 22px 0}
.am-avatar{width:38px;height:38px;border-radius:50%;background:var(--teal);
  color:#0d1117;font-size:16px;font-weight:700;display:flex;
  align-items:center;justify-content:center;flex-shrink:0;overflow:hidden}
.am-avatar img{width:100%;height:100%;object-fit:cover;border-radius:50%}
.am-identity-text{flex:1;min-width:0}
.am-identity-name{font-size:13px;font-weight:600;color:var(--text)}
.am-identity-email{font-size:11px;color:var(--text2);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.am-identity-badge{font-size:10px;font-weight:700;letter-spacing:.06em;
  background:rgba(63,185,80,.15);color:var(--teal);
  padding:2px 8px;border-radius:20px;flex-shrink:0}
/* Tabs */
.am-tabs{display:flex;gap:2px;padding:14px 22px 0;border-bottom:1px solid var(--border);
  margin:14px 0 0}
.am-tab{background:none;border:none;color:var(--text2);font-size:13px;
  font-family:var(--font);padding:8px 14px;cursor:pointer;border-radius:6px 6px 0 0;
  position:relative;bottom:-1px;border-bottom:2px solid transparent;
  transition:color .15s}
.am-tab:hover{color:var(--text)}
.am-tab.active{color:var(--teal);border-bottom-color:var(--teal);
  background:var(--surface2)}
/* Panes */
.am-pane{padding:18px 22px}
.am-hint{font-size:12px;color:var(--text3);margin-bottom:14px;line-height:1.55}
/* Provider rows */
.am-provider-row{display:flex;align-items:center;gap:12px;
  border:1px solid var(--border);border-radius:10px;padding:11px 14px;
  margin-bottom:8px;transition:border-color .15s,background .15s}
.am-provider-row:hover{border-color:var(--teal);background:var(--surface2)}
.am-provider-row.connected{border-color:rgba(63,185,80,.4);
  background:rgba(63,185,80,.05)}
.am-provider-icon{width:34px;height:34px;border-radius:8px;
  display:flex;align-items:center;justify-content:center;
  font-size:14px;font-weight:800;flex-shrink:0;overflow:hidden}
.am-provider-icon svg,.am-provider-icon img{width:20px;height:20px}
.am-provider-info{flex:1;min-width:0}
.am-provider-name{font-size:13px;font-weight:600;color:var(--text)}
.am-provider-sub{font-size:11px;color:var(--text2);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.am-provider-sub.email-badge{color:var(--blue);font-weight:500}
.am-connected-tick{color:var(--teal);font-size:16px;flex-shrink:0}
.am-btn{display:inline-flex;align-items:center;gap:5px;padding:6px 14px;
  border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;
  border:1px solid var(--border);background:var(--surface2);color:var(--text);
  font-family:var(--font);transition:all .15s;white-space:nowrap}
.am-btn:hover{border-color:var(--teal);color:var(--teal)}
.am-btn-primary{background:var(--teal);color:#0d1117;border-color:var(--teal)}
.am-btn-primary:hover{background:#5dcd6e;color:#0d1117}
.am-btn-danger{color:var(--red);border-color:rgba(248,81,73,.4)}
.am-btn-danger:hover{background:rgba(248,81,73,.1);border-color:var(--red)}
/* LLM key entry */
.am-key-entry{margin-top:12px;background:var(--surface2);
  border:1px solid var(--border);border-radius:8px;padding:14px}
.am-key-label{font-size:12px;font-weight:600;color:var(--text2);
  text-transform:uppercase;letter-spacing:.06em}
.am-key-status{font-size:12px;margin-top:8px;min-height:16px}
.am-key-status.ok{color:var(--teal)}
.am-key-status.err{color:var(--red)}
.am-key-status.spin{color:var(--text3)}
.am-input{width:100%;padding:9px 12px;border-radius:6px;
  border:1px solid var(--border);background:var(--surface);color:var(--text);
  font-size:13px;font-family:var(--font)}
.am-input:focus{outline:none;border-color:var(--teal)}
/* Type toggle (Email tab) */
.am-type-row{display:flex;gap:6px;margin-bottom:12px}
.am-type-btn{flex:1;padding:8px 0;border-radius:6px;font-size:13px;cursor:pointer;
  border:1px solid var(--border);background:var(--surface2);color:var(--text2);
  font-family:var(--font);font-weight:500;transition:all .15s}
.am-type-btn:hover{border-color:var(--blue);color:var(--blue)}
.am-type-btn.active{background:var(--blue);color:#fff;border-color:var(--blue)}
/* Footer */
.am-footer{padding:10px 22px 18px;font-size:11px;color:var(--text3);
  border-top:1px solid var(--border);margin-top:4px}
.am-footer code{font-family:var(--mono);background:var(--surface2);
  padding:1px 5px;border-radius:4px}
/* ── Auth gate (sign in / sign up) ── */
#am-authgate{padding:20px 22px 8px}
.am-seg{display:flex;background:var(--surface2);border-radius:10px;padding:4px;
  margin-bottom:18px}
.am-seg-btn{flex:1;padding:8px 0;border:none;background:none;cursor:pointer;
  font-family:var(--font);font-size:13px;font-weight:600;color:var(--text2);
  border-radius:7px;transition:all .15s}
.am-seg-btn.active{background:var(--teal);color:#0d1117}
.am-social-grid{display:flex;flex-direction:column;gap:8px}
.am-social-btn{display:flex;align-items:center;gap:12px;width:100%;
  padding:10px 14px;border-radius:10px;cursor:pointer;
  background:var(--surface);border:1px solid var(--border);
  color:var(--text);font-family:var(--font);font-size:13px;font-weight:500;
  transition:border-color .15s,background .15s;text-align:left}
.am-social-btn:hover{border-color:var(--teal);background:var(--surface2)}
.am-social-ic{width:30px;height:30px;border-radius:7px;display:flex;
  align-items:center;justify-content:center;flex-shrink:0}
.am-social-ic svg{width:18px;height:18px}
.am-or{display:flex;align-items:center;text-align:center;gap:10px;
  margin:18px 0 16px;color:var(--text3);font-size:12px}
.am-or::before,.am-or::after{content:'';flex:1;height:1px;background:var(--border)}
.am-form .form-group{margin-bottom:12px}
.am-form label{display:block;font-size:11px;font-weight:600;color:var(--text2);
  margin-bottom:5px;text-transform:uppercase;letter-spacing:.04em}
/* Profile card (signed in) */
.am-profile{display:flex;align-items:center;gap:12px;
  background:rgba(63,185,80,.07);border:1px solid rgba(63,185,80,.2);
  border-radius:10px;padding:14px 16px;margin:16px 22px 0}

/* ── Setup panel ── */
.am-setup-panel{background:var(--surface2);border:1px solid var(--border);
  border-radius:10px;padding:18px;margin:14px 22px 0;animation:amFadeIn .2s ease}
.am-setup-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.am-setup-title{font-size:14px;font-weight:700;color:var(--text)}
.am-setup-steps{font-size:12px;color:var(--text2);line-height:1.9;
  padding-left:18px;margin-bottom:14px}
.am-setup-steps li{padding-left:4px}
.am-setup-steps code{background:var(--surface);border:1px solid var(--border);
  border-radius:4px;padding:1px 6px;font-family:var(--mono);font-size:11px;color:var(--teal)}
.am-setup-redirect{margin-bottom:4px}
.am-redirect-uri{display:flex;align-items:center;justify-content:space-between;gap:8px;
  background:var(--surface);border:1px solid var(--border);border-radius:6px;
  padding:8px 12px;cursor:pointer;transition:border-color .15s}
.am-redirect-uri:hover{border-color:var(--teal)}
.am-redirect-uri span{font-size:11px;font-family:var(--mono);color:var(--teal);
  word-break:break-all}
.am-copy-btn{background:none;border:1px solid var(--border);border-radius:4px;
  color:var(--text2);font-size:11px;padding:2px 8px;cursor:pointer;flex-shrink:0;
  font-family:var(--font)}
.am-copy-btn:hover{border-color:var(--teal);color:var(--teal)}
/* ── Email cap badge ── */
.am-email-cap{font-size:10px;font-weight:700;letter-spacing:.04em;
  background:rgba(63,185,80,.15);color:var(--teal);
  padding:1px 6px;border-radius:3px;margin-left:6px;vertical-align:middle}
/* ── Email modal redesign ── */
.email-via-box{display:flex;align-items:center;gap:12px;
  background:rgba(63,185,80,.07);border:1px solid rgba(63,185,80,.25);
  border-radius:var(--radius);padding:12px 14px;margin-bottom:14px}
.email-via-icon{width:36px;height:36px;border-radius:8px;
  display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden}
.email-via-icon svg{width:22px;height:22px}
.email-via-details{flex:1;min-width:0}
.email-via-label{font-size:13px;font-weight:600;color:var(--teal)}
.email-via-addr{font-size:11px;color:var(--text2)}
.email-no-account-box{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius);padding:14px;margin-bottom:14px;text-align:center}
.email-no-account-box p{font-size:13px;color:var(--text2);margin-bottom:10px}
.email-or-divider{font-size:11px;color:var(--text3);text-align:center;
  margin:14px 0;position:relative}
.email-or-divider::before,.email-or-divider::after{content:'';
  position:absolute;top:50%;width:40%;height:1px;background:var(--border)}
.email-or-divider::before{left:0}
.email-or-divider::after{right:0}

/* ── Identity chip + sign-out dropdown ── */
.id-chip{position:relative;display:inline-flex;align-items:center;gap:7px;
  padding:5px 10px 5px 5px;border-radius:20px;cursor:pointer;
  background:var(--surface2);border:1px solid var(--border);
  transition:border-color .15s;user-select:none}
.id-chip:hover{border-color:var(--teal)}
.id-avatar{width:26px;height:26px;border-radius:50%;background:var(--teal);
  color:#0d1117;font-size:11px;font-weight:700;display:flex;align-items:center;
  justify-content:center;flex-shrink:0;overflow:hidden}
.id-avatar img{width:100%;height:100%;border-radius:50%;object-fit:cover}
.id-email{font-size:12px;color:var(--text);max-width:160px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.id-caret{font-size:10px;color:var(--text3)}
/* Dropdown */
.id-menu{position:absolute;top:calc(100% + 6px);right:0;min-width:220px;
  background:var(--surface);border:1px solid var(--border);border-radius:10px;
  box-shadow:0 8px 32px rgba(0,0,0,.5);z-index:500;overflow:hidden;
  display:none;animation:amFadeIn .15s ease}
.id-chip.open .id-menu{display:block}
.id-menu-user{padding:14px 16px 12px}
.id-menu-name{font-size:13px;font-weight:600;color:var(--text);margin-bottom:2px}
.id-menu-email{font-size:11px;color:var(--text2);margin-bottom:4px;word-break:break-all}
.id-menu-provider{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:var(--teal);background:rgba(63,185,80,.12);display:inline-block;
  padding:2px 8px;border-radius:20px}
.id-menu-divider{height:1px;background:var(--border);margin:0}
.id-menu-item{display:block;width:100%;text-align:left;background:none;border:none;
  color:var(--text);font-family:var(--font);font-size:13px;padding:10px 16px;
  cursor:pointer;transition:background .12s}
.id-menu-item:hover{background:var(--surface2)}
.id-menu-signout{color:var(--red)!important}
.id-menu-signout:hover{background:rgba(248,81,73,.08)!important}

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

// ── Auth modal ────────────────────────────────────────────────────────────
var AM_API = 'http://localhost:8765';
var amCurrentLlm = null;
var amPollTimer  = null;

// ── Provider default subtitles (shown when disconnected) ─────────────────
var AM_DEFAULTS = {
  google:    'Send reports via Gmail — no App Password needed',
  microsoft: 'Send reports via Outlook — no App Password needed',
  linkedin:  'Professional identity for sender name',
  github:    'Developer identity + work email',
  atlassian: 'Jira / Confluence workspace identity',
  slack:     'Slack workspace identity',
  claude:    'Anthropic',
  gpt:       'OpenAI',
  grok:      'xAI',
  ollama:    'Local — no key needed',
};

var AM_ICONS = {
  google:    '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>',
  microsoft: '<svg viewBox="0 0 21 21" width="20" height="20"><rect x="1" y="1" width="9" height="9" fill="#f25022"/><rect x="11" y="1" width="9" height="9" fill="#7fba00"/><rect x="1" y="11" width="9" height="9" fill="#00a4ef"/><rect x="11" y="11" width="9" height="9" fill="#ffb900"/></svg>',
  linkedin:  '<svg viewBox="0 0 24 24" width="20" height="20" fill="#fff"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>',
  github:    '<svg viewBox="0 0 24 24" width="20" height="20" fill="#fff"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>',
  atlassian: '<svg viewBox="0 0 24 24" width="20" height="20"><defs><linearGradient id="atl-g" x1="98.%" y1="10.19%" x2="58.888%" y2="40.234%"><stop offset="0%" stop-color="#0052CC"/><stop offset="100%" stop-color="#2684FF"/></linearGradient></defs><path fill="url(#atl-g)" d="M.195 11.408L8.31 22.857c.504.744 1.629.744 2.133 0l8.117-11.449c.538-.75.03-1.797-.878-1.797H14.22c-.373 0-.726.172-.958.46L12 11.658l-1.262-1.587a1.21 1.21 0 0 0-.958-.46H6.073c-.909 0-1.417 1.047-.878 1.797zm11.55-9.265L9.72 5.867c.504.744 1.629.744 2.133 0l2.027-2.724a1.21 1.21 0 0 0 0-1.427L11.852.992a1.21 1.21 0 0 0-2.133 0L7.692 3.716a1.21 1.21 0 0 0 0 1.427l2.027 2.724c.504.744 1.629.744 2.133 0l2.027-2.724z" fill="#fff"/></svg>',
  slack:     '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#E01E5A" d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z"/><path fill="#36C5F0" d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z"/><path fill="#2EB67D" d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 0 1-2.522 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.164 0a2.528 2.528 0 0 1 2.522 2.522v6.312z"/><path fill="#ECB22E" d="M15.164 18.956a2.528 2.528 0 0 1 2.522 2.522A2.528 2.528 0 0 1 15.164 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.27a2.527 2.527 0 0 1-2.52-2.522 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.164a2.528 2.528 0 0 1-2.523 2.522h-6.313z"/></svg>',
  claude:    '<span style="font-size:17px;font-weight:800;color:#D4A574">✦</span>',
  gpt:       '<span style="font-size:15px;font-weight:800;color:#10A37F">⬡</span>',
  grok:      '<span style="font-size:14px;font-weight:900;color:#1DA1F2">𝕏</span>',
  ollama:    '<span style="font-size:15px;color:#9B59B6">⚙</span>',
};

var AM_PROVIDER_BG = {
  google:'#fff', microsoft:'#2f2f2f', linkedin:'#0A66C2',
  github:'#24292e', atlassian:'#0052CC', slack:'#4A154B',
  claude:'#2d1f0e', gpt:'#0a2a20', grok:'#0a1a2a', ollama:'#1a0a2a',
};

// ── Tab switching ─────────────────────────────────────────────────────────
function amTab(name) {
  document.querySelectorAll('.am-tab').forEach(function(t) {
    t.classList.toggle('active', t.getAttribute('data-tab') === name);
  });
  document.querySelectorAll('.am-pane').forEach(function(p) { p.style.display = 'none'; });
  var pane = document.getElementById('am-pane-' + name);
  if (pane) pane.style.display = '';
}

// ── Sign in / sign up / sign out ───────────────────────────────────────────
var amAuthMode = 'signin';

window.amSetAuthMode = function(mode) {
  amAuthMode = mode;
  var inSign = mode === 'signin';
  document.getElementById('am-seg-signin').classList.toggle('active', inSign);
  document.getElementById('am-seg-signup').classList.toggle('active', !inSign);
  document.getElementById('am-name-group').style.display = inSign ? 'none' : '';
  var submit = document.getElementById('am-auth-submit');
  if (submit) submit.textContent = inSign ? 'Sign in' : 'Create account';
  var pass = document.getElementById('am-auth-pass');
  if (pass) pass.setAttribute('autocomplete', inSign ? 'current-password' : 'new-password');
  var st = document.getElementById('am-auth-status');
  if (st) { st.textContent = ''; st.className = 'am-key-status'; }
};

window.amSubmitAuth = function() {
  var email = (document.getElementById('am-auth-email') || {}).value || '';
  var pass  = (document.getElementById('am-auth-pass')  || {}).value || '';
  var name  = (document.getElementById('am-auth-name')  || {}).value || '';
  var st    = document.getElementById('am-auth-status');
  var endpoint = amAuthMode === 'signin' ? '/auth/signin' : '/auth/signup';
  var body = amAuthMode === 'signin'
    ? { email: email, password: pass }
    : { email: email, password: pass, name: name };

  if (st) { st.textContent = 'Please wait…'; st.className = 'am-key-status spin'; }
  fetch(AM_API + endpoint, {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body),
  }).then(function(r) {
    if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail || 'Failed'); });
    return r.json();
  }).then(function(d) {
    if (st) { st.textContent = '✓ Welcome' + (d.user.name ? ', ' + d.user.name : '') + '!'; st.className = 'am-key-status ok'; }
    // Persist locally so the report header reflects it immediately
    if (typeof saveIdentityFromUser === 'function') saveIdentityFromUser(d.user);
    amApplyAuthState(d.user);
    amLoadStatus();
    if (typeof updateIdentityDisplay === 'function') updateIdentityDisplay();
  }).catch(function(e) {
    if (st) { st.textContent = '✗ ' + e.message; st.className = 'am-key-status err'; }
  });
};

window.amSignOut = function() {
  fetch(AM_API + '/auth/signout', { method: 'POST' })
    .catch(function() {})
    .then(function() {
      clearIdentity();
      amApplyAuthState(null);
      if (typeof updateIdentityDisplay === 'function') updateIdentityDisplay();
      if (typeof amUpdateEmailVia === 'function') amUpdateEmailVia(null);
    });
};

function amApplyAuthState(user) {
  var gate = document.getElementById('am-authgate');
  var signedIn = document.getElementById('am-signedin');
  var tagline = document.getElementById('am-tagline');
  if (user && user.email) {
    if (gate)     gate.style.display     = 'none';
    if (signedIn) signedIn.style.display = '';
    if (tagline)  tagline.textContent    = 'Your account';
    // Profile card
    var av = document.getElementById('am-avatar');
    if (av) {
      var initial = (user.name || user.email).charAt(0).toUpperCase();
      if (user.picture) {
        var img = document.createElement('img');
        img.src = user.picture;
        img.style.cssText = 'width:100%;height:100%;border-radius:50%;object-fit:cover';
        img.onerror = function() { av.textContent = initial; };
        av.innerHTML = ''; av.appendChild(img);
      } else { av.textContent = initial; }
    }
    var nm = document.getElementById('am-identity-name');
    if (nm) nm.textContent = user.name || user.email.split('@')[0];
    var em = document.getElementById('am-identity-email');
    if (em) em.textContent = user.email;
    // Mirror to local identity so report header + email modal stay in sync
    if (typeof saveIdentityFromUser === 'function') saveIdentityFromUser(user);
  } else {
    if (gate)     gate.style.display     = '';
    if (signedIn) signedIn.style.display = 'none';
    if (tagline)  tagline.textContent    = 'Sign in to continue';
  }
}

// ── Status update (DOM-only — no re-render) ───────────────────────────────
function amLoadStatus() {
  Promise.all([
    fetch(AM_API + '/auth/status').then(function(r) { return r.json(); }),
    fetch(AM_API + '/auth/providers').then(function(r) { return r.json(); }),
  ]).then(function(results) {
    var status    = results[0];
    var providers = results[1];

    // Toggle signed-out gate vs signed-in management view
    amApplyAuthState(status.user || null);

    // Build configured map {provider: bool}
    var configuredMap = {};
    (providers.oauth || []).forEach(function(p) { configuredMap[p.id] = p.configured; });

    amUpdateStatus(status.oauth || [], status.llm || [], status.primary || null);

    // For disconnected + unconfigured providers → show "Setup" button
    (providers.oauth || []).forEach(function(p) {
      if (!p.configured) {
        var row = document.getElementById('am-row-' + p.id);
        var btn = document.getElementById('am-btn-' + p.id);
        if (row && !row.classList.contains('connected') && btn) {
          btn.textContent = 'Setup';
          btn.className   = 'am-btn';   // secondary (not primary blue)
          btn.onclick     = (function(pid) { return function() { amShowSetup(pid); }; })(p.id);
        }
      }
    });
  }).catch(function() {
    // Backend off — buttons stay as "Connect" (can't proceed anyway)
  });
}

function amUpdateStatus(oauthList, llmList, primary) {
  // Index by provider
  var oc = {}, lc = {};
  (oauthList || []).forEach(function(c) { oc[c.provider] = c; });
  (llmList   || []).forEach(function(l) { lc[l.provider] = l; });

  // OAuth rows
  ['google','microsoft','linkedin','github','atlassian','slack'].forEach(function(p) {
    var c    = oc[p];
    var row  = document.getElementById('am-row-' + p);
    var btn  = document.getElementById('am-btn-' + p);
    var sub  = document.getElementById('am-sub-' + p);
    var tick = document.getElementById('am-tick-' + p);
    if (!row) return;
    if (c) {
      row.classList.add('connected');
      if (tick) tick.style.display = '';
      if (sub)  sub.textContent = (c.workspace ? c.workspace + ' · ' : '') + (c.name || c.email || 'Connected');
      if (btn)  { btn.textContent = 'Disconnect'; btn.className = 'am-btn am-btn-danger';
                  btn.onclick = (function(pp){ return function(){ amDisconnect(pp); }; })(p); }
    } else {
      row.classList.remove('connected');
      if (tick) tick.style.display = 'none';
      if (sub)  sub.textContent = AM_DEFAULTS[p] || p;
      if (btn)  { btn.textContent = 'Connect'; btn.className = 'am-btn am-btn-primary';
                  btn.onclick = (function(pp){ return function(){ amConnect(pp); }; })(p); }
    }
  });

  // LLM rows
  var llmLabels = {claude:'Claude', gpt:'GPT-4o', grok:'Grok', ollama:'Ollama'};
  ['claude','gpt','grok','ollama'].forEach(function(p) {
    var c    = lc[p];
    var row  = document.getElementById('am-row-' + p);
    var btn  = document.getElementById('am-btn-' + p);
    var sub  = document.getElementById('am-sub-' + p);
    var tick = document.getElementById('am-tick-' + p);
    if (!row) return;
    if (c) {
      row.classList.add('connected');
      if (tick) tick.style.display = '';
      if (sub)  sub.textContent = c.key_snippet || (c.from_env ? 'via env var' : 'connected');
      if (btn && p !== 'ollama') {
        btn.textContent = 'Remove'; btn.className = 'am-btn am-btn-danger';
        btn.onclick = (function(pp){ return function(){ amDisconnectLlm(pp); }; })(p);
      } else if (btn) { btn.textContent = '✓ Running'; btn.disabled = true; }
    } else {
      row.classList.remove('connected');
      if (tick) tick.style.display = 'none';
      if (sub)  sub.textContent = AM_DEFAULTS[p] || p;
      if (btn)  {
        btn.textContent = p === 'ollama' ? 'Check' : 'Add key';
        btn.className = 'am-btn am-btn-primary'; btn.disabled = false;
        btn.onclick = (function(pp,ll){ return function(){ amStartLlmKey(pp, ll); }; })(p, llmLabels[p]);
      }
    }
  });

  // Identity banner
  amUpdateIdentityBanner(primary || oauthList[0] || null);
  // Also refresh email modal OAuth section if open
  amUpdateEmailVia(primary || oauthList[0] || null);
}

function amUpdateIdentityBanner(primary) {
  var banner = document.getElementById('am-identity');
  if (!banner) return;
  if (!primary) { banner.style.display = 'none'; return; }
  banner.style.display = 'flex';
  var av = document.getElementById('am-avatar');
  if (av) {
    var initial = (primary.name || primary.email || '?').charAt(0).toUpperCase();
    if (primary.picture) {
      var img = document.createElement('img');
      img.src = primary.picture;
      img.style.cssText = 'width:100%;height:100%;border-radius:50%;object-fit:cover';
      img.onerror = function() { av.textContent = initial; };
      av.innerHTML = '';
      av.appendChild(img);
    } else {
      av.textContent = initial;
    }
  }
  var nm = document.getElementById('am-identity-name');
  if (nm) nm.textContent = primary.name || '';
  var em = document.getElementById('am-identity-email');
  if (em) em.textContent = primary.email || '';
  var badge = document.getElementById('am-identity-badge');
  if (badge) badge.textContent = primary.can_email ? 'Sends via ' + primary.label : 'Identity';
}

// ── OAuth connect (popup) ─────────────────────────────────────────────────
window.amConnect = function(provider) {
  // Disable the button while popup is open
  var btn = document.getElementById('am-btn-' + provider);
  if (btn) { btn.textContent = 'Connecting…'; btn.disabled = true; }

  var popup = window.open(
    AM_API + '/auth/login/' + provider,
    'qamill-oauth',
    'width=560,height=700,menubar=no,toolbar=no,location=no,status=no'
  );
  if (amPollTimer) clearInterval(amPollTimer);
  amPollTimer = setInterval(function() {
    // Stop if popup was closed manually without completing
    if (popup && popup.closed) {
      clearInterval(amPollTimer); amPollTimer = null;
      var b = document.getElementById('am-btn-' + provider);
      if (b) { b.textContent = 'Connect'; b.disabled = false; b.className = 'am-btn am-btn-primary'; }
      return;
    }
    fetch(AM_API + '/auth/status/' + provider)
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.connected) {
          clearInterval(amPollTimer); amPollTimer = null;
          if (popup && !popup.closed) popup.close();
          amLoadStatus();
          updateIdentityDisplay();
        }
      }).catch(function() {});
  }, 1200);
  setTimeout(function() {
    if (amPollTimer) { clearInterval(amPollTimer); amPollTimer = null; }
    var b = document.getElementById('am-btn-' + provider);
    if (b && b.disabled) { b.textContent = 'Connect'; b.disabled = false; b.className = 'am-btn am-btn-primary'; }
  }, 600000);
};

window.amDisconnect = function(provider) {
  fetch(AM_API + '/auth/logout/' + provider, {method:'DELETE'})
    .then(function() { amLoadStatus(); updateIdentityDisplay(); });
};

// ── LLM key entry ─────────────────────────────────────────────────────────
window.amStartLlmKey = function(provider, label) {
  amCurrentLlm = provider;
  var entry = document.getElementById('am-key-entry');
  var lbl   = document.getElementById('am-key-label');
  var inp   = document.getElementById('am-key-input');
  var stat  = document.getElementById('am-key-status');
  if (!entry) return;
  if (lbl)  lbl.textContent = 'Enter ' + label + ' API key';
  if (inp)  { inp.value = ''; inp.placeholder = provider === 'ollama' ? '(no key needed)' : 'sk-...'; }
  if (stat) { stat.textContent = ''; stat.className = 'am-key-status'; }
  entry.style.display = '';
  if (inp && provider !== 'ollama') inp.focus();
};

window.amSaveLlmKey = function() {
  var provider = amCurrentLlm;
  var key  = ((document.getElementById('am-key-input') || {}).value || '');
  var stat = document.getElementById('am-key-status');
  if (!provider) return;
  if (stat) { stat.textContent = 'Validating…'; stat.className = 'am-key-status spin'; }
  fetch(AM_API + '/auth/llm/connect', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({provider: provider, api_key: key}),
  }).then(function(r) {
    if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail || 'Validation failed'); });
    return r.json();
  }).then(function(d) {
    if (stat) { stat.textContent = '✓ ' + d.label + ' connected'; stat.className = 'am-key-status ok'; }
    setTimeout(function() { amCancelKey(); amLoadStatus(); }, 900);
  }).catch(function(e) {
    if (stat) { stat.textContent = '✗ ' + e.message; stat.className = 'am-key-status err'; }
  });
};

window.amCancelKey = function() {
  var entry = document.getElementById('am-key-entry');
  if (entry) entry.style.display = 'none';
  amCurrentLlm = null;
};

window.amDisconnectLlm = function(provider) {
  fetch(AM_API + '/auth/llm/disconnect/' + provider, {method:'DELETE'})
    .then(function() { amLoadStatus(); });
};

window.amSetType = function(type) {
  document.getElementById('login-type').value = type;
  var w = document.getElementById('am-type-work');
  var p = document.getElementById('am-type-personal');
  if (w) w.classList.toggle('active', type === 'work');
  if (p) p.classList.toggle('active', type === 'personal');
  var em = document.getElementById('login-email');
  if (em) em.placeholder = type === 'work' ? 'you@company.com' : 'you@gmail.com';
};

// ── Provider setup (enter client_id + client_secret) ─────────────────────
var AM_SETUP_INFO = {
  google:    { url:'https://console.cloud.google.com/apis/credentials',
               label:'Google Cloud Console',
               steps:['Create/select a project','Enable the <strong>Gmail API</strong> under APIs &amp; Services',
                      'Go to <strong>Credentials → Create OAuth 2.0 Client ID</strong>',
                      'Type: <strong>Web application</strong>',
                      'Add the Redirect URI shown below',
                      'Copy Client ID and Client Secret'] },
  microsoft: { url:'https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps',
               label:'Azure Portal',
               steps:['Click <strong>New registration</strong>','Platform: <strong>Web</strong>',
                      'Add the Redirect URI shown below',
                      'Copy <strong>Application (client) ID</strong>',
                      'Certificates &amp; Secrets → New client secret'] },
  github:    { url:'https://github.com/settings/developers',
               label:'GitHub Developer Settings',
               steps:['OAuth Apps → <strong>New OAuth App</strong>',
                      'Homepage URL: <code>http://localhost:8765</code>',
                      'Authorization callback URL: see below',
                      'Click Register, then <strong>Generate a new client secret</strong>'] },
  linkedin:  { url:'https://www.linkedin.com/developers/apps',
               label:'LinkedIn Developer Portal',
               steps:['Create app → <strong>Auth tab</strong>',
                      'Add the Redirect URL below to <strong>Authorized redirect URLs</strong>',
                      'Copy Client ID and Primary Client Secret'] },
  atlassian: { url:'https://developer.atlassian.com/console/myapps',
               label:'Atlassian Developer Console',
               steps:['Create app → select <strong>OAuth 2.0 (3LO)</strong>',
                      'Add the Callback URL below','Settings → copy Client ID and Secret'] },
  slack:     { url:'https://api.slack.com/apps',
               label:'Slack API Console',
               steps:['Create New App → <strong>From scratch</strong>',
                      'OAuth &amp; Permissions → add the Redirect URL below',
                      'Settings → Basic Information → copy Client ID and Client Secret'] },
};

var amCurrentSetupProvider = null;

window.amShowSetup = function(provider) {
  amCurrentSetupProvider = provider;
  var info = AM_SETUP_INFO[provider] || {};
  var redirectUri = AM_API + '/auth/callback/' + provider;

  var stepsHtml = (info.steps || []).map(function(s, i) {
    return '<li>' + s + '</li>';
  }).join('');

  var panel = document.getElementById('am-setup-panel');
  if (!panel) return;

  panel.innerHTML =
    '<div class="am-setup-header">' +
      '<div class="am-setup-title">Set up ' + provider.charAt(0).toUpperCase() + provider.slice(1) + ' OAuth</div>' +
      '<button class="am-close" onclick="amHideSetup()" style="font-size:14px">✕</button>' +
    '</div>' +
    (info.url
      ? '<a href="' + info.url + '" target="_blank" class="am-btn am-btn-primary" style="display:block;text-align:center;margin-bottom:14px">Open ' + (info.label||'Developer Console') + ' ↗</a>'
      : '') +
    '<ol class="am-setup-steps">' + stepsHtml + '</ol>' +
    '<div class="am-setup-redirect">' +
      '<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text3);margin-bottom:6px">Redirect URI (copy this exactly)</div>' +
      '<div class="am-redirect-uri" id="am-redirect-uri">' +
        '<span></span>' +
        '<button class="am-copy-btn" tabindex="-1">Copy</button>' +
      '</div>' +
    '</div>' +
    '<div class="form-group" style="margin-top:14px">' +
      '<label>Client ID</label>' +
      '<input type="text" id="am-setup-id" class="am-input" placeholder="Paste your Client ID here" autocomplete="off">' +
    '</div>' +
    '<div class="form-group">' +
      '<label>Client Secret</label>' +
      '<input type="password" id="am-setup-secret" class="am-input" placeholder="Paste your Client Secret here">' +
    '</div>' +
    '<div class="am-key-status" id="am-setup-status"></div>' +
    '<div style="display:flex;gap:8px;margin-top:12px">' +
      '<button class="am-btn" onclick="amHideSetup()">Cancel</button>' +
      '<button class="am-btn am-btn-primary" onclick="amSaveOAuthConfig()" style="flex:1">Save &amp; Enable Connect</button>' +
    '</div>';

  // Set redirect URI text + wire copy handler via JS (no inline-onclick quote issues)
  var uriRow = document.getElementById('am-redirect-uri');
  if (uriRow) {
    uriRow.querySelector('span').textContent = redirectUri;
    uriRow.onclick = function() {
      navigator.clipboard.writeText(redirectUri).then(function() {
        var btn = uriRow.querySelector('.am-copy-btn');
        if (btn) { btn.textContent = 'Copied ✓'; btn.style.color = 'var(--teal)'; }
        setTimeout(function() { if (btn) { btn.textContent = 'Copy'; btn.style.color = ''; } }, 2000);
      });
    };
  }

  panel.style.display = '';
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  var inp = document.getElementById('am-setup-id');
  if (inp) inp.focus();
};

window.amHideSetup = function() {
  var panel = document.getElementById('am-setup-panel');
  if (panel) panel.style.display = 'none';
  amCurrentSetupProvider = null;
};

window.amSaveOAuthConfig = function() {
  var provider = amCurrentSetupProvider;
  if (!provider) return;
  var clientId     = ((document.getElementById('am-setup-id')     || {}).value || '').trim();
  var clientSecret = ((document.getElementById('am-setup-secret') || {}).value || '').trim();
  var status       = document.getElementById('am-setup-status');

  if (!clientId || !clientSecret) {
    if (status) { status.textContent = 'Both Client ID and Client Secret are required.'; status.className = 'am-key-status err'; }
    return;
  }
  if (status) { status.textContent = 'Saving…'; status.className = 'am-key-status spin'; }

  fetch(AM_API + '/auth/configure/' + provider, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ client_id: clientId, client_secret: clientSecret }),
  }).then(function(r) {
    if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail || 'Save failed'); });
    return r.json();
  }).then(function(d) {
    if (status) { status.textContent = '✓ Saved — click Connect to sign in'; status.className = 'am-key-status ok'; }
    // Upgrade the button from Setup → Connect
    var btn = document.getElementById('am-btn-' + provider);
    if (btn) {
      btn.textContent = 'Connect';
      btn.className   = 'am-btn am-btn-primary';
      btn.disabled    = false;
      btn.onclick     = function() { amHideSetup(); amConnect(provider); };
    }
    setTimeout(function() {
      amHideSetup();
      amConnect(provider);  // immediately start the OAuth flow
    }, 1000);
  }).catch(function(e) {
    if (status) { status.textContent = '✗ ' + e.message; status.className = 'am-key-status err'; }
  });
};

// ── Open/close — show immediately (providers already rendered in HTML)
window.openLoginModal = function() {
  var m = document.getElementById('login-modal');
  if (!m) return;
  m.style.display = 'flex';
  m.style.animation = 'amFadeIn .2s ease';
  amLoadStatus();
};
window.closeLoginModal = function() {
  var m = document.getElementById('login-modal');
  if (m) { m.style.display = 'none'; m.style.animation = ''; }
  if (amPollTimer) { clearInterval(amPollTimer); amPollTimer = null; }
};
window.openAuthModal  = window.openLoginModal;
window.closeAuthModal = window.closeLoginModal;

// ── Identity / Login ──────────────────────────────────────────────────────
var IDENTITY_KEY = 'qamill-identity';

function getIdentity() {
  try { return JSON.parse(localStorage.getItem(IDENTITY_KEY) || 'null'); }
  catch (e) { return null; }
}

// Persist the signed-in user to local identity (drives the report header chip)
function saveIdentityFromUser(user) {
  if (!user || !user.email) return;
  try {
    localStorage.setItem(IDENTITY_KEY, JSON.stringify({
      email: user.email, name: user.name || '', picture: user.picture || '',
      provider: (user.providers && user.providers[0]) || user.auth_type || '',
      can_email: !!user.can_email, type: 'work',
    }));
  } catch (e) {}
}

window.toggleIdMenu = function(e) {
  var chip = document.getElementById('id-chip');
  if (!chip) return;
  chip.classList.toggle('open');
  e.stopPropagation();
};
// Close dropdown when clicking anywhere outside
document.addEventListener('click', function() {
  var chip = document.getElementById('id-chip');
  if (chip) chip.classList.remove('open');
});

window.signOut = function() {
  // Close dropdown
  var chip = document.getElementById('id-chip');
  if (chip) chip.classList.remove('open');

  // 1. End the QAMill session (clears server-side session token)
  fetch(AM_API + '/auth/signout', { method: 'POST' })
    .catch(function() { /* best-effort — clear local state regardless */ });

  // 2. Clear local identity state
  clearIdentity();
  updateIdentityDisplay();

  // 3. Reflect signed-out state in the auth modal + email modal
  if (typeof amApplyAuthState === 'function') amApplyAuthState(null);
  amUpdateEmailVia(null);
};

function updateIdentityDisplay() {
  var id  = getIdentity();
  var btn = document.getElementById('login-btn');
  var chip = document.getElementById('id-chip');

  if (id && id.email) {
    // Show chip, hide plain Login button
    if (chip) chip.style.display = 'inline-flex';
    if (btn)  btn.style.display  = 'none';

    // Avatar
    var av = document.getElementById('id-avatar');
    if (av) {
      if (id.picture) {
        var img = document.createElement('img');
        img.src = id.picture;
        img.onerror = function() { av.textContent = id.email.charAt(0).toUpperCase(); };
        av.innerHTML = ''; av.appendChild(img);
      } else {
        av.textContent = id.email.charAt(0).toUpperCase();
      }
    }
    // Email in chip
    var em = document.getElementById('id-email');
    if (em) em.textContent = id.name || id.email;

    // Dropdown details
    var mn = document.getElementById('id-menu-name');
    if (mn) mn.textContent = id.name || '';
    var me = document.getElementById('id-menu-email');
    if (me) me.textContent = id.email;
    var mp = document.getElementById('id-menu-provider');
    if (mp) {
      var label = id.label || id.provider || '';
      mp.textContent = label ? 'via ' + label : 'Connected';
      mp.style.display = label ? '' : 'none';
    }
  } else {
    // Signed out — show Login button, hide chip
    if (chip) { chip.style.display = 'none'; chip.classList.remove('open'); }
    if (btn)  { btn.style.display  = ''; btn.textContent = 'Log in'; }
  }

  var bar = document.getElementById('sender-as-bar');

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

// ── Email via-OAuth state sync ─────────────────────────────────────────────
var AM_VIA_ICONS = {
  google:    '<svg viewBox="0 0 24 24" width="22" height="22"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>',
  microsoft: '<svg viewBox="0 0 21 21" width="22" height="22"><rect x="1" y="1" width="9" height="9" fill="#f25022"/><rect x="11" y="1" width="9" height="9" fill="#7fba00"/><rect x="1" y="11" width="9" height="9" fill="#00a4ef"/><rect x="11" y="11" width="9" height="9" fill="#ffb900"/></svg>',
};

function amUpdateEmailVia(primary) {
  var viaBox  = document.getElementById('email-via-box');
  var noAcct  = document.getElementById('email-no-account-area');
  if (!viaBox || !noAcct) return;

  if (primary && primary.can_email) {
    viaBox.style.display  = '';
    noAcct.style.display  = 'none';
    var icon  = document.getElementById('email-via-icon');
    var label = document.getElementById('email-via-label');
    var addr  = document.getElementById('email-via-addr');
    if (icon)  icon.innerHTML  = AM_VIA_ICONS[primary.provider] || '';
    if (label) label.textContent = 'Sending via ' + (primary.label || primary.provider);
    if (addr)  addr.textContent  = primary.email || '';
  } else {
    viaBox.style.display  = 'none';
    noAcct.style.display  = '';
    // Fall back: pre-fill sender from local identity
    var id = getIdentity();
    if (id && id.email) {
      var fromField = document.getElementById('email-from');
      if (fromField && !fromField.value) fromField.value = id.email;
      if (id.password) {
        var passField = document.getElementById('email-pass');
        if (passField && !passField.value) passField.value = id.password;
      }
    }
  }
}

// ── Email modal ────────────────────────────────────────────────────────────
window.openEmailModal = function() {
  var modal = document.getElementById('email-modal');
  if (!modal) return;
  modal.classList.add('open');

  // Pre-fill subject/body
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

  // Check OAuth status → show OAuth path or SMTP form
  fetch(AM_API + '/auth/status')
    .then(function(r) { return r.json(); })
    .then(function(d) { amUpdateEmailVia(d.primary || null); })
    .catch(function()  { amUpdateEmailVia(null); }); // backend off → show SMTP form
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
    logo_html = _logo_img("34px")
    return f"""
<header class="qm-header">
  <div class="qm-logo">{logo_html}<span class="qm-logo-text" style="margin-left:8px;font-size:18px;font-weight:700;color:var(--teal)">QAMill</span></div>
  <div class="qm-file" title="{_html_esc(file_name)}">{_html_esc(file_name)}</div>
  <div class="qm-header-right">
    <!-- Identity chip — shown when signed in -->
    <div class="id-chip" id="id-chip" style="display:none" onclick="toggleIdMenu(event)">
      <div class="id-avatar" id="id-avatar"></div>
      <span class="id-email" id="id-email"></span>
      <span class="id-caret">▾</span>
      <!-- Dropdown -->
      <div class="id-menu" id="id-menu">
        <div class="id-menu-user">
          <div class="id-menu-name" id="id-menu-name"></div>
          <div class="id-menu-email" id="id-menu-email"></div>
          <div class="id-menu-provider" id="id-menu-provider"></div>
        </div>
        <div class="id-menu-divider"></div>
        <button class="id-menu-item" onclick="event.stopPropagation();openLoginModal()">Manage accounts</button>
        <button class="id-menu-item id-menu-signout" onclick="event.stopPropagation();signOut()">Sign out</button>
      </div>
    </div>
    <!-- Log in button — shown when signed out -->
    <button class="btn btn-login" id="login-btn" onclick="openLoginModal()">Log in</button>
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


def _am_oauth_row(pid: str, label: str, subtitle: str, bg: str,
                  icon: str, can_email: bool = False) -> str:
    """Static OAuth provider row — JS updates connect/disconnect state by ID."""
    email_cap = '<span class="am-email-cap">Sends email</span>' if can_email else ''
    return (
        f'<div class="am-provider-row" id="am-row-{pid}" data-provider="{pid}">'
        f'<div class="am-provider-icon" style="background:{bg}">{icon}</div>'
        f'<div class="am-provider-info">'
        f'<div class="am-provider-name">{label}{email_cap}</div>'
        f'<div class="am-provider-sub" id="am-sub-{pid}">{subtitle}</div>'
        f'</div>'
        f'<span class="am-connected-tick" id="am-tick-{pid}" style="display:none">✓</span>'
        f'<button class="am-btn am-btn-primary" id="am-btn-{pid}" '
        f'onclick="amConnect(\'{pid}\')" style="flex-shrink:0">Connect</button>'
        f'</div>'
    )


def _am_llm_row(pid: str, label: str, subtitle: str, bg: str, icon: str) -> str:
    """Static LLM provider row."""
    is_ollama = pid == "ollama"
    btn_text  = "Check" if is_ollama else "Add key"
    return (
        f'<div class="am-provider-row" id="am-row-{pid}" data-provider="{pid}">'
        f'<div class="am-provider-icon" style="background:{bg}">{icon}</div>'
        f'<div class="am-provider-info">'
        f'<div class="am-provider-name">{label}</div>'
        f'<div class="am-provider-sub" id="am-sub-{pid}">{subtitle}</div>'
        f'</div>'
        f'<span class="am-connected-tick" id="am-tick-{pid}" style="display:none">✓</span>'
        f'<button class="am-btn am-btn-primary" id="am-btn-{pid}" '
        f'onclick="amStartLlmKey(\'{pid}\',\'{label}\')" '
        f'style="flex-shrink:0">{btn_text}</button>'
        f'</div>'
    )


# Pre-built SVG icons (defined once, reused in Python HTML generation)
_G = '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>'
_MS= '<svg viewBox="0 0 21 21" width="20" height="20"><rect x="1" y="1" width="9" height="9" fill="#f25022"/><rect x="11" y="1" width="9" height="9" fill="#7fba00"/><rect x="1" y="11" width="9" height="9" fill="#00a4ef"/><rect x="11" y="11" width="9" height="9" fill="#ffb900"/></svg>'
_LI= '<svg viewBox="0 0 24 24" width="20" height="20" fill="#fff"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'
_GH= '<svg viewBox="0 0 24 24" width="20" height="20" fill="#fff"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>'
_AT= '<svg viewBox="0 0 24 24" width="20" height="20"><path d="M.195 11.408L8.31 22.857c.504.744 1.629.744 2.133 0l8.117-11.449c.538-.75.03-1.797-.878-1.797H14.22c-.373 0-.726.172-.958.46L12 11.658l-1.262-1.587a1.21 1.21 0 0 0-.958-.46H6.073c-.909 0-1.417 1.047-.878 1.797zm11.55-9.265L9.72 5.867c.504.744 1.629.744 2.133 0l2.027-2.724a1.21 1.21 0 0 0 0-1.427L11.852.992a1.21 1.21 0 0 0-2.133 0L7.692 3.716a1.21 1.21 0 0 0 0 1.427l2.027 2.724c.504.744 1.629.744 2.133 0l2.027-2.724z" fill="#fff"/></svg>'
_SL= '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#E01E5A" d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z"/><path fill="#36C5F0" d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z"/><path fill="#2EB67D" d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 0 1-2.522 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.164 0a2.528 2.528 0 0 1 2.522 2.522v6.312z"/><path fill="#ECB22E" d="M15.164 18.956a2.528 2.528 0 0 1 2.522 2.522A2.528 2.528 0 0 1 15.164 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zm0-1.27a2.527 2.527 0 0 1-2.52-2.522 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.164a2.528 2.528 0 0 1-2.523 2.522h-6.313z"/></svg>'


def _build_login_modal() -> str:
    """Elite multi-provider authentication popup — providers rendered statically."""
    social_rows = (
        _am_oauth_row("google",    "Google",    "Send reports via Gmail — no App Password needed", "#fff",    _G,  can_email=True) +
        _am_oauth_row("microsoft", "Microsoft", "Send reports via Outlook — no App Password needed","#2f2f2f",_MS, can_email=True) +
        _am_oauth_row("linkedin",  "LinkedIn",  "Professional identity for sender name",            "#0A66C2", _LI)
    )
    dev_rows = (
        _am_oauth_row("github",    "GitHub",    "Developer identity + work email",          "#24292e", _GH) +
        _am_oauth_row("atlassian", "Atlassian", "Jira / Confluence workspace identity",     "#0052CC", _AT) +
        _am_oauth_row("slack",     "Slack",     "Slack workspace identity",                 "#4A154B", _SL)
    )
    llm_rows = (
        _am_llm_row("claude", "Claude",  "Anthropic",             "#2d1f0e", '<span style="font-size:17px;font-weight:800;color:#D4A574">✦</span>') +
        _am_llm_row("gpt",    "GPT-4o",  "OpenAI",                "#0a2a20", '<span style="font-size:15px;font-weight:800;color:#10A37F">⬡</span>') +
        _am_llm_row("grok",   "Grok",    "xAI",                   "#0a1a2a", '<span style="font-size:14px;font-weight:900;color:#1DA1F2">𝕏</span>') +
        _am_llm_row("ollama", "Ollama",  "Local — no key needed", "#1a0a2a", '<span style="font-size:15px;color:#9B59B6">⚙</span>')
    )

    return f"""
<div class="am-overlay" id="login-modal" onclick="if(event.target===this)closeLoginModal()">
<div class="am-card">

  <div class="am-header">
    <div class="am-header-left">
      <span class="am-logo">QAMill</span>
      <span class="am-tagline" id="am-tagline">Sign in to continue</span>
    </div>
    <button class="am-close" onclick="closeLoginModal()">✕</button>
  </div>

  <!-- ════════ SIGNED-OUT: Auth gate ════════ -->
  <div id="am-authgate">
    <!-- Sign in / Sign up segmented control -->
    <div class="am-seg">
      <button class="am-seg-btn active" id="am-seg-signin" onclick="amSetAuthMode('signin')">Sign in</button>
      <button class="am-seg-btn"        id="am-seg-signup" onclick="amSetAuthMode('signup')">Sign up</button>
    </div>

    <!-- Social sign-in (each also creates a QAMill account) -->
    <div class="am-social-grid">
      <button class="am-social-btn" onclick="amConnect('google')">
        <span class="am-social-ic" style="background:#fff">{_G}</span>Continue with Google</button>
      <button class="am-social-btn" onclick="amConnect('microsoft')">
        <span class="am-social-ic" style="background:#2f2f2f">{_MS}</span>Continue with Microsoft</button>
      <button class="am-social-btn" onclick="amConnect('atlassian')">
        <span class="am-social-ic" style="background:#0052CC">{_AT}</span>Continue with Atlassian (Jira)</button>
      <button class="am-social-btn" onclick="amConnect('github')">
        <span class="am-social-ic" style="background:#24292e">{_GH}</span>Continue with GitHub</button>
    </div>

    <div class="am-or"><span>or</span></div>

    <!-- Email + password form -->
    <div class="am-form">
      <div class="form-group" id="am-name-group" style="display:none">
        <label>Name</label>
        <input type="text" id="am-auth-name" class="am-input" placeholder="Your name" autocomplete="name">
      </div>
      <div class="form-group">
        <label>Email</label>
        <input type="email" id="am-auth-email" class="am-input" placeholder="you@company.com" autocomplete="email"
               onkeydown="if(event.key==='Enter')document.getElementById('am-auth-pass').focus()">
      </div>
      <div class="form-group">
        <label>Password</label>
        <input type="password" id="am-auth-pass" class="am-input" placeholder="At least 8 characters"
               autocomplete="current-password" onkeydown="if(event.key==='Enter')amSubmitAuth()">
      </div>
      <div class="am-key-status" id="am-auth-status"></div>
      <button class="am-btn am-btn-primary" id="am-auth-submit" onclick="amSubmitAuth()"
              style="width:100%;justify-content:center;padding:10px">Sign in</button>
    </div>
    <div class="am-footer" style="border:none;text-align:center;padding-top:14px">
      Your password is hashed and stored only on this machine.
    </div>
  </div>

  <!-- ════════ SIGNED-IN: profile + connection management ════════ -->
  <div id="am-signedin" style="display:none">
    <!-- Profile card -->
    <div class="am-profile">
      <div class="am-avatar" id="am-avatar">?</div>
      <div class="am-identity-text">
        <div class="am-identity-name"  id="am-identity-name"></div>
        <div class="am-identity-email" id="am-identity-email"></div>
      </div>
      <button class="am-btn am-btn-danger" onclick="amSignOut()" style="flex-shrink:0">Sign out</button>
    </div>

    <!-- Setup panel — populated by amShowSetup(), hidden by default -->
    <div class="am-setup-panel" id="am-setup-panel" style="display:none"></div>

    <div class="am-tabs">
      <button class="am-tab active" data-tab="social"    onclick="amTab('social')">Connections</button>
      <button class="am-tab"        data-tab="developer" onclick="amTab('developer')">Developer</button>
      <button class="am-tab"        data-tab="llm"       onclick="amTab('llm')">LLM Keys</button>
      <button class="am-tab"        data-tab="email"     onclick="amTab('email')">Email</button>
    </div>

    <!-- Social tab — Google / Microsoft / LinkedIn -->
    <div class="am-pane" id="am-pane-social">
      <p class="am-hint">Connect Google or Microsoft to send reports without an App Password.</p>
      {social_rows}
    </div>

  <!-- Developer tab — GitHub / Atlassian / Slack -->
  <div class="am-pane" id="am-pane-developer" style="display:none">
    <p class="am-hint">Connect GitHub, Atlassian or Slack to use your work identity as sender.</p>
    {dev_rows}
  </div>

  <!-- LLM Keys tab -->
  <div class="am-pane" id="am-pane-llm" style="display:none">
    <p class="am-hint">API keys are validated then stored locally. Never sent to QAMill servers.</p>
    {llm_rows}
    <div class="am-key-entry" id="am-key-entry" style="display:none">
      <div class="am-key-label" id="am-key-label">Enter API Key</div>
      <div style="display:flex;gap:8px;margin-top:8px">
        <input type="password" id="am-key-input" class="am-input" placeholder="sk-..."
               onkeydown="if(event.key==='Enter')amSaveLlmKey()" style="flex:1">
        <button class="am-btn am-btn-primary" onclick="amSaveLlmKey()">Validate</button>
        <button class="am-btn" onclick="amCancelKey()">✕</button>
      </div>
      <div class="am-key-status" id="am-key-status"></div>
    </div>
  </div>

  <!-- Email tab — manual SMTP fallback -->
  <div class="am-pane" id="am-pane-email" style="display:none">
    <p class="am-hint">Use this only if you prefer not to connect an account above.</p>
    <div class="am-type-row">
      <button class="am-type-btn active" id="am-type-work"     onclick="amSetType('work')">💼 Work</button>
      <button class="am-type-btn"        id="am-type-personal" onclick="amSetType('personal')">🏠 Personal</button>
    </div>
    <input type="hidden" id="login-type" value="work">
    <input type="email"    class="am-input" id="login-email"    placeholder="you@company.com" style="margin-bottom:8px">
    <input type="password" class="am-input" id="login-password" placeholder="App password (optional)">
    <div class="am-hint" style="margin-top:8px">
      <a href="https://myaccount.google.com/apppasswords" target="_blank">Gmail App Password →</a>
      &nbsp;·&nbsp;
      <a href="https://account.live.com/proofs/AppPassword" target="_blank">Outlook App Password →</a>
    </div>
    <div class="login-error" id="login-error"></div>
    <div style="display:flex;gap:8px;margin-top:14px">
      <button class="am-btn am-btn-danger" onclick="clearIdentity();closeLoginModal()">Clear</button>
      <button class="am-btn am-btn-primary" onclick="saveLogin()" style="margin-left:auto">Save</button>
    </div>
  </div>

  <div class="am-footer">
    Tokens stored in <code>~/.qamill/auth.json</code> — never transmitted to QAMill.
  </div>
  </div><!-- /am-signedin -->
</div>
</div>"""


def build_login_page() -> str:
    """
    Standalone browser login/sign-up page served at GET /login.
    Self-contained: reuses the elite `am-*` styles + a focused auth script.
    """
    return f"""<!DOCTYPE html><html data-theme="dark" lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in · QAMill</title>
{_favicon_tag()}
<style>
{_CSS}
/* Standalone page: center the card, no overlay dimming */
body{{background:radial-gradient(ellipse at top,#10202a 0%,var(--bg) 60%);
  min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
.lp-card{{width:440px;max-width:100%;background:var(--surface);
  border:1px solid var(--border);border-radius:16px;
  box-shadow:0 32px 80px rgba(0,0,0,.5);overflow:hidden}}
.lp-brand{{display:flex;align-items:center;gap:10px;padding:22px 24px 4px}}
.lp-brand img{{height:34px}}
.lp-brand .nm{{font-size:20px;font-weight:800;color:var(--teal)}}
.lp-sub{{padding:0 24px;font-size:13px;color:var(--text2);margin-bottom:6px}}
</style></head>
<body>
<div class="lp-card">
  <div class="lp-brand">{_logo_img("34px")}<span class="nm">QAMill</span></div>
  <div class="lp-sub" id="lp-sub">Sign in to send reports and manage your account.</div>

  <!-- ════ SIGNED OUT: gate ════ -->
  <div id="am-authgate" style="padding:16px 24px 8px">
    <div class="am-seg">
      <button class="am-seg-btn active" id="am-seg-signin" onclick="amSetAuthMode('signin')">Sign in</button>
      <button class="am-seg-btn"        id="am-seg-signup" onclick="amSetAuthMode('signup')">Sign up</button>
    </div>
    <div class="am-social-grid">
      <button class="am-social-btn" onclick="amConnect('google')">
        <span class="am-social-ic" style="background:#fff">{_G}</span>Continue with Google</button>
      <button class="am-social-btn" onclick="amConnect('microsoft')">
        <span class="am-social-ic" style="background:#2f2f2f">{_MS}</span>Continue with Microsoft</button>
      <button class="am-social-btn" onclick="amConnect('atlassian')">
        <span class="am-social-ic" style="background:#0052CC">{_AT}</span>Continue with Atlassian (Jira)</button>
      <button class="am-social-btn" onclick="amConnect('github')">
        <span class="am-social-ic" style="background:#24292e">{_GH}</span>Continue with GitHub</button>
    </div>
    <div class="am-or"><span>or</span></div>
    <div class="am-form">
      <div class="form-group" id="am-name-group" style="display:none">
        <label>Name</label>
        <input type="text" id="am-auth-name" class="am-input" placeholder="Your name" autocomplete="name">
      </div>
      <div class="form-group">
        <label>Email</label>
        <input type="email" id="am-auth-email" class="am-input" placeholder="you@company.com" autocomplete="email"
               onkeydown="if(event.key==='Enter')document.getElementById('am-auth-pass').focus()">
      </div>
      <div class="form-group">
        <label>Password</label>
        <input type="password" id="am-auth-pass" class="am-input" placeholder="At least 8 characters"
               autocomplete="current-password" onkeydown="if(event.key==='Enter')amSubmitAuth()">
      </div>
      <div class="am-key-status" id="am-auth-status"></div>
      <button class="am-btn am-btn-primary" id="am-auth-submit" onclick="amSubmitAuth()"
              style="width:100%;justify-content:center;padding:11px">Sign in</button>
    </div>
    <div class="am-footer" style="border:none;text-align:center;padding:14px 0 18px">
      Your password is hashed and stored only on this machine.
    </div>
  </div>

  <!-- ════ SIGNED IN: profile ════ -->
  <div id="am-signedin" style="display:none;padding:8px 24px 22px">
    <div class="am-profile" style="margin:8px 0 0">
      <div class="am-avatar" id="am-avatar">?</div>
      <div class="am-identity-text">
        <div class="am-identity-name"  id="am-identity-name"></div>
        <div class="am-identity-email" id="am-identity-email"></div>
      </div>
      <button class="am-btn am-btn-danger" onclick="amSignOut()" style="flex-shrink:0">Sign out</button>
    </div>
    <div id="lp-providers" style="margin-top:14px"></div>
    <div class="am-footer" style="border:none;text-align:center;padding-top:16px">
      You can close this tab — your session is saved.
    </div>
  </div>
</div>

<script>
var AM_API = '';   // same origin (served by the backend)
var amAuthMode = 'signin';

window.amSetAuthMode = function(mode) {{
  amAuthMode = mode;
  var inSign = mode === 'signin';
  document.getElementById('am-seg-signin').classList.toggle('active', inSign);
  document.getElementById('am-seg-signup').classList.toggle('active', !inSign);
  document.getElementById('am-name-group').style.display = inSign ? 'none' : '';
  document.getElementById('am-auth-submit').textContent = inSign ? 'Sign in' : 'Create account';
  var st = document.getElementById('am-auth-status');
  st.textContent = ''; st.className = 'am-key-status';
}};

window.amSubmitAuth = function() {{
  var email = document.getElementById('am-auth-email').value || '';
  var pass  = document.getElementById('am-auth-pass').value || '';
  var name  = (document.getElementById('am-auth-name')||{{}}).value || '';
  var st = document.getElementById('am-auth-status');
  var ep = amAuthMode === 'signin' ? '/auth/signin' : '/auth/signup';
  var body = amAuthMode === 'signin' ? {{email:email,password:pass}} : {{email:email,password:pass,name:name}};
  st.textContent = 'Please wait…'; st.className = 'am-key-status spin';
  fetch(ep, {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}})
    .then(function(r){{ if(!r.ok) return r.json().then(function(e){{throw new Error(e.detail||'Failed');}}); return r.json(); }})
    .then(function(d){{ st.textContent='✓ Welcome'+(d.user.name?', '+d.user.name:'')+'!'; st.className='am-key-status ok'; applyState(d.user); }})
    .catch(function(e){{ st.textContent='✗ '+e.message; st.className='am-key-status err'; }});
}};

var amPoll=null;
window.amConnect = function(provider) {{
  var w = window.open('/auth/login/'+provider, 'qamill-oauth', 'width=560,height=720');
  if (amPoll) clearInterval(amPoll);
  amPoll = setInterval(function(){{
    if (w && w.closed) {{ clearInterval(amPoll); amPoll=null; }}
    fetch('/auth/me').then(function(r){{return r.json();}}).then(function(d){{
      if (d.user) {{ clearInterval(amPoll); amPoll=null; if(w&&!w.closed)w.close(); applyState(d.user); }}
    }}).catch(function(){{}});
  }}, 1200);
  setTimeout(function(){{ if(amPoll){{clearInterval(amPoll);amPoll=null;}} }}, 600000);
}};

window.amSignOut = function() {{
  fetch('/auth/signout',{{method:'POST'}}).catch(function(){{}}).then(function(){{ applyState(null); }});
}};

function applyState(user) {{
  var gate = document.getElementById('am-authgate');
  var si   = document.getElementById('am-signedin');
  var sub  = document.getElementById('lp-sub');
  if (user && user.email) {{
    gate.style.display='none'; si.style.display='';
    sub.textContent = 'You are signed in.';
    var initial = (user.name||user.email).charAt(0).toUpperCase();
    var av = document.getElementById('am-avatar');
    if (user.picture) {{
      var img=document.createElement('img'); img.src=user.picture;
      img.style.cssText='width:100%;height:100%;border-radius:50%;object-fit:cover';
      img.onerror=function(){{av.textContent=initial;}}; av.innerHTML=''; av.appendChild(img);
    }} else av.textContent=initial;
    document.getElementById('am-identity-name').textContent = user.name||user.email.split('@')[0];
    document.getElementById('am-identity-email').textContent = user.email;
    var prov = (user.providers||[]).map(function(p){{return p.charAt(0).toUpperCase()+p.slice(1);}});
    document.getElementById('lp-providers').innerHTML = prov.length
      ? '<div class="am-hint">Connected: '+prov.join(', ')+'</div>' : '';
  }} else {{
    gate.style.display=''; si.style.display='none';
    sub.textContent = 'Sign in to send reports and manage your account.';
  }}
}}

// Load current session on open
fetch('/auth/me').then(function(r){{return r.json();}}).then(function(d){{applyState(d.user);}}).catch(function(){{}});
</script>
</body></html>"""


def _build_email_modal(file_name: str) -> str:
    return """
<div class="modal-overlay" id="email-modal">
  <div class="modal">
    <div class="modal-header">
      <h3>✉ Email Report</h3>
      <button class="modal-close" onclick="closeEmailModal()">✕</button>
    </div>
    <div class="modal-body">

      <!-- ① OAuth path — shown when Google/Microsoft connected -->
      <div class="email-via-box" id="email-via-box" style="display:none">
        <div class="email-via-icon" id="email-via-icon"></div>
        <div class="email-via-details">
          <div class="email-via-label" id="email-via-label">Sending via Google</div>
          <div class="email-via-addr"  id="email-via-addr">user@gmail.com</div>
        </div>
        <button class="am-btn" onclick="closeEmailModal();openLoginModal()"
                style="margin-left:auto;font-size:11px">Change</button>
      </div>

      <!-- ② No account — CTA + SMTP fallback -->
      <div id="email-no-account-area">
        <div class="email-no-account-box">
          <p>Connect Google or Microsoft for one-click sending — no App Password needed</p>
          <button class="am-btn am-btn-primary"
                  onclick="closeEmailModal();openLoginModal()">Connect account</button>
        </div>
        <div class="email-or-divider">or send via SMTP</div>
        <div class="form-group">
          <label>Your Email (Sender)</label>
          <input type="email" id="email-from" placeholder="you@gmail.com">
        </div>
        <div class="form-group">
          <label>Provider</label>
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
          <label>App Password</label>
          <input type="password" id="email-pass" placeholder="xxxx xxxx xxxx xxxx">
          <div class="hint">
            Use an App Password, not your regular password.<br>
            <a href="https://myaccount.google.com/apppasswords" target="_blank">Gmail App Password →</a>
          </div>
        </div>
      </div>

      <!-- Always visible: recipient + subject + message -->
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
        <textarea id="email-body" style="height:70px"></textarea>
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
{_favicon_tag()}
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
