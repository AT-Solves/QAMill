# QAMill User Validation Guide

**For:** Project Managers, QA Teams, Developers  
**Purpose:** Learn to use QAMill to analyze your test quality  
**Time:** ~30 minutes for first project  
**Skill Level:** Beginner-friendly

---

## 🚀 Getting Started

### **What is QAMill?**

QAMill is an **AI-powered mutation testing tool** that tells you exactly what your tests are catching — and what they're missing.

**In simple terms:**
- 🧬 Creates 50+ variations of your code (mutations)
- 🧪 Runs all your tests against each variation
- 📊 Shows you how many mutations your tests caught
- 📈 Recommends improvements to your test suite

### **What You'll Learn**

By the end of this guide, you can:
- ✅ Create a project in QAMill
- ✅ Upload your test files
- ✅ Run an analysis
- ✅ Read the results
- ✅ Improve your tests

---

## 📝 Step 1: Login to QAMill

### **1.1 Open QAMill**

Open your browser and go to:
```
http://localhost:5173
```

Or if deployed:
```
https://yourdomain.com
```

### **1.2 Create an Account or Login**

**If new user:**
1. Click **"Sign Up"**
2. Enter your email: `your-email@company.com`
3. Create password: `MySecurePassword123!`
4. Click **"Create Account"**

**If existing user:**
1. Click **"Login"**
2. Enter email and password
3. Click **"Login"**

### **1.3 Alternative: Login with GitHub or Google**

1. Click **"GitHub"** or **"Google"** button
2. Authenticate with your account
3. Grant permissions
4. You're logged in! ✅

---

## 📁 Step 2: Create Your First Project

### **2.1 Start New Project**

1. You'll see the **Dashboard** with a "New Project" button
2. Click **"New Project"** or **"Create Project"**

### **2.2 Fill in Project Details**

**Project Name:**
```
Example: "Calculator App Tests"
```

**Language (Choose one):**
- 🐍 **Python** — for Python projects
- 📜 **JavaScript** — for Node.js, React, Vue
- (More coming soon: C#, Java, Go)

**Test Framework (Choose one):**

**For Python:**
- pytest ✅ (recommended)
- unittest
- Django

**For JavaScript:**
- Jest ✅ (recommended)
- Vitest
- Mocha

**Description (optional):**
```
"Testing the calculator module functionality"
```

### **2.3 Create Project**

Click **"Create Project"** button.

**You should see:**
- ✅ Project created
- ✅ Project name displayed
- ✅ Ready to upload files

---

## 📤 Step 3: Upload Your Test Files

### **3.1 Prepare Test Files**

Have your test files ready:

**For Python:**
```
test_calculator.py
calculator.py
```

**For JavaScript:**
```
calculator.test.js
calculator.js
```

### **3.2 Upload Files**

**Option A: Drag and Drop**
1. Drag test files into the upload area
2. Release to upload
3. Wait for upload to complete

**Option B: Click to Browse**
1. Click **"Select Files"** button
2. Browse your computer
3. Select test file(s)
4. Click **"Open"**

**Option C: Paste Code**
1. Click **"Paste Code"** tab
2. Copy-paste your test code
3. Click **"Add Code"**

### **3.3 Verify Upload**

After upload, you should see:
```
✅ File uploaded successfully
✅ File size displayed (e.g., 2.5 KB)
✅ Framework auto-detected (pytest, Jest, etc.)
✅ Test count shown (e.g., "6 tests detected")
```

---

## ▶️ Step 4: Start Analysis

### **4.1 Click "Analyze"**

Click the **"Analyze"** or **"Start Analysis"** button.

### **4.2 Configure Analysis (Optional)**

You'll see a settings panel:

```
LLM Provider: Claude ✅ (leave as default)
Auto-healing: Enabled ✅ (finds missing tests)
Equivalence Detection: Enabled ✅ (removes false alarms)
```

**What these mean:**
- **LLM Provider:** Which AI to use for analysis
- **Auto-healing:** AI suggests new tests
- **Equivalence Detection:** Filters out fake mutations

### **4.3 Start Analysis**

Click **"Start Analysis"** button.

**What happens:**
- ✅ Analysis begins (takes 2-5 minutes)
- ✅ Progress bar appears
- ✅ Real-time updates show progress
- ✅ Mutations are generated and tested
- ✅ Results calculated

---

## 👀 Step 5: Watch Real-time Progress

### **5.1 Progress Bar**

You'll see a progress bar:
```
█████░░░░ 50% - Testing mutation 25 of 50
```

### **5.2 What's Happening**

**Phase 1: Mutation Generation (First 25%)**
```
Status: Generating mutations...
Time: 10-20 seconds
What it does: Creates 50+ variations of your code
```

**Phase 2: Test Execution (Next 75%)**
```
Status: Running tests...
Time: 1-4 minutes
What it does: Runs all your tests against each mutation
```

**Phase 3: Analysis Complete (100%)**
```
Status: Analysis complete!
Time: 5-10 seconds total
What it does: Calculates final scores
```

### **5.3 Real-time Updates**

Watch the dashboard update live:
- Current mutation being tested
- Tests passing/failing
- Progress percentage
- Estimated time remaining

---

## 📊 Step 6: Understand Your Results

### **6.1 Results Summary**

After analysis completes, you'll see:

```
╔════════════════════════════════════════╗
║         YOUR TEST QUALITY SCORE        ║
║                                        ║
║  Overall Score:           87%          ║
║  Coverage:                96%          ║
║  Quality Rating:          GOOD ✅      ║
╚════════════════════════════════════════╝
```

### **6.2 What Each Metric Means**

**Overall Score (Mutation Score):** 87%
```
"Your tests caught 87% of injected code changes"

Range:    0-100%
Meaning:  85%+ = Excellent ✅
          70-85% = Good
          50-70% = Fair ⚠️
          <50% = Poor ❌

Your Score: 87% = Excellent! ✅
```

**Coverage:** 96%
```
"Your tests execute 96% of your code"

Range:    0-100%
Meaning:  90%+ = Excellent ✅
          80-90% = Good
          70-80% = Fair ⚠️
          <70% = Poor ❌

Your Score: 96% = Excellent! ✅
```

**Quality Rating:** GOOD
```
Based on mutation score + coverage
EXCELLENT (90-100%)
GOOD (75-90%)
FAIR (60-75%)
POOR (<60%)

Your Rating: GOOD ✅
```

### **6.3 Detailed Metrics**

Scroll down to see:

```
Mutations Analyzed:     50
├─ Killed:             43 (86%)  = Tests caught these
├─ Survived:            5 (10%)  = Tests missed these
└─ Equivalent:          2 (4%)   = Ignored (safe)

What this means:
- Killed = Good! Tests are working
- Survived = Problem! Tests need improvement
- Equivalent = Ignore these
```

---

## 🔍 Step 7: Review Survived Mutants

### **7.1 What are "Survived Mutants"?**

"Survived mutants" are code changes your tests **did NOT catch**.

**Example:**
```python
Original code:
    if x > 0:
        return True

Survived mutation (not caught):
    if x >= 0:  ← Changed > to >=
        return True

Your test didn't notice this change!
```

### **7.2 View Survived Mutants**

Scroll to **"Survived Mutants"** section.

You'll see a list like:

```
1. Line 12: Arithmetic operator changed
   Original: x + y
   Mutated:  x - y
   Impact: Could cause calculation errors
   
2. Line 25: Comparison operator changed
   Original: if count > 5:
   Mutated:  if count >= 5:
   Impact: Boundary condition not tested
   
3. Line 38: Boolean changed
   Original: return True
   Mutated:  return False
   Impact: Logic error not caught
```

### **7.3 What to Do**

For each survived mutant:

1. **Read the description** - understand what changed
2. **Look at the code** - find the line number
3. **Write a test** - add a test case for that scenario

**Example:**
```python
# Survived mutant: x > 0 changed to x >= 0

# BEFORE (incomplete):
def test_positive():
    assert is_positive(5) == True
    assert is_positive(0) == False  # ← Edge case!

# AFTER (complete):
def test_positive():
    assert is_positive(5) == True
    assert is_positive(1) == True
    assert is_positive(0) == False     # ← Added this
    assert is_positive(-1) == False
```

---

## 📥 Step 8: Download Report

### **8.1 Get the Report**

1. Look for **"Download Report"** button
2. Click it
3. File saves: `qamill-analysis-report.html`

### **8.2 Open Report**

1. Open the HTML file in your browser
2. You'll see a professional report with:
   - ✅ Executive summary
   - ✅ Visual charts
   - ✅ All metrics
   - ✅ Recommendations
   - ✅ Mutation details

### **8.3 Share Report**

The HTML file is **self-contained** (no internet needed):
- ✅ Send via email
- ✅ Share in Slack
- ✅ Upload to wiki
- ✅ Store in archive
- ✅ Print to PDF

---

## 💡 Step 9: Improve Your Tests

### **9.1 Review Recommendations**

The report includes suggestions like:

```
Recommendations:

1. Add more edge case tests
   Current: 3 edge cases
   Suggested: 5-7 edge cases
   
2. Test error conditions
   Current: No error tests
   Suggested: Add try/catch tests
   
3. Test boundary values
   Current: Only center values tested
   Suggested: Test min/max values
```

### **9.2 Fix Failed Tests**

For each survived mutant:

1. **Understand the mutation** - what code changed?
2. **Identify the gap** - what scenario wasn't tested?
3. **Write a test** - add test case
4. **Run analysis again** - verify improvement

**Example improvement:**
```python
# OLD TEST (87% score):
def test_divide():
    assert divide(10, 2) == 5

# NEW TEST (95% score):
def test_divide():
    assert divide(10, 2) == 5      # Normal
    assert divide(10, 0) is None   # Error case
    assert divide(7, 2) == 3.5     # Decimal
    assert divide(-10, 2) == -5    # Negative
```

### **9.3 Re-run Analysis**

1. Upload updated test file
2. Click **"Analyze"** again
3. Compare new score with old score
4. See improvement! 📈

---

## ✅ Step 10: Verify Results

### **10.1 Run Analysis Again**

After improving your tests:

1. Upload new test file
2. Click **"Analyze"**
3. Wait for completion
4. Compare scores

### **10.2 Expect Improvement**

```
Before improvements: 87%
After improvements:  94%
Improvement:        +7% ✅
```

### **10.3 Track Progress**

QAMill saves all analysis history:

1. Click **"Analysis History"**
2. See all past analyses
3. Track score over time
4. Celebrate improvements! 🎉

---

## 🎯 Quick Reference: What to Do With Results

### **Score 90-100%** ✅ Excellent
```
Your tests are in excellent shape!
- Keep current practices
- Focus on maintaining coverage
- Use as baseline for new code
```

### **Score 75-90%** ✅ Good
```
Your tests are good but could be better.
- Focus on survived mutants (5-10 mutations)
- Add edge case tests
- Test error conditions
- Target: Get to 90%
```

### **Score 60-75%** ⚠️ Fair
```
Your tests need improvement.
- Review all survived mutants (15-25 mutations)
- Add comprehensive test cases
- Test boundary values
- Test error scenarios
- Target: Get to 80%+
```

### **Score <60%** ❌ Poor
```
Your tests have significant gaps.
- Significant testing effort needed
- Review all mutation categories
- Add tests for all code paths
- Consider pair programming on tests
- Target: Get to 70%+
```

---

## 🐛 Troubleshooting

### **"Analysis is taking too long"**

**Normal times:**
- Small project (10-20 tests): 2-3 minutes
- Medium project (50+ tests): 3-5 minutes
- Large project (100+ tests): 5-10 minutes

**If longer:**
- Check internet connection
- Reduce file size
- Try simpler project first

### **"Score seems low for good tests"**

**Common reasons:**
1. Missing edge cases
2. Not testing error conditions
3. No boundary value tests
4. Tests only check happy path

**Solution:** Review survived mutants and add tests

### **"Framework not detected"**

**Solution:**
1. Make sure files are named correctly
   - Python: `test_*.py` or `*_test.py`
   - JavaScript: `*.test.js` or `*.spec.js`
2. Select framework manually
3. Upload again

### **"File upload failed"**

**Try:**
1. Check file size (should be < 10MB)
2. Use modern browser (Chrome, Firefox)
3. Check internet connection
4. Paste code directly instead

---

## 📚 Common Test Scenarios

### **Scenario 1: New Project**

```
Goal: Establish baseline test quality

Steps:
1. Upload initial test files
2. Run analysis
3. Note the score (baseline)
4. Improve over time
5. Goal: 85%+ score
```

### **Scenario 2: Code Review**

```
Goal: Ensure tests cover new code

Steps:
1. Add new test file
2. Run analysis
3. Review mutations in new code
4. Add missing tests
5. Verify coverage before merge
```

### **Scenario 3: Test Improvement**

```
Goal: Improve existing test suite

Steps:
1. Upload current tests (score: 78%)
2. Review survived mutants
3. Add edge case tests
4. Re-run analysis (score: 88%)
5. Celebrate improvement! 🎉
```

---

## 📖 Key Concepts

### **Mutation Score**
```
"What percentage of code changes did your tests catch?"

If score = 87%:
- 87 out of 100 code changes were caught
- 13 code changes went undetected
- Need to improve tests for those 13 areas
```

### **Coverage vs Mutation Score**
```
Coverage: Code execution
- Tells you which code is RUN
- Doesn't tell you if it's tested correctly

Mutation Score: Test effectiveness
- Tells you if tests actually VALIDATE logic
- More important than coverage alone

Example:
  Coverage: 100% (all code runs)
  Mutation: 75% (but tests miss some changes)
  → Need better tests, not just more code execution
```

### **Survived Mutant**
```
"A code change your tests didn't catch"

Example:
  if x > 5:  ← Your test didn't notice this changed to >=
  
This means your tests are incomplete for this scenario.
```

---

## 🎓 Best Practices

### **✅ DO:**
- Run analysis regularly (weekly or before release)
- Review ALL survived mutants
- Write tests for edge cases
- Test error conditions
- Test boundary values
- Test negative scenarios

### **❌ DON'T:**
- Ignore low mutation scores
- Only test happy path
- Copy test code without understanding
- Use 100% coverage as sole metric
- Skip analysis before deployment

---

## 📊 Team Best Practices

### **For QA Teams:**
```
1. Run analysis before each release
2. Review report together
3. Assign mutations to team members
4. Track score over time
5. Celebrate improvements
```

### **For Development Teams:**
```
1. Include analysis in code review
2. Address survived mutants before merge
3. Track test quality metrics
4. Learn from mutations
5. Improve test practices
```

### **For Managers:**
```
1. Track test quality metrics over time
2. Set quality goals (e.g., 85%+)
3. Allocate time for test improvements
4. Use reports for team health check
5. Celebrate test quality wins
```

---

## 🎯 Success Metrics

Track these over time:

```
Month 1: 75% mutation score
Month 2: 80% mutation score (+5%)
Month 3: 85% mutation score (+5%)
Month 4: 90% mutation score (+5%)

Goal: Continuous improvement
Target: 90%+ mutation score
```

---

## 🆘 Need Help?

### **Within QAMill:**
1. Click **"Help"** or **"?"** icon
2. Read documentation
3. Contact support

### **Documentation:**
- 📖 Full user guide (in repo)
- 🎥 Video tutorials (coming soon)
- 💬 Community forum (coming soon)

### **Contact Support:**
- 📧 Email: support@qamill.io
- 💬 Discord: (coming soon)
- 📞 Phone: (coming soon)

---

## ✨ You're Ready!

You now know how to:
✅ Create projects  
✅ Upload tests  
✅ Run analysis  
✅ Read results  
✅ Improve tests  
✅ Track progress  

### **Next Steps:**
1. Create your first project
2. Upload your test files
3. Run analysis
4. Review results
5. Improve tests
6. Re-run to verify improvement

**Congratulations!** 🎉

You're now using QAMill to improve test quality!

---

**Questions? Need help?** Contact support@qamill.io

**Happy Testing!** 🚀

