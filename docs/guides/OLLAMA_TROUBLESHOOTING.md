# Ollama Test Generation Troubleshooting Guide

## Quick Diagnosis

**Error you're seeing:**
```
ERROR: Local Ollama timed out generating the suite — large test suites are slow on CPU. 
Try again, use a smaller file, or switch to Claude/GPT-4o for fast results.
```

**What this means:**
- Ollama took too long to generate (more than timeout allowed)
- Your CPU isn't fast enough for the full generation
- Need to use **FAST MODE** or a faster provider

---

## Solution 1: Use FAST MODE (Recommended) ✅

### What is Fast Mode?
Reduces token limit for quicker generation on slow CPUs.

### How to Enable
```javascript
// In your frontend code
const result = await generateUnitTestsStream(
  'math_utils.py',
  'ollama',
  true  // ← fast_mode = true
);
```

### Expected Time
```
Fast Mode (150 tokens):  2-3 minutes
Normal Mode (300 tokens): 4-5 minutes
Cloud (30-60 seconds):    For comparison
```

### Quality vs Speed
```
Fast Mode:   ✅ Fewer tests, but valid
Normal Mode: ✅ More tests, more thorough
```

**Recommendation:** Start with FAST MODE. You can regenerate without it if you need more tests.

---

## Solution 2: Smaller Files

### Problem
```
Large file (100+ functions) → many tokens needed → slow
Small file (5-10 functions) → fewer tokens → fast
```

### What to Do
```
Test smaller files first:
1. math_utils.py (5-10 functions) ✅
2. Full project.py (50+ functions) ❌

Split large files:
project.py → module_a.py, module_b.py, module_c.py
Then test each separately
```

### File Size Guide
```
Lines of Code    Functions    Generation Time
────────────────────────────────────────────
< 100 lines      < 5         1-2 minutes ✅
100-300 lines    5-10        2-3 minutes ✅
300-500 lines    10-20       4-5 minutes ⚠️
> 500 lines      > 20        > 5 minutes ❌
```

---

## Solution 3: Check Your Ollama Setup

### Verify Ollama is Running
```bash
# Check if Ollama is active
curl http://localhost:11434/api/tags

# Should return JSON with available models
# If error: Ollama isn't running
```

### Start Ollama (if not running)
```bash
# Windows
ollama serve

# Mac/Linux
ollama serve

# Keep this terminal open while generating tests
```

### Check Available Models
```bash
ollama list

# Output example:
# NAME                  SIZE     DIGEST
# mistral:latest        4.1GB    ...
# neural-chat:latest    3.8GB    ...
# llama3:latest         4.7GB    ...
```

### List of Model Speeds
```
Fast Models (Recommended for Ollama):
✅ mistral:latest (4.1GB)      - Good balance
✅ neural-chat:latest (3.8GB)  - Fast
✅ phi:latest (1.3GB)          - Very fast

Slower Models (Avoid for test generation):
⚠️ llama3:latest (4.7GB)       - Slower
⚠️ llama2:latest (3.8GB)       - Slower
```

### Check CPU Usage During Generation
```bash
# On another terminal, monitor CPU
# Windows
tasklist /v | find "ollama"

# Mac/Linux
top -p $(pgrep ollama)

# Good sign: CPU at 50-100%
# Bad sign: CPU at 10-20% (model too large for your CPU)
```

---

## Solution 4: Check Your Computer

### System Requirements for Ollama
```
CPU Cores         Generation Time
─────────────────────────────────
2 cores           8-10 minutes
4 cores           4-5 minutes
8+ cores          2-3 minutes
16+ cores         1-2 minutes
```

### Check Your System
```bash
# Windows: Open Task Manager → Performance
# Look for: CPU cores, RAM

# Ideal: 8+ cores, 8GB+ RAM
# Minimum: 4 cores, 4GB RAM
```

### Check Available RAM
```bash
# Windows PowerShell
Get-ComputerInfo | Select CsTotalPhysicalMemory

# Should show: 8GB or more
# For Ollama: 4GB minimum, 8GB recommended
```

### RAM During Generation
```
Monitor RAM usage while generating
- Normal: Uses 2-4GB
- Too high: Model too large for your RAM
- Solution: Use smaller model or enable disk swapping
```

---

## Solution 5: Switch Providers (Fastest)

### If You Have API Keys

```javascript
// Switch to Cloud Provider
const result = await generateUnitTestsStream(
  'math_utils.py',
  'claude',  // ← Much faster!
  false      // Normal mode (still only ~30-60 seconds)
);
```

### Expected Times by Provider
```
Provider     Time      Setup                Cost
─────────────────────────────────────────────────
Claude       30-60s    API key required     Paid
GPT-4o       20-50s    API key required     Paid
Grok         30-60s    API key required     Paid
Ollama (fast) 2-3 min   Local (no API)      Free
Ollama       4-5 min   Local (no API)      Free
```

### Get Free API Keys
- **Claude**: anthropic.com/api
- **GPT-4o**: openai.com/api
- **Grok**: x.ai/api

---

## Advanced Troubleshooting

### Issue: Ollama Returns Incomplete Response

**Error:**
```
[DEBUG] JSON parse error: Unterminated string...
[DEBUG] Attempting JSON repair...
```

**Cause:** Ollama hit token limit mid-generation

**Solution:**
1. Use `fast_mode=true` (smaller tokens)
2. Use smaller file
3. Try faster model

---

### Issue: Out of Memory (OOM)

**Error:**
```
ollama: out of memory
```

**Solution:**
```bash
# Reduce context size
export OLLAMA_MAX_CONTEXT_SIZE=2048

# Then restart
ollama serve
```

---

### Issue: Very Slow Generation (> 10 minutes)

**Check:**
```
1. Model too large for your CPU?
   → Use smaller/faster model
   
2. Your CPU too old?
   → Consider cloud provider
   
3. Not enough cores?
   → Use fast_mode=true
   
4. Disk swapping?
   → Install more RAM or use cloud
```

---

## Step-by-Step Solution

### If getting timeout error:

```
Step 1: Enable FAST MODE
├─ Change fast_mode=true
└─ Try again (2-3 minutes max)
   ├─ ✅ Success? Done!
   └─ ❌ Still timeout? Go to Step 2

Step 2: Try Smaller File
├─ Pick a file with < 10 functions
└─ Try generation
   ├─ ✅ Success? Done!
   └─ ❌ Still timeout? Go to Step 3

Step 3: Check Your Setup
├─ Verify Ollama is running
├─ Check available models
├─ Monitor CPU usage
└─ Try faster model (mistral, neural-chat)
   ├─ ✅ Success? Done!
   └─ ❌ Still timeout? Go to Step 4

Step 4: Switch to Cloud Provider
├─ Get Claude or GPT API key
├─ Switch provider in settings
└─ Generate tests
   └─ ✅ Should work (30-60 seconds)
```

---

## Performance Comparison

### Real-World Times
```
File: math_utils.py (8 functions, 200 lines)

Provider          Normal Mode    Fast Mode
──────────────────────────────────────────
Claude            30-60s         20-40s
GPT-4o            20-50s         15-35s
Ollama (fast CPU) 2-3 min        1.5-2 min
Ollama (slow CPU) 4-5 min        2-3 min
```

### Large File Times
```
File: Full project (100+ functions)

Provider          Time           Recommendation
────────────────────────────────────────────────
Claude            60-90s         ✅ Use this
GPT-4o            50-80s         ✅ Use this
Ollama (fast)     15-20 min      ⚠️ Be patient
Ollama (slow)     30+ min        ❌ Not practical
```

---

## FAQ

**Q: Why is Ollama so slow?**  
A: It's running on your CPU locally, not in a data center. Trade-off: free + offline but slower.

**Q: Can I speed up Ollama?**  
A: Yes:
1. Use fast_mode=true
2. Use faster model (mistral, neural-chat)
3. Upgrade CPU or use cloud provider

**Q: Will my tests be bad with fast_mode?**  
A: No, just fewer tests. Quality is the same.

**Q: Should I use Ollama or cloud?**  
A:
- **Ollama**: Free, offline, slow
- **Cloud**: Paid, fast, needs internet

**Q: How much do API keys cost?**  
A: ~$0.01-0.05 per test generation (Claude cheaper)

**Q: Can I get free API keys?**  
A: Some providers offer free tiers, but limited.

**Q: What if I can't wait 5 minutes?**  
A: Use Claude or GPT (30-60 seconds) or upgrade your CPU.

---

## Quick Decision Tree

```
Are you getting timeout errors?
├─ YES
│  ├─ Are you using Ollama?
│  │  └─ YES → Enable fast_mode=true
│  │           If still slow:
│  │           ├─ Try smaller file
│  │           ├─ Try faster Ollama model
│  │           └─ Switch to Claude/GPT
│  └─ NO → Contact support
└─ NO → Tests generating fine, no action needed
```

---

## Need More Help?

### Debug Commands

```bash
# Check Ollama is responding
curl http://localhost:11434/api/tags

# Check specific model
ollama show mistral:latest

# Monitor generation in real-time
# (Open separate terminal while generating)
top -p $(pgrep ollama)  # Mac/Linux
tasklist /v | find "ollama"  # Windows
```

### Enable Debug Logging

```javascript
// In browser console during generation
localStorage.setItem('debug', '*');
// Generates verbose logs for troubleshooting
```

---

## Summary

| Issue | Solution | Time |
|-------|----------|------|
| Timeout (60s) | Enable `fast_mode=true` | 2-3 min |
| Still timeout | Use smaller file | Try again |
| Very slow | Try faster model | Monitor CPU |
| Need speed | Switch to Claude | 30-60s |

---

**Last Updated:** 2026-06-29  
**For:** Ollama test generation issues  
**Status:** Complete troubleshooting guide ✅
