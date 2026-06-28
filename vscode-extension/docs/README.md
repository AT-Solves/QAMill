# QAMill — AI QA Governance Platform

**Enterprise-grade QA governance with AI-powered test quality intelligence.** Comprehensive test analysis, coverage mapping, auto-healing tests, and automated test generation — all in your IDE.

## What is QAMill?

QAMill is a **complete QA Governance Platform** that empowers teams to establish and maintain test excellence standards. It provides comprehensive test quality metrics, intelligent test gap identification, AI-powered test generation, and automated test improvement — transforming manual QA processes into data-driven governance.

### Core QA Governance Capabilities

#### 📊 **Complete Test Quality Governance**
- **Test quality intelligence** — understand exactly what your tests are catching
- **Coverage analysis** — both code execution and mutation coverage metrics
- **Test effectiveness scoring** — comprehensive metrics for test suite health
- **Test weakness mapping** — identify which code areas lack sufficient testing
- **Compliance reporting** — traceability matrices for regulated environments
- **Real-time dashboards** — live test quality metrics and insights

#### 🧬 **Intelligent Test Quality Analysis**
- **Advanced mutation engine** — 17+ mutation operators (arithmetic, logic, boundary, string, list operations)
- **Survived mutant detection** — pinpoint exactly which code variations your tests miss
- **Equivalent mutant filtering** — eliminate noise for accurate quality metrics
- **Automated test gap fixing** — AI-powered test generation to eliminate quality gaps
- **Real-time streaming** — live mutation analysis with progress tracking and detailed insights

#### 🎯 **Test Authoring & Generation**
- **Unit test generation** — AI writes complete pytest suites with edge cases
- **BDD test authoring** — Gherkin scenarios for behavior-driven development
- **Manual QA test cases** — structured test suites for QA teams
- **Traceability matrices** — requirements → test case mapping for compliance
- **Multi-format output** — pytest, plain text, markdown tables, Gherkin, JSON

#### 📈 **Elite Analytics & Reporting**
- **Elite HTML reports** — self-contained dashboards with zero external dependencies
- **Test quality scoring** — comprehensive test effectiveness metrics
- **Performance analytics** — phase breakdown, analysis speed, trend analysis
- **Email distribution** — OAuth-powered (Gmail, Office 365, custom SMTP)
- **Executive dashboards** — high-level QA governance metrics

#### 🔐 **Enterprise Features**
- **OAuth 2.0 PKCE** — Google, Microsoft, GitHub, LinkedIn, Atlassian, Slack authentication
- **Email + password accounts** — local account creation with enterprise security
- **Session management** — 30-day TTL, HMAC-signed tokens
- **Identity & role tracking** — synchronized across all dashboards
- **Team collaboration** — shared reports and metrics

#### 🤖 **Multi-Provider AI Engine** 
**8 world-class LLM providers with instant switching:**
- **Claude (Anthropic)** — most capable for complex analysis and edge cases
- **GPT-4o (OpenAI)** — fast, reliable, industry-standard quality
- **Gemini (Google)** — advanced reasoning with latest capabilities
- **Grok (xAI)** — cutting-edge reasoning for complex test scenarios
- **OpenRouter** — access to 200+ models with load balancing
- **DeepSeek** — cost-effective high-quality reasoning
- **Mistral** — European AI with excellent performance
- **Ollama (Local)** — 100% private, fully offline, zero cloud dependency

**Smart provider management:** Connect multiple providers, select by task, automatic fallback to local Ollama if cloud provider unavailable

---

## Quick Start

### 1. **Analyze Test Quality & Coverage**
```
Right-click any .py file → "QAMill: Analyze Test Quality"
```
- Comprehensive test quality analysis with mutation-based insights
- Dashboard streams real-time results
- Live metrics: coverage, test effectiveness, quality score
- One-click email report or save as HTML

### 2. **Generate Missing Tests**
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

### 4. **Sign In for Full Governance**
```
Click "Sign in" in dashboard or Test Studio header
```
- OAuth: Google, Microsoft, GitHub, LinkedIn, Atlassian, Slack
- Email/password: create a local account
- Identity syncs across all dashboards
- Reports sent from your connected account

---

## Features in Detail

### QA Governance Metrics
- **Test Quality Score** — overall test suite health and effectiveness
- **Code Coverage** — % of code lines executed by tests
- **Mutation Coverage** — % of code behavior changes caught by tests
- **Test Weakness Areas** — functions/modules needing stronger tests
- **Compliance Readiness** — traceability and documentation metrics
- **Trend Analysis** — test quality improvement over time

### Test Auto-Healing Workflow
1. Run quality analysis → identify test gaps
2. AI suggests improvements → generates test code
3. Tests verified against original code
4. Copy to your test suite (one-click save)

### Report Types
- **HTML Elite Report** — 200KB self-contained, 10+ sections
- **Email Summary** — clean card layout, full report as attachment
- **Markdown Export** — CI/CD pipeline friendly
- **JSON** — programmatic access to all metrics

### Dashboard Panels

| Panel | Purpose |
|-------|---------|
| **Test Quality Analysis** | Real-time quality metrics, coverage, effectiveness |
| **Test Gap Identification** | AI-suggested tests for uncovered scenarios |
| **QAMill Assistant** | Ask questions about test quality ("worst test gap?") |
| **Output Terminal** | Job progress, analysis phases, logs |

---

## Technical Details

### Architecture
- **Backend:** FastAPI (Python) on port 8765
- **Frontend:** VS Code webview + standalone HTML
- **LLM Pipeline:** Async prompt streaming with retry logic
- **Analysis Engine:** AST-based code analysis with incremental processing
- **Report Generation:** Self-contained HTML (no CDN, fully offline)
- **Auth:** OAuth 2.0 PKCE + local session tokens (HMAC-SHA256)

### Supported Languages
- Python 3.8+ (primary)
- Extensible to JavaScript, Java, Go (roadmap)

### Performance
- Incremental analysis (don't re-analyze unchanged code)
- Streaming results (insights appear as they're computed)
- Parallel test execution (pytest-xdist ready)
- Smart analysis optimization (reduce noise 30-50%)

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
Enforce test quality standards in your build pipeline.

### 2. **Legacy Code Testing**
- Run QAMill on old modules
- Identify test gaps systematically
- Auto-generate missing tests
- Gradually improve coverage

### 3. **Code Review & Quality Assurance**
- Reviewer runs QAMill on PR
- "Are tests adequate for these changes?"
- Comments on test gaps with suggestions

### 4. **Test Authoring (Zero to Complete)**
- New function written
- QAMill generates comprehensive tests
- Review + integrate in 5 minutes

### 5. **Compliance & Traceability**
- Generate traceability matrix
- Map requirements → test cases
- Export for audits and compliance reports

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
| `amil.autoHeal` | `true` | Auto-generate tests for gaps |
| `amil.detectEquivalents` | `true` | Smart analysis filtering |
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
- Run **Quality Analysis** on small modules first (< 1000 LOC)
- Review **auto-generated tests** before committing (verify they're correct)
- Export **HTML reports** for stakeholders (zero dependencies, professional)
- Set **quality threshold** in CI to enforce governance standards

🚀 **Getting Started:**
1. Right-click a test file → "Analyze Test Quality"
2. Watch the live dashboard show quality metrics
3. Click on gaps → see what your tests missed
4. Open "Test Studio" → generate tests to cover gaps
5. Save the new tests to your suite

---

## Support & Feedback

- **Issues?** Check the VS Code extension details tab
- **Questions?** Run "QAMill AI Assistant" in the dashboard
- **Feedback?** We read every report — help us improve

---

**QAMill: Enterprise QA Governance, Powered by AI**

*Comprehensive test quality intelligence. Automated gap identification. Complete test excellence.*
