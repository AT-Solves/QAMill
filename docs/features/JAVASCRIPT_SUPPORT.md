# QAMill JavaScript/TypeScript Support (MVP - Phase 1)

**Status:** Production Ready - Phase 1 Complete  
**Date:** June 27, 2026  
**Supported Languages:** JavaScript, TypeScript  
**Supported Frameworks:** Jest, Vitest, Mocha (auto-detected)  
**Operators:** 5 Critical (AOR, ROR, LCR, BCR, STR)

---

## 📋 What's New

### Multi-Language Architecture
- **Language Detection:** Auto-detect from file extension (.js, .ts, .jsx, .tsx)
- **Framework Detection:** Auto-detect from package.json (Jest, Vitest, Mocha)
- **Runtime Check:** Verify Node.js availability before analysis
- **Language-Agnostic Core:** Unified mutation interface across Python & JavaScript

### JavaScript Mutation Engine
Implements 5 critical mutation operators:

| Operator | Example | Purpose |
|----------|---------|---------|
| **AOR** | `a + b` → `a - b` | Arithmetic operations |
| **ROR** | `a === b` → `a !== b` | Relational comparisons |
| **LCR** | `a && b` → `a \|\| b` | Logical connectors |
| **BCR** | `true` → `false` | Boolean constants |
| **STR** | `"hello"` → `""` | String mutations |

### Test Framework Support
- **Jest** (Default) - Most popular, works everywhere
- **Vitest** - Modern, fast, Vite-native
- **Mocha** - Lightweight, minimal setup

---

## 🚀 Quick Start

### 1. Analyze JavaScript File

```bash
# Using extension (auto-detects JS and framework)
Right-click math_utils.js → "QAMill: Analyze Test Quality"
```

### 2. Backend API

```bash
# Detect language
curl http://localhost:8765/detect/language?file_path=utils.js

# Detect framework
curl http://localhost:8765/detect/framework?project_path=/path/to/project

# Start analysis
curl -X POST http://localhost:8765/analyze/javascript \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/utils.js",
    "project_root": "/path/to/project"
  }'
```

### 3. Expected Output

```
JavaScript Mutation Testing Results
====================================
Framework: Jest ✓
Language: JavaScript 🟨
File: utils.js
Lines: 42
Mutants Generated: 127

Results:
- Killed: 110 (87%)
- Survived: 17 (13%)
- Mutation Score: 87%
```

---

## 📁 File Structure

```
backend/
├── language_adapters/
│   ├── __init__.py                    # Detection & routing
│   ├── base_adapter.py                # Abstract interface
│   ├── python_adapter.py              # Python support (future)
│   └── javascript_adapter.py          # JavaScript support (NEW)
├── javascript_mutation_engine.py      # 5 operators (NEW)
├── javascript_test_runner.py          # Jest/Vitest/Mocha (NEW)
└── main.py                            # API endpoints (updated)
```

---

## 🔧 Technical Details

### Mutation Operators (Regex-based for MVP)

**Why Regex instead of Babel AST?**
- ✅ Simpler, faster implementation
- ✅ Works for MVP phase
- ✅ Can upgrade to Babel later for production

**Regex Patterns:**
```python
AOR: r"(\w|\))\s*[+\-\*/%]\s*(\w|\()"
ROR: r"(===|!==|==|!=|>|<|>=|<=)"
LCR: r"(&&|\|\|)"
BCR: r"\b(true|false)\b"
STR: r'"([^"]*)"|\'([^\']*)\''
```

### Test Runner Integration

```
JavaScript File → Detect Framework (package.json)
                ↓
           Jest | Vitest | Mocha
                ↓
         Generate Mutants (5 ops)
                ↓
         Apply Mutant to File
                ↓
         Run Tests (`jest`, `vitest run`, `mocha`)
                ↓
         Parse JSON Output
                ↓
         Determine: Killed | Survived | Error
                ↓
         Restore Original File
```

### Error Handling

**Graceful Failures:**
- ✅ Node.js not found → Helpful error message
- ✅ Jest not installed → Suggest `npm install --save-dev jest`
- ✅ Syntax error in mutant → Mark as error, restore original
- ✅ Test timeout (60s) → Fail gracefully, continue
- ✅ Framework auto-detection fails → Default to Jest

---

## 📊 Performance (Expected)

| Task | Time |
|------|------|
| Detect language | <100ms |
| Detect framework | <200ms |
| Generate 127 mutants | ~500ms |
| Run 127 tests sequentially | 30-60s |
| Generate report | <1s |

**Optimization Opportunities:**
- Parallel mutant testing (coming Phase 2)
- Caching framework detection (Phase 2)
- Incremental mutation testing (Phase 3)

---

## 🧪 Testing the Implementation

### Test with Sample JavaScript Project

```bash
# 1. Create sample project
mkdir test-js-project
cd test-js-project
npm init -y
npm install --save-dev jest

# 2. Create sample file: utils.js
cat > utils.js << 'EOF'
function add(a, b) {
  return a + b;
}

function isEven(num) {
  return num % 2 === 0;
}

module.exports = { add, isEven };
EOF

# 3. Create test file: utils.test.js
cat > utils.test.js << 'EOF'
const { add, isEven } = require('./utils');

describe('add', () => {
  it('adds 2 + 3 = 5', () => {
    expect(add(2, 3)).toBe(5);
  });
});

describe('isEven', () => {
  it('returns true for even numbers', () => {
    expect(isEven(4)).toBe(true);
  });
});
EOF

# 4. Analyze with QAMill
curl -X POST http://localhost:8765/analyze/javascript \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/test-js-project/utils.js",
    "project_root": "/path/to/test-js-project"
  }'
```

---

## 🚧 Known Limitations (Phase 1 MVP)

### Limitations (Intentional for MVP)
- ❌ Only 5 operators (not full 17)
- ❌ Regex-based (not AST-based)
- ❌ No equivalence detection (Phase 2)
- ❌ No test generation (Phase 2)
- ❌ No TypeScript-specific features (Phase 2)
- ❌ Sequential test execution only (Phase 2 adds parallel)

### Future Enhancements (Phase 2+)
- ✅ All 17 operators (LIR, VDL, MIR, CFD, RVR, CBD, OOR, etc.)
- ✅ Babel/TypeScript AST parser for accuracy
- ✅ Equivalence detection for JS (type-aware)
- ✅ Test generation with Claude
- ✅ TypeScript-specific mutations
- ✅ Parallel test execution
- ✅ Vue/Svelte/React-specific mutations
- ✅ E2E test mutations (Playwright/Cypress)

---

## 🔄 Migration Path from Python

### For Developers with Python Projects
- ✅ Zero changes needed
- ✅ QAMill continues to work exactly as before
- ✅ Can now also analyze .js/.ts files in same project

### For JavaScript Developers (New Users)
- ✅ Same UX as Python version
- ✅ Right-click → "QAMill: Analyze Test Quality"
- ✅ Same elite HTML reports
- ✅ Same LLM provider support (Claude, GPT, etc.)

---

## 📝 Example Mutation Report

```
File: utils.js
Language: JavaScript 🟨
Framework: Jest ✓
Operators: AOR, ROR, LCR, BCR, STR

Mutations by Type:
  AOR (Arithmetic): 47 mutants
    ├─ add(1, 2) + 3  →  add(1, 2) - 3  [KILLED]
    ├─ x * y          →  x / y          [SURVIVED]
    └─ ...

  ROR (Relational): 38 mutants
    ├─ if (x === 5)   →  if (x !== 5)   [KILLED]
    ├─ arr.length > 0 →  arr.length < 0 [SURVIVED]
    └─ ...

  LCR (Logical): 24 mutants
    ├─ a && b         →  a || b         [KILLED]
    └─ ...

  BCR (Boolean): 12 mutants
    ├─ return true    →  return false   [SURVIVED]
    └─ ...

  STR (String): 6 mutants
    ├─ "error"        →  ""             [KILLED]
    └─ ...

Summary:
  Total Mutants: 127
  Killed: 110 (87%)
  Survived: 17 (13%)
  Mutation Score: 87%

Issues Found:
  ⚠️ Survived mutation: x > 5 → x < 5 (line 23)
     Suggestion: Add test for boundary case x == 5
```

---

## 🎯 Next Steps (Phase 2 - 4 weeks)

- [ ] Implement full 17 operators
- [ ] Add Babel AST parser
- [ ] Implement equivalence detection
- [ ] Add test generation with Claude
- [ ] Add TypeScript-specific support
- [ ] Parallel test execution
- [ ] Integration with VS Code extension

---

## 📞 Support

For issues with JavaScript support:
1. Check Node.js installed: `node --version`
2. Check Jest installed: `npm list jest`
3. Check tests pass: `npm test`
4. View backend logs: `python main.py` output

---

**QAMill JavaScript Support - Bringing Mutation Testing to the Web** 🚀
