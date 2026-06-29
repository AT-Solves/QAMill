# QAMill — AI Mutation Testing for VS Code

**Enterprise-grade mutation testing and AI-powered test generation for Python, JavaScript, TypeScript, and React.**

[![Visual Studio Marketplace Version](https://img.shields.io/visual-studio-marketplace/v/achieverthoughts.qamill-mutation-testing?style=flat-square)](https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing)
[![Visual Studio Marketplace Downloads](https://img.shields.io/visual-studio-marketplace/d/achieverthoughts.qamill-mutation-testing?style=flat-square)](https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing)
[![Visual Studio Marketplace Rating](https://img.shields.io/visual-studio-marketplace/r/achieverthoughts.qamill-mutation-testing?style=flat-square)](https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://github.com/AT-Solves/QAMill/blob/main/LICENSE)

---

## 📦 Installation

Install directly from the **[VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing)**:

- **Search** for "QAMill" in VS Code Extensions
- **Click Install** and reload
- **Right-click** on any supported file to start

---

## 🚀 Quick Start

1. **Install the extension** from VS Code Marketplace
2. **Right-click** on any Python, JavaScript, or TypeScript file
3. **Select QAMill** → Choose an option:
   - **Test Quality Check** - Analyze test coverage and quality
   - **Unit Tests** - Generate pytest/Jest tests automatically
   - **QA Tests** - Generate manual QA test cases
4. **Watch tests generate in real-time** (30-60 seconds!)

---

## ✨ Features

### 🌐 **Multi-Language Support**
- ✅ **Python** (.py) - Full mutation testing + test generation
- ✅ **JavaScript** (.js) - AI test generation with Jest
- ✅ **TypeScript** (.ts) - AI test generation with Jest
- ✅ **React** (.jsx, .tsx) - Component test generation

### 🧪 **Test Generation**
- **Unit Tests** - Generate pytest or Jest test suites automatically
- **QA Tests** - Create detailed manual test cases with steps
- **Test Quality Check** - Analyze coverage and identify gaps
- **Real-time Progress** - See generation status as it happens
- **Ultra-fast Mode** - Get results in 30-60 seconds

### 🤖 **Multi-LLM Support**
- **Claude** (Anthropic) - Fast, high-quality tests
- **GPT-4o** (OpenAI) - Advanced test generation
- **Grok** (xAI) - Alternative provider
- **Ollama** (Local) - Fully offline, no API keys needed
- **Gemini**, **DeepSeek**, **Mistral** - Additional options

### 📊 **Mutation Testing** (Python)
- Detect weak tests by running mutations
- Identify untested code paths
- Generate auto-healing tests
- Elite HTML reports with detailed analysis

### ⚡ **Performance**
- **Ultra-fast streaming** - Results appear instantly
- **No blank screens** - Real-time progress feedback
- **Adaptive timeouts** - Works on slow CPUs
- **Fast mode** - 30-60 second test generation

---

## 📋 Installation & Setup

### **1. Install Extension**
Search for "QAMill" in VS Code Extensions marketplace and click Install.

### **2. Configure LLM Provider**

#### **Option A: Use Local Ollama (Free, Offline)**
```bash
# 1. Install Ollama
# Download from: https://ollama.ai

# 2. Start Ollama
ollama serve

# 3. In VS Code Settings:
"amil.llmProvider": "inhouse"
"amil.ollamaModel": "llama3"
```

#### **Option B: Use Claude (Recommended)**
```
1. Get API key: https://console.anthropic.com/
2. VS Code Settings:
   "amil.llmProvider": "claude"
   "amil.anthropicApiKey": "sk-ant-..."
3. Done! ✅
```

#### **Option C: Use GPT-4o**
```
1. Get API key: https://platform.openai.com/
2. VS Code Settings:
   "amil.llmProvider": "gpt"
   "amil.openaiApiKey": "sk-..."
3. Done! ✅
```

### **3. Enable Fast Mode** (Optional)
```
VS Code Settings:
"amil.fastMode": true
# Reduces generation time by 50%
# Generates fewer tests but still high quality
```

---

## 🎯 How to Use

### **Generate Unit Tests**
```
1. Open any .py, .js, .ts, .jsx, or .tsx file
2. Right-click → QAMill → Unit Tests
3. Select test format (if prompted)
4. Click "Generate"
5. Watch tests appear in real-time
6. Tests are ready to commit! ✅
```

### **Generate QA Tests**
```
1. Right-click on source file → QAMill → QA Tests
2. Detailed manual test cases are generated
3. Perfect for QA teams and documentation
4. Copy/paste to your test management system
```

### **Check Test Quality**
```
1. Right-click → QAMill → Test Quality Check
2. See mutation testing results
3. Identify weak tests
4. Learn what's not being tested
5. Generate auto-healing tests
```

---

## ⚙️ Configuration

### **Essential Settings**

| Setting | Options | Default | Purpose |
|---------|---------|---------|---------|
| `amil.llmProvider` | claude, gpt, grok, inhouse, gemini, etc | inhouse | Choose your LLM |
| `amil.anthropicApiKey` | Your API key | (empty) | Claude authentication |
| `amil.openaiApiKey` | Your API key | (empty) | GPT-4o authentication |
| `amil.ollamaModel` | llama3, mistral, neural-chat | llama3 | Local model selection |
| `amil.backendPort` | 8765 (default) | 8765 | Backend server port |

### **Optional Settings**

| Setting | Options | Default | Purpose |
|---------|---------|---------|---------|
| `amil.fastMode` | true/false | false | Faster generation (fewer tests) |
| `amil.detectEquivalents` | true/false | true | Filter equivalent mutants |
| `amil.autoHeal` | true/false | true | Generate healing tests |

---

## 📊 Performance

### **Expected Times**

| Provider | Mode | Time | Quality |
|----------|------|------|---------|
| **Claude** | Fast | 15-30s | ⭐⭐⭐⭐⭐ |
| **Claude** | Normal | 30-60s | ⭐⭐⭐⭐⭐ |
| **GPT-4o** | Fast | 10-20s | ⭐⭐⭐⭐⭐ |
| **Ollama** | Fast | 1-2 min | ⭐⭐⭐⭐ |
| **Ollama** | Normal | 2-5 min | ⭐⭐⭐⭐⭐ |

---

## 🔧 Troubleshooting

### **Ollama Timeout?**
```
Solution 1: Enable fast mode
  Settings → amil.fastMode: true

Solution 2: Use smaller model
  Settings → amil.ollamaModel: mistral

Solution 3: Switch to cloud provider (Claude/GPT)
  Faster and more reliable
```

### **Tests Not Generating?**
```
Check:
1. LLM provider is configured
2. API key is valid (if using cloud)
3. Ollama is running (if using local)
4. File is a supported type (.py, .js, .ts, .jsx, .tsx)
5. Backend is running on port 8765
```

### **Need Help?**
See complete guides:
- 📖 [Ollama Troubleshooting](https://github.com/AT-Solves/QAMill/blob/main/docs/guides/OLLAMA_TROUBLESHOOTING.md)
- 📖 [Performance Optimization](https://github.com/AT-Solves/QAMill/blob/main/docs/guides/PERFORMANCE_OPTIMIZATION.md)
- 📖 [Deployment Guide](https://github.com/AT-Solves/QAMill/blob/main/docs/guides/DEPLOYMENT_GUIDE.md)

---

## 🌍 Supported Languages

### **Python**
- ✅ Unit test generation (pytest syntax)
- ✅ Mutation testing
- ✅ Test quality analysis
- ✅ QA test generation
- ✅ Auto-healing tests

### **JavaScript**
- ✅ Unit test generation (Jest syntax)
- ✅ QA test generation
- ✅ Test quality analysis
- ✅ Works with Node.js projects

### **TypeScript**
- ✅ Unit test generation (Jest syntax)
- ✅ Type-aware test generation
- ✅ QA test generation
- ✅ React component testing

### **React**
- ✅ Component test generation
- ✅ Testing-library syntax
- ✅ Hook testing
- ✅ Full integration test support

---

## 💡 Example: Generate Tests for JavaScript

### **Before**
```javascript
// calculator.js
function add(a, b) {
  return a + b;
}

function subtract(a, b) {
  return a - b;
}

module.exports = { add, subtract };
```

### **After (AI-Generated Tests)**
```javascript
// calculator.test.js
const { add, subtract } = require('./calculator');

describe('Calculator', () => {
  describe('add', () => {
    test('adds positive numbers', () => {
      expect(add(2, 3)).toBe(5);
    });
    test('adds negative numbers', () => {
      expect(add(-1, -1)).toBe(-2);
    });
    test('handles zero', () => {
      expect(add(0, 5)).toBe(5);
    });
  });

  describe('subtract', () => {
    test('subtracts positive numbers', () => {
      expect(subtract(5, 3)).toBe(2);
    });
    test('subtracts with negative result', () => {
      expect(subtract(2, 5)).toBe(-3);
    });
  });
});
```

✅ **100% generated by QAMill AI** - Ready to run immediately!

---

## 🎓 Use Cases

### **For Individual Developers**
- 🚀 Quickly generate test suites
- 🧪 Improve test coverage
- ⚡ Focus on business logic, not boilerplate
- 📈 Ship better code faster

### **For Teams**
- 📊 Maintain high test coverage standards
- 🎯 Ensure consistent test quality
- 🤖 Automate test generation
- 📚 Generate documentation tests

### **For QA Teams**
- 📋 Generate detailed test cases
- 🔍 Identify untested code paths
- ✅ Verify test adequacy
- 📝 Export to test management systems

### **For DevOps/CI**
- 🔄 Auto-generate tests in CI pipeline
- 📊 Track test coverage metrics
- 🚀 Enforce quality gates
- 📈 Improve mutation score

---

## 📞 Support

### **Documentation**
- 📖 [Full Documentation](https://github.com/AT-Solves/QAMill)
- 🔧 [Troubleshooting Guide](https://github.com/AT-Solves/QAMill/blob/main/docs/guides/OLLAMA_TROUBLESHOOTING.md)
- ⚡ [Performance Guide](https://github.com/AT-Solves/QAMill/blob/main/docs/guides/PERFORMANCE_OPTIMIZATION.md)

### **Issues & Feedback**
- 🐛 [Report Issues](https://github.com/AT-Solves/QAMill/issues)
- 💬 [Discussions](https://github.com/AT-Solves/QAMill/discussions)
- ⭐ [Star on GitHub](https://github.com/AT-Solves/QAMill)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

Built with ❤️ for developers who love quality code.

**Supported by:**
- Anthropic Claude API
- OpenAI GPT-4o
- Ollama (Local LLMs)
- VS Code API
- Open source community

---

## 🚀 Get Started Now!

1. **Install**: Search "QAMill" in VS Code Extensions
2. **Configure**: Add your LLM API key or use Ollama
3. **Generate**: Right-click any file → QAMill → Unit Tests
4. **Done!** Tests ready in 30-60 seconds ✅

---

**QAMill v1.2.2** - Making test generation easy for everyone.

**Happy Testing! 🧪**
