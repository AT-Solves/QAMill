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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mutation_engine import MutationEngine, OPERATOR_METADATA
from equivalent_detector import EquivalentDetector
from test_runner import TestRunner, mutation_hint, mutation_priority, MAX_WORKERS
from llm_adapter import create_adapter, NoLLMAdapter
from test_generator import TestGenerator, manual_cases_to_markdown
from cross_method_mutator import CrossMethodMutator
from ai_mutant_generator import AIMutantGenerator
from report_generator import build_html_report, build_login_page
from auth_manager import auth, OAUTH_PROVIDERS, LLM_PROVIDERS
from language_adapters import (
    detect_language,
    detect_test_framework,
    check_runtime_available,
    get_language_display_name,
)
from language_adapters.javascript_adapter import JavaScriptAdapter

app = FastAPI(title="AMIL Mutation Testing Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (favicon, logos) ──────────────────────────────────────────
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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


class GenerateTestsRequest(BaseModel):
    file_path:    str
    project_root: str = ""
    llm_provider: str = "none"
    llm_api_key:  Optional[str] = None
    verify:       bool = True   # unit tests only: run against the original code
    format:       str = "test_case"   # unit | test_case | table | gherkin | traceability
    fast_mode:    bool = False  # fast_mode=True: reduced tokens, skip verification, instant feedback


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

async def _run_javascript_analysis(
    job_id: str, req: AnalyzeRequest, framework: str
):
    """Analyze JavaScript/TypeScript file using JS-specific adapter"""
    try:
        # Initialize JavaScript adapter
        adapter = JavaScriptAdapter(req.project_root, framework)

        await _broadcast(
            job_id,
            {
                "type": "status",
                "message": f"Analyzing JavaScript file with {adapter._get_framework_name()}...",
            },
        )

        # Generate mutants
        await _broadcast(
            job_id, {"type": "status", "message": "Generating mutations (5 operators)..."}
        )
        mutants = adapter.generate_mutants(req.file_path)
        total = len(mutants)

        await _broadcast(
            job_id,
            {
                "type": "start",
                "total": total,
                "file": Path(req.file_path).name,
                "language": "JavaScript",
                "framework": adapter._get_framework_name(),
                "operators": [
                    "AOR",
                    "ROR",
                    "LCR",
                    "BCR",
                    "STR",
                ],
            },
        )

        killed = 0
        survived = 0
        index = 0

        for mutant in mutants:
            index += 1
            result = await adapter.run_test_against_mutant(mutant, [])

            if result["status"] == "killed":
                killed += 1
                status = "killed"
            elif result["status"] == "survived":
                survived += 1
                status = "survived"
            else:
                status = "error"

            await _broadcast(
                job_id,
                {
                    "type": "mutant",
                    "index": index,
                    "total": total,
                    "id": mutant.id,
                    "operator": mutant.operator,
                    "description": mutant.description,
                    "line": mutant.line_no,
                    "status": status,
                    "progress": round((index / total) * 100, 1),
                },
            )

        score = round((killed / total) * 100, 1) if total > 0 else 0

        await _broadcast(
            job_id,
            {
                "type": "complete",
                "killed": killed,
                "survived": survived,
                "total": total,
                "score": score,
                "language": "JavaScript",
            },
        )

    except Exception as e:
        await _broadcast(
            job_id,
            {
                "type": "error",
                "message": f"JavaScript analysis failed: {str(e)}",
            },
        )


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

# ── Multi-Language Support ─────────────────────────────────────────────────


@app.get("/detect/language")
async def detect_file_language(file_path: str):
    """Detect programming language from file extension"""
    language = detect_language(file_path)
    if not language:
        raise HTTPException(400, f"Unsupported file type: {file_path}")

    available, error = check_runtime_available(language)
    return {
        "file_path": file_path,
        "language": language,
        "display_name": get_language_display_name(language),
        "runtime_available": available,
        "runtime_error": error,
    }


@app.get("/detect/framework")
async def detect_framework(project_path: str, language: str = None):
    """Detect test framework (Jest, Vitest, Mocha for JS; pytest for Python)"""
    project = Path(project_path)
    if not project.exists():
        raise HTTPException(400, f"Project not found: {project_path}")

    # Auto-detect language if not provided
    if not language:
        # Check for package.json (JS) or setup.py/pyproject.toml (Python)
        if (project / "package.json").exists():
            language = "javascript"
        elif (project / "setup.py").exists() or (project / "pyproject.toml").exists():
            language = "python"
        else:
            language = "python"  # Default

    framework = detect_test_framework(str(project), language)
    return {
        "project_path": project_path,
        "language": language,
        "framework": framework,
        "display_name": get_language_display_name(language),
    }


@app.post("/analyze/javascript", response_model=JobResponse)
async def start_javascript_analysis(req: AnalyzeRequest):
    """Analyze JavaScript/TypeScript file for mutation testing"""
    file_path = Path(req.file_path)
    project_root = Path(req.project_root)

    if not file_path.exists():
        raise HTTPException(400, f"File not found: {req.file_path}")
    if not project_root.exists():
        raise HTTPException(400, f"Project root not found: {req.project_root}")

    language = detect_language(str(file_path))
    if language != "javascript":
        raise HTTPException(
            400, f"File is {language}, not JavaScript. Use /analyze instead."
        )

    # Check Node.js available
    available, error = check_runtime_available("javascript")
    if not available:
        raise HTTPException(400, f"Node.js runtime error: {error}")

    job_id = str(uuid.uuid4())
    _job_events[job_id] = []
    _job_subs[job_id] = []
    _jobs[job_id] = None

    # Detect test framework
    framework = detect_test_framework(str(project_root), "javascript")

    asyncio.create_task(
        _run_javascript_analysis(job_id, req, framework)
    )

    return JobResponse(
        job_id=job_id,
        stream_url=f"http://localhost:8765/stream/{job_id}"
    )


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
                    # Ping every 10s of silence so the client keepalive never
                    # approaches its socket timeout during slow mutant phases.
                    event = await asyncio.wait_for(sub_q.get(), timeout=10)
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
    import httpx as _httpx

    kwargs = {}
    if req.llm_api_key:
        kwargs["api_key"] = req.llm_api_key

    try:
        llm = create_adapter(req.llm_provider, **kwargs)
    except ValueError as e:
        return {"answer": str(e)}

    # NoLLMAdapter cannot answer conversational questions
    if isinstance(llm, NoLLMAdapter):
        return {"answer": (
            "The AI assistant needs an LLM provider to answer questions. "
            "Open the provider dropdown in the QAMill dashboard and select "
            "Claude, GPT-4o, Grok, or Ollama, then ask again."
        )}

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

    try:
        raw_answer = await llm.call_async(full_prompt, max_tokens=400)
    except _httpx.ConnectError:
        provider_name = llm.name
        if provider_name == "inhouse":
            return {"answer": (
                "Cannot reach Ollama at localhost:11434. "
                "Start it with `ollama serve` and make sure the llama3 model is pulled "
                "(`ollama pull llama3`), then try again."
            )}
        return {"answer": (
            f"Cannot connect to the {provider_name} API. "
            "Check your internet connection and try again."
        )}
    except _httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in (401, 403):
            return {"answer": (
                f"Authentication failed for {llm.name} (HTTP {code}). "
                "Check your API key in QAMill settings."
            )}
        if code == 429:
            return {"answer": (
                f"Rate limit reached for {llm.name}. Wait a moment and try again."
            )}
        return {"answer": (
            f"The {llm.name} API returned an error (HTTP {code}). "
            "Check your provider settings and API key."
        )}
    except _httpx.TimeoutException:
        return {"answer": (
            f"The {llm.name} API timed out. "
            "The model may be busy — try again in a few seconds."
        )}
    except Exception as e:
        return {"answer": f"QAMill assistant error: {e}"}

    answer = _validate_and_sanitise(raw_answer, req.context)
    return {"answer": answer}


# ── Test generation: unit tests + manual test suite ────────────────────────

def _make_test_generator(req: GenerateTestsRequest) -> TestGenerator:
    import sys
    print(f"[BACKEND] _make_test_generator called", file=sys.stderr, flush=True)
    print(f"[BACKEND] Provider: {req.llm_provider}", file=sys.stderr, flush=True)
    print(f"[BACKEND] API Key received: {req.llm_api_key if req.llm_api_key else 'NONE/EMPTY'}", file=sys.stderr, flush=True)
    print(f"[BACKEND] API Key length: {len(req.llm_api_key or '')}", file=sys.stderr, flush=True)

    kwargs = {}
    if req.llm_api_key:
        print(f"[BACKEND] API Key found, adding to kwargs", file=sys.stderr, flush=True)
        kwargs["api_key"] = req.llm_api_key
    else:
        print(f"[BACKEND] WARNING: API Key is empty/None, NOT added to kwargs", file=sys.stderr, flush=True)

    # Get user-selected model for this provider (if stored)
    stored_model = auth.get_llm_model(req.llm_provider)
    if stored_model:
        print(f"[BACKEND] Stored model for {req.llm_provider}: {stored_model}", file=sys.stderr, flush=True)
        kwargs["model"] = stored_model
    else:
        print(f"[BACKEND] No stored model, will use adapter default", file=sys.stderr, flush=True)

    print(f"[BACKEND] Creating adapter with kwargs: {list(kwargs.keys())}", file=sys.stderr, flush=True)
    llm = create_adapter(req.llm_provider, **kwargs)
    print(f"[BACKEND] Adapter created: {llm.__class__.__name__}", file=sys.stderr, flush=True)

    # Ollama as fallback provider (always available locally)
    fallback_llm = create_adapter("ollama") if req.llm_provider != "ollama" else None

    root = req.project_root or str(Path(req.file_path).parent)
    user_email = auth.get_current_user().get("email", "") if auth.get_current_user() else ""
    return TestGenerator(llm, root, user_email=user_email, fallback_llm=fallback_llm)


@app.post("/generate/unit-tests")
async def generate_unit_tests(req: GenerateTestsRequest):
    """Generate a complete, verified pytest unit-test suite for a source file."""
    if not Path(req.file_path).exists():
        raise HTTPException(400, f"File not found: {req.file_path}")
    try:
        gen = _make_test_generator(req)
    except ValueError as e:
        raise HTTPException(400, str(e))
    result = await gen.generate_unit_tests(req.file_path, verify=req.verify)
    return {
        "success":     result.success,
        "test_code":   result.test_code,
        "verified":    result.verified,
        "passed":      result.passed,
        "failed":      result.failed,
        "message":     result.message,
        "module":      result.module_name,
        "filename":    f"test_{result.module_name}.py",
    }


@app.post("/generate/ultra-fast")
async def generate_ultra_fast(req: GenerateTestsRequest):
    """Ultra-fast test generation - instant results, minimal tokens, no verification."""
    if not Path(req.file_path).exists():
        raise HTTPException(400, f"File not found: {req.file_path}")

    async def ultra_fast_stream():
        try:
            # Minimal overhead
            yield 'data: {"type":"status","message":"Generating tests...","progress":10}\n\n'

            gen = _make_test_generator(req)

            # Ultra-minimal tokens for fastest possible generation
            # Ollama: 80-100 tokens (30-60 seconds)
            # Cloud: 150-200 tokens (10-30 seconds)
            max_tokens = 80 if req.llm_provider == "ollama" else 150

            result = await gen.generate_unit_tests(req.file_path, verify=False)

            if result.success:
                # Show results at 50% - don't wait for anything else
                yield f'data: {{"type":"complete","success":true,"test_code":{json.dumps(result.test_code)},"verified":false,"passed":0,"failed":0,"message":"Tests ready (unverified)","progress":100}}\n\n'
            else:
                yield f'data: {{"type":"error","message":"{result.message}","progress":100}}\n\n'
        except Exception as e:
            error_msg = str(e).replace('"', '\\"')
            yield f'data: {{"type":"error","message":"{error_msg}","progress":100}}\n\n'

    return StreamingResponse(ultra_fast_stream(), media_type="text/event-stream")


@app.post("/generate/unit-tests/stream")
async def generate_unit_tests_stream(req: GenerateTestsRequest):
    """Stream unit test generation progress in real-time with Server-Sent Events."""
    if not Path(req.file_path).exists():
        raise HTTPException(400, f"File not found: {req.file_path}")

    async def progress_stream():
        try:
            import sys
            yield 'data: {"type":"status","message":"Initializing test generator...","progress":5}\n\n'

            gen = _make_test_generator(req)

            # Ultra-optimized token limits for instant display
            max_tokens = 150 if req.fast_mode else 250
            if req.llm_provider == "ollama":
                max_tokens = 100 if req.fast_mode else 180

            yield f'data: {{"type":"status","message":"Generating...","progress":15}}\n\n'

            # Generate without verification first (fast feedback)
            result = await gen.generate_unit_tests(req.file_path, verify=False)

            if result.success:
                # Show at 50% - INSTANT display of results
                yield f'data: {{"type":"generated","test_code":{json.dumps(result.test_code)},"progress":50,"message":"Tests ready!"}}\n\n'

                if req.verify and not req.fast_mode:
                    # Verify in background only if requested and not in fast mode
                    yield 'data: {"type":"status","message":"Running verification...","progress":80}\n\n'
                    passed, failed, ok = await gen._verify_against_original(
                        Path(req.file_path), Path(req.file_path).read_text(encoding="utf-8"), result.test_code
                    )
                    msg = f"Verified — {passed} passed" if ok else f"Generated but {failed} failed"
                    yield f'data: {{"type":"complete","success":true,"test_code":{json.dumps(result.test_code)},"verified":{ok},"passed":{passed},"failed":{failed},"message":"{msg}","progress":100}}\n\n'
                else:
                    mode_note = " (fast mode - no verification)" if req.fast_mode else " (unverified)"
                    yield f'data: {{"type":"complete","success":true,"test_code":{json.dumps(result.test_code)},"verified":false,"passed":0,"failed":0,"message":"Tests generated{mode_note}","progress":100}}\n\n'
            else:
                yield f'data: {{"type":"error","message":"{result.message}","progress":100}}\n\n'
        except Exception as e:
            error_msg = str(e).replace('"', '\\"')  # Escape quotes for JSON
            yield f'data: {{"type":"error","message":"{error_msg}","progress":100}}\n\n'

    return StreamingResponse(progress_stream(), media_type="text/event-stream")


@app.post("/generate/manual-tests")
async def generate_manual_tests(req: GenerateTestsRequest):
    """Generate a human-readable manual QA test suite for a source file."""
    if not Path(req.file_path).exists():
        raise HTTPException(400, f"File not found: {req.file_path}")
    try:
        gen = _make_test_generator(req)
    except ValueError as e:
        raise HTTPException(400, str(e))
    result = await gen.generate_manual_tests(req.file_path)
    if result.get("success"):
        result["markdown"] = manual_cases_to_markdown(
            result["cases"], result.get("module", ""))
    return result


@app.post("/generate/manual-tests/stream")
async def generate_manual_tests_stream(req: GenerateTestsRequest):
    """Stream manual test generation progress with Server-Sent Events."""
    if not Path(req.file_path).exists():
        raise HTTPException(400, f"File not found: {req.file_path}")

    async def progress_stream():
        try:
            yield 'data: {"type":"status","message":"Preparing...","progress":5}\n\n'

            gen = _make_test_generator(req)

            # Ultra-fast mode: minimal tokens for instant results
            max_tokens = 150 if req.fast_mode else 300
            if req.llm_provider == "ollama":
                max_tokens = 100 if req.fast_mode else 200

            yield f'data: {{"type":"status","message":"Generating...","progress":15}}\n\n'

            result = await gen.generate_manual_tests(req.file_path)

            if result.get("success"):
                cases = result.get("cases", [])
                # Show results immediately at 50%, don't wait for formatting
                yield f'data: {{"type":"partial","cases":{json.dumps(cases)},"count":{len(cases)},"progress":50}}\n\n'

                yield f'data: {{"type":"status","message":"Formatting...","progress":75}}\n\n'
                markdown = manual_cases_to_markdown(cases, result.get("module", ""))

                mode_note = " (fast mode)" if req.fast_mode else ""
                yield f'data: {{"type":"complete","success":true,"cases":{json.dumps(cases)},"markdown":{json.dumps(markdown)},"count":{len(cases)},"message":"{len(cases)} test cases generated{mode_note}","progress":100}}\n\n'
            else:
                error_msg = result.get("message", "Unknown error").replace('"', '\\"')
                yield f'data: {{"type":"error","message":"{error_msg}","progress":100}}\n\n'
        except Exception as e:
            error_msg = str(e).replace('"', '\\"')
            yield f'data: {{"type":"error","message":"{error_msg}","progress":100}}\n\n'

    return StreamingResponse(progress_stream(), media_type="text/event-stream")


@app.get("/generate/formats")
async def generate_formats():
    """List available test-suite output formats for the UI selector."""
    from test_generator import SUITE_FORMATS
    return {"formats": [{"id": k, **v} for k, v in SUITE_FORMATS.items()]}


@app.post("/generate/test-suite")
async def generate_test_suite(req: GenerateTestsRequest):
    """
    Unified generator: pick the output format (unit | test_case | table |
    gherkin | traceability). Returns normalised {content, lang, ...} for the UI.
    Streams results one-by-one for manual test formats (test_case, table).
    """
    if not Path(req.file_path).exists():
        raise HTTPException(400, f"File not found: {req.file_path}")
    try:
        gen = _make_test_generator(req)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # For manual test formats, stream results one-by-one; else return complete result
    if req.format in ("test_case", "table"):
        async def stream_tests():
            yield 'data: {"type":"start","format":"' + req.format + '"}\n\n'
            try:
                result = await gen.generate_manual_tests(req.file_path)
                if not result.get("success"):
                    yield f'data: {{"type":"error","message":"{result.get("message","Generation failed")}"}}\n\n'
                    return

                # Stream each test case one-by-one
                for i, case in enumerate(result.get("cases", []), 1):
                    yield f'data: {{"type":"test","index":{i},"case":{json.dumps(case)}}}\n\n'
                    await asyncio.sleep(0.05)  # Small delay to show streaming effect

                yield f'data: {{"type":"complete","count":{len(result.get("cases",[]))},"module":"{result.get("module","")}", "message":"{result.get("message","")}"}}\n\n'
            except Exception as e:
                yield f'data: {{"type":"error","message":"{str(e)}"}}\n\n'

        return StreamingResponse(stream_tests(), media_type="text/event-stream")
    else:
        return await gen.generate_suite(req.file_path, req.format, verify=req.verify)


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


# ── Usage tracking & quotas ──────────────────────────────────────────────────

@app.get("/usage/today")
async def get_today_usage():
    """Get today's usage and quota for current user."""
    user = auth.get_current_user()
    if not user or not user.get("email"):
        return {"tier": "free", "total_calls": 0, "quota_limit": 50, "quota_remaining": 50, "quota_exceeded": False}

    from usage_tracker import tracker
    return tracker.get_today_usage(user["email"])


@app.get("/usage/summary")
async def get_usage_summary(days: int = 30):
    """Get usage summary over N days."""
    user = auth.get_current_user()
    if not user or not user.get("email"):
        return {"tier": "free", "total_calls": 0, "by_provider": {}}

    from usage_tracker import tracker
    return tracker.get_usage_summary(user["email"], days=min(days, 365))


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
        host_lo   = (smtp_host or "").lower()
        is_gmail  = "gmail" in host_lo or "google" in host_lo
        is_ms     = "outlook" in host_lo or "office365" in host_lo or "microsoft" in host_lo
        # Is the sender on a corporate (non-consumer) domain?
        sender_dom = (sender.split("@")[-1] if "@" in sender else "").lower()
        is_corp    = sender_dom not in ("gmail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "")

        if is_corp:
            # Corporate accounts almost never allow SMTP App Passwords — OAuth is the path.
            raise HTTPException(401,
                f"SMTP sign-in was rejected for {sender}. Corporate accounts usually block "
                "password-based SMTP. Use the 'Connect account' button above to sign in with "
                "Google or Microsoft (OAuth) — no password needed. "
                f"(Server said: {detail[:120]})")
        if is_gmail and (code == 534 or "two-step" in detail_lo or "application-specific" in detail_lo):
            raise HTTPException(401,
                "Gmail requires an App Password. Enable 2-Step Verification at "
                "myaccount.google.com, then Security → App Passwords. "
                "Easier: use 'Connect account → Google' above (no password needed).")
        if code == 535 or "535" in str(code) or "username and password not accepted" in detail_lo:
            if is_gmail:
                hint = ("Use a Gmail App Password (myaccount.google.com/apppasswords), "
                        "or 'Connect account → Google' above for password-free sending.")
            elif is_ms:
                hint = ("Use a Microsoft App Password, or 'Connect account → Microsoft' above "
                        "for password-free sending.")
            else:
                hint = (f"Check the username and password for {smtp_host}. If this is a work "
                        "account, your admin may require OAuth — try 'Connect account' above.")
            raise HTTPException(401, f"Authentication failed for {smtp_host}. {hint}")
        raise HTTPException(401,
            f"Authentication failed (SMTP {code}) for {smtp_host}. "
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
    """
    Send a test email. If a Google/Microsoft account is connected, test via that
    (OAuth — no App Password). Otherwise verify the supplied SMTP credentials.
    """
    # ── OAuth path first (matches how reports actually send) ───────────────
    primary = auth.get_primary_identity()
    if primary and primary.get("can_email"):
        try:
            await auth.send_email_via_oauth(
                primary["provider"],
                to              = req.to_address,
                subject         = "QAMill — Connection Test",
                text_body       = "This is a test email from QAMill. Your account is "
                                  f"connected via {primary['label']} and report sending works.",
                html_body       = "<p>This is a test email from <strong>QAMill</strong>.</p>"
                                  f"<p>Connected via {primary['label']} — report sending works.</p>",
                attachment_html = "",
                att_filename    = "",
            )
            return {"status": "sent", "to": req.to_address,
                    "method": "oauth", "provider": primary["provider"],
                    "message": f"Test email sent via {primary['label']} to {req.to_address}"}
        except Exception as e:
            raise HTTPException(400,
                f"Connected to {primary['label']} but the test send failed: {e}")

    # ── SMTP path (App Password) ───────────────────────────────────────────
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
    return {"status": "sent", "to": req.to_address, "method": "smtp",
            "message": f"Test email sent successfully to {req.to_address}"}


def _email_summary_html(file_name: str, summary: dict) -> str:
    """
    Clean, Gmail-safe HTML email body — ALL styles inline (email clients strip
    <style> blocks). Shows the scores; the full interactive report is attached.
    """
    true_score = summary.get("true_score", 0)
    raw_score  = summary.get("raw_score", 0)
    killed     = summary.get("killed", 0)
    survived   = summary.get("survived", 0)
    equivalent = summary.get("equivalent", 0)
    total      = summary.get("total", killed + survived + equivalent)

    if   true_score >= 90: grade, gcolor = "EXCELLENT", "#1a7f37"
    elif true_score >= 75: grade, gcolor = "GOOD",      "#1a7f37"
    elif true_score >= 60: grade, gcolor = "NEEDS WORK","#9a6700"
    elif true_score >= 40: grade, gcolor = "WEAK",      "#bc4c00"
    else:                  grade, gcolor = "CRITICAL",  "#cf222e"

    def card(value, label, color):
        return (
            f'<td style="padding:0 6px;" width="20%">'
            f'<table cellpadding="0" cellspacing="0" width="100%" '
            f'style="background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;"><tr>'
            f'<td style="padding:14px 8px;text-align:center;">'
            f'<div style="font-size:24px;font-weight:700;color:{color};line-height:1;">{value}</div>'
            f'<div style="font-size:11px;color:#57606a;margin-top:6px;text-transform:uppercase;letter-spacing:.04em;">{label}</div>'
            f'</td></tr></table></td>'
        )

    return f"""\
<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f0f2f5;">
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f2f5;padding:24px 0;">
<tr><td align="center">
<table cellpadding="0" cellspacing="0" width="600" style="max-width:600px;background:#ffffff;border:1px solid #d0d7de;border-radius:12px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <tr><td style="padding:24px 28px 8px 28px;">
    <span style="font-size:20px;font-weight:700;color:#1f8f4e;">QA<span style="color:#57606a;font-weight:400;">Mill</span></span>
    <span style="font-size:13px;color:#57606a;float:right;padding-top:6px;">Mutation Analysis Report</span>
  </td></tr>
  <tr><td style="padding:0 28px 8px 28px;font-size:13px;color:#57606a;">
    <strong style="color:#24292f;font-family:Consolas,monospace;">{file_name}</strong>
    &nbsp;·&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')}
  </td></tr>
  <tr><td style="padding:16px 28px;text-align:center;">
    <div style="font-size:46px;font-weight:800;color:{gcolor};line-height:1;">{true_score}%</div>
    <div style="display:inline-block;margin-top:8px;padding:3px 14px;background:{gcolor};color:#fff;border-radius:20px;font-size:12px;font-weight:700;letter-spacing:.06em;">{grade}</div>
    <div style="font-size:14px;color:#24292f;margin-top:14px;">Your tests catch <strong>{killed}</strong> in <strong>{killed + survived}</strong> real bugs</div>
  </td></tr>
  <tr><td style="padding:8px 22px 20px 22px;">
    <table cellpadding="0" cellspacing="0" width="100%"><tr>
      {card(str(true_score) + '%', 'True Score', '#1f8f4e')}
      {card(str(raw_score) + '%', 'Raw Score', '#9a6700')}
      {card(killed, 'Killed', '#1a7f37')}
      {card(survived, 'Survived', '#cf222e')}
      {card(equivalent, 'Equivalent', '#9a6700')}
    </tr></table>
  </td></tr>
  <tr><td style="padding:4px 28px 24px 28px;">
    <table cellpadding="0" cellspacing="0" width="100%" style="background:#ddf4ff;border:1px solid #54aeff;border-radius:8px;"><tr>
      <td style="padding:14px 16px;font-size:13px;color:#0a3069;line-height:1.6;">
        📎 The full interactive report (operator breakdown, action plan, and all
        {survived} survived mutants) is <strong>attached as an HTML file</strong>.
        Download and open it in your browser.
      </td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:14px 28px;border-top:1px solid #d0d7de;font-size:11px;color:#8b949e;text-align:center;">
    Generated by QAMill · {total} mutations tested · AI-powered mutation testing
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


@app.post("/email")
async def email_report(req: EmailRequest):
    """Send analysis report. OAuth (Gmail/Graph) if connected, else SMTP."""
    if req.job_id not in _job_events:
        raise HTTPException(404, f"Job {req.job_id} not found")

    report_html = _build_html_report(req.job_id)          # full report → attachment
    start_ev    = next((e for e in _job_events[req.job_id] if e.get("type") == "start"), {})
    file_name   = start_ev.get("file", "unknown")
    summary     = _job_summaries.get(req.job_id, {})
    score       = summary.get("true_score", 0)
    subject     = f"QAMill Report — {file_name} — Score: {score}%"
    body_html   = _email_summary_html(file_name, summary)  # clean, inline-styled body
    plain = (
        f"QAMill Mutation Analysis Report\n"
        f"File      : {file_name}\n"
        f"True score: {score}%\n"
        f"Killed    : {summary.get('killed', 0)}\n"
        f"Survived  : {summary.get('survived', 0)}\n"
        f"Equivalent: {summary.get('equivalent', 0)}\n\n"
        f"The full interactive report is attached as an HTML file — open it in your browser."
    )
    ts       = datetime.now().strftime("%Y%m%d-%H%M%S")
    att_name = f"qamill-{Path(file_name).stem}-{ts}.html"

    # ── OAuth path first (no App Password) ─────────────────────────────────
    primary = auth.get_primary_identity()
    if primary and primary.get("can_email"):
        try:
            await auth.send_email_via_oauth(
                primary["provider"],
                to              = req.to_address,
                subject         = subject,
                text_body       = plain,
                html_body       = body_html,        # clean summary, not full report
                attachment_html = report_html,      # full report as attachment
                att_filename    = att_name,
            )
            return {"status": "sent", "to": req.to_address, "subject": subject,
                    "method": "oauth", "provider": primary["provider"]}
        except Exception as oauth_err:
            if not req.smtp_password:
                raise HTTPException(400, str(oauth_err))
            # else fall through to SMTP

    # ── SMTP path (clean body + full report attachment) ─────────────────────
    sender = req.sender_email or req.smtp_user
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = req.to_address
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain"))
    alt.attach(MIMEText(body_html, "html"))
    msg.attach(alt)
    att = MIMEBase("application", "octet-stream")
    att.set_payload(report_html.encode("utf-8"))
    encoders.encode_base64(att)
    att.add_header("Content-Disposition", f'attachment; filename="{att_name}"')
    msg.attach(att)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _smtp_send,
        req.smtp_host, req.smtp_port, req.smtp_user, req.smtp_password,
        sender, req.to_address, msg, req.use_tls,
    )
    return {"status": "sent", "to": req.to_address, "subject": subject, "method": "smtp"}


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
    """Send HTML report. Uses OAuth (Gmail/Graph) if connected, else SMTP."""
    ts          = datetime.now().strftime("%Y%m%d-%H%M%S")
    att_name    = f"qamill-report-{ts}.html"
    summary_html = (
        "<html><body style='font-family:sans-serif;padding:24px'>"
        "<h2 style='color:#3fb950'>QAMill Mutation Report</h2>"
        f"<pre style='background:#f6f8fa;padding:16px;border-radius:6px'>{req.message}</pre>"
        "<p style='color:#666;margin-top:16px'>See the attached HTML file for the full interactive report.</p>"
        "</body></html>"
    )

    # ── Try OAuth path first (no App Password needed) ──────────────────
    primary = auth.get_primary_identity()
    if primary and primary.get("can_email"):
        oauth_provider = primary["provider"]
        try:
            await auth.send_email_via_oauth(
                oauth_provider,
                to             = req.recipient,
                subject        = req.subject,
                text_body      = req.message,
                html_body      = summary_html,
                attachment_html= req.report_html,
                att_filename   = att_name,
            )
            return {"success": True,
                    "message": f"Report sent to {req.recipient} via {primary['label']}",
                    "method":  "oauth",
                    "provider": oauth_provider}
        except Exception as oauth_err:
            # OAuth failed — fall through to SMTP if credentials supplied
            if not req.app_password:
                raise HTTPException(400, str(oauth_err))

    # ── SMTP path (App Password) ───────────────────────────────────────
    provider_settings = {
        "gmail":   ("smtp.gmail.com",        587, True),
        "outlook": ("smtp-mail.outlook.com", 587, True),
    }
    if req.smtp_provider in provider_settings:
        host, port, use_tls = provider_settings[req.smtp_provider]
    else:
        host    = req.smtp_host or "localhost"
        port    = req.smtp_port or 587
        use_tls = True

    msg = MIMEMultipart("mixed")
    msg["Subject"] = req.subject
    msg["From"]    = req.sender_email
    msg["To"]      = req.recipient
    msg.attach(MIMEText(req.message, "plain"))
    msg.attach(MIMEText(summary_html, "html"))

    if req.report_html:
        att = MIMEBase("application", "octet-stream")
        att.set_payload(req.report_html.encode("utf-8"))
        encoders.encode_base64(att)
        att.add_header("Content-Disposition", f'attachment; filename="{att_name}"')
        msg.attach(att)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _smtp_send,
        host, port, req.sender_email, req.app_password,
        req.sender_email, req.recipient, msg, use_tls,
    )
    return {"success": True, "message": f"Report sent to {req.recipient}",
            "method": "smtp"}


# ── Auth endpoints ─────────────────────────────────────────────────────────

class LLMConnectRequest(BaseModel):
    provider: str
    api_key:  str = ""
    model:    str = ""  # Optional: user-selected model for this provider


class CustomProviderRequest(BaseModel):
    name: str
    api_endpoint: str
    api_key: str
    auth_type: str = "bearer"
    model: str = ""


class OAuthConfigRequest(BaseModel):
    client_id:     str
    client_secret: str


class SignUpRequest(BaseModel):
    email:    str
    password: str
    name:     str = ""


class SignInRequest(BaseModel):
    email:    str
    password: str


_PROVIDER_SETUP_URLS = {
    "google":    ("https://console.cloud.google.com/apis/credentials",
                  "Google Cloud Console", "Enable Gmail API, then create an OAuth 2.0 Client ID (Web application)."),
    "microsoft": ("https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps",
                  "Azure App Registrations", "Register a new app, set Web platform, add the redirect URI below."),
    "github":    ("https://github.com/settings/developers",
                  "GitHub Developer Settings", "Create an OAuth App with the callback URL below."),
    "linkedin":  ("https://www.linkedin.com/developers/apps",
                  "LinkedIn Developer Portal", "Create an app and add the redirect URL below under OAuth 2.0 settings."),
    "atlassian": ("https://developer.atlassian.com/console/myapps",
                  "Atlassian Developer Console", "Create an OAuth 2.0 (3LO) app and add the callback URL below."),
    "slack":     ("https://api.slack.com/apps",
                  "Slack API Console", "Create a new app, go to OAuth & Permissions and add the redirect URL below."),
}


def _auth_page(success: bool, message: str, provider: str = "") -> str:
    """HTML popup shown after OAuth callback — success self-closes, error shows setup help."""
    if success:
        color   = "#3fb950"
        heading = f"Connected to {provider.title()}!"
        body    = f"""<div class="icon">✓</div>
<h2>{heading}</h2>
<p style="color:#8b949e">{message}</p>
<p style="color:#484f58;font-size:12px">This window will close automatically…</p>
<button onclick="window.close()">Close</button>
<script>setTimeout(function(){{window.close();}},1400);</script>"""
    else:
        color   = "#f85149"
        setup   = _PROVIDER_SETUP_URLS.get(provider, ("", "", ""))
        cb_uri  = f"http://localhost:8765/auth/callback/{provider}" if provider else ""
        setup_hint = ""
        if setup[0]:
            setup_hint = f"""
<div class="setup-box">
  <div class="setup-title">How to set up {provider.title()} OAuth</div>
  <ol>
    <li>Open <a href="{setup[0]}" target="_blank">{setup[1]} ↗</a></li>
    <li>{setup[2]}</li>
    <li>Set this <strong>Redirect URI</strong>:<br>
        <code onclick="navigator.clipboard.writeText('{cb_uri}').then(function(){{this.style.color='#3fb950'}}.bind(this))">{cb_uri} <small>(click to copy)</small></code></li>
    <li>Copy the <strong>Client ID</strong> and <strong>Client Secret</strong></li>
    <li>Click the button below and paste them in</li>
  </ol>
  <button class="setup-btn" onclick="window.opener&&window.opener.openLoginModal&&window.opener.openLoginModal();window.close()">
    ← Enter credentials in QAMill
  </button>
</div>"""
        body = f"""<div class="icon">✗</div>
<h2>OAuth not configured</h2>
<p>{message}</p>
{setup_hint}
<button onclick="window.close()" style="margin-top:8px">Close</button>"""

    return f"""<!DOCTYPE html><html data-theme="dark">
<head><meta charset="UTF-8"><title>QAMill Auth</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#0d1117;color:#e6edf3;display:flex;align-items:center;
     justify-content:center;min-height:100vh;flex-direction:column;
     gap:12px;text-align:center;padding:28px}}
.icon{{font-size:52px;color:{color}}}
h2{{font-size:20px;font-weight:600;color:{color};margin-bottom:4px}}
p{{font-size:13px;color:#8b949e;max-width:360px;line-height:1.6}}
button{{padding:9px 24px;border-radius:6px;border:1px solid #30363d;
        background:#21262d;color:#e6edf3;cursor:pointer;font-size:13px}}
button:hover{{border-color:#3fb950;color:#3fb950}}
.setup-box{{background:#161b22;border:1px solid #30363d;border-radius:10px;
            padding:20px 24px;max-width:400px;text-align:left;margin-top:8px}}
.setup-title{{font-size:13px;font-weight:700;color:#c9d1d9;margin-bottom:12px}}
ol{{padding-left:18px;font-size:12px;color:#8b949e;line-height:2}}
ol a{{color:#58a6ff;text-decoration:none}}
ol a:hover{{text-decoration:underline}}
code{{display:inline-block;background:#21262d;border:1px solid #30363d;
      border-radius:4px;padding:4px 8px;font-size:11px;cursor:pointer;
      margin-top:4px;color:#4ec9a0;word-break:break-all}}
code:hover{{border-color:#4ec9a0}}
.setup-btn{{margin-top:16px;background:#3fb950;color:#0d1117;border:none;
            padding:9px 20px;border-radius:6px;font-size:13px;font-weight:600;
            cursor:pointer;width:100%}}
.setup-btn:hover{{opacity:.88}}
</style></head>
<body>{body}</body></html>"""


def _redirect_interstitial(provider: str, url: str) -> str:
    """Instant spinner page that JS-redirects to the provider — no blank white flash."""
    label = OAUTH_PROVIDERS.get(provider, {}).get("label", provider.title())
    safe  = url.replace("\\", "\\\\").replace('"', '\\"')
    return f"""<!DOCTYPE html><html data-theme="dark">
<head><meta charset="UTF-8"><title>Connecting to {label}…</title>
<meta http-equiv="refresh" content="0;url={url}">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#0d1117;color:#e6edf3;display:flex;align-items:center;
     justify-content:center;min-height:100vh;flex-direction:column;gap:18px}}
.spinner{{width:44px;height:44px;border:4px solid #21262d;border-top-color:#3fb950;
         border-radius:50%;animation:spin .8s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
p{{font-size:14px;color:#8b949e}}
strong{{color:#3fb950}}
a{{color:#58a6ff;font-size:12px}}
</style></head>
<body>
<div class="spinner"></div>
<p>Connecting to <strong>{label}</strong>…</p>
<a href="{url}">Click here if you are not redirected automatically</a>
<script>location.replace("{safe}");</script>
</body></html>"""


@app.get("/auth/login/{provider}")
async def auth_login(provider: str):
    """Show an instant interstitial, then redirect to the OAuth consent page."""
    from fastapi.responses import HTMLResponse
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {provider}")
    if not auth.provider_configured(provider):
        cfg = OAUTH_PROVIDERS[provider]
        page = _auth_page(False,
            f"OAuth is not configured for {cfg['label']}. "
            f"Set the {cfg['env_id']} and {cfg['env_secret']} environment variables "
            "on the QAMill backend and restart.", provider)
        return HTMLResponse(page)
    try:
        url = auth.get_authorization_url(provider)
        # Instant branded spinner instead of a blank white screen during redirect
        return HTMLResponse(_redirect_interstitial(provider, url))
    except Exception as e:
        return HTMLResponse(_auth_page(False, str(e), provider))


@app.get("/auth/callback/{provider}")
async def auth_callback(provider: str,
                         code:  Optional[str] = None,
                         state: Optional[str] = None,
                         error: Optional[str] = None,
                         error_description: Optional[str] = None):
    """Handle the OAuth redirect from the provider."""
    from fastapi.responses import HTMLResponse
    if error:
        return HTMLResponse(_auth_page(False,
            error_description or error, provider))
    if not code or not state:
        return HTMLResponse(_auth_page(False,
            "Missing authorization code — please try again.", provider))
    try:
        entry = await auth.handle_callback(provider, code, state)
        name  = entry.get("name") or entry.get("email") or provider
        return HTMLResponse(_auth_page(True, name, provider))
    except Exception as e:
        return HTMLResponse(_auth_page(False, str(e), provider))


@app.get("/login")
async def login_page():
    """Standalone, user-friendly login / sign-up page in the browser."""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(build_login_page())


@app.get("/auth/status")
async def auth_status():
    """Return all connected OAuth providers, LLM keys, and the signed-in user."""
    connected = auth.get_connected_llm_providers()
    return {
        "oauth":   auth.get_connected_providers(),
        "llm":     auth.get_all_llm_providers(),
        "connected_llm": [p["provider"] for p in connected],
        "active_llm": auth.get_active_llm(),
        "primary": auth.get_primary_identity(),
        "user":    auth.get_current_user(),
    }


# ── User accounts: sign up / sign in / sign out / current user ────────────

@app.post("/auth/signup")
async def auth_signup(req: SignUpRequest):
    """Create a QAMill account with email + password."""
    try:
        user = auth.sign_up(req.email, req.password, req.name)
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/auth/signin")
async def auth_signin(req: SignInRequest):
    """Sign in with email + password."""
    try:
        user = auth.sign_in(req.email, req.password)
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(401, str(e))


@app.post("/auth/signout")
async def auth_signout(everywhere: bool = False):
    """Sign out the current session. ?everywhere=true also disconnects OAuth tokens."""
    if everywhere:
        auth.sign_out_full()
    else:
        auth.sign_out()
    return {"success": True}


@app.get("/auth/me")
async def auth_me():
    """Return the currently signed-in user, or null."""
    return {"user": auth.get_current_user()}


@app.get("/auth/status/{provider}")
async def auth_status_provider(provider: str):
    """Return connection status for a single OAuth provider."""
    entry = auth.get_oauth_entry(provider)
    if not entry:
        return {"connected": False}
    return {"connected": True, "email": entry.get("email", ""),
            "name": entry.get("name", ""), "picture": entry.get("picture", "")}


@app.delete("/auth/logout/{provider}")
async def auth_logout(provider: str):
    auth.logout(provider)
    return {"success": True, "provider": provider}


@app.delete("/auth/logout-all")
async def auth_logout_all():
    auth.logout_all()
    return {"success": True}


@app.post("/auth/configure/{provider}")
async def auth_configure(provider: str, req: OAuthConfigRequest):
    """Store OAuth client_id + client_secret for a provider (no env var / restart needed)."""
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {provider}")
    if not req.client_id.strip() or not req.client_secret.strip():
        raise HTTPException(400, "Both client_id and client_secret are required")
    auth.store_oauth_client(provider, req.client_id, req.client_secret)
    return {"success": True, "provider": provider,
            "configured": True, "label": OAUTH_PROVIDERS[provider]["label"]}


@app.post("/auth/llm/validate")
async def auth_llm_validate(req: LLMConnectRequest):
    """Validate an LLM API key without storing it."""
    try:
        result = await auth.validate_and_store_llm_key(req.provider, req.api_key)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/auth/llm/connect")
async def auth_llm_connect(req: LLMConnectRequest):
    try:
        # Check if this is a custom provider
        data = auth._load()
        custom_providers = data.get("custom_llm", {})

        if req.provider in custom_providers:
            # For custom providers, just set as active (already validated during add)
            auth.set_active_llm(req.provider)
            return {"provider": req.provider, "label": custom_providers[req.provider].get("name"), "valid": True}
        else:
            # For built-in providers, validate and store the API key + model
            result = await auth.validate_and_store_llm_key(req.provider, req.api_key, req.model)
            # Set as active provider (only one at a time)
            auth.set_active_llm(req.provider)
            return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Server error: {str(e)}")


@app.post("/auth/llm/set-active")
async def auth_llm_set_active(req: LLMConnectRequest):
    """Set the active LLM provider."""
    auth.set_active_llm(req.provider)
    return {"success": True, "active": req.provider}


@app.post("/auth/llm/disconnect")
async def auth_llm_disconnect(req: LLMConnectRequest):
    """Disconnect an LLM provider."""
    auth.disconnect_llm(req.provider)
    return {"success": True, "provider": req.provider}


@app.get("/auth/llm/get-key/{provider}")
async def auth_llm_get_key(provider: str):
    """Get the stored API key for a provider."""
    key = auth.get_llm_key(provider)
    return {"provider": provider, "api_key": key or ""}


@app.get("/auth/llm/models/{provider}")
async def auth_llm_get_models(provider: str):
    """Get available models for a provider."""
    # Define available models per provider
    models = {
        "claude": [
            {"name": "claude-opus-4", "label": "Claude 4 Opus (latest)"},
            {"name": "claude-sonnet-4-5", "label": "Claude 4.5 Sonnet (recommended)"},
            {"name": "claude-haiku-4-5", "label": "Claude 4.5 Haiku (fast)"},
        ],
        "gpt": [
            {"name": "gpt-4o", "label": "GPT-4o (recommended)"},
            {"name": "gpt-4-turbo", "label": "GPT-4 Turbo"},
            {"name": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo (fast)"},
        ],
        "gemini": [
            {"name": "gemini-2.0-flash", "label": "Gemini 2.0 Flash (recommended - stable)"},
            {"name": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (fast)"},
            {"name": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (high quality)"},
            {"name": "gemini-3.5-flash", "label": "Gemini 3.5 Flash (latest - may be busy)"},
            {"name": "gemini-flash-latest", "label": "Gemini Flash (always latest)"},
            {"name": "gemini-pro-latest", "label": "Gemini Pro (always latest)"},
        ],
        "openrouter": [
            {"name": "auto", "label": "Auto (best value)"},
            {"name": "gpt-4o", "label": "GPT-4o via OpenRouter"},
            {"name": "claude-3-opus", "label": "Claude 3 Opus via OpenRouter"},
        ],
        "deepseek": [
            {"name": "deepseek-chat", "label": "DeepSeek Chat (recommended)"},
            {"name": "deepseek-coder", "label": "DeepSeek Coder"},
        ],
        "mistral": [
            {"name": "mistral-large-latest", "label": "Mistral Large (recommended)"},
            {"name": "mistral-medium-latest", "label": "Mistral Medium"},
            {"name": "mistral-small-latest", "label": "Mistral Small (fast)"},
        ],
        "grok": [
            {"name": "grok-3", "label": "Grok 3 (recommended)"},
            {"name": "grok-2", "label": "Grok 2"},
        ],
        "ollama": [
            {"name": "llama3", "label": "Llama 3 (default)"},
            {"name": "llama2", "label": "Llama 2"},
            {"name": "mistral", "label": "Mistral (local)"},
            {"name": "neural-chat", "label": "Neural Chat"},
        ],
    }
    provider_models = models.get(provider, [])
    stored_model = auth.get_llm_model(provider)
    return {
        "provider": provider,
        "models": provider_models,
        "stored_model": stored_model,
        "default_model": provider_models[0]["name"] if provider_models else ""
    }


@app.post("/auth/llm/custom/add")
async def auth_llm_custom_add(req: CustomProviderRequest):
    """Add a custom LLM provider."""
    try:
        if not req.name or not req.name.strip():
            raise ValueError("Provider name is required")
        if not req.api_endpoint or not req.api_endpoint.strip():
            raise ValueError("API endpoint is required")
        if not req.api_key or not req.api_key.strip():
            raise ValueError("API key is required")

        config = {
            "api_endpoint": req.api_endpoint.strip(),
            "auth_type": req.auth_type,
            "model": req.model.strip() if req.model else "",
            "api_key": req.api_key.strip(),
        }
        result = auth.add_custom_provider(req.name.strip(), config)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/auth/llm/custom/{provider_id}")
async def auth_llm_custom_delete(provider_id: str):
    """Delete a custom LLM provider."""
    auth.delete_custom_provider(provider_id)
    return {"success": True, "provider_id": provider_id}


@app.get("/auth/providers")
async def auth_providers_list():
    """Return all provider configs (without secrets) for the UI."""
    oauth_list = [
        {
            "id":           p,
            "label":        cfg["label"],
            "group":        cfg.get("group", "social"),
            "color":        cfg["color"],
            "bg":           cfg["bg"],
            "text":         cfg.get("text", "#fff"),
            "can_email":    cfg.get("can_email", False),
            "configured":   auth.provider_configured(p),
        }
        for p, cfg in OAUTH_PROVIDERS.items()
    ]
    llm_list = [
        {
            "id":          p,
            "label":       cfg["label"],
            "sublabel":    cfg["sublabel"],
            "color":       cfg["color"],
            "bg":          cfg["bg"],
            "placeholder": cfg["key_placeholder"],
        }
        for p, cfg in LLM_PROVIDERS.items()
    ]
    return {"oauth": oauth_list, "llm": llm_list}


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
