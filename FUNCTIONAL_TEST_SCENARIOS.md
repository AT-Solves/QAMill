# QAMill v1.2.0 - Functional Test Scenarios

**Status:** Pre-Launch Validation  
**Date:** 2026-06-27  
**Target:** Production-ready validation before Marketplace launch

---

## 🎯 Functional Validation Roadmap

### **Core Scenarios to Validate**

```
1. Authentication & Authorization
2. Multi-Language Support (Python + JavaScript)
3. Real-time WebSocket Updates
4. Team Collaboration
5. Reporting & Analytics
6. API Endpoints
7. VSCode Extension Integration
8. End-to-End Workflows
```

---

## 🔐 **Scenario 1: Authentication & Authorization**

### **1.1 Email/Password Registration**

**Preconditions:**
- Backend running on `localhost:8765`
- Frontend running on `localhost:5173`

**Steps:**
1. Open frontend: http://localhost:5173
2. Click "Sign Up"
3. Enter:
   - Email: `test@example.com`
   - Password: `TestPassword123!`
   - Confirm: `TestPassword123!`
4. Click "Sign Up" button

**Expected Results:**
- ✅ Account created successfully
- ✅ Redirected to dashboard
- ✅ User name displayed in header
- ✅ Can access protected pages

**Validation:**
```bash
# Check user created in database
curl http://localhost:8765/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

### **1.2 Email/Password Login**

**Steps:**
1. Logout if needed
2. Go to login page: http://localhost:5173/login
3. Enter email: `test@example.com`
4. Enter password: `TestPassword123!`
5. Click "Login"

**Expected Results:**
- ✅ Login successful
- ✅ Redirected to dashboard
- ✅ JWT token stored in localStorage
- ✅ Access token valid (30 min expiry)
- ✅ Refresh token valid (7 day expiry)

**Validation:**
```bash
# Check tokens in browser console
localStorage.getItem('accessToken')
localStorage.getItem('refreshToken')
```

---

### **1.3 Token Refresh**

**Steps:**
1. Login successfully
2. Wait 1 minute
3. Make API request to `/api/v1/projects`
4. Verify token auto-refreshes

**Expected Results:**
- ✅ Access token refreshes automatically
- ✅ No "Unauthorized" errors
- ✅ API calls continue working
- ✅ User stays logged in

---

### **1.4 GitHub OAuth Login**

**Preconditions:**
- GitHub OAuth app configured
- Credentials in `.env`

**Steps:**
1. Go to login page
2. Click "GitHub" button
3. Authenticate with GitHub
4. Grant permissions
5. Redirected back to app

**Expected Results:**
- ✅ OAuth redirect works
- ✅ GitHub user info fetched
- ✅ User account created/updated
- ✅ Avatar loaded from GitHub
- ✅ JWT tokens generated
- ✅ Redirected to dashboard

**Validation:**
```bash
# Check OAuth callback endpoint
curl -X POST http://localhost:8765/api/v1/oauth/github/callback \
  -d "code=<github_auth_code>"
```

---

### **1.5 Google OAuth Login**

**Preconditions:**
- Google OAuth app configured
- Credentials in `.env`

**Steps:**
1. Click "Google" button
2. Authenticate with Google
3. Grant permissions
4. Redirected back to app

**Expected Results:**
- ✅ OAuth redirect works
- ✅ Google user info fetched
- ✅ Avatar loaded from Google
- ✅ User logged in successfully
- ✅ Email verified

---

### **1.6 Logout**

**Steps:**
1. Click user menu (top right)
2. Click "Logout"
3. Verify redirected to login page

**Expected Results:**
- ✅ Tokens cleared from localStorage
- ✅ Redirected to login
- ✅ Protected pages blocked
- ✅ Cannot access dashboard

---

## 🐍 **Scenario 2: Python Project Analysis**

### **2.1 Create Python Project**

**Steps:**
1. Dashboard → "New Project"
2. Enter:
   - Name: `Python Calculator`
   - Language: `Python`
   - Framework: `pytest`
3. Click "Create"

**Expected Results:**
- ✅ Project created
- ✅ Listed in projects
- ✅ Can navigate to project detail

---

### **2.2 Run Python Mutation Analysis**

**Steps:**
1. Go to project detail
2. Upload or link Python test file:
   ```python
   def add(a, b):
       return a + b
   
   def test_add():
       assert add(2, 3) == 5
   ```
3. Click "Analyze"
4. Select LLM: Claude
5. Start analysis

**Expected Results:**
- ✅ Analysis starts
- ✅ Real-time progress updates
- ✅ Mutations generated
- ✅ Tests executed against mutations
- ✅ Mutation score calculated
- ✅ Elite HTML report generated

**Validation:**
```
Expected mutation score: 80-100% (for simple test)
Expected analysis time: 2-5 minutes
Supported operators: AOR, ROR, LCR, BCR, STR, etc.
```

---

### **2.3 View Python Analysis Results**

**Steps:**
1. Wait for analysis to complete
2. View results in dashboard
3. Open elite HTML report

**Expected Results:**
- ✅ Mutation score displayed
- ✅ Coverage metrics shown
- ✅ Survived mutants listed
- ✅ Report is professional
- ✅ Mutations visualized
- ✅ Test effectiveness metrics

---

## 📜 **Scenario 3: JavaScript Project Analysis**

### **3.1 Create JavaScript Project**

**Steps:**
1. Dashboard → "New Project"
2. Enter:
   - Name: `JavaScript Calculator`
   - Language: `JavaScript`
   - Framework: `Jest`
3. Create project

**Expected Results:**
- ✅ JavaScript project created
- ✅ Framework auto-detected as Jest

---

### **3.2 Run JavaScript Mutation Analysis**

**Steps:**
1. Upload JavaScript test file:
   ```javascript
   function add(a, b) {
     return a + b;
   }
   
   test('add works', () => {
     expect(add(2, 3)).toBe(5);
   });
   ```
2. Start analysis
3. Select LLM provider

**Expected Results:**
- ✅ Analysis starts
- ✅ JavaScript mutations generated
- ✅ 17+ operators applied
- ✅ Tests run against mutations
- ✅ Results calculated
- ✅ Report generated

---

### **3.3 JavaScript + TypeScript Support**

**Steps:**
1. Create TypeScript project
2. Upload `.ts` file with types
3. Run analysis

**Expected Results:**
- ✅ TypeScript compiles correctly
- ✅ Type information used
- ✅ Mutations respect types
- ✅ Analysis successful

---

## 🔄 **Scenario 4: Real-time WebSocket Updates**

### **4.1 Live Progress Streaming**

**Steps:**
1. Start analysis
2. Open browser dev tools (F12)
3. Go to Network → WS tab
4. Watch WebSocket messages

**Expected Results:**
- ✅ WebSocket connection established
- ✅ Real-time progress messages received
- ✅ Mutation progress updates flowing
- ✅ No lag in updates
- ✅ Connection stable throughout analysis

**Validation:**
```javascript
// Check WebSocket in console
const messages = [];
ws.addEventListener('message', (e) => {
  console.log('Update:', JSON.parse(e.data));
  messages.push(e.data);
});
```

---

### **4.2 Live Dashboard Updates**

**Steps:**
1. Start analysis
2. Watch dashboard in real-time
3. Check progress bar updates

**Expected Results:**
- ✅ Progress bar updates live
- ✅ Mutation count updates
- ✅ Test results update in real-time
- ✅ No page refresh needed
- ✅ Smooth animations

---

## 👥 **Scenario 5: Team Collaboration**

### **5.1 Create Organization**

**Steps:**
1. Settings → Organizations
2. Click "Create Organization"
3. Enter:
   - Name: `Test Team`
   - Description: `Testing Team`
4. Create

**Expected Results:**
- ✅ Organization created
- ✅ User is admin
- ✅ Can manage organization

---

### **5.2 Create Team**

**Steps:**
1. Organization → Create Team
2. Enter name: `QA Team`
3. Add team members

**Expected Results:**
- ✅ Team created
- ✅ Can add members
- ✅ Members can access projects

---

### **5.3 Share Project with Team**

**Steps:**
1. Project → Settings
2. Add team: `QA Team`
3. Set permissions: View, Analyze

**Expected Results:**
- ✅ Project shared
- ✅ Team members can see
- ✅ Permissions enforced
- ✅ Activity logged

---

## 📊 **Scenario 6: Reporting & Analytics**

### **6.1 Elite HTML Report**

**Steps:**
1. Complete analysis
2. Download HTML report
3. Open in browser

**Expected Results:**
- ✅ Report is self-contained
- ✅ No external dependencies
- ✅ Beautiful formatting
- ✅ All metrics visible
- ✅ Mutations mapped
- ✅ Trends shown

---

### **6.2 Dashboard Metrics**

**Steps:**
1. Go to dashboard
2. Check metrics cards:
   - Total projects
   - Total analyses
   - Avg mutation score
   - Avg coverage

**Expected Results:**
- ✅ All metrics calculated
- ✅ Numbers accurate
- ✅ Charts displayed
- ✅ Trends visible

---

### **6.3 Analysis History**

**Steps:**
1. Project → Analysis History
2. View past analyses
3. Compare results

**Expected Results:**
- ✅ All analyses listed
- ✅ Timestamps correct
- ✅ Scores tracked
- ✅ Can compare results

---

## 🔌 **Scenario 7: API Endpoints**

### **7.1 Authentication Endpoints**

| Endpoint | Method | Test |
|----------|--------|------|
| `/auth/register` | POST | Create account |
| `/auth/login` | POST | Login |
| `/auth/refresh` | POST | Refresh token |
| `/auth/logout` | POST | Logout |
| `/auth/me` | GET | Get profile |
| `/auth/change-password` | POST | Change password |

**Test Each:**
```bash
# Register
curl -X POST http://localhost:8765/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"Test123!","name":"User"}'

# Login
curl -X POST http://localhost:8765/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"Test123!"}'

# Get profile
curl http://localhost:8765/api/v1/auth/me \
  -H "Authorization: Bearer <token>"
```

---

### **7.2 Project Endpoints**

| Endpoint | Method | Test |
|----------|--------|------|
| `/projects` | GET | List projects |
| `/projects` | POST | Create project |
| `/projects/{id}` | GET | Get project |
| `/projects/{id}` | PUT | Update project |
| `/projects/{id}` | DELETE | Delete project |

---

### **7.3 Analysis Endpoints**

| Endpoint | Method | Test |
|----------|--------|------|
| `/analyses` | GET | List analyses |
| `/analyses` | POST | Start analysis |
| `/analyses/{id}` | GET | Get analysis |
| `/analyses/{id}/report` | GET | Get report |

---

### **7.4 OAuth Endpoints**

| Endpoint | Method | Test |
|----------|--------|------|
| `/oauth/github/login` | GET | Get GitHub URL |
| `/oauth/github/callback` | POST | Handle callback |
| `/oauth/google/login` | GET | Get Google URL |
| `/oauth/google/callback` | POST | Handle callback |
| `/oauth/status` | GET | Check status |

---

## 🔧 **Scenario 8: VSCode Extension**

### **8.1 Extension Installation**

**Steps:**
1. Install from Marketplace
   ```
   code --install-extension achieverthoughts.qamill-mutation-testing
   ```
2. Reload VSCode

**Expected Results:**
- ✅ Extension installs
- ✅ No errors
- ✅ QAMill icon appears in activity bar

---

### **8.2 Extension Commands**

**Steps:**
1. Open Command Palette: Ctrl+Shift+P
2. Type "QAMill"
3. See all commands

**Expected Results:**
- ✅ QAMill commands listed
- ✅ Commands work
- ✅ No errors

**Commands to test:**
- `QAMill: Start Analysis`
- `QAMill: Login`
- `QAMill: Logout`
- `QAMill: Open Dashboard`

---

### **8.3 Sidebar Explorer**

**Steps:**
1. Click QAMill icon in activity bar
2. View sidebar
3. Check:
   - Projects list
   - Recent analyses
   - Statistics

**Expected Results:**
- ✅ Sidebar displays
- ✅ All views load
- ✅ Can interact with items

---

### **8.4 Settings Panel**

**Steps:**
1. Settings → QAMill
2. Configure:
   - API URL: http://localhost:8765
   - LLM Provider: Claude
   - Auto-healing: On

**Expected Results:**
- ✅ All settings visible
- ✅ Can change values
- ✅ Settings persist

---

## 🔄 **Scenario 9: End-to-End Workflow**

### **9.1 Complete Python Workflow**

**Timeline:** ~10 minutes

**Steps:**
1. ✅ Register new account
2. ✅ Create Python project
3. ✅ Upload test file
4. ✅ Start analysis
5. ✅ Watch real-time updates
6. ✅ View results
7. ✅ Download report
8. ✅ Share with team
9. ✅ View analytics

**Validation:**
- All steps complete
- No errors encountered
- Results accurate
- Report professional

---

### **9.2 Complete JavaScript Workflow**

**Timeline:** ~10 minutes

**Steps:**
1. ✅ Create JavaScript project
2. ✅ Upload Jest test
3. ✅ Auto-detect framework
4. ✅ Run analysis
5. ✅ Monitor progress
6. ✅ View JavaScript mutations
7. ✅ Compare with Python
8. ✅ Generate report

**Validation:**
- JavaScript mutations applied correctly
- Same 17+ operators
- Results consistent
- Performance similar

---

### **9.3 Complete OAuth Workflow**

**Timeline:** ~5 minutes

**Steps:**
1. ✅ Click GitHub login
2. ✅ Authenticate
3. ✅ Redirect back
4. ✅ Account created
5. ✅ Dashboard loaded
6. ✅ Profile updated
7. ✅ Avatar displayed

**Validation:**
- OAuth flow seamless
- User info synced
- No errors

---

## 🐛 **Scenario 10: Error Handling**

### **10.1 Invalid Login**

**Steps:**
1. Login with wrong password
2. Check error message

**Expected Results:**
- ✅ Clear error message
- ✅ No password revealed
- ✅ Can retry

---

### **10.2 Network Errors**

**Steps:**
1. Stop backend server
2. Try API call
3. Check error handling

**Expected Results:**
- ✅ Graceful error
- ✅ User-friendly message
- ✅ Can retry

---

### **10.3 Invalid File**

**Steps:**
1. Upload invalid test file
2. Start analysis

**Expected Results:**
- ✅ Validation error
- ✅ Clear message
- ✅ Suggests fix

---

## ✅ **Validation Checklist**

### **Authentication** (6 tests)
- [ ] Email/password registration
- [ ] Email/password login
- [ ] Token refresh
- [ ] GitHub OAuth
- [ ] Google OAuth
- [ ] Logout

### **Python Analysis** (3 tests)
- [ ] Create project
- [ ] Run analysis
- [ ] View results

### **JavaScript Analysis** (3 tests)
- [ ] Create project
- [ ] Run analysis
- [ ] View results

### **Real-time Updates** (2 tests)
- [ ] WebSocket connection
- [ ] Live dashboard updates

### **Team Collaboration** (3 tests)
- [ ] Create organization
- [ ] Create team
- [ ] Share project

### **Reporting** (3 tests)
- [ ] HTML report generation
- [ ] Dashboard metrics
- [ ] Analysis history

### **API Endpoints** (3 tests)
- [ ] Auth endpoints
- [ ] Project endpoints
- [ ] Analysis endpoints

### **VSCode Extension** (4 tests)
- [ ] Installation
- [ ] Commands
- [ ] Sidebar
- [ ] Settings

### **End-to-End** (3 tests)
- [ ] Python workflow
- [ ] JavaScript workflow
- [ ] OAuth workflow

### **Error Handling** (3 tests)
- [ ] Invalid login
- [ ] Network errors
- [ ] Invalid file

---

## 📋 **Execution Plan**

### **Phase 1: Core (Day 1)**
- Authentication (6 tests)
- Python Analysis (3 tests)
- JavaScript Analysis (3 tests)

### **Phase 2: Real-time (Day 2)**
- WebSocket (2 tests)
- Dashboard (1 test)

### **Phase 3: Collaboration (Day 3)**
- Team features (3 tests)
- Reporting (3 tests)

### **Phase 4: Integration (Day 4)**
- API endpoints (3 tests)
- VSCode extension (4 tests)
- End-to-end (3 tests)

### **Phase 5: Polish (Day 5)**
- Error handling (3 tests)
- Edge cases
- Performance

---

## 🎯 **Success Criteria**

✅ **All 40+ tests pass**  
✅ **No critical bugs**  
✅ **Performance acceptable** (<10s per analysis)  
✅ **UI/UX smooth**  
✅ **Reports professional**  
✅ **Real-time updates working**  
✅ **Error messages clear**  
✅ **Documentation complete**  

---

## 📊 **Test Results Template**

```
Scenario: [Name]
Steps: [List of steps]
Expected: [Expected results]
Actual: [Actual results]
Status: ✅ PASS / ❌ FAIL
Notes: [Any issues or observations]
```

---

**Ready to validate QAMill v1.2.0 for production launch!** 🚀

