# QAMill — AI QA Governance Platform

**Complete test quality intelligence for Python projects.** Mutation testing, test gap analysis, auto-healing tests, and AI-powered test generation — all in your IDE.

## What is QAMill?

QAMill is an enterprise-grade **QA Governance Platform** that transforms how teams measure and improve test quality. Instead of guessing whether your tests are catching real bugs, QAMill **mutates your code** to find gaps, **analyzes coverage deeply**, and **auto-heals weak tests** using AI.

### Core Capabilities

#### 🧬 **Mutation Testing & Test Quality Analysis**
- **Intelligent mutation engine** with 17+ operators (arithmetic, logic, boundary, string, list mutations)
- **Equivalent mutant detection** — filters out noise that doesn't matter
- **Survived mutant identification** — shows exactly which code changes your tests *don't* catch
- **Auto-healing** — AI writes new tests to kill survived mutants
- **Live dashboard** — real-time mutation analysis with elite scoring and insights

#### 🎯 **Test Authoring & Generation**
- **Unit test generation** — AI writes complete pytest suites with edge cases
- **BDD test authoring** — Gherkin scenarios for behavior-driven development
- **Manual QA test cases** — structured test suites for QA teams
- **Traceability matrices** — requirements → test case mapping for compliance
- **Multi-format output** — pytest, plain text, markdown tables, Gherkin, JSON

#### 📊 **Live Analytics & Reporting**
- **Elite HTML reports** — self-contained dashboards with zero external dependencies
- **Test quality scoring** — mutation score, coverage, test effectiveness
- **Performance graphs** — mutation phase breakdown, analysis speed insights
- **Email reports** — OAuth-powered (Gmail, Office 365, custom SMTP)
- **Detailed mutant tables** — searchable, sortable, with side-by-side diffs

#### 🔐 **Enterprise Authentication**
- **OAuth 2.0 PKCE** for Google, Microsoft, GitHub, LinkedIn, Atlassian, Slack
- **Email + password accounts** — local account creation with scrypt hashing
- **Session management** — 30-day TTL, HMAC-signed tokens
- **Identity tracking** — synchronized across both dashboards

#### 🤖 **AI Integration**
- **Claude (Anthropic)** — most capable, recommended
- **GPT-4o (OpenAI)** — fast, excellent quality
- **Grok (xAI)** — cutting-edge reasoning
- **Ollama (local)** — private, fully offline
- **Multi-LLM support** — switch providers per task

---

## Quick Start

### 1. **Analyze Test Quality**
```
Right-click any .py file → "QAMill: Analyze Test Quality"
```
- Mutations are generated and tested in real-time
- Dashboard streams results as they complete
- Live mutation counter, phase breakdown, survived mutants table
- One-click email report or save as HTML

### 2. **Generate Tests**
```
Right-click any .py file → "QAMill: Open Test Authoring Studio"
```
Choose format:
- **Unit Tests (pytest)** — complete suite with validation
- **Test Case Format** — detailed manual cases (ID, preconditions, steps, expected)
- **Table Format** — compact markdown for reviews
- **Gherkin (BDD)** — Given/When/Then scenarios
- **Traceability Matrix** — requirements mapping

AI writes tests, you review and save.

### 3. **Select AI Provider**
```
Ctrl+Shift+P → "QAMill: Select AI Model"
```
Pick Claude, GPT-4o, Grok, or local Ollama.

### 4. **Sign In with QAMill**
```
Click "Sign in" in dashboard or Test Studio header
```
- OAuth: Google, Microsoft, GitHub, LinkedIn, Atlassian, Slack
- Email/password: create a local account
- Identity syncs across both dashboards
- Reports sent from your connected account

---

## Features in Detail

### Test Quality Metrics
- **Mutation Score** — % of mutants killed by your tests
- **Coverage Analysis** — code execution coverage + mutation coverage
- **Equivalent Mutants** — AI-detected mutations that don't matter
- **Survived Mutants** — code changes your tests missed
- **Test Weakness Map** — function-by-function breakdown

### Auto-Healing Workflow
1. Run analysis → identify survived mutants
2. Select mutant → AI writes a test to kill it
3. Test verified against original code
4. Copy to your test suite (one-click save)

### Report Types
- **HTML Elite Report** — 200KB self-contained, 10+ sections
- **Email Summary** — clean card layout, full report as attachment
- **Markdown Export** — CI/CD pipeline friendly
- **JSON** — programmatic access to all metrics

### Dashboard Panels

| Panel | Purpose |
|-------|---------|
| **Mutant Results** | Real-time streaming, searchable table, line diffs |
| **Suggested Tests** | AI-generated tests for survived mutants |
| **QAMill Assistant** | Ask questions about your results ("worst survived mutant?") |
| **Output Terminal** | Job progress, phase breakdown, logs |

---

## Technical Details

### Architecture
- **Backend:** FastAPI (Python) on port 8765
- **Frontend:** VS Code webview + standalone HTML
- **LLM Pipeline:** Async prompt streaming with retry logic
- **Mutation Engine:** AST-based mutation with incremental generation
- **Report Generation:** Self-contained HTML (no CDN, fully offline)
- **Auth:** OAuth 2.0 PKCE + local session tokens (HMAC-SHA256)

### Supported Languages
- Python 3.8+ (primary)
- Extensible to JavaScript, Java, Go (roadmap)

### Performance
- Incremental mutation generation (don't re-mutate unchanged code)
- Streaming results (mutations appear as they're tested)
- Parallel test execution (pytest-xdist ready)
- Equivalent mutant filtering (AI-powered, reduces noise 30-50%)

### Data & Privacy
- All auth tokens stored locally (`~/.qamill/auth.json`, user-locked)
- OAuth tokens never logged
- Reports can be emailed or saved locally
- Ollama mode = fully offline, zero cloud calls

---

## Use Cases

### 1. **Test Quality Gates (CI/CD)**
```bash
qamill analyze src/mymodule.py --threshold 80
```
Fail the build if mutation score < 80%.

### 2. **Legacy Code Testing**
- Run QAMill on old modules
- Auto-heal weak tests
- Gradually improve coverage

### 3. **Code Review Checkpoints**
- Reviewer runs QAMill on PR
- "Does this PR's test suite catch the changes?"
- Comments on survived mutants

### 4. **Test Authoring (Zero to Hero)**
- New function written
- QAMill generates unit tests
- Review + integrate in 5 minutes

### 5. **Compliance & Traceability**
- Generate traceability matrix
- Map requirements → test cases
- Export for audits

---

## Configuration

Open VS Code Settings (`Ctrl+,`), search `qamill`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `amil.llmProvider` | `inhouse` | Claude / GPT-4o / Grok / Ollama |
| `amil.anthropicApiKey` | — | Claude API key |
| `amil.openaiApiKey` | — | OpenAI API key |
| `amil.xaiApiKey` | — | Grok API key |
| `amil.ollamaModel` | `llama3` | Local Ollama model |
| `amil.autoHeal` | `true` | Auto-generate tests for mutants |
| `amil.detectEquivalents` | `true` | Filter equivalent mutants |
| `amil.backendPort` | `8765` | Backend API port |
| `amil.email.provider` | `gmail` | SMTP provider (gmail/outlook/custom) |

---

## Keyboard Shortcuts

| Command | Shortcut |
|---------|----------|
| Analyze Test Quality | Right-click `.py` file |
| Open Test Studio | Right-click `.py` file |
| Select AI Model | `Ctrl+Shift+P` → "QAMill: Select AI Model" |
| Reload Dashboard | `Ctrl+Shift+P` → "Developer: Reload Window" |

---

## Pro Tips

✨ **For Best Results:**
- Use **Claude** for test generation (most reliable)
- Run **Analyze** on small modules first (< 1000 LOC)
- Review **auto-healed tests** before committing (verify they're correct)
- Export **HTML reports** for stakeholders (zero dependencies, professional)
- Set **mutation threshold** in CI to enforce quality gates

🚀 **Getting Started:**
1. Right-click a test file → "Analyze Test Quality"
2. Watch the live dashboard stream results
3. Click a survived mutant → see what your tests missed
4. Open "Test Studio" → generate a test to cover it
5. Save the new test to your suite

---

## Support & Feedback

- **Issues?** Check the VS Code extension details tab
- **Questions?** Run "QAMill AI Assistant" in the dashboard
- **Feedback?** We read every report — help us improve

---

**QAMill: Because Great Tests Don't Guess.**

*Powered by AI. Owned by You. Zero Cloud Lock-in.*
