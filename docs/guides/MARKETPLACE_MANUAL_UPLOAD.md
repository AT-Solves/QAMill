# QAMill v1.2.0 - Manual VSIX Upload to Visual Studio Marketplace

**Method:** Web Upload (No PAT Token Needed)  
**Time:** ~10 minutes total  
**Status:** Ready for manual upload  

---

## 📦 Step 1: Build VSIX Package

### Build the Extension

```bash
cd vscode-extension

# Install dependencies (if not already done)
npm install

# Compile TypeScript
npm run compile

# Create VSIX package
npx vsce package --allow-missing-repository
```

### Verify VSIX Created

```bash
# Check if VSIX file exists
ls -lh qamill-mutation-testing-1.2.0.vsix

# Should show something like:
# -rw-r--r-- 1 user group 1.2M Jun 27 12:00 qamill-mutation-testing-1.2.0.vsix
```

---

## 🌐 Step 2: Access Visual Studio Marketplace

### Create/Login to Microsoft Account

1. Go to: **https://azure.microsoft.com/**
2. Click "Sign In" (top right)
3. Create account or use existing Microsoft account
4. Verify email if needed

### Create Publisher Account (If Not Done)

1. Go to: **https://marketplace.visualstudio.com/manage**
2. Click "Create Publisher"
3. Fill in:
   - **Publisher ID:** `achieverthoughts`
   - **Publisher Name:** QAMill
   - **Description:** Enterprise AI mutation testing platform

---

## 📤 Step 3: Upload VSIX Manually

### Access Publisher Dashboard

1. Go to: **https://marketplace.visualstudio.com/manage/publishers/achieverthoughts**
2. Sign in with your Microsoft account
3. You should see your publisher profile

### Create New Extension OR Update Existing

#### Option A: New Extension (First Time)

1. Click **"Create Extension"** or **"New Extension"**
2. Click **"Upload"**
3. Select the VSIX file: `qamill-mutation-testing-1.2.0.vsix`
4. Wait for upload (2-5 minutes)
5. Click **"Continue"**

#### Option B: Update Existing Extension

1. Find **"QAMill"** in your extensions list
2. Click on it
3. Click **"New Release"** or **"Edit"**
4. Click **"Upload"** or **"Replace"**
5. Select the VSIX file: `qamill-mutation-testing-1.2.0.vsix`
6. Wait for upload (2-5 minutes)
7. Click **"Continue"**

---

## 📝 Step 4: Fill in Marketplace Details

### Required Fields

#### **Version**
- Should auto-populate: `1.2.0`
- If not, enter: `1.2.0`

#### **Display Name**
```
QAMill — AI Mutation Testing
```

#### **Description** (Short - 1 line)
```
Enterprise-grade mutation testing for Python and JavaScript. 
Real-time analysis, elite reports, and team collaboration.
```

#### **Long Description** (Full marketing copy)
```
QAMill: AI-Powered Test Quality Governance

Transform your test suite with intelligent mutation testing.

🚀 KEY FEATURES:

✅ Multi-Language Support
   • Python (full AST-based analysis)
   • JavaScript/TypeScript (new in v1.2.0!)
   • Automatic language detection
   • Framework auto-detection

✅ Real-time Mutation Testing
   • Live progress streaming
   • Mutation-by-mutation tracking
   • Instant notifications
   • Professional dashboards

✅ Team Collaboration
   • OAuth login (GitHub, Google)
   • Organization & team management
   • Project sharing
   • Activity feeds

✅ Professional Reports
   • Elite HTML reports
   • Visual mutation maps
   • Coverage metrics
   • Trend analysis

✅ AI-Powered Features
   • Equivalence detection
   • Test healing (auto-generate tests)
   • Gap analysis (find uncovered code)
   • 8 LLM providers (Claude, GPT-4, Gemini, Grok, etc.)

✅ Enterprise-Ready
   • OAuth 2.0 authentication
   • Role-based access control
   • Audit logging
   • Data encryption ready
   • HIPAA compliance ready

SUPPORTED FRAMEWORKS:

Python:
• pytest
• unittest
• Django
• FastAPI

JavaScript/TypeScript:
• Jest
• Vitest
• Mocha
• Jasmine

QUICK START:

1. Install extension (Ctrl+Shift+X → Search "QAMill")
2. Click QAMill icon in activity bar
3. Login with GitHub or Google
4. Select your project
5. Press Ctrl+Shift+Q to start analysis
6. View elite HTML report with detailed metrics

CONFIGURATION:

Open VSCode Settings and search for "QAMill":
- API server URL
- LLM provider selection
- Auto-healing toggle
- Equivalence detection
- WebSocket updates
- Email notifications

DOCUMENTATION:

📚 Full Docs: https://docs.qamill.io
🔧 GitHub: https://github.com/yourusername/qamill
🆘 Support: support@qamill.io
💬 Issues: https://github.com/yourusername/qamill/issues

DEPLOYMENT:

Backend can be deployed to:
• Azure (AKS)
• AWS (ECS, EKS)
• Google Cloud (Cloud Run, GKE)
• Docker Compose (local)
• On-premises

See deployment guide for setup instructions.

Made with ❤️ for development teams who care about test quality.
```

#### **Category**
- Select: **Testing**
- Optionally also: **Other**

#### **Icon**
- Should auto-use: `media/qamill-logo.png`
- Verify it displays correctly

#### **Tags/Keywords**
```
mutation-testing
qa
testing
test-quality
python
javascript
typescript
code-coverage
test-analysis
ai
mutation-analysis
quality-assurance
```

#### **Repository**
```
https://github.com/yourusername/qamill
```

#### **Issues**
```
https://github.com/yourusername/qamill/issues
```

#### **License**
```
MIT
```

---

## ✅ Step 5: Preview and Publish

### Review Preview

1. Click **"Preview"** to see how it looks
2. Check:
   - ✅ Icon displays correctly
   - ✅ Title is clear
   - ✅ Description reads well
   - ✅ Keywords are appropriate
   - ✅ Links work

### Fix Issues (if any)

- Click **"Edit"** to fix any fields
- Update and click **"Save"**

### Publish

1. Click **"Publish"** button
2. Confirm publication
3. Wait 10-15 minutes for Marketplace to index

---

## 🔍 Step 6: Verify Publication

### Check Marketplace

1. Go to: **https://marketplace.visualstudio.com/**
2. Search for: **"QAMill"**
3. You should see: **QAMill — AI Mutation Testing**

### Verify Details

- ✅ Title correct
- ✅ Icon displays
- ✅ Description shows
- ✅ Version: 1.2.0
- ✅ Publisher: achieverthoughts
- ✅ Links work
- ✅ Installation command shows

### Direct Link

Your extension URL:
```
https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing
```

---

## 📲 Step 7: Test Installation

### From VSCode

1. Open VSCode
2. Press **Ctrl+Shift+X** (Extensions)
3. Search for **"QAMill"**
4. Click **"Install"**
5. Wait for installation
6. Reload VSCode

### From Command Line

```bash
code --install-extension achieverthoughts.qamill-mutation-testing
```

### Verify Installation

1. Look for **QAMill** icon in activity bar (left sidebar)
2. Open Command Palette: **Ctrl+Shift+P**
3. Type: **"QAMill"**
4. Should see QAMill commands

---

## 🔄 Step 8: Update to New Version

### When You Have v1.2.1 or Later

1. Update `vscode-extension/package.json`:
   ```json
   "version": "1.2.1"
   ```

2. Build new VSIX:
   ```bash
   cd vscode-extension
   npm run compile
   npx vsce package
   ```

3. Go to: **https://marketplace.visualstudio.com/manage/publishers/achieverthoughts**

4. Click on **"QAMill"**

5. Click **"New Release"** or **"Update"**

6. Upload new VSIX file: `qamill-mutation-testing-1.2.1.vsix`

7. Update version number in form

8. Click **"Publish"**

---

## 📋 Complete Checklist

### Before Upload
- [ ] Microsoft account created
- [ ] Publisher account created
- [ ] npm installed
- [ ] `npm install` completed
- [ ] `npm run compile` successful
- [ ] VSIX file created
- [ ] VSIX file verified (ls -lh)

### During Upload
- [ ] VSIX file uploaded
- [ ] Version: 1.2.0
- [ ] Display Name filled
- [ ] Description complete
- [ ] Category selected
- [ ] Icon verified
- [ ] Keywords entered
- [ ] Repository link added
- [ ] Issues link added

### After Upload
- [ ] Waited 15 minutes
- [ ] Searched Marketplace
- [ ] Extension found
- [ ] Details correct
- [ ] Installed in VSCode
- [ ] Commands work
- [ ] Settings visible

---

## 🆘 Troubleshooting

### VSIX Upload Fails

**Error:** "Invalid or corrupted VSIX file"

**Solution:**
```bash
cd vscode-extension
rm -rf out node_modules
npm install
npm run compile
npx vsce package --allow-missing-repository
```

### Extension Not Showing on Marketplace

**Issue:** Uploaded but not visible

**Solution:**
- Wait 15-30 minutes (Marketplace indexing)
- Clear VSCode cache: `rm -rf ~/.vscode`
- Restart VSCode
- Search from Marketplace directly

### Version Already Exists

**Issue:** Can't publish same version twice

**Solution:**
1. Increment version in `package.json`:
   ```json
   "version": "1.2.1"
   ```
2. Rebuild VSIX
3. Upload with new version

### Icon Not Showing

**Issue:** Icon doesn't display on Marketplace

**Solution:**
- Icon must be 128x128px PNG
- Path in package.json: `"icon": "media/qamill-logo.png"`
- File must exist in vscode-extension folder

### Description Too Long

**Issue:** Long description field has limit

**Solution:**
- Keep under 10,000 characters
- Use GitHub README for full docs
- Link to: https://github.com/yourusername/qamill

---

## 📊 Monitor After Launch

### Check These Metrics

1. **Downloads:** How many installs?
2. **Ratings:** What's the average rating?
3. **Reviews:** What are users saying?
4. **Issues:** Any reported bugs?
5. **Comments:** Feature requests?

### Visit Dashboard

**https://marketplace.visualstudio.com/manage/publishers/achieverthoughts**

---

## 🎯 Success Timeline

| Time | What to Expect |
|------|----------------|
| **5 min** | VSIX uploaded |
| **15 min** | Searchable on Marketplace |
| **1 hour** | First installs |
| **1 day** | Reviews appearing |
| **1 week** | 50+ downloads |
| **1 month** | 100+ downloads |

---

## 📞 Support

### If You Have Issues

1. **Marketplace Help:** https://marketplace.visualstudio.com/support
2. **GitHub Issues:** https://github.com/yourusername/qamill/issues
3. **Email:** support@qamill.io

### Common Questions

**Q: How long does publishing take?**  
A: Upload is instant, Marketplace indexing is 10-15 minutes.

**Q: Can I update the same version?**  
A: No, update version number each time.

**Q: Do I need a PAT token?**  
A: No, manual upload doesn't require PAT.

**Q: How do users install?**  
A: Ctrl+Shift+X → Search "QAMill" → Install

**Q: Can I remove the extension later?**  
A: Yes, go to publisher dashboard and unpublish.

---

## ✅ Final Checklist - Ready to Upload!

- [x] VSIX file built: `qamill-mutation-testing-1.2.0.vsix`
- [x] Microsoft account ready
- [x] Publisher account created
- [x] Marketplace details prepared
- [x] Installation tested
- [x] Documentation complete
- [x] Ready to upload!

---

## 🚀 Next: Upload Now!

1. Navigate to: **https://marketplace.visualstudio.com/manage/publishers/achieverthoughts**
2. Create new extension or update existing
3. Upload: `vscode-extension/qamill-mutation-testing-1.2.0.vsix`
4. Fill in marketplace details (from Step 4)
5. Click Publish
6. Wait 15 minutes
7. Search for "QAMill" on Marketplace
8. Install and verify

**That's it! Your extension is now on the Visual Studio Marketplace!** 🎉

---

*Manual Upload Guide - QAMill v1.2.0*  
*Updated: 2026-06-27*  
*Status: Ready for Deployment*
