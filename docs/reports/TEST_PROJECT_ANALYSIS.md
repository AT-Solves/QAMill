# Project Analysis - Detailed Test Steps

**Purpose:** Validate mutation testing analysis for Python and JavaScript projects  
**Duration:** ~25 minutes per language  
**Status:** Ready for execution

---

## 📋 Prerequisites

### System Requirements
- ✅ Backend running: `localhost:8765`
- ✅ Frontend running: `localhost:5173`
- ✅ User logged in
- ✅ Browser dev tools ready (F12)

### Test Accounts
```
Email: test@example.com
Password: TestPassword123!
```

### Test Files Ready
```
Python test file: simple_calculator.py
JavaScript test file: simple_calculator.js
```

---

## 🐍 PYTHON PROJECT ANALYSIS

### **PART 1: Create Python Project**

#### **Step 1.1: Navigate to Dashboard**

1. Open: `http://localhost:5173`
2. Login if needed
3. Click "Projects" in sidebar
4. Should see projects list

**Validation:**
- ✅ Dashboard loads
- ✅ Projects visible
- ✅ "New Project" button visible

---

#### **Step 1.2: Create New Project**

1. Click **"New Project"** button
2. Fill in form:
   ```
   Project Name: Python Calculator Test
   Description: Testing Python mutation analysis
   Language: Python
   Framework: pytest
   ```
3. Click **"Create Project"**

**Validation:**
- ✅ Form appears
- ✅ Fields populate
- ✅ Project created
- ✅ Redirected to project detail

**Expected response:**
```json
{
  "id": "proj_123abc",
  "name": "Python Calculator Test",
  "language": "python",
  "framework": "pytest",
  "status": "active"
}
```

---

### **PART 2: Create Python Test File**

#### **Step 2.1: Create Test File**

Create `simple_calculator.py` with this code:

```python
# simple_calculator.py
def add(a, b):
    """Add two numbers"""
    return a + b

def subtract(a, b):
    """Subtract b from a"""
    return a - b

def multiply(a, b):
    """Multiply two numbers"""
    return a * b

def divide(a, b):
    """Divide a by b"""
    if b == 0:
        return None
    return a / b

# Test file: test_calculator.py
import pytest
from simple_calculator import add, subtract, multiply, divide

class TestCalculator:
    
    def test_add_positive(self):
        """Test adding positive numbers"""
        assert add(2, 3) == 5
        assert add(10, 20) == 30
    
    def test_add_negative(self):
        """Test adding negative numbers"""
        assert add(-2, -3) == -5
        assert add(5, -3) == 2
    
    def test_subtract(self):
        """Test subtraction"""
        assert subtract(5, 3) == 2
        assert subtract(10, 20) == -10
    
    def test_multiply(self):
        """Test multiplication"""
        assert multiply(3, 4) == 12
        assert multiply(5, 0) == 0
    
    def test_divide(self):
        """Test division"""
        assert divide(10, 2) == 5
        assert divide(7, 2) == 3.5
    
    def test_divide_by_zero(self):
        """Test division by zero"""
        assert divide(10, 0) is None
```

**File location:**
```
~/test_projects/python_calculator/
├── simple_calculator.py
└── test_calculator.py
```

---

#### **Step 2.2: Upload Test File**

1. In project detail, click **"Upload Files"** or **"Add Test"**
2. Select `test_calculator.py`
3. Click **"Upload"**
4. Or paste code directly in web editor

**Validation:**
- ✅ File uploaded
- ✅ File content visible
- ✅ Framework detected (pytest)
- ✅ Tests listed

**Expected UI:**
```
Files:
├── simple_calculator.py (108 bytes)
└── test_calculator.py (445 bytes)

Tests Detected:
- test_add_positive
- test_add_negative
- test_subtract
- test_multiply
- test_divide
- test_divide_by_zero
(6 tests total)
```

---

### **PART 3: Run Python Analysis**

#### **Step 3.1: Start Analysis**

1. Click **"Analyze"** or **"Start Analysis"** button
2. Configure analysis:
   ```
   LLM Provider: Claude
   Auto-healing: Enabled
   Equivalence Detection: Enabled
   Mutation Operators: All (AOR, ROR, LCR, BCR, STR, etc.)
   ```
3. Click **"Start Analysis"**

**Validation:**
- ✅ Analysis starts
- ✅ Loading indicator appears
- ✅ WebSocket connection establishes
- ✅ Progress bar appears

---

#### **Step 3.2: Monitor Real-time Progress**

**Watch for (in real-time):**

1. **Mutation Generation Phase**
   - Progress: 0% → 25%
   - Messages: "Generating mutations..."
   - Count: Total mutants being created

   **Expected:**
   ```
   Mutations generated: 45-60 (for this code)
   Time: 10-20 seconds
   ```

2. **Test Execution Phase**
   - Progress: 25% → 100%
   - Messages: "Testing mutation X/Y..."
   - Live updates each test

   **Expected:**
   ```
   Tests per mutation: 6
   Total test runs: 45-60 × 6 = 270-360
   Time: 30-60 seconds
   ```

#### **Step 3.3: Open Browser Dev Tools**

1. Press **F12** to open dev tools
2. Go to **Network tab**
3. Filter by **WS** (WebSocket)
4. Watch messages flow

**Expected messages:**
```json
{
  "type": "analysis_update",
  "event": "mutation_generated",
  "analysis_id": "ana_abc123",
  "data": {
    "total": 50,
    "completed": 12,
    "killed": 8,
    "survived": 4
  }
}
```

**Validation:**
- ✅ WebSocket connected
- ✅ Messages flowing
- ✅ No errors
- ✅ Low latency (<1s)

---

#### **Step 3.4: Wait for Completion**

Analysis should complete in **2-5 minutes**.

Watch dashboard for:
- ✅ Progress bar reaches 100%
- ✅ Final metrics displayed
- ✅ Results panel shows scores
- ✅ Report ready to view

---

### **PART 4: Validate Python Results**

#### **Step 4.1: Check Mutation Metrics**

After analysis completes, verify:

```
Expected Metrics:
┌─────────────────────────────────────┐
│ Mutation Score:      80-95%         │
│ Total Mutants:       45-60          │
│ Killed:              36-57          │
│ Survived:            5-15           │
│ Equivalent:          2-5            │
│ Coverage Score:      90-100%        │
│ Test Effectiveness:  85-95%         │
└─────────────────────────────────────┘
```

**Validation checklist:**
- [ ] Mutation score > 80%
- [ ] Coverage score > 90%
- [ ] All tests executed
- [ ] No errors
- [ ] Metrics calculated correctly

---

#### **Step 4.2: View Results Dashboard**

1. Click **"View Results"** or **"Analysis Report"**
2. Check sections:

**Summary Section:**
```
✅ Overall Score: 87%
✅ Mutations: 52 total
✅ Killed: 45 (86%)
✅ Survived: 5 (10%)
✅ Equivalent: 2 (4%)
```

**Test Coverage:**
```
✅ Code Coverage: 96%
✅ Line Coverage: 96%
✅ Branch Coverage: 92%
✅ Function Coverage: 100%
```

**Mutation Breakdown:**
```
✅ Arithmetic Mutations (AOR): 12 → 10 killed
✅ Relational Mutations (ROR): 8 → 7 killed
✅ Logical Mutations (LCR): 15 → 13 killed
✅ Boundary Mutations (BCR): 10 → 10 killed
✅ String Mutations (STR): 7 → 5 killed
```

---

#### **Step 4.3: View Survived Mutants**

1. Scroll to **"Survived Mutants"** section
2. See list of mutations that escaped tests

**Example survived mutants:**
```
1. Line 10: Changed == to != in divide function
   Original: if b == 0:
   Mutant:   if b != 0:
   Reason: Test didn't catch this edge case

2. Line 6: Changed + to - in add function
   Original: return a + b
   Mutant:   return a - b
   Reason: Only tested positive numbers

3. Line 15: Removed zero check
   Original: if b == 0: return None
   Mutant:   return a / b
   Reason: Test didn't call divide(10, 0)
```

**Validation:**
- ✅ Survived mutants listed
- ✅ Code shown
- ✅ Explanation provided
- ✅ Suggests test improvements

---

#### **Step 4.4: Download Elite HTML Report**

1. Click **"Download Report"** or **"Export HTML"**
2. Save file: `qamill-analysis-python-calculator.html`
3. Open in browser

**Verify report contains:**
- ✅ Executive summary
- ✅ Mutation score chart
- ✅ Coverage metrics
- ✅ Detailed mutations
- ✅ Survived mutants
- ✅ Recommendations
- ✅ Self-contained (no external JS/CSS)
- ✅ Professional styling

**Report structure:**
```html
<!DOCTYPE html>
<html>
  <head>
    <title>QAMill Analysis Report</title>
    <style>/* Embedded CSS */</style>
  </head>
  <body>
    <header>QAMill Analysis Report</header>
    <section>Summary</section>
    <section>Metrics</section>
    <section>Mutations</section>
    <section>Recommendations</section>
  </body>
</html>
```

---

#### **Step 4.5: API Validation**

Test via curl:

```bash
# Get analysis results
curl http://localhost:8765/api/v1/analyses/ana_abc123 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"

# Expected response:
{
  "id": "ana_abc123",
  "project_id": "proj_123abc",
  "status": "completed",
  "mutation_score": 87,
  "coverage_score": 96,
  "total_mutations": 52,
  "killed": 45,
  "survived": 5,
  "equivalent": 2,
  "test_count": 6,
  "duration_seconds": 145,
  "created_at": "2026-06-27T13:00:00Z",
  "completed_at": "2026-06-27T13:02:25Z"
}
```

```bash
# Get report
curl http://localhost:8765/api/v1/analyses/ana_abc123/report \
  -H "Authorization: Bearer <token>"

# Returns: HTML report content
```

---

## 📜 JAVASCRIPT PROJECT ANALYSIS

### **PART 5: Create JavaScript Project**

#### **Step 5.1: Create New Project**

1. Click **"New Project"**
2. Fill form:
   ```
   Project Name: JavaScript Calculator Test
   Description: Testing JavaScript mutation analysis
   Language: JavaScript
   Framework: Jest
   ```
3. Click **"Create"**

**Validation:**
- ✅ Project created
- ✅ JavaScript selected
- ✅ Jest detected

---

### **PART 6: Create JavaScript Test File**

#### **Step 6.1: Create Test File**

Create `simple_calculator.js`:

```javascript
// simple_calculator.js
function add(a, b) {
  return a + b;
}

function subtract(a, b) {
  return a - b;
}

function multiply(a, b) {
  return a * b;
}

function divide(a, b) {
  if (b === 0) {
    return null;
  }
  return a / b;
}

module.exports = { add, subtract, multiply, divide };

// test_calculator.js - Jest tests
const { add, subtract, multiply, divide } = require('./simple_calculator');

describe('Calculator', () => {
  
  describe('add', () => {
    test('adds positive numbers', () => {
      expect(add(2, 3)).toBe(5);
      expect(add(10, 20)).toBe(30);
    });

    test('adds negative numbers', () => {
      expect(add(-2, -3)).toBe(-5);
      expect(add(5, -3)).toBe(2);
    });
  });

  describe('subtract', () => {
    test('subtracts correctly', () => {
      expect(subtract(5, 3)).toBe(2);
      expect(subtract(10, 20)).toBe(-10);
    });
  });

  describe('multiply', () => {
    test('multiplies correctly', () => {
      expect(multiply(3, 4)).toBe(12);
      expect(multiply(5, 0)).toBe(0);
    });
  });

  describe('divide', () => {
    test('divides correctly', () => {
      expect(divide(10, 2)).toBe(5);
      expect(divide(7, 2)).toBe(3.5);
    });

    test('handles division by zero', () => {
      expect(divide(10, 0)).toBeNull();
    });
  });
});
```

---

#### **Step 6.2: Upload Test File**

1. Click **"Upload Files"**
2. Select `test_calculator.js`
3. Click **"Upload"**

**Validation:**
- ✅ File uploaded
- ✅ Jest tests detected
- ✅ 6 tests listed

---

### **PART 7: Run JavaScript Analysis**

#### **Step 7.1: Start Analysis**

1. Click **"Analyze"**
2. Configure:
   ```
   LLM Provider: Claude
   Auto-healing: Enabled
   Equivalence Detection: Enabled
   ```
3. Click **"Start"**

**Validation:**
- ✅ Analysis starts
- ✅ Progress displays
- ✅ WebSocket connects

---

#### **Step 7.2: Monitor Progress**

Watch for:

**Phase 1: Mutation Generation**
```
Status: Generating mutations...
Progress: 0% → 25%
Expected mutants: 45-60
Time: 10-20 seconds
```

**Phase 2: Test Execution**
```
Status: Running tests...
Progress: 25% → 100%
Tests per mutation: 6
Total: 270-360 test runs
Time: 30-60 seconds
```

**Phase 3: Analysis**
```
Status: Calculating metrics...
Progress: 90% → 100%
Time: 5-10 seconds
```

---

#### **Step 7.3: Monitor WebSocket**

Open dev tools (F12) and check Network → WS:

**Expected message pattern:**
```json
Message 1: { "event": "mutation_generated", "total": 50, "completed": 0 }
Message 2: { "event": "test_running", "mutation": 1 }
Message 3: { "event": "test_completed", "killed": true }
... (repeat for each mutation)
Message N: { "event": "analysis_complete", "score": 87 }
```

---

### **PART 8: Validate JavaScript Results**

#### **Step 8.1: Check Metrics**

Compare with Python results:

```
JAVASCRIPT vs PYTHON (should be similar):

                    JavaScript    Python    Match?
Mutation Score:     85-95%        80-95%    ✅ Similar
Total Mutants:      45-60         45-60     ✅ Same
Killed %:           85-90%        85-90%    ✅ Same
Coverage:           90-100%       90-100%   ✅ Same
```

**Validation:**
- ✅ Mutation score reasonable
- ✅ Metrics calculated
- ✅ Similar to Python results
- ✅ Framework auto-detected

---

#### **Step 8.2: View JavaScript-Specific Results**

1. Check **"Mutation Operators"** section
2. Verify JavaScript operators applied:

```
✅ Arithmetic Mutations (AOR)
   + changed to -
   - changed to +
   * changed to /
   / changed to *

✅ Logical Mutations (LCR)
   && changed to ||
   || changed to &&
   ! removed

✅ Comparison Mutations (ROR)
   === changed to !==
   !== changed to ===
   > changed to <
   < changed to >

✅ Other JavaScript-specific
   null changed to undefined
   true changed to false
```

---

#### **Step 8.3: Compare Python vs JavaScript**

| Aspect | Python | JavaScript | Status |
|--------|--------|-----------|--------|
| Mutations Generated | 52 | 50 | ✅ Similar |
| Mutation Score | 87% | 86% | ✅ Similar |
| Test Coverage | 96% | 95% | ✅ Similar |
| Operators Used | 17+ | 17+ | ✅ Same |
| Analysis Time | 2.5 min | 2.3 min | ✅ Similar |

---

#### **Step 8.4: Validate Framework Detection**

```bash
# Test framework detection API
curl http://localhost:8765/api/v1/detect/framework \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/path/to/project"}'

# Expected response:
{
  "framework": "jest",
  "language": "javascript",
  "detected_version": "29.5.0",
  "confidence": 0.99,
  "test_files": ["test_calculator.js"],
  "test_count": 6
}
```

---

## 📊 COMPARISON TEST

### **Step 9: Compare Python vs JavaScript**

#### **Step 9.1: Side-by-side Metrics**

Create comparison table:

```
Feature                 Python      JavaScript    Match?
─────────────────────────────────────────────────────────
Mutation Score          87%         86%           ✅ YES
Total Mutations         52          50            ✅ Similar
Killed Mutations        45          43            ✅ Similar
Survived Mutations      5           5             ✅ YES
Equivalent Mutations    2           2             ✅ YES
Coverage Score          96%         95%           ✅ Similar
Test Count              6           6             ✅ YES
Analysis Duration       145s        138s          ✅ Similar
Report Generated        ✅ YES      ✅ YES        ✅ YES
WebSocket Updates       ✅ YES      ✅ YES        ✅ YES
Framework Detected      pytest      jest          ✅ YES
```

---

#### **Step 9.2: Validate Multi-language Support**

✅ **Both languages supported equally**
✅ **Same 17+ operators applied**
✅ **Consistent metrics**
✅ **Same reporting format**
✅ **Real-time updates work**

---

## ✅ VALIDATION CHECKLIST

### **Python Analysis Tests**
- [ ] Project created successfully
- [ ] Test file uploaded
- [ ] Analysis started
- [ ] WebSocket connected
- [ ] Real-time progress visible
- [ ] Analysis completed (2-5 min)
- [ ] Mutation score: 80-95%
- [ ] Coverage score: 90-100%
- [ ] Survived mutants listed
- [ ] HTML report generated
- [ ] Report is self-contained
- [ ] API endpoints working

### **JavaScript Analysis Tests**
- [ ] Project created successfully
- [ ] Test file uploaded
- [ ] Framework detected (Jest)
- [ ] Analysis started
- [ ] WebSocket connected
- [ ] Real-time progress visible
- [ ] Analysis completed (2-5 min)
- [ ] Mutation score: 80-95%
- [ ] Coverage score: 90-100%
- [ ] JavaScript operators applied
- [ ] HTML report generated
- [ ] API endpoints working

### **Comparison Tests**
- [ ] Metrics similar between languages
- [ ] Same number of operators used
- [ ] Analysis time comparable
- [ ] Reports have same format
- [ ] Multi-language support validated

### **Real-time Tests**
- [ ] WebSocket connects
- [ ] Messages flow in real-time
- [ ] Dashboard updates live
- [ ] Progress bar accurate
- [ ] No connection drops
- [ ] Low latency (<1s)

### **API Tests**
- [ ] GET /analyses/{id} works
- [ ] GET /analyses/{id}/report works
- [ ] Analysis data complete
- [ ] Report content valid
- [ ] Error handling works

---

## 🎯 SUCCESS CRITERIA

**Analysis passes if:**

✅ **Metrics Valid**
- Mutation score in reasonable range (75-95%)
- Coverage score > 85%
- All tests executed

✅ **Performance Good**
- Analysis completes in 2-5 minutes
- WebSocket latency < 1 second
- Report generates instantly

✅ **Multi-language Works**
- Python and JavaScript produce similar results
- Same 17+ operators applied
- Framework auto-detection accurate

✅ **Real-time Working**
- WebSocket connects
- Progress updates live
- No connection drops

✅ **Reports Professional**
- HTML self-contained
- Metrics clearly displayed
- Mutations highlighted
- Ready for sharing

---

## 📝 TEST REPORT TEMPLATE

```
===========================================
PROJECT ANALYSIS TEST REPORT
===========================================

Date: [DATE]
Tester: [NAME]
Project: Python Calculator Test

ANALYSIS EXECUTION
──────────────────
Start Time: [TIME]
End Time: [TIME]
Duration: [MIN:SEC]
Status: ✅ COMPLETED / ❌ FAILED

METRICS
───────
Mutation Score: [X%]
Coverage Score: [Y%]
Total Mutations: [N]
Killed: [N] ([%])
Survived: [N] ([%])
Equivalent: [N] ([%])

VALIDATION
──────────
WebSocket: ✅ Connected
Progress: ✅ Updated in real-time
Report: ✅ Generated
API: ✅ Working
Performance: ✅ Within limits

ISSUES
──────
[List any issues found]

NOTES
─────
[Any observations]

PASS/FAIL: ✅ PASS / ❌ FAIL
===========================================
```

---

## 🚀 Next Steps After Validation

If all tests pass:
1. ✅ Document results
2. ✅ Generate test report
3. ✅ Commit findings
4. ✅ Ready for Marketplace launch

If issues found:
1. ❌ Document bugs
2. ❌ Create fixes
3. ❌ Re-test
4. ❌ Validate fixes

---

**Ready to test project analysis!** 🎯

Follow these steps in order and validate at each checkpoint.

