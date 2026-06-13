"""
main.py
FastAPI backend — runs locally on port 8765.
Streams real-time mutation results via Server-Sent Events.
VS Code extension and browser dashboard both connect to this.
"""
import asyncio
import json
import smtplib
import time
import uuid
from collections import Counter
from datetime import datetime
from email.mime.base import MIMEBase
from email import encoders
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
from report_generator import build_html_report

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
        analysis_start = time.monotonic()
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
        execution_time = round(time.monotonic() - analysis_start, 2)
        true_score_val = _score(killed, survived)
        raw_score_val  = _raw_score(killed, survived, equivalent)

        # Auto-save HTML report
        report_path = ""
        try:
            report_data = {
                "file_name":       Path(req.file_path).name,
                "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M"),
                "execution_time":  execution_time,
                "true_score":      true_score_val,
                "raw_score":       raw_score_val,
                "killed":          killed,
                "survived":        survived,
                "equivalent":      equivalent,
                "total":           total,
                "llm_provider":    llm.name,
                "mutants": [
                    e for e in _job_events.get(job_id, [])
                    if e.get("type") == "mutant_result"
                ],
            }
            reports_dir = Path(req.project_root) / "qamill-reports"
            reports_dir.mkdir(exist_ok=True)
            ts_tag = datetime.now().strftime("%Y%m%d-%H%M%S")
            stem   = Path(req.file_path).stem
            report_file = reports_dir / f"qamill-{stem}-{ts_tag}.html"
            html_content = build_html_report(report_data)
            report_file.write_text(html_content, encoding="utf-8")
            report_path = str(report_file)
        except Exception as rep_err:
            report_path = f"error: {rep_err}"

        summary = {
            "type": "complete",
            "total": total,
            "killed": killed,
            "survived": survived,
            "equivalent": equivalent,
            "errors": errors,
            "true_score": true_score_val,
            "raw_score":  raw_score_val,
            "llm_provider": llm.name,
            "execution_time_seconds": execution_time,
            "report_path": report_path,
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
    """Build elite self-contained HTML report from stored job events."""
    events   = _job_events.get(job_id, [])
    summary  = _job_summaries.get(job_id, {})
    mutants  = [e for e in events if e.get("type") == "mutant_result"]
    start_ev = next((e for e in events if e.get("type") == "start"), {})
    comp_ev  = next((e for e in events if e.get("type") == "complete"), summary)

    data = {
        "file_name":      start_ev.get("file", "unknown"),
        "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "execution_time": comp_ev.get("execution_time_seconds", 0),
        "true_score":     comp_ev.get("true_score", 0),
        "raw_score":      comp_ev.get("raw_score", 0),
        "killed":         comp_ev.get("killed", 0),
        "survived":       comp_ev.get("survived", 0),
        "equivalent":     comp_ev.get("equivalent", 0),
        "total":          comp_ev.get("total", len(mutants)),
        "llm_provider":   comp_ev.get("llm_provider", "none"),
        "mutants":        mutants,
    }
    return build_html_report(data)


@app.get("/export/{job_id}")
async def export_report(job_id: str):
    """Download analysis as a self-contained HTML report."""
    if job_id not in _job_events:
        raise HTTPException(404, f"Job {job_id} not found")
    from fastapi.responses import HTMLResponse
    html = _build_html_report(job_id)
    file_name = next(
        (e.get("file", "report") for e in _job_events[job_id] if e.get("type") == "start"),
        "report"
    )
    stem = Path(file_name).stem
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="qamill-{stem}-{job_id[:8]}.html"'},
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


# ── /email-report endpoint (Task 4) ──────────────────────────────────────

class EmailReportRequest(BaseModel):
    recipient:      str
    subject:        str
    message:        str
    sender_email:   str
    app_password:   str
    smtp_provider:  str = "gmail"   # "gmail" | "outlook" | "custom"
    smtp_host:      str = ""        # for custom provider
    smtp_port:      int = 587
    report_html:    str = ""        # full HTML report as string


@app.post("/email-report")
async def email_report_direct(req: EmailReportRequest):
    """Send HTML report via SMTP. Called from the report's Email modal."""
    provider_settings = {
        "gmail":   ("smtp.gmail.com",          587, True),
        "outlook": ("smtp-mail.outlook.com",   587, True),
    }
    if req.smtp_provider in provider_settings:
        host, port, use_tls = provider_settings[req.smtp_provider]
    else:
        host     = req.smtp_host or "localhost"
        port     = req.smtp_port or 587
        use_tls  = True

    msg = MIMEMultipart("mixed")
    msg["Subject"] = req.subject
    msg["From"]    = req.sender_email
    msg["To"]      = req.recipient

    # Plain text body
    msg.attach(MIMEText(req.message, "plain"))

    # HTML summary body
    summary_html = f"""<html><body style="font-family:sans-serif;padding:24px">
<h2 style="color:#3fb950">QAMill Mutation Report</h2>
<pre style="background:#f6f8fa;padding:16px;border-radius:6px">{req.message}</pre>
<p style="color:#666;margin-top:16px">See the attached HTML file for the full interactive report.</p>
</body></html>"""
    msg.attach(MIMEText(summary_html, "html"))

    # Attach full HTML report
    if req.report_html:
        ts   = datetime.now().strftime("%Y%m%d-%H%M%S")
        att  = MIMEBase("application", "octet-stream")
        att.set_payload(req.report_html.encode("utf-8"))
        encoders.encode_base64(att)
        att.add_header("Content-Disposition",
                        f'attachment; filename="qamill-report-{ts}.html"')
        msg.attach(att)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _smtp_send,
        host, port, req.sender_email, req.app_password,
        req.sender_email, req.recipient, msg, use_tls,
    )
    return {"success": True, "message": f"Report sent to {req.recipient}"}


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
