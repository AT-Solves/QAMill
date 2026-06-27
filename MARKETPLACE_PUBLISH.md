# QAMill v1.2.0 - Visual Studio Marketplace Publishing Guide

**Extension:** QAMill — AI Mutation Testing  
**Version:** 1.2.0  
**Status:** Ready for Publication  
**Platform:** Visual Studio Code  

---

## Prerequisites

### 1. Create Microsoft Account
- Go to https://azure.microsoft.com/
- Create a free Microsoft Account if you don't have one

### 2. Create Publisher Account
- Go to https://marketplace.visualstudio.com/manage
- Sign in with your Microsoft Account
- Click "Create Publisher"
- Fill in publisher details:
  - **Publisher ID:** `achieverthoughts` (or your ID)
  - **Publisher Name:** QAMill
  - **Description:** Enterprise AI mutation testing platform

### 3. Create Personal Access Token (PAT)
```bash
# In Azure DevOps:
# 1. Go to https://dev.azure.com/
# 2. Click your avatar → Security
# 3. Click "Personal access tokens"
# 4. Click "New Token"
# 5. Name: "VSCode Extension Publishing"
# 6. Scopes: Check "Marketplace" → "Manage"
# 7. Expiration: 90 days (or longer)
# 8. Create token
# 9. COPY THE TOKEN (you can only see it once!)
```

### 4. Install vsce (Visual Studio Code Extension CLI)
```bash
npm install -g vsce
```

### 5. Verify Installation
```bash
vsce --version
```

---

## Build and Package Extension

### Step 1: Install Dependencies
```bash
cd vscode-extension
npm install
```

### Step 2: Compile TypeScript
```bash
npm run compile
```

### Step 3: Create VSIX Package
```bash
vsce package
```

This creates `qamill-mutation-testing-1.2.0.vsix` in the current directory.

### Step 4: Verify Package
```bash
# Check the VSIX was created
ls -lh qamill-mutation-testing-1.2.0.vsix

# Extract and inspect (optional)
unzip -l qamill-mutation-testing-1.2.0.vsix
```

---

## Test Extension Locally

### Install Locally
```bash
# In VSCode
# 1. Open Extensions panel (Ctrl+Shift+X)
# 2. Click "..." menu → "Install from VSIX..."
# 3. Select qamill-mutation-testing-1.2.0.vsix
```

### Test Features
- ✅ Extension loads without errors
- ✅ Commands appear in command palette (Ctrl+Shift+P)
- ✅ Context menus work
- ✅ Settings configurable
- ✅ No console errors

---

## Publish to Marketplace

### Option 1: Using PAT (Recommended)

```bash
cd vscode-extension

# Login with PAT
vsce login achieverthoughts

# When prompted, paste your Personal Access Token
# (It will ask for the token, not your password)

# Publish
vsce publish
```

### Option 2: Using PAT Directly

```bash
cd vscode-extension

vsce publish -p <YOUR_PAT_TOKEN>

# Example:
vsce publish -p vsabcde123xyz
```

### Option 3: Web Upload (Manual)

1. Go to https://marketplace.visualstudio.com/manage/publishers/achieverthoughts
2. Click "Create Extension" or find QAMill
3. Upload the `.vsix` file manually
4. Fill in marketplace details
5. Publish

---

## Complete Package Checklist

- [x] README.md updated
- [x] CHANGELOG.md with v1.2.0 changes
- [x] LICENSE file included
- [x] Extension icon (qamill-logo.png)
- [x] package.json version updated to 1.2.0
- [x] All dependencies specified
- [x] TypeScript compiles without errors
- [x] All commands defined
- [x] All menus configured
- [x] All settings documented
- [x] Extension tested locally

---

## What's New in v1.2.0

### New Features
✨ **Multi-Language Support**
- Python mutation testing (full AST engine)
- JavaScript/TypeScript support (new!)
- Automatic language detection
- Framework auto-detection (pytest, Jest, Vitest, Mocha)

✨ **Real-time Updates**
- WebSocket integration
- Live mutation progress
- Real-time test results
- Instant notifications

✨ **Team Collaboration**
- OAuth login (GitHub, Google)
- Organization & team management
- Project sharing
- Activity feeds

✨ **Enhanced Reports**
- Elite HTML reports
- Visual dashboards
- Trend analysis
- Coverage metrics

✨ **Improved UI**
- Sidebar explorer
- Activity sidebar
- Statistics dashboard
- Command palette integration

### Breaking Changes
- None

### Bug Fixes
- Fixed WebSocket connection issues
- Improved error handling
- Better token refresh mechanism
- Fixed OAuth callback handling

---

## Marketplace Store Details

### Title
**QAMill — AI Mutation Testing**

### Short Description
Enterprise-grade mutation testing for Python and JavaScript. Real-time analysis, elite reports, and team collaboration.

### Full Description
```
QAMill: AI-Powered Test Quality Governance

Transform your test suite with intelligent mutation testing.

🚀 KEY FEATURES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Multi-Language Support
   • Python (full AST-based analysis)
   • JavaScript/TypeScript (regex + AST)
   • Auto-detect language & framework

✅ Real-time Mutation Testing
   • Live progress streaming
   • Instant test results
   • Real-time dashboards
   • Activity feeds

✅ Team Collaboration
   • OAuth login (GitHub, Google)
   • Organization accounts
   • Team management
   • Project sharing

✅ Professional Reports
   • Elite HTML reports
   • Visual dashboards
   • Mutation score tracking
   • Coverage analysis
   • Trend analysis

✅ LLM-Powered Intelligence
   • Anthropic Claude
   • OpenAI GPT-4
   • Google Gemini
   • xAI Grok
   • DeepSeek
   • Mistral
   • Local Ollama

✅ Enterprise-Grade
   • JWT authentication
   • OAuth 2.0
   • RBAC (role-based access)
   • Audit logging
   • Data encryption ready
   • HIPAA-ready

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUICK START:

1. Install extension
2. Login with GitHub or Google OAuth
3. Select project
4. Run Ctrl+Shift+Q to start analysis
5. View results in elite HTML report

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SETTINGS:

• API Server URL (default: localhost:8765)
• LLM Provider (Claude, GPT, Grok, Ollama, etc.)
• Auto-healing (auto-generate tests)
• Equivalence detection
• WebSocket updates
• Email notifications

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEPLOYMENT:

QAMill backend can be deployed:
• Azure Kubernetes Service (AKS)
• Docker Compose
• On-premises
• Cloud (AWS, GCP, Azure)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOCUMENTATION:

📚 Full Docs: https://docs.qamill.io
🔧 Setup Guide: https://github.com/yourusername/qamill
🆘 Support: support@qamill.io
💬 Community: https://github.com/yourusername/qamill/discussions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERSION 1.2.0 HIGHLIGHTS:

🎉 Multi-language support (Python + JavaScript)
🎉 Real-time WebSocket updates
🎉 Team collaboration features
🎉 Professional reporting
🎉 Enterprise security

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Made with ❤️ for development teams who care about test quality.
```

### Keywords
```
mutation-testing, qa, testing, test-quality, python, javascript, 
typescript, code-coverage, test-analysis, ai, mutation, 
quality-assurance, test-generation, mutation-analysis
```

### Categories
- Testing
- Other

### Homepage
https://qamill.io

### Repository
https://github.com/yourusername/qamill

### Bugs/Issues
https://github.com/yourusername/qamill/issues

### License
MIT

---

## After Publication

### Monitor Metrics
- https://marketplace.visualstudio.com/manage/publishers/achieverthoughts
- View downloads, reviews, ratings
- Check user feedback
- Monitor issues

### Update Extension

```bash
# Make changes to source
# Update version in package.json

# Compile and test
npm run compile
npm test

# Create new package
vsce package

# Publish new version
vsce publish -p <YOUR_PAT_TOKEN>
```

### Automatic Updates
VSCode automatically updates extensions unless users disable it.

---

## Troubleshooting

### "Invalid Publisher"
- Verify publisher ID matches in package.json
- Check publisher is activated on Marketplace

### "VSIX Validation Failed"
- Run `vsce package --allow-missing-repository` to skip git check
- Ensure all files in package.json exist
- Check TypeScript compiles: `npm run compile`

### "Token Expired"
- Generate new Personal Access Token
- Log out: `vsce logout`
- Log in again: `vsce login achieverthoughts`

### "File Not Found in VSIX"
- Verify .vscodeignore settings
- Check all referenced files exist
- Run `vsce ls` to list files in package

### "Extension Not Showing in Marketplace"
- Wait 10-15 minutes for indexing
- Clear VSCode cache: `rm -rf ~/.vscode`
- Try manually installing from: https://marketplace.visualstudio.com

---

## Complete Commands Reference

```bash
# Setup
npm install -g vsce                    # Install vsce globally

# Login
vsce login achieverthoughts            # Interactive login with PAT

# Build
npm install                            # Install dependencies
npm run compile                        # Compile TypeScript

# Package
vsce package                           # Create VSIX (v1.2.0)
vsce ls                                # List files in VSIX

# Test locally
# In VSCode: Ctrl+Shift+X → ... → Install from VSIX

# Publish
vsce publish                           # Publish using stored token
vsce publish -p <TOKEN>                # Publish with token
vsce publish minor                     # Auto-increment version

# Logout
vsce logout achieverthoughts           # Remove stored token
```

---

## Publishing Timeline

```
Day 1: Prepare
  □ Update package.json version
  □ Update README.md
  □ Write CHANGELOG
  □ Test locally

Day 2: Build
  □ npm install
  □ npm run compile
  □ vsce package
  □ Verify VSIX

Day 3: Publish
  □ Create PAT token
  □ vsce login
  □ vsce publish
  □ Verify on Marketplace
  □ Announce release
```

---

## Marketplace Best Practices

✅ **Icon**: Use consistent 128x128px logo  
✅ **README**: Clear, with screenshots  
✅ **Keywords**: Include relevant terms  
✅ **Description**: Professional, feature-focused  
✅ **Version**: Semantic versioning  
✅ **Changelog**: Document changes  
✅ **Repository**: Link to GitHub  
✅ **License**: Include MIT/Apache/etc  
✅ **Tests**: Verify locally first  
✅ **Support**: Provide issue tracker link  

---

## Success Metrics

Track after publication:

| Metric | Target |
|--------|--------|
| **Downloads (1st week)** | 100+ |
| **Rating (avg)** | 4.0+ stars |
| **Active Users** | 50+ |
| **Issues/Bugs** | <5% of users |
| **Reviews** | 3+ positive |

---

## Next Steps

1. ✅ Create Microsoft/Azure account
2. ✅ Create Publisher account (achieverthoughts)
3. ✅ Generate Personal Access Token
4. ✅ Install vsce: `npm install -g vsce`
5. ✅ Build package: `vsce package`
6. ✅ Test locally in VSCode
7. ✅ Publish: `vsce publish -p <TOKEN>`
8. ✅ Verify on Marketplace
9. ✅ Announce to community

---

## Support

**Having issues?**

- 📖 **vsce Docs**: https://github.com/microsoft/vscode-vsce
- 🆘 **Marketplace Help**: https://marketplace.visualstudio.com/support
- 💬 **GitHub Issues**: https://github.com/yourusername/qamill/issues
- 📧 **Email**: support@qamill.io

---

**Ready to launch QAMill on the Visual Studio Marketplace!** 🚀

Let's make test quality a priority for developers everywhere.

---

*Version: 1.2.0*  
*Last Updated: 2026-06-27*  
*Status: Ready for Publication*
