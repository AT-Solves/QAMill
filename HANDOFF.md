# QAMill — Session Handoff

Pick-up notes for continuing this work in another Claude Code session (this machine, web, or after a restart). Last updated: 2026-06-15.

## What QAMill is
AI-powered mutation testing tool. FastAPI backend (`backend/`, port 8765) runs a 17-operator mutation engine, streams results over SSE, and generates a self-contained elite HTML report. A VS Code extension (`vscode-extension/`) drives it and shows a live dashboard.

## What was built/changed in recent sessions

### 1. Elite HTML report — `backend/report_generator.py`
- Single self-contained HTML (CSS + JS inline), ~200KB. 10 sections: header, health-badge ring, score cards, "What this means", operator coverage, action plan, survived-mutant table (search/filter/sort), killed section, equivalent explainer, footer.
- Auto-saved to `{project_root}/qamill-reports/` on analysis complete.
- Demo: `python report_generator.py <out.html>` → writes a demo using fixed math_utils.py data (445 mutants, 81.3% true score).

### 2. Authentication — `backend/auth_manager.py` (+ `/auth/*` in `main.py`)
- OAuth 2.0 PKCE for **Google, Microsoft, LinkedIn, GitHub, Atlassian, Slack** + LLM key validation (Claude, GPT-4o, Grok, Ollama).
- Tokens stored in `~/.qamill/auth.json`, locked to current user (`_secure_file()` uses `icacls` on Windows, `chmod 600` on Unix).
- OAuth client credentials resolve **env var first, then stored config**. Env vars: `QAMILL_<PROVIDER>_CLIENT_ID` / `_CLIENT_SECRET`.
- Endpoints: `/auth/login/{provider}`, `/auth/callback/{provider}`, `/auth/status`, `/auth/configure/{provider}` (store client id+secret at runtime, no restart), `/auth/llm/connect`, `/auth/logout/{provider}`, `/auth/providers`.
- Email reports send via Gmail/Graph API when Google/Microsoft connected (no App Password); SMTP is the fallback.

### 3. Elite auth popup
- In `report_generator.py` (`_build_login_modal`) and mirrored in the VS Code dashboard.
- Provider rows are **statically rendered in Python** (no skeleton/async-render bug). JS `amUpdateStatus()` only flips Connect↔Disconnect state.
- Unconfigured providers show a **Setup** button → in-modal panel with console link, step-by-step instructions, copy-able redirect URI, and client-id/secret inputs → `/auth/configure`.
- Email modal is OAuth-first: shows "Sending via Google" when connected, else CTA + SMTP fallback.

### 4. Bug fixes
- `/ask` endpoint no longer 500s when provider=none or LLM unreachable — returns friendly messages.
- VS Code extension AggregateError fix: all Node HTTP calls pinned to `127.0.0.1` via `ipv4()` helper (backend binds IPv4 only; `localhost` → `::1` race caused AggregateError when backend was down/starting). Friendly "still starting, click Retry" error.

## Current state (2026-06-15)
- Google OAuth **configured and live**: client id `368898033418-qvb0stbgma8...` set via User-scope env vars (`setx`). `/auth/login/google` returns 307 → accounts.google.com with PKCE.
- **Action still needed by user**: add `http://localhost:8765/auth/callback/google` to Authorized redirect URIs in Google Cloud Console, or login returns `redirect_uri_mismatch`.

## How to run
```powershell
# Backend (normally the VS Code extension spawns this automatically):
cd backend; python main.py            # binds 127.0.0.1:8765
# Extension build:
cd vscode-extension; npx tsc -p ./    # outputs out/extension.js
```
Note: User-scope env vars (`setx`) only reach the backend when launched by a **freshly-spawned** process (e.g. the VS Code extension). A shell started before `setx` won't have them — inject via `[Environment]::GetEnvironmentVariable(name,"User")` if launching manually.

## Key files
- `backend/main.py` — FastAPI app, all endpoints, SSE, email
- `backend/auth_manager.py` — OAuth + LLM key manager
- `backend/report_generator.py` — elite HTML report + auth/email modals
- `backend/mutation_engine.py` — 17 mutation operators
- `vscode-extension/src/extension.ts` — extension + inlined dashboard HTML
- `sample_project/` — math_utils.py demo target
