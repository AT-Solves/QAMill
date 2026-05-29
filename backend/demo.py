"""
demo.py — QAMill command-line demo runner.

Starts the backend server, triggers analysis on sample_project/math_utils.py,
streams and prints results, then shuts the server down.

Usage examples:
  python demo.py
  python demo.py --llm claude --key sk-ant-xxx --heal --ai
  python demo.py --llm gpt    --key sk-xxx     --heal
  python demo.py --llm inhouse                 --ai
"""
import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx


BASE_URL = "http://localhost:8765"
SAMPLE_FILE = str(Path(__file__).parent.parent / "sample_project" / "math_utils.py")
SAMPLE_ROOT = str(Path(__file__).parent.parent / "sample_project")

STATUS_ICONS = {
    "killed":     "[KILLED    ]",
    "survived":   "[SURVIVED  ]",
    "equivalent": "[EQUIVALENT]",
    "error":      "[ERROR     ]",
}


def parse_args():
    p = argparse.ArgumentParser(description="QAMill demo runner")
    p.add_argument("--llm",  default="none",  help="LLM provider: none|claude|gpt|grok|inhouse")
    p.add_argument("--key",  default="",      help="API key for the chosen LLM provider")
    p.add_argument("--heal", action="store_true", help="Enable auto-healing of survived mutants")
    p.add_argument("--ai",   action="store_true", help="Enable AI semantic mutant generation")
    p.add_argument("--port", default=8765,    type=int, help="Backend port (default 8765)")
    return p.parse_args()


def start_server(port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["CURL_CA_BUNDLE"] = (
        str(Path.home() / "AppData/Roaming/Python/Python313/site-packages/certifi/cacert.pem")
    )
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(Path(__file__).parent),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def wait_for_server(port: int, timeout: int = 15) -> bool:
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


async def run_demo(args):
    port = args.port
    print(f"\nStarting QAMill backend on port {port}...")
    server = start_server(port)

    if not wait_for_server(port):
        print("ERROR: Backend failed to start within 15 seconds.")
        server.terminate()
        sys.exit(1)
    print("Backend ready.\n")

    payload = {
        "file_path":         SAMPLE_FILE,
        "project_root":      SAMPLE_ROOT,
        "llm_provider":      args.llm,
        "llm_api_key":       args.key or None,
        "auto_heal":         args.heal,
        "detect_equivalents": True,
        "ai_mutants":        args.ai,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"http://localhost:{port}/analyze", json=payload)
        r.raise_for_status()
        job = r.json()
        stream_url = job["stream_url"]
        print(f"Analysis started (job {job['job_id'][:8]}...)\n")

    # Stream results
    total = killed = survived = equivalent = errors = ast_c = ai_c = 0
    true_score = raw_score = 0.0

    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("GET", stream_url) as resp:
            async for raw_line in resp.aiter_lines():
                raw_line = raw_line.strip()
                if not raw_line.startswith("data:"):
                    continue
                e = json.loads(raw_line[5:])
                t = e.get("type")

                if t == "status":
                    print(f"  ... {e['message']}")

                elif t == "start":
                    total = e.get("total", 0)
                    ast_c = e.get("ast_mutant_count", total)
                    ai_c  = e.get("ai_mutant_count", 0)
                    ai_note = f" + {ai_c} AI" if ai_c else ""
                    print(f"Mutants: {ast_c} AST{ai_note} = {total} total\n")

                elif t == "mutant_result":
                    status = e.get("status", "error")
                    icon   = STATUS_ICONS.get(status, "[?????????]")
                    fn     = e.get("function", "?")
                    desc   = e.get("description", "")
                    mid    = e.get("mutant_id", "?")
                    op     = e.get("operator", "")
                    ai_tag = " [AI]" if op == "AI" else ""
                    desc_safe = desc.replace("→", "->").replace("↔", "<->")
                    print(f"  {icon}  {mid} | {fn} | {desc_safe}{ai_tag}")
                    if status == "killed":     killed += 1
                    elif status == "survived": survived += 1
                    elif status == "equivalent": equivalent += 1
                    else:                      errors += 1

                elif t == "complete":
                    true_score = e.get("true_score", 0.0)
                    raw_score  = e.get("raw_score", 0.0)
                    break

                elif t == "error":
                    print(f"\nERROR: {e.get('message')}")
                    break

    # Final summary
    print("\n" + "=" * 48)
    print("  QAMill Analysis Complete")
    print("=" * 48)
    print(f"  Total mutants  : {total}")
    print(f"  AST mutants    : {ast_c}")
    print(f"  AI mutants     : {ai_c}")
    print(f"  Killed         : {killed}")
    print(f"  Survived       : {survived}")
    print(f"  Equivalent     : {equivalent}")
    print(f"  Errors         : {errors}")
    print(f"  True Score     : {true_score}%")
    print(f"  Raw Score      : {raw_score}%")
    print("=" * 48 + "\n")

    server.terminate()
    server.wait()
    print("Server stopped.")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_demo(args))
