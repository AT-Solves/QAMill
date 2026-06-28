# QAMill VSIX Upload - Quick Start (3 Simple Steps)

**No PAT Token Needed - Web Upload Only**

---

## ⚡ 3 Minutes to Launch

### **Step 1: Build VSIX (2 min)**

```bash
cd vscode-extension
npm install
npm run compile
npx vsce package --allow-missing-repository
```

✅ Creates: `qamill-mutation-testing-1.2.0.vsix`

---

### **Step 2: Go to Marketplace (1 min)**

**LINK:** https://marketplace.visualstudio.com/manage/publishers/achieverthoughts

1. Sign in with Microsoft account
2. Find "QAMill" in your extensions
3. Click **"New Release"** or **"Update"**

---

### **Step 3: Upload VSIX (No coding needed!)**

1. Click **"Upload VSIX"** button
2. Select file: `qamill-mutation-testing-1.2.0.vsix`
3. Fill in:
   - **Version:** 1.2.0
   - **Display Name:** QAMill — AI Mutation Testing
   - **Description:** Enterprise-grade mutation testing for Python and JavaScript
4. Click **"Publish"**

**DONE! ✅**

---

## 🔗 Your Extension Link

After publishing (wait 15 min):

```
https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing
```

---

## 📥 How Users Install

```
Ctrl+Shift+X → Search "QAMill" → Install
```

**OR**

```bash
code --install-extension achieverthoughts.qamill-mutation-testing
```

---

## 📋 Marketplace Form Fields (Copy-Paste)

### Display Name
```
QAMill — AI Mutation Testing
```

### Short Description
```
Enterprise-grade mutation testing for Python and JavaScript. Real-time analysis, elite reports, and team collaboration.
```

### Long Description
```
QAMill: AI-Powered Test Quality Governance

Transform your test suite with intelligent mutation testing.

🚀 FEATURES:
✅ Python & JavaScript/TypeScript support
✅ Real-time mutation analysis
✅ Team collaboration (OAuth login)
✅ Professional HTML reports
✅ 8 LLM providers (Claude, GPT-4, Gemini, etc.)
✅ Enterprise security (RBAC, audit logs)

QUICK START:
1. Install QAMill extension
2. Login with GitHub or Google
3. Select your project
4. Press Ctrl+Shift+Q to analyze
5. View elite HTML report

SUPPORTED FRAMEWORKS:
Python: pytest, unittest, Django, FastAPI
JavaScript: Jest, Vitest, Mocha, Jasmine

DOCUMENTATION:
📚 Docs: https://docs.qamill.io
🔧 GitHub: https://github.com/yourusername/qamill
💬 Issues: https://github.com/yourusername/qamill/issues
```

### Keywords
```
mutation-testing, qa, testing, test-quality, python, javascript, typescript, code-coverage, ai
```

### Repository
```
https://github.com/yourusername/qamill
```

### Issues
```
https://github.com/yourusername/qamill/issues
```

### License
```
MIT
```

---

## ✅ File Locations

**VSIX File Location:**
```
vscode-extension/qamill-mutation-testing-1.2.0.vsix
```

**Icon Location:**
```
vscode-extension/media/qamill-logo.png
```

---

## 🎯 What Happens Next

| Time | Status |
|------|--------|
| **Now** | Upload starts |
| **2 min** | Upload completes |
| **15 min** | Marketplace indexes |
| **30 min** | Searchable on Marketplace |
| **1 hour** | First users installing |

---

## 🆘 Common Issues & Fixes

### "VSIX File Not Found"
```bash
# Make sure you're in vscode-extension folder and built it:
npm install
npm run compile
npx vsce package --allow-missing-repository
```

### "Invalid or Corrupted VSIX"
```bash
# Rebuild it:
rm -rf out
npm run compile
npx vsce package --allow-missing-repository
```

### "Extension Not on Marketplace"
- Wait 15-30 minutes (indexing)
- Clear cache: `rm -rf ~/.vscode`
- Restart VSCode
- Search from Marketplace web directly

---

## 🚀 Launch Checklist

- [ ] Build VSIX: `npx vsce package`
- [ ] VSIX file exists: `ls qamill-mutation-testing-1.2.0.vsix`
- [ ] Go to Marketplace manager
- [ ] Click "New Release" or "Update"
- [ ] Upload VSIX file
- [ ] Fill marketplace form
- [ ] Click Publish
- [ ] Wait 15 minutes
- [ ] Search for "QAMill" on Marketplace
- [ ] Verify it shows up
- [ ] Test install in VSCode

---

## 🎉 Success!

Your extension is now on the **Visual Studio Marketplace** and available to **millions of developers**!

**Marketplace URL:**
```
https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing
```

**Share with team:**
```
"Check out QAMill on VSCode Marketplace: 
https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing"
```

---

## 📞 Support

- **Full Guide:** `MARKETPLACE_MANUAL_UPLOAD.md` (in this repo)
- **Issues:** https://github.com/yourusername/qamill/issues
- **Email:** support@qamill.io

---

**That's it! You're live on Visual Studio Marketplace! 🎉🚀**
