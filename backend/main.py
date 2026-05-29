"""
main.py
FastAPI backend — runs locally on port 8765.
Streams real-time mutation results via Server-Sent Events.
VS Code extension and browser dashboard both connect to this.
"""
import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mutation_engine import MutationEngine
from equivalent_detector import EquivalentDetector
from test_runner import TestRunner
from auto_healer import AutoHealer
from llm_adapter import create_adapter
from cross_method_mutator import CrossMethodMutator
from ai_mutant_generator import AIMutantGenerator
from llm_adapter import NoLLMAdapter

app = FastAPI(title="AMIL Mutation Testing Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active jobs: job_id → asyncio.Queue of SSE event dicts
_jobs: dict[str, asyncio.Queue] = {}
_job_summaries: dict[str, dict] = {}


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


class JobResponse(BaseModel):
    job_id: str
    stream_url: str


class AskRequest(BaseModel):
    prompt: str
    context: str
    llm_provider: str = "none"
    llm_api_key: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────

def _emit(queue: asyncio.Queue, event_type: str, data: dict):
    """Push a typed SSE event onto the queue."""
    asyncio.get_event_loop().call_soon_threadsafe(
        queue.put_nowait, {"type": event_type, **data}
    )


# ── Core analysis pipeline ─────────────────────────────────────────────────

async def _run_analysis(job_id: str, queue: asyncio.Queue, req: AnalyzeRequest):
    try:
        # Build components
        kwargs = {}
        if req.llm_api_key:
            kwargs["api_key"] = req.llm_api_key
        if req.llm_model:
            kwargs["model"] = req.llm_model

        llm = create_adapter(req.llm_provider, **kwargs)
        detector = EquivalentDetector(llm_adapter=llm if req.detect_equivalents else None)
        runner = TestRunner(req.project_root, req.test_command)
        healer = AutoHealer(llm, req.project_root) if req.auto_heal else None
        engine = MutationEngine()
        cm_engine = CrossMethodMutator()
        ai_engine = AIMutantGenerator()

        # ── Baseline check ──
        await queue.put({"type": "status", "message": "Running baseline tests..."})
        baseline_ok = await runner.run_baseline()
        if not baseline_ok:
            await queue.put({
                "type": "error",
                "message": "Baseline tests FAILED. Fix your tests before running QAMill."
            })
            return

        # ── Generate mutants ──
        await queue.put({"type": "status", "message": "Generating mutants..."})
        ast_mutants = engine.generate_mutants(req.file_path)
        cm_mutants = cm_engine.generate_mutants(req.file_path)
        ast_count = len(ast_mutants) + len(cm_mutants)

        ai_count = 0
        ai_generated: list = []
        if req.ai_mutants and not isinstance(llm, NoLLMAdapter):
            await queue.put({"type": "status", "message": "Generating AI semantic mutants..."})
            ai_generated = await ai_engine.generate(req.file_path, llm)
            ai_count = len(ai_generated)

        mutants = ast_mutants + cm_mutants + ai_generated
        total = len(mutants)
        cross_method_count = len(cm_mutants)

        await queue.put({
            "type": "start",
            "total": total,
            "file": Path(req.file_path).name,
            "llm_provider": llm.name,
            "ast_mutant_count": ast_count,
            "ai_mutant_count": ai_count,
            "cross_method_count": cross_method_count,
        })

        if total == 0:
            await queue.put({"type": "complete",
                             "message": "No mutants generated. Add more logic to your code."})
            return

        # ── Per-mutant pipeline ──
        killed = survived = equivalent = errors = 0

        for i, mutant in enumerate(mutants, 1):
            # ── Step A: Equivalence check ──
            equiv_result = await detector.classify(mutant.original_src, mutant.mutant_src)

            if equiv_result.equivalent:
                mutant.status = "equivalent"
                mutant.equivalent_reason = equiv_result.reason
                equivalent += 1
                await queue.put({
                    "type": "mutant_result",
                    "index": i, "total": total,
                    "mutant_id": mutant.id,
                    "function": mutant.function_name,
                    "line": mutant.line_no,
                    "operator": mutant.operator,
                    "description": mutant.description,
                    "status": "equivalent",
                    "reason": equiv_result.reason,
                    "method": equiv_result.method,
                    "killed": killed, "survived": survived,
                    "equivalent": equivalent, "errors": errors,
                    "true_score": _score(killed, survived),
                    "raw_score": _raw_score(killed, survived, equivalent),
                })
                continue

            # ── Step B: Run tests ──
            result = await runner.run_mutant(mutant)
            mutant.status = result

            if result == "killed":
                killed += 1
            elif result == "survived":
                survived += 1
            else:
                errors += 1

            heal_result = None
            diff_result = None
            explanation = None

            # ── Step C: Rank difficulty + explain + auto-heal survived mutants ──
            if result == "survived" and healer:
                diff_result = await healer.rank_difficulty(mutant)
                mutant.difficulty = diff_result["difficulty"]
                mutant.difficulty_reason = diff_result["reason"]

                if llm.name != "none":
                    explanation = await healer.explain(mutant)
                    await queue.put({
                        "type": "healing",
                        "mutant_id": mutant.id,
                        "message": f"Writing test to kill {mutant.id}..."
                    })
                    heal_result = await healer.heal(mutant)
                    mutant.suggested_test = heal_result.test_code

            await queue.put({
                "type": "mutant_result",
                "index": i, "total": total,
                "mutant_id": mutant.id,
                "function": mutant.function_name,
                "line": mutant.line_no,
                "operator": mutant.operator,
                "description": mutant.description,
                "status": result,
                "killed": killed, "survived": survived,
                "equivalent": equivalent, "errors": errors,
                "true_score": _score(killed, survived),
                "raw_score": _raw_score(killed, survived, equivalent),
                "suggested_test": heal_result.test_code if heal_result else None,
                "test_verified": heal_result.verified if heal_result else None,
                "difficulty": mutant.difficulty,
                "difficulty_reason": mutant.difficulty_reason,
                "explanation": explanation,
            })

        # ── Final summary ──
        summary = {
            "type": "complete",
            "total": total,
            "killed": killed,
            "survived": survived,
            "equivalent": equivalent,
            "errors": errors,
            "true_score": _score(killed, survived),
            "raw_score": _raw_score(killed, survived, equivalent),
            "llm_provider": llm.name,
        }
        _job_summaries[job_id] = summary
        await queue.put(summary)

    except Exception as e:
        await queue.put({"type": "error", "message": str(e)})


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
    queue: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = queue

    asyncio.create_task(_run_analysis(job_id, queue, req))

    return JobResponse(
        job_id=job_id,
        stream_url=f"http://localhost:8765/stream/{job_id}"
    )


@app.get("/stream/{job_id}")
async def stream_results(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, f"Job {job_id} not found")

    queue = _jobs[job_id]

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"ping\"}\n\n"

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


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
