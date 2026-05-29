# QAMill — Autonomous Mutation Intelligence for Developers

> **QA** your code. **Mill** through every gap. Never miss a bug again.

---

## What is QAMill?

QAMill is an AI-powered mutation testing tool that runs inside your IDE.
It finds weaknesses in your test suite by secretly introducing small bugs
into your code — then checking whether your tests catch them.

But QAMill goes far beyond any existing mutation testing tool.
It does not just tell you what went wrong. It tells you *why*, filters
out the false alarms, and automatically writes the missing tests for you.

---

## The problem QAMill solves

Every software team writes tests. But how do you know your tests are
actually good? A test that always passes — even when the code is broken —
is worse than no test at all. It gives you false confidence.

Traditional mutation testing tools exist, but they have three deep flaws:

**Flaw 1 — They lie about your score.**
They count *equivalent mutants* as survived — mutants that are
mathematically identical to your original code and can never be caught
by any test. This makes your mutation score look worse than it really is
and sends developers chasing problems that do not exist.

**Flaw 2 — They only report, never fix.**
When a mutant survives, existing tools give you a list and walk away.
You are on your own to figure out what test to write.

**Flaw 3 — They cannot test how methods interact.**
Existing tools mutate one function at a time. Bugs that live at the
boundary between two functions — where one calls the other — are
completely invisible.

QAMill solves all three.

---

## How QAMill works

### Step 1 — Generate mutants (no LLM required)
QAMill reads your source code and creates hundreds of small broken
copies using AST (Abstract Syntax Tree) analysis. It swaps operators,
flips booleans, changes comparisons, and alters return values —
all the ways real bugs appear in production code.

This entire step runs locally on your machine. No internet connection.
No API key. No cost.

### Step 2 — Filter equivalent mutants (the honest score)
Before running a single test, QAMill checks each mutant through
a 3-stage pipeline:

- **Stage 1 — Pattern rules:** Instantly catches known equivalent
  rewrites like `x - 1` and `x + (-1)` using pattern matching. Free.
- **Stage 2 — Z3 mathematical solver:** For arithmetic mutations,
  formally proves whether two expressions can ever produce different
  results. Algebraically certain.
- **Stage 3 — LLM semantic judge:** For complex logic, sends the
  original and mutant function to your chosen LLM and asks it to
  reason about semantic equivalence.

Equivalent mutants are removed from your score entirely.
What remains is your **true mutation score** — something no other
tool gives you today.

### Step 3 — Run your existing tests
QAMill creates a temporary copy of your project, injects the mutant
into the copy, and runs your existing test suite against it.
Your original source code is **never modified**.

If your tests fail → mutant **killed** (your tests are good here).
If your tests pass → mutant **survived** (you have a test gap).

### Step 4 — Auto-heal survived mutants
For every mutant that survives, QAMill asks your chosen LLM to write
a new test specifically designed to catch it. It then runs the
generated test against the mutant to **verify it actually works**
before presenting it to you. You get a ready-to-commit, verified test —
not a suggestion.

### Step 5 — Live dashboard in your IDE
Every result streams to a live panel inside your IDE as it happens.
You see the score bar grow, each mutant classified in real time,
and survived mutants appear with their suggested tests alongside them.
No waiting for a final report.

---

## The four game-changing capabilities

### 1. True mutation score via equivalent mutant detection
The biggest unsolved problem in mutation testing research.
QAMill is the first practical tool to filter equivalent mutants
using a multi-stage pipeline, giving developers an honest score
they can actually trust and act on.

### 2. Self-healing test suite
When a real mutant survives, QAMill does not just report it.
It drafts a new test, verifies the test kills the mutant,
and hands you the validated code ready to add to your suite.
The mutation score improves automatically over time.

### 3. Cross-method interaction mutations
QAMill analyses the call graph between your functions and generates
mutations at the boundary where one method calls another.
These interaction-level mutations catch the bugs that single-function
mutation testing completely misses.

### 4. Mutation difficulty ranking
Not all survived mutants are equally dangerous. QAMill ranks each
survived mutant by how hard it is to kill and how risky it is to leave
undetected, so developers tackle the most important gaps first.

---

## LLM providers — your choice, your data

QAMill treats LLM selection as a user preference, not a product
dependency. You choose which AI engine powers the intelligence layer,
or none at all.

| Provider       | Mode         | Privacy              |
|----------------|--------------|----------------------|
| None           | In-house AST | Fully offline        |
| Ollama (local) | In-house LLM | Fully offline        |
| Claude         | Cloud LLM    | Function body only   |
| GPT-4o         | Cloud LLM    | Function body only   |
| Grok           | Cloud LLM    | Function body only   |

When a cloud LLM is used, QAMill sends only the function body —
never file paths, project names, or any identifying information.

---

## IDE support

QAMill is built on the Language Server Protocol, meaning the
intelligence engine is written once and works across all major IDEs.

| IDE              | Support        |
|------------------|---------------|
| VS Code          | Full — built-in dashboard + gutter markers |
| Eclipse          | Full — via LSP4J adapter |
| Visual Studio    | Full — via LSP adapter |
| Jupyter Notebook | Full — via VS Code extension |
| IntelliJ / IDEA  | Via plugin adapter |
| Neovim           | Native LSP support |

---

## Language support

| Language   | Status       |
|------------|-------------|
| Python     | Full support |
| JavaScript | Planned      |
| TypeScript | Planned      |
| Java       | Planned      |

---

## Mutation operators

| Code | Name                          | Example                     |
|------|-------------------------------|-----------------------------|
| AOR  | Arithmetic Operator Replacement | `+` → `-`, `*` → `/`     |
| ROR  | Relational Operator Replacement | `==` → `!=`, `>` → `>=`  |
| LCR  | Logical Connector Replacement   | `and` → `or`              |
| BCR  | Boolean Constant Replacement    | `True` → `False`          |
| RVR  | Return Value Replacement        | `return x` → `return None`|

---

## Understanding your results

Every mutant receives one of four classifications:

| Status       | Meaning                                          | Action needed         |
|--------------|--------------------------------------------------|-----------------------|
| **Killed**   | Your tests caught the mutation                   | None — tests are good |
| **Survived** | Your tests missed the mutation — real gap found  | Review suggested test |
| **Equivalent** | Mutation is mathematically identical to original | None — filtered out |
| **Error**    | Test execution failed unexpectedly               | Check test setup      |

### Two scores, one truth

**Raw score** = killed ÷ all mutants
This is what every other tool reports. It includes equivalent mutants
in the denominator, making your score look artificially low.

**True score** = killed ÷ (killed + survived)
This is what QAMill reports. Equivalent mutants are excluded.
This is the number that actually reflects the quality of your tests.

---

## Quick start

**Requirements:** Python 3.10+, pip, VS Code, Node.js 18+

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Start the server
python main.py

# 3. Trigger your first analysis
curl -X POST http://localhost:8765/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/your/file.py",
    "project_root": "/path/to/your/project",
    "llm_provider": "none"
  }'

# 4. Watch live results
curl -N http://localhost:8765/stream/<job_id>
```

**VS Code dashboard:**

```bash
cd vscode-extension
npm install && npm run compile
# Press F5 in VS Code, then right-click any .py file
# → AMIL: Run Mutation Analysis on Current File
```

---

## Project structure

```
qamill/
├── backend/
│   ├── main.py                 API server with SSE live streaming
│   ├── mutation_engine.py      AST-based mutant generation (no LLM)
│   ├── equivalent_detector.py  3-stage: rules → Z3 → LLM
│   ├── llm_adapter.py          Claude / GPT / Grok / Ollama switcher
│   ├── test_runner.py          Wraps pytest/jest, never modifies originals
│   ├── auto_healer.py          Generates and verifies killing tests
│   └── requirements.txt
├── vscode-extension/
│   ├── src/extension.ts        Extension entry point + live dashboard
│   └── package.json
└── sample_project/
    ├── math_utils.py           Demo target code
    └── tests/
        └── test_math_utils.py  Intentionally incomplete tests for demo
```

---

## Powered by

QAMill is built by the team participating in the
**AI Based Mutation Testing Hackathon** — Focus Areas 02 and 03:
AI Performance Improvement and Adaptation of Frameworks.

Powered by **achiever thoughts**

---

*QAMill — because good code deserves honest tests.*
