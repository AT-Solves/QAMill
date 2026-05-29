"""
main.py
FastAPI backend — runs locally on port 8765.
Streams real-time mutation results via Server-Sent Events.
VS Code extension and browser dashboard both connect to this.
"""
import asyncio
import json
import smtplib
import uuid
from collections import Counter
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mutation_engine import MutationEngine, OPERATOR_METADATA
from equivalent_detector import EquivalentDetector
from test_runner import TestRunner, mutation_hint, mutation_priority, MAX_WORKERS
from llm_adapter import create_adapter, NoLLMAdapter
from cross_method_mutator import CrossMethodMutator
from ai_mutant_generator import AIMutantGenerator

app = FastAPI(title="AMIL Mutation Testing Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Job state ──────────────────────────────────────────────────────────────
# _job_events  : full ordered history of every event (for replay on reconnect)
# _job_subs    : per-connection subscriber queues (fan-out to concurrent readers)
# _job_done    : set of completed/errored job IDs
_job_events: dict[str, list] = {}
_job_subs:   dict[str, list[asyncio.Queue]] = {}
_job_done:   set[str] = set()
_job_summaries: dict[str, dict] = {}

# ── Legacy alias so any code that still references _jobs doesn't crash ──────
_jobs: dict[str, None] = {}  # kept for API compatibility, no longer holds queues


# ── Request / Response models ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    file_path: str
    project_root: str
    llm_provider: str = "none"      # "claude" | "gpt" | "grok" | "inhouse" | "none"
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    test_command: Optional[str] = None
    auto_heal: bool = True
    detect_equivalents: bool = True
    ai_mutants: bool = False
    enabled_operators: List[str] = ["all"]


class JobResponse(BaseModel):
    job_id: str
    stream_url: str


class AskRequest(BaseModel):
    prompt: str
    context: str
    llm_provider: str = "none"
    llm_api_key: Optional[str] = None


class EmailRequest(BaseModel):
    job_id: str
    to_address: str
    sender_email: Optional[str] = None   # display From address (defaults to smtp_user)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    use_tls: bool = True                 # True = STARTTLS (port 587); False = SMTP_SSL (port 465)


class EmailTestRequest(BaseModel):
    """Verify SMTP credentials by sending a test email — no job_id needed."""
    to_address: str
    sender_email: Optional[str] = None
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    use_tls: bool = True


class EmailHtmlRequest(BaseModel):
    """Send an HTML body directly — no job_id lookup needed."""
    html: str
    subject: str
    to_address: str
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    use_tls: bool = True


# ── Helpers ────────────────────────────────────────────────────────────────

async def _broadcast(job_id: str, event: dict) -> None:
    """Append event to history and fan-out to all active subscriber queues."""
    _job_events.setdefault(job_id, []).append(event)
    for q in list(_job_subs.get(job_id, [])):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # slow subscriber — skip; they'll get it via replay on reconnect
    if event.get("type") in ("complete", "error"):
        _job_done.add(job_id)


# ── Core analysis pipeline ─────────────────────────────────────────────────

async def _run_analysis(job_id: str, req: AnalyzeRequest):
    runner: TestRunner | None = None
    try:
        kwargs: dict = {}
        if req.llm_api_key:
            kwargs["api_key"] = req.llm_api_key
        if req.llm_model:
            kwargs["model"] = req.llm_model

        llm      = create_adapter(req.llm_provider, **kwargs)
        detector = EquivalentDetector(llm_adapter=llm if req.detect_equivalents else None)
        runner   = TestRunner(req.project_root, req.test_command)
        enable_ops  = req.enabled_operators if req.enabled_operators != ["all"] else "all"
        engine      = MutationEngine(enable=enable_ops)
        cm_engine   = CrossMethodMutator()
        ai_engine   = AIMutantGenerator()

        # ── Baseline ──────────────────────────────────────────────────────────
        await _broadcast(job_id, {"type": "status", "message": "Running baseline tests..."})
        if not await runner.run_baseline():
            await _broadcast(job_id, {
                "type": "error",
                "message": "Baseline tests FAILED. Fix your tests before running QAMill.",
            })
            return

        # ── Generate mutants ───────────────────────────────────────────────────
        await _broadcast(job_id, {"type": "status", "message": "Generating mutants..."})
        ast_mutants = engine.generate_mutants(req.file_path)
        cm_mutants  = cm_engine.generate_mutants(req.file_path)
        ast_count   = len(ast_mutants) + len(cm_mutants)

        ai_count: int = 0
        ai_generated: list = []
        if req.ai_mutants and not isinstance(llm, NoLLMAdapter):
            await _broadcast(job_id, {"type": "status", "message": "Generating AI semantic mutants..."})
            ai_generated = await ai_engine.generate(req.file_path, llm)
            ai_count = len(ai_generated)

        mutants           = ast_mutants + cm_mutants + ai_generated
        total             = len(mutants)
        cross_method_count = len(cm_mutants)
        operator_counts   = dict(Counter(m.operator for m in mutants))

        await _broadcast(job_id, {
            "type": "start",
            "total": total,
            "file": Path(req.file_path).name,
            "llm_provider": llm.name,
            "ast_mutant_count": ast_count,
            "ai_mutant_count": ai_count,
            "cross_method_count": cross_method_count,
            "operator_counts": operator_counts,
        })

        if total == 0:
            await _broadcast(job_id, {"type": "complete",
                                      "message": "No mutants generated. Add more logic to your code."})
            return

        # ── Worker pool ────────────────────────────────────────────────────────
        await runner.setup_pool(MAX_WORKERS)

        # ── Parallel mutant processing ─────────────────────────────────────────
        # asyncio cooperative scheduling makes plain int counters safe here:
        # no await between a counter read and its write.
        processed = 0
        killed = survived = equivalent = errors = 0

        async def process_one(mutant: "Mutant") -> None:  # type: ignore[name-defined]
            nonlocal processed, killed, survived, equivalent, errors

            # Step A: equivalence check (fast heuristic or LLM)
            equiv = await detector.classify(mutant.original_src, mutant.mutant_src)
            if equiv.equivalent:
                mutant.status = "equivalent"
                mutant.equivalent_reason = equiv.reason
                equivalent += 1
                processed  += 1
                await _broadcast(job_id, {
                    "type": "mutant_result",
                    "index": processed, "total": total,
                    "mutant_id": mutant.id,
                    "function": mutant.function_name,
                    "line": mutant.line_no,
                    "operator": mutant.operator,
                    "description": mutant.description,
                    "status": "equivalent",
                    "reason": equiv.reason,
                    "method": equiv.method,
                    "killed": killed, "survived": survived,
                    "equivalent": equivalent, "errors": errors,
                    "true_score": _score(killed, survived),
                    "raw_score": _raw_score(killed, survived, equivalent),
                })
                return

            # Step B: run tests against the mutant (uses worker pool slot)
            status, killer_info = await runner.run_mutant(mutant)
            mutant.status = status

            if status == "killed":
                killed  += 1
            elif status == "survived":
                survived += 1
            else:
                errors   += 1

            processed += 1

            hint     = mutation_hint(mutant.operator, mutant.description) if status == "survived" else None
            priority = mutation_priority(mutant.operator)                 if status == "survived" else None

            await _broadcast(job_id, {
                "type": "mutant_result",
                "index": processed, "total": total,
                "mutant_id": mutant.id,
                "function": mutant.function_name,
                "line": mutant.line_no,
                "operator": mutant.operator,
                "description": mutant.description,
                "status": status,
                # killed → which test caught it; survived → None
                "killer_test_file": killer_info.get("test_file") if killer_info else None,
                "killer_test_name": killer_info.get("test_name") if killer_info else None,
                # survived → actionable hint; killed → None
                "hint":     hint,
                "priority": priority,
                "killed": killed, "survived": survived,
                "equivalent": equivalent, "errors": errors,
                "true_score": _score(killed, survived),
                "raw_score":  _raw_score(killed, survived, equivalent),
            })

        # Bounded by the worker pool size; equivalence checks run concurrently too
        await asyncio.gather(*[process_one(m) for m in mutants])

        # ── Survived priority panel (high → medium → low) ─────────────────────
        _PRANK = {"high": 0, "medium": 1, "low": 2}
        survived_sorted = sorted(
            [m for m in mutants if m.status == "survived"],
            key=lambda m: _PRANK.get(mutation_priority(m.operator), 1),
        )
        if survived_sorted:
            await _broadcast(job_id, {
                "type": "survived_priority",
                "mutants": [
                    {
                        "mutant_id": m.id,
                        "function":  m.function_name,
                        "line":      m.line_no,
                        "operator":  m.operator,
                        "description": m.description,
                        "priority":  mutation_priority(m.operator),
                        "hint":      mutation_hint(m.operator, m.description),
                    }
                    for m in survived_sorted
                ],
            })

        # ── Final summary ──────────────────────────────────────────────────────
        summary = {
            "type": "complete",
            "total": total,
            "killed": killed,
            "survived": survived,
            "equivalent": equivalent,
            "errors": errors,
            "true_score": _score(killed, survived),
            "raw_score":  _raw_score(killed, survived, equivalent),
            "llm_provider": llm.name,
        }
        _job_summaries[job_id] = summary
        await _broadcast(job_id, summary)

    except Exception as e:
        await _broadcast(job_id, {"type": "error", "message": str(e)})
    finally:
        if runner:
            runner.teardown_pool()


def _score(killed: int, survived: int) -> float:
    """True mutation score — excludes equivalents."""
    total = killed + survived
    return round(killed / total * 100, 1) if total > 0 else 0.0


def _raw_score(killed: int, survived: int, equivalent: int) -> float:
    """Naive score — includes equivalents in denominator."""
    total = killed + survived + equivalent
    return round(killed / total * 100, 1) if total > 0 else 0.0


# ── API Endpoints ──────────────────────────────────────────────────────────

@app.post("/analyze", response_model=JobResponse)
async def start_analysis(req: AnalyzeRequest):
    if not Path(req.file_path).exists():
        raise HTTPException(400, f"File not found: {req.file_path}")
    if not Path(req.project_root).exists():
        raise HTTPException(400, f"Project root not found: {req.project_root}")

    job_id = str(uuid.uuid4())
    _job_events[job_id] = []
    _job_subs[job_id] = []
    _jobs[job_id] = None  # presence marker for legacy compatibility

    asyncio.create_task(_run_analysis(job_id, req))

    return JobResponse(
        job_id=job_id,
        stream_url=f"http://localhost:8765/stream/{job_id}"
    )


@app.get("/stream/{job_id}")
async def stream_results(job_id: str, from_event: int = 0):
    """
    Stream SSE events for a job.
    from_event=N skips the first N events (used on reconnect to resume
    without replaying events the client already processed).
    """
    if job_id not in _job_events:
        raise HTTPException(404, f"Job {job_id} not found")

    # Per-connection subscriber queue (max 2000 events buffered)
    sub_q: asyncio.Queue = asyncio.Queue(maxsize=2000)
    _job_subs.setdefault(job_id, []).append(sub_q)

    async def event_generator():
        try:
            # ── Phase 1: replay past events the client hasn't seen yet ──
            snapshot = list(_job_events.get(job_id, []))
            for event in snapshot[from_event:]:
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("complete", "error"):
                    return

            # ── Phase 2: stream future events as they arrive ──
            if job_id in _job_done:
                return  # already complete; replay was everything

            while True:
                try:
                    event = await asyncio.wait_for(sub_q.get(), timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("complete", "error"):
                        return
                except asyncio.TimeoutError:
                    yield 'data: {"type": "ping"}\n\n'
        finally:
            subs = _job_subs.get(job_id, [])
            if sub_q in subs:
                subs.remove(sub_q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/summary/{job_id}")
async def get_summary(job_id: str):
    if job_id not in _job_summaries:
        raise HTTPException(404, "Summary not ready yet")
    return _job_summaries[job_id]


_ASK_SYSTEM = """\
You are QAMill Assistant — a mutation testing analyst embedded in a developer's IDE.

YOUR AUTHORITY:
You may only speak to what is explicitly present in the ANALYSIS DATA block below.
You have no knowledge of the project, functions, or code beyond what the data states.

GROUNDING CONTRACT — every rule is mandatory:
1. Every factual claim must trace to a specific value in ANALYSIS DATA.
2. Never state a number (score, count, line number) not present in the data.
3. Never name a mutant ID not listed in the survived section.
4. If survived count is 0 → there are no survived mutants. Do not suggest otherwise.
5. If the data says True Score is X%, do not state a different percentage.
6. Never speculate about code behaviour you have not been shown.
7. If the data is insufficient to answer accurately, say exactly:
   "The analysis data does not contain enough information to answer this."
8. Do not invent hypothetical scenarios and present them as real results.

RESPONSE QUALITY:
- Be specific: reference actual mutant IDs, function names, line numbers from the data.
- Be actionable: tell the developer exactly what to do, not just what the problem is.
- Be concise: 3–5 sentences. No padding.
- Prioritise: high-difficulty survived mutants are most dangerous."""


@app.post("/ask")
async def ask_assistant(req: AskRequest):
    kwargs = {}
    if req.llm_api_key:
        kwargs["api_key"] = req.llm_api_key
    llm = create_adapter(req.llm_provider, **kwargs)

    full_prompt = (
        f"{_ASK_SYSTEM}\n\n"
        "=== ANALYSIS DATA (the only facts you may reference) ===\n"
        f"{req.context}\n"
        "=== END ANALYSIS DATA ===\n\n"
        f"QUESTION: {req.prompt}\n\n"
        "ANSWER PROTOCOL:\n"
        "Step 1 — Find which lines of ANALYSIS DATA are relevant to this question.\n"
        "Step 2 — Check: does the data actually contain what is needed to answer?\n"
        "Step 3 — If yes, answer in 3-5 sentences citing exact values from the data.\n"
        "         If no, state which specific information is missing.\n\n"
        "ANSWER:"
    )

    raw_answer = await llm.call_async(full_prompt, max_tokens=400)
    answer = _validate_and_sanitise(raw_answer, req.context)
    return {"answer": answer}


def _validate_and_sanitise(answer: str, context: str) -> str:
    """
    Lightweight hallucination guard: strip any invented mutant IDs or scores
    that do not appear in the context, and flag if detected.
    """
    import re as _re
    # Extract mutant IDs actually present in context (e.g. M0012, CMR0003)
    ctx_ids = set(_re.findall(r'\b[MC][A-Z0-9]{3,6}\b', context))
    # Find mutant IDs mentioned in the answer
    ans_ids = set(_re.findall(r'\b[MC][A-Z0-9]{3,6}\b', answer))
    hallucinated = ans_ids - ctx_ids
    if hallucinated:
        note = (
            "\n\n[QAMill Note: the assistant referenced "
            + ", ".join(sorted(hallucinated))
            + " which are not in the analysis data. "
            "Please re-run the analysis or ask a more specific question.]"
        )
        return answer + note
    return answer


@app.get("/operators")
async def list_operators():
    """Return all available mutation operators with metadata."""
    operators = []
    for code, meta in OPERATOR_METADATA.items():
        operators.append({
            "code": code,
            "name": meta["name"],
            "description": meta["description"],
        })
    return {"operators": operators}


@app.get("/providers")
async def list_providers():
    """Return available LLM providers and whether each is configured via env var."""
    import os
    return {
        "providers": [
            {"name": "none",    "label": "None (in-house only)", "configured": True,  "model": "AST"},
            {"name": "claude",  "label": "Claude (Anthropic)",   "configured": bool(os.getenv("ANTHROPIC_API_KEY")), "model": "claude-sonnet-4-5"},
            {"name": "gpt",     "label": "GPT-4o (OpenAI)",      "configured": bool(os.getenv("OPENAI_API_KEY")),    "model": "gpt-4o"},
            {"name": "grok",    "label": "Grok (xAI)",           "configured": bool(os.getenv("XAI_API_KEY")),       "model": "grok-3"},
            {"name": "inhouse", "label": "Ollama (local)",        "configured": True,  "model": "llama3"},
        ]
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Report generation ──────────────────────────────────────────────────────

def _build_html_report(job_id: str) -> str:
    """Build a self-contained dark-themed HTML report from stored job events."""
    events   = _job_events.get(job_id, [])
    summary  = _job_summaries.get(job_id, {})
    mutants  = [e for e in events if e.get("type") == "mutant_result"]
    start_ev = next((e for e in events if e.get("type") == "start"), {})
    comp_ev  = next((e for e in events if e.get("type") == "complete"), summary)

    file_name  = start_ev.get("file", "unknown")
    true_score = comp_ev.get("true_score", 0)
    raw_score  = comp_ev.get("raw_score", 0)
    killed     = comp_ev.get("killed", 0)
    survived   = comp_ev.get("survived", 0)
    equivalent = comp_ev.get("equivalent", 0)
    total      = comp_ev.get("total", len(mutants))
    now        = datetime.now().strftime("%Y-%m-%d %H:%M")
    score_col  = "#4ec9a0" if true_score >= 80 else "#d29922" if true_score >= 60 else "#f48771"

    op_total  = Counter(m["operator"] for m in mutants)
    op_killed = Counter(m["operator"] for m in mutants if m["status"] == "killed")
    survived_list = [m for m in mutants if m["status"] == "survived"]

    # ── CSS ──────────────────────────────────────────────────────────────────
    css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #1e1e1e; color: #d4d4d4; font-size: 14px; line-height: 1.6; padding: 36px 48px; }
h1  { font-size: 26px; color: #4ec9a0; margin-bottom: 4px; }
h2  { font-size: 15px; font-weight: 700; color: #c9d1d9; margin: 28px 0 12px;
      border-bottom: 1px solid #30363d; padding-bottom: 6px; text-transform: uppercase;
      letter-spacing: .06em; }
.meta { color: #8b949e; font-size: 12px; margin-bottom: 28px; }
.score-row { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 28px; }
.sc { background: #252526; border: 1px solid #30363d; border-radius: 8px; padding: 14px 20px; min-width: 110px; }
.sc .v { font-size: 36px; font-weight: 700; }
.sc .l { font-size: 10px; color: #8b949e; text-transform: uppercase; letter-spacing: .07em; margin-top: 2px; }
.v-ts  { color: """ + score_col + """; }
.v-raw { color: #ce9178; }
.v-k   { color: #4ec9a0; }
.v-s   { color: #f48771; }
.v-eq  { color: #dcdcaa; }
.op-row { margin-bottom: 10px; }
.op-hd  { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px; }
.bar-w  { background: #30363d; border-radius: 4px; height: 10px; overflow: hidden; }
.bar-f  { height: 100%; background: #4ec9a0; border-radius: 4px; }
table  { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 6px; }
th  { text-align: left; padding: 7px 10px; background: #252526; color: #8b949e;
      font-size: 10px; text-transform: uppercase; letter-spacing: .06em; }
td  { padding: 7px 10px; border-bottom: 1px solid #252526; vertical-align: top; }
tr:hover td { background: #252526; }
.b  { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.bk { background: #1e3a2f; color: #4ec9a0; }
.bs { background: #3a1e1e; color: #f48771; }
.be { background: #2a2a1e; color: #dcdcaa; }
.footer { margin-top: 40px; font-size: 11px; color: #555; border-top: 1px solid #252526; padding-top: 12px; }
"""

    # ── Operator breakdown rows ───────────────────────────────────────────────
    op_rows = ""
    for op, cnt in sorted(op_total.items(), key=lambda x: -x[1]):
        k   = op_killed.get(op, 0)
        pct = round(k / cnt * 100) if cnt else 0
        op_rows += (
            f'<div class="op-row">'
            f'<div class="op-hd"><span><strong>{op}</strong> &nbsp;{cnt} mutants</span>'
            f'<span>{k}/{cnt} killed &nbsp;({pct}%)</span></div>'
            f'<div class="bar-w"><div class="bar-f" style="width:{pct}%"></div></div>'
            f'</div>\n'
        )

    # ── Survived table ────────────────────────────────────────────────────────
    surv_rows = ""
    for m in survived_list:
        diff = m.get("difficulty", "")
        tag  = f' <span style="color:#d29922;font-size:10px">[{diff.upper()}]</span>' if diff else ""
        surv_rows += (
            f'<tr><td>{m["mutant_id"]}</td><td>{m["operator"]}</td>'
            f'<td>{m["function"]}</td><td>{m["line"]}</td>'
            f'<td>{m["description"]}{tag}</td></tr>\n'
        )

    # ── Full results table ────────────────────────────────────────────────────
    all_rows = ""
    for m in mutants:
        st  = m["status"]
        bc  = {"killed": "bk", "survived": "bs", "equivalent": "be"}.get(st, "")
        all_rows += (
            f'<tr><td>{m["mutant_id"]}</td><td>{m["operator"]}</td>'
            f'<td>{m["function"]}</td><td>{m["line"]}</td>'
            f'<td>{m["description"]}</td>'
            f'<td><span class="b {bc}">{st.upper()}</span></td></tr>\n'
        )

    surv_section = ""
    if survived_list:
        surv_section = f"""
<h2>Survived Mutants ({len(survived_list)})</h2>
<table>
  <thead><tr><th>ID</th><th>Op</th><th>Function</th><th>Line</th><th>Description</th></tr></thead>
  <tbody>{surv_rows}</tbody>
</table>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QAMill Report — {file_name}</title>
<style>{css}</style>
</head>
<body>
<h1>QAMill &mdash; Mutation Analysis Report</h1>
<div class="meta">
  File: <strong>{file_name}</strong> &nbsp;&middot;&nbsp;
  Generated: {now} &nbsp;&middot;&nbsp;
  Total mutants: {total}
</div>

<h2>Score Summary</h2>
<div class="score-row">
  <div class="sc"><div class="l">True Score</div><div class="v v-ts">{true_score}%</div></div>
  <div class="sc"><div class="l">Raw Score</div><div class="v v-raw">{raw_score}%</div></div>
  <div class="sc"><div class="l">Killed</div><div class="v v-k">{killed}</div></div>
  <div class="sc"><div class="l">Survived</div><div class="v v-s">{survived}</div></div>
  <div class="sc"><div class="l">Equivalent</div><div class="v v-eq">{equivalent}</div></div>
</div>

<h2>Coverage by Operator</h2>
{op_rows}
{surv_section}

<h2>All Mutants ({total})</h2>
<table>
  <thead><tr><th>ID</th><th>Op</th><th>Function</th><th>Line</th><th>Description</th><th>Status</th></tr></thead>
  <tbody>{all_rows}</tbody>
</table>

<div class="footer">Generated by QAMill &mdash; AI Mutation Testing &nbsp;&middot;&nbsp; {now}</div>
</body>
</html>"""


@app.get("/export/{job_id}")
async def export_report(job_id: str):
    """Download analysis as a self-contained HTML report."""
    if job_id not in _job_events:
        raise HTTPException(404, f"Job {job_id} not found")
    from fastapi.responses import HTMLResponse
    html = _build_html_report(job_id)
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="qamill-{job_id[:8]}.html"'},
    )


# ── Shared SMTP helper ─────────────────────────────────────────────────────

def _smtp_send(
    smtp_host: str, smtp_port: int,
    smtp_user: str, smtp_password: str,
    sender: str, to_address: str,
    msg: MIMEMultipart,
    use_tls: bool = True,
) -> None:
    """
    Send a MIME message.
    use_tls=True  → plain SMTP + STARTTLS (port 587, Gmail / Outlook).
    use_tls=False → SMTP_SSL direct (port 465).
    Raises HTTPException with a user-actionable message on every failure.
    """
    import socket as _socket
    try:
        if use_tls:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as srv:
                srv.ehlo()
                srv.starttls()          # upgrade to TLS
                srv.ehlo()              # RFC-required re-greeting after STARTTLS
                srv.login(smtp_user, smtp_password)
                srv.sendmail(sender, to_address, msg.as_string())
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as srv:
                srv.ehlo()
                srv.login(smtp_user, smtp_password)
                srv.sendmail(sender, to_address, msg.as_string())

    except smtplib.SMTPAuthenticationError as e:
        code   = e.smtp_code
        detail = e.smtp_error.decode(errors="replace") if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
        detail_lo = detail.lower()
        if code == 534 or "534" in str(code) or "two-step" in detail_lo or "application-specific" in detail_lo:
            raise HTTPException(401,
                "Gmail requires an App Password. "
                "Enable 2-Step Verification at myaccount.google.com, "
                "then go to Security → App Passwords and generate one.")
        if code == 535 or "535" in str(code) or "username and password not accepted" in detail_lo:
            raise HTTPException(401,
                "Authentication failed — use an App Password, not your regular password. "
                "Regular passwords are blocked by Gmail and Outlook for SMTP access. "
                "See: myaccount.google.com/apppasswords")
        raise HTTPException(401,
            f"Authentication failed (SMTP {code}) — "
            "check your App Password and sender address. "
            f"Server said: {detail[:160]}")

    except smtplib.SMTPSenderRefused as e:
        raise HTTPException(422, f"Invalid sender email address '{e.sender}' — check your sender field.")

    except smtplib.SMTPRecipientsRefused as e:
        bad = ", ".join(e.recipients.keys())
        raise HTTPException(422, f"Recipient address rejected by server: {bad}")

    except smtplib.SMTPConnectError as e:
        raise HTTPException(503,
            f"Could not connect to {smtp_host}:{smtp_port} — {e}. "
            "Gmail: smtp.gmail.com:587 | Outlook: smtp-mail.outlook.com:587")

    except (_socket.timeout, TimeoutError):
        raise HTTPException(503,
            f"Connection to {smtp_host}:{smtp_port} timed out — "
            "check hostname and port, and that your firewall allows outbound SMTP.")

    except _socket.gaierror:
        raise HTTPException(503,
            f"Cannot resolve SMTP hostname '{smtp_host}' — "
            "check for typos and that you have internet access.")

    except smtplib.SMTPException as e:
        raise HTTPException(500, f"SMTP error: {e}")


@app.post("/email/test")
async def test_email_connection(req: EmailTestRequest):
    """Send a test email to verify SMTP credentials before sending a real report."""
    sender = req.sender_email or req.smtp_user
    msg    = MIMEMultipart("alternative")
    msg["Subject"] = "QAMill — SMTP Connection Test"
    msg["From"]    = sender
    msg["To"]      = req.to_address
    plain = (
        "This is a test email from QAMill.\n\n"
        "Your SMTP settings are working correctly.\n"
        "You can now send QAMill mutation analysis reports to this address.\n"
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(
        "<p>This is a test email from <strong>QAMill</strong>.</p>"
        "<p>Your SMTP settings are working correctly.</p>",
        "html"
    ))
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _smtp_send,
        req.smtp_host, req.smtp_port, req.smtp_user, req.smtp_password,
        sender, req.to_address, msg, req.use_tls,
    )
    return {"status": "sent", "to": req.to_address,
            "message": f"Test email sent successfully to {req.to_address}"}


@app.post("/email")
async def email_report(req: EmailRequest):
    """Send analysis report to an email address via SMTP."""
    if req.job_id not in _job_events:
        raise HTTPException(404, f"Job {req.job_id} not found")

    html_body = _build_html_report(req.job_id)
    start_ev  = next((e for e in _job_events[req.job_id] if e.get("type") == "start"), {})
    file_name = start_ev.get("file", "unknown")
    summary   = _job_summaries.get(req.job_id, {})
    score     = summary.get("true_score", 0)

    sender = req.sender_email or req.smtp_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"QAMill Report — {file_name} — Score: {score}%"
    msg["From"]    = sender
    msg["To"]      = req.to_address

    plain = (
        f"QAMill Mutation Analysis Report\n"
        f"File      : {file_name}\n"
        f"True score: {score}%\n"
        f"Killed    : {summary.get('killed', 0)}\n"
        f"Survived  : {summary.get('survived', 0)}\n"
        f"Equivalent: {summary.get('equivalent', 0)}\n\n"
        f"Open the HTML report in your browser for the full details."
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _smtp_send,
        req.smtp_host, req.smtp_port, req.smtp_user, req.smtp_password,
        sender, req.to_address, msg, req.use_tls,
    )

    return {"status": "sent", "to": req.to_address, "subject": msg["Subject"]}


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
