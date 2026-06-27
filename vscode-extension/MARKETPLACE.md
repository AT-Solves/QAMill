# QAMill v1.2.0 - Visual Studio Marketplace

**Extension:** QAMill — AI Mutation Testing  
**Version:** 1.2.0  
**Publisher:** AchieverThoughts  
**Downloads:** [View on Marketplace](https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing)

---

## 🎯 What is QAMill?

QAMill is an **enterprise-grade mutation testing platform** that transforms how development teams approach test quality. It analyzes your test suite against thousands of code mutations to reveal exactly what your tests are catching — and what they're missing.

### For Python Projects ✅
- Full AST-based mutation analysis
- pytest & unittest support
- 17+ mutation operators
- Automatic test framework detection
- Coverage analysis & reporting

### For JavaScript/TypeScript Projects ✅ NEW!
- Comprehensive mutation testing
- Jest, Vitest, and Mocha support
- Same powerful operators as Python
- Full TypeScript support
- Professional HTML reports

---

## 🚀 Quick Start

### 1. Install Extension
```
Ctrl+Shift+X → Search "QAMill" → Install
```

### 2. Start Analysis
```
Ctrl+Shift+Q  (or Ctrl+Shift+P → "QAMill: Analyze")
```

### 3. View Results
- Open generated `qamill-report.html`
- Check mutation score
- Review survived mutants
- Run auto-healing tests

---

## ✨ Key Features

### 🔬 Real-time Mutation Analysis
- Live progress streaming
- Mutation-by-mutation tracking
- Instant results
- Professional dashboards

### 🎯 Multi-Language Support
- **Python:** Full AST analysis
- **JavaScript/TypeScript:** Regex + AST
- Auto-detection
- Framework auto-detection

### 📊 Elite HTML Reports
- Self-contained reports
- Visual mutation maps
- Coverage metrics
- Trend analysis
- Export ready

### 🤖 AI-Powered Features
- **Equivalence Detection** — eliminates false positives
- **Test Healing** — AI auto-generates tests
- **Gap Analysis** — finds uncovered code
- **Smart Mutations** — context-aware operators

### 👥 Team Collaboration
- Share projects with team
- Real-time dashboards
- Activity feeds
- Audit logs

### 🔐 Enterprise Security
- OAuth 2.0 (GitHub, Google)
- RBAC (role-based access)
- JWT authentication
- Audit logging
- HIPAA-ready

---

## 📋 Supported Frameworks

### Python
✅ pytest  
✅ unittest  
✅ Django  
✅ FastAPI  

### JavaScript/TypeScript
✅ Jest  
✅ Vitest  
✅ Mocha  
✅ Jasmine  

---

## 🔧 Configuration

Open VSCode Settings and search for "QAMill":

```json
{
  "amil.llmProvider": "claude",              // LLM provider
  "amil.backendPort": 8765,                  // Backend server port
  "amil.autoHeal": true,                     // Auto-generate tests
  "amil.detectEquivalents": true,            // Filter equivalents
  "amil.anthropicApiKey": "sk-ant-...",      // API keys
  "amil.autoSend": false                     // Auto-email reports
}
```

---

## 📚 Documentation

- **[Full Documentation](https://docs.qamill.io)**
- **[GitHub Repository](https://github.com/yourusername/qamill)**
- **[Deployment Guide](https://github.com/yourusername/qamill/blob/main/DEPLOYMENT_GUIDE.md)**
- **[API Reference](https://api.qamill.io/docs)**

---

## 💻 System Requirements

- **VSCode** 1.85.0 or higher
- **Node.js** 18+ (for QAMill backend)
- **Python** 3.9+ (for Python projects)
- **4GB RAM** (8GB recommended)
- **Network connection** (for OAuth)

---

## 🌐 Backend Deployment

QAMill backend is fully containerized:

### Quick Start (Docker Compose)
```bash
docker-compose up -d
```

### Production (Azure AKS)
```bash
bash scripts/deploy-azure.sh
```

### Other Platforms
- AWS (ECS, EKS)
- Google Cloud (Cloud Run, GKE)
- On-premises (Docker, Kubernetes)

[Full Deployment Guide →](https://github.com/yourusername/qamill/blob/main/AZURE_DEPLOYMENT.md)

---

## 🎓 Learning Resources

### Getting Started
1. **Install Extension** — 1 min
2. **Configure Settings** — 2 min
3. **Run First Analysis** — 5 min
4. **View Report** — 2 min

### Understanding Mutation Testing
- [What is Mutation Testing?](https://en.wikipedia.org/wiki/Mutation_testing)
- [QAMill Blog](https://blog.qamill.io)
- [Video Tutorial](https://www.youtube.com/qamill)

### Advanced Usage
- [API Documentation](https://docs.qamill.io/api)
- [Custom Operators](https://docs.qamill.io/custom-operators)
- [Team Setup](https://docs.qamill.io/teams)

---

## ❓ FAQ

**Q: Is QAMill free?**  
A: Yes! Core mutation testing is free. Professional features (teams, OAuth) are included.

**Q: Which languages does QAMill support?**  
A: Python and JavaScript/TypeScript. More coming soon (C#, Java, Go).

**Q: Do I need a QAMill account?**  
A: You can use locally without an account. Teams and cloud features require login.

**Q: What's the performance impact?**  
A: Mutation testing takes 2-10x longer than running tests once. Results are worth it!

**Q: Can I use it offline?**  
A: Yes! Use Ollama for local LLM. See configuration docs.

**Q: How do I deploy the backend?**  
A: Docker Compose for local, Azure/AWS/GCP scripts for production. See DEPLOYMENT_GUIDE.md.

---

## 🐛 Bugs & Issues

Found a bug? Have a suggestion?

- **Report Issue:** [GitHub Issues](https://github.com/yourusername/qamill/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/qamill/discussions)
- **Email:** support@qamill.io

---

## 📝 Changelog

### v1.2.0 (Current)
✨ **New:** JavaScript/TypeScript support  
✨ **New:** Real-time WebSocket updates  
✨ **New:** Team collaboration features  
🔧 **Improved:** Better error messages  
🔧 **Improved:** Faster mutation generation  
🐛 **Fixed:** OAuth callback issues  

[Full Changelog →](https://github.com/yourusername/qamill/blob/main/CHANGELOG.md)

---

## 📄 License

MIT License - See [LICENSE](https://github.com/yourusername/qamill/blob/main/LICENSE)

---

## 🙏 Credits

Built with:
- FastAPI (backend)
- Vue 3 (frontend)
- VSCode Extension API
- Anthropic Claude
- OpenAI GPT-4

---

## 🚀 Ready to Transform Your Test Suite?

### Install Now
[Get QAMill from Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing)

### Join the Community
- **Star on GitHub:** [qamill](https://github.com/yourusername/qamill)
- **Follow on Twitter:** [@qamill_io](https://twitter.com/qamill_io)
- **Join Discord:** [QAMill Community](https://discord.gg/qamill)

---

**Made with ❤️ by the QAMill Team**

Transform your test quality today. 🎯
