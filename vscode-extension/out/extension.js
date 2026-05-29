"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
/**
 * extension.ts
 * VS Code extension entry point for AMIL.
 * Spawns Python backend, opens live dashboard webview.
 */
const vscode = require("vscode");
const path = require("path");
const cp = require("child_process");
const http = require("http");
const fs = require("fs");
let backendProcess;
let dashboardPanel;
let statusBarItem;
let llmStatusBarItem;
let lastFilePath;
let jobDeliveryTimer;
let lastProjectRoot;
let pendingJob;
function activate(context) {
    // Status bar pill
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.text = "$(beaker) QAMill";
    statusBarItem.tooltip = "QAMill Mutation Testing — click to run";
    statusBarItem.command = "amil.runAnalysis";
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    // LLM status bar item — click to switch provider (like GitHub Copilot)
    llmStatusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 99);
    llmStatusBarItem.command = "amil.selectLLM";
    llmStatusBarItem.tooltip = "QAMill: Click to switch LLM provider";
    updateLlmStatusBar();
    llmStatusBarItem.show();
    context.subscriptions.push(llmStatusBarItem);
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(e => {
        if (e.affectsConfiguration("amil.llmProvider")) {
            updateLlmStatusBar();
        }
    }));
    // ── Commands ──────────────────────────────────────────────────────────────
    // uri is passed automatically when invoked from Explorer right-click
    context.subscriptions.push(vscode.commands.registerCommand("amil.runAnalysis", (uri) => runAnalysis(context, uri)), vscode.commands.registerCommand("amil.stopAnalysis", stopAnalysis), vscode.commands.registerCommand("amil.selectLLM", selectLLM));
}
function deactivate() {
    stopAnalysis();
}
// ── Run Analysis ─────────────────────────────────────────────────────────────
async function runAnalysis(context, uri) {
    const config = vscode.workspace.getConfiguration("amil");
    const port = config.get("backendPort", 8765);
    // ── Resolve file path ────────────────────────────────────────────────────
    let filePath;
    let projectRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (uri) {
        const stat = fs.statSync(uri.fsPath);
        if (stat.isDirectory()) {
            // Folder right-click — find first Python source file
            filePath = findPythonSourceFile(uri.fsPath);
            if (!filePath) {
                vscode.window.showErrorMessage("QAMill: No Python source files found in this folder.");
                return;
            }
            projectRoot = uri.fsPath;
        }
        else {
            filePath = uri.fsPath;
            projectRoot = projectRoot || path.dirname(uri.fsPath);
        }
    }
    else {
        // Fallback: active editor
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage("QAMill: Right-click a .py file or folder in the Explorer.");
            return;
        }
        filePath = editor.document.fileName;
    }
    if (!projectRoot) {
        vscode.window.showErrorMessage("QAMill: Open a workspace folder first.");
        return;
    }
    // Warn if the user selected a test file instead of a source file
    const basename = path.basename(filePath);
    if (/^test_|_test\.py$/i.test(basename)) {
        const pick = await vscode.window.showWarningMessage(`QAMill: "${basename}" looks like a test file. Select the SOURCE file (e.g. math_utils.py) for meaningful mutation testing.`, "Analyze Anyway", "Cancel");
        if (pick !== "Analyze Anyway") {
            statusBarItem.text = "$(beaker) QAMill";
            return;
        }
    }
    lastFilePath = filePath;
    lastProjectRoot = projectRoot;
    const llmProvider = config.get("llmProvider", "inhouse");
    // ── Ensure backend is running ────────────────────────────────────────────
    statusBarItem.text = "$(sync~spin) QAMill Starting...";
    const backendReady = await ensureBackendRunning(context, port);
    if (!backendReady) {
        vscode.window.showErrorMessage("QAMill: Could not start backend. Check Python is on PATH.");
        statusBarItem.text = "$(beaker) QAMill";
        return;
    }
    // ── Start analysis BEFORE opening dashboard ──────────────────────────────
    const payload = {
        file_path: filePath,
        project_root: projectRoot,
        llm_provider: llmProvider,
        llm_api_key: getApiKey(config, llmProvider),
        auto_heal: config.get("autoHeal", true),
        detect_equivalents: config.get("detectEquivalents", true),
        ai_mutants: config.get("aiMutants", false),
    };
    let jobResp;
    try {
        jobResp = await postJson(`http://localhost:${port}/analyze`, payload);
    }
    catch (err) {
        vscode.window.showErrorMessage(`QAMill: Failed to start analysis — ${err}`);
        statusBarItem.text = "$(beaker) QAMill";
        return;
    }
    // Store job so it can be delivered once the dashboard is ready
    pendingJob = {
        stream_url: jobResp.stream_url,
        file: path.basename(filePath),
        llm_provider: llmProvider,
    };
    // ── Open / reveal dashboard (retains context, so JS state is preserved) ──
    openDashboard(context, port);
    // Deliver immediately — works if dashboard was already loaded
    deliverPendingJob();
    statusBarItem.text = "$(sync~spin) QAMill Running...";
    vscode.window.showInformationMessage(`QAMill: Analysing ${path.basename(filePath)}…`);
}
// ── Python source file discovery ──────────────────────────────────────────────
function findPythonSourceFile(dir) {
    try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        // Prefer files at the top level first
        for (const e of entries) {
            if (e.isFile() && e.name.endsWith(".py")) {
                const n = e.name;
                if (!n.startsWith("test_") && !n.endsWith("_test.py") && n !== "conftest.py") {
                    return path.join(dir, n);
                }
            }
        }
        // Recurse into subdirectories (skip hidden / cache)
        for (const e of entries) {
            if (e.isDirectory() && !e.name.startsWith(".") && e.name !== "__pycache__" && e.name !== "node_modules" && e.name !== "tests") {
                const found = findPythonSourceFile(path.join(dir, e.name));
                if (found) {
                    return found;
                }
            }
        }
    }
    catch { /* ignore permission errors */ }
    return undefined;
}
// ── Backend lifecycle ─────────────────────────────────────────────────────────
async function ensureBackendRunning(context, port) {
    // Check if already running
    if (await isPortOpen(port))
        return true;
    const backendDir = path.join(context.extensionPath, "..", "backend");
    backendProcess = cp.spawn("python", ["main.py"], {
        cwd: backendDir,
        detached: false,
        stdio: ["ignore", "pipe", "pipe"],
    });
    backendProcess.stdout?.on("data", (d) => {
        const text = d.toString().trim();
        if (text) {
            dashboardPanel?.webview.postMessage({ type: "backend_log", text, level: "info" });
        }
    });
    backendProcess.stderr?.on("data", (d) => {
        const text = d.toString().trim();
        if (text) {
            console.error("[QAMill backend]", text);
            dashboardPanel?.webview.postMessage({ type: "backend_log", text, level: "warn" });
        }
    });
    // Wait up to 8 seconds for backend to be ready
    for (let i = 0; i < 16; i++) {
        await sleep(500);
        if (await isPortOpen(port))
            return true;
    }
    return false;
}
function stopAnalysis() {
    if (backendProcess) {
        backendProcess.kill();
        backendProcess = undefined;
    }
    statusBarItem.text = "$(beaker) QAMill";
}
function isPortOpen(port) {
    return new Promise((resolve) => {
        const req = http.get(`http://localhost:${port}/health`, (res) => {
            resolve(res.statusCode === 200);
        });
        req.on("error", () => resolve(false));
        req.setTimeout(500, () => { req.destroy(); resolve(false); });
    });
}
// ── Dashboard Webview ─────────────────────────────────────────────────────────
function openDashboard(context, port) {
    if (dashboardPanel) {
        dashboardPanel.reveal(vscode.ViewColumn.Beside);
        return;
    }
    dashboardPanel = vscode.window.createWebviewPanel("amilDashboard", "QAMill Dashboard", vscode.ViewColumn.Beside, {
        enableScripts: true,
        retainContextWhenHidden: true, // keep JS state alive — no reloads on focus change
        localResourceRoots: [
            vscode.Uri.joinPath(context.extensionUri, "media"),
        ],
    });
    dashboardPanel.webview.html = getDashboardHtml(port);
    // Tell dashboard which file and LLM are active on first open
    setTimeout(() => {
        if (lastFilePath) {
            dashboardPanel?.webview.postMessage({
                type: "set_file",
                file: path.basename(lastFilePath),
            });
        }
        const currentProvider = vscode.workspace.getConfiguration("amil").get("llmProvider", "inhouse");
        dashboardPanel?.webview.postMessage({ type: "sync_settings", provider: currentProvider });
    }, 500);
    // Handle messages from webview
    dashboardPanel.webview.onDidReceiveMessage(async (msg) => {
        if (msg.type === "webview_ready") {
            // Webview just (re)loaded — deliver any pending job immediately
            if (lastFilePath) {
                dashboardPanel?.webview.postMessage({
                    type: "set_file",
                    file: path.basename(lastFilePath),
                });
            }
            dashboardPanel?.webview.postMessage(buildSyncPayload());
            deliverPendingJob();
            return;
        }
        if (msg.type === "open_file") {
            vscode.workspace.openTextDocument(msg.file).then((doc) => {
                vscode.window.showTextDocument(doc).then((editor) => {
                    const line = new vscode.Range(msg.line - 1, 0, msg.line - 1, 0);
                    editor.revealRange(line, vscode.TextEditorRevealType.InCenter);
                });
            });
        }
        if (msg.type === "request_current_job") {
            // Webview is polling — respond if there is a pending job
            if (pendingJob) {
                dashboardPanel?.webview.postMessage({ type: "job_started", ...pendingJob });
            }
            return;
        }
        if (msg.type === "job_received") {
            // Webview confirmed receipt — cancel the retry timer
            if (jobDeliveryTimer) {
                clearTimeout(jobDeliveryTimer);
                jobDeliveryTimer = undefined;
            }
            return;
        }
        if (msg.type === "analysis_complete") {
            pendingJob = undefined;
            if (jobDeliveryTimer) {
                clearTimeout(jobDeliveryTimer);
                jobDeliveryTimer = undefined;
            }
            statusBarItem.text = `$(beaker) QAMill ${msg.true_score}%`;
        }
        if (msg.type === "run_analysis") {
            // ── Resolve target file ──────────────────────────────────────────────
            // Prefer lastFilePath (set by right-click).
            // Fall back to active editor — but skip test files (test_*.py / *_test.py).
            const activeFile = vscode.window.activeTextEditor?.document.fileName;
            const activeIsPy = activeFile?.endsWith(".py") ?? false;
            const activeIsTestFile = activeFile
                ? /[/\\](test_[^/\\]+|[^/\\]+_test)\.py$/i.test(activeFile)
                : false;
            const targetFile = lastFilePath
                || (activeIsPy && !activeIsTestFile ? activeFile : undefined);
            const targetRoot = lastProjectRoot
                || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
            if (!targetFile || !targetRoot) {
                const msg2 = "Open a .py file in the editor, then click Run Analysis.";
                vscode.window.showErrorMessage(`QAMill: ${msg2}`);
                dashboardPanel?.webview.postMessage({ type: "run_error", message: msg2 });
                return;
            }
            // Keep module-level refs up to date
            lastFilePath = targetFile;
            lastProjectRoot = targetRoot;
            // ── Ensure backend is running ────────────────────────────────────────
            statusBarItem.text = "$(sync~spin) QAMill Starting...";
            const backendReady = await ensureBackendRunning(context, port);
            if (!backendReady) {
                const msg2 = "Could not start QAMill backend. Check that Python is on PATH.";
                vscode.window.showErrorMessage(`QAMill: ${msg2}`);
                dashboardPanel?.webview.postMessage({ type: "run_error", message: msg2 });
                statusBarItem.text = "$(beaker) QAMill";
                return;
            }
            // ── Fire analysis ────────────────────────────────────────────────────
            const config = vscode.workspace.getConfiguration("amil");
            const llmProvider = config.get("llmProvider", "inhouse");
            const payload = {
                file_path: targetFile,
                project_root: targetRoot,
                llm_provider: llmProvider,
                llm_api_key: getApiKey(config, llmProvider),
                auto_heal: msg.auto_heal ?? config.get("autoHeal", true),
                detect_equivalents: config.get("detectEquivalents", true),
                ai_mutants: msg.ai_mutants ?? config.get("aiMutants", false),
            };
            try {
                const jobResp = await postJson(`http://localhost:${port}/analyze`, payload);
                pendingJob = { stream_url: jobResp.stream_url, file: path.basename(targetFile), llm_provider: llmProvider };
                deliverPendingJob();
                statusBarItem.text = "$(sync~spin) QAMill Running...";
            }
            catch (err) {
                const msg2 = `POST to backend failed: ${err}`;
                vscode.window.showErrorMessage(`QAMill: ${msg2}`);
                dashboardPanel?.webview.postMessage({ type: "run_error", message: msg2 });
                statusBarItem.text = "$(beaker) QAMill";
            }
        }
        if (msg.type === "save_llm_settings") {
            const config = vscode.workspace.getConfiguration("amil");
            await config.update("llmProvider", msg.provider, vscode.ConfigurationTarget.Workspace);
            if (msg.auto_heal !== undefined) {
                await config.update("autoHeal", msg.auto_heal, vscode.ConfigurationTarget.Workspace);
            }
            if (msg.ai_mutants !== undefined) {
                await config.update("aiMutants", msg.ai_mutants, vscode.ConfigurationTarget.Workspace);
            }
            updateLlmStatusBar();
        }
        if (msg.type === "ai_query") {
            const config = vscode.workspace.getConfiguration("amil");
            const llmProvider = config.get("llmProvider", "inhouse");
            const llmApiKey = getApiKey(config, llmProvider);
            try {
                const resp = await postJson(`http://localhost:${port}/ask`, {
                    prompt: msg.prompt,
                    context: msg.context,
                    llm_provider: llmProvider,
                    llm_api_key: llmApiKey,
                });
                dashboardPanel?.webview.postMessage({ type: "ai_response", answer: resp.answer });
            }
            catch (err) {
                dashboardPanel?.webview.postMessage({
                    type: "ai_response",
                    answer: `QAMill assistant unavailable — make sure a LLM provider is configured. (${err})`,
                });
            }
        }
    });
    dashboardPanel.onDidDispose(() => {
        dashboardPanel = undefined;
        statusBarItem.text = "$(beaker) QAMill";
    });
}
// ── LLM selector quick-pick ───────────────────────────────────────────────────
async function selectLLM() {
    const choice = await vscode.window.showQuickPick([
        { label: "$(circle-slash) None — in-house AST only", value: "none" },
        { label: "$(sparkle) Claude (Anthropic)", value: "claude" },
        { label: "$(sparkle) GPT-4o (OpenAI)", value: "gpt" },
        { label: "$(sparkle) Grok (xAI)", value: "grok" },
        { label: "$(home) Ollama — fully offline", value: "inhouse" },
    ], { placeHolder: "Select LLM provider for QAMill" });
    if (choice) {
        await vscode.workspace.getConfiguration("amil").update("llmProvider", choice.value, vscode.ConfigurationTarget.Workspace);
        updateLlmStatusBar();
        dashboardPanel?.webview.postMessage(buildSyncPayload());
        vscode.window.showInformationMessage(`QAMill: LLM set to ${choice.label}`);
    }
}
// ── Helpers ───────────────────────────────────────────────────────────────────
function buildSyncPayload() {
    const cfg = vscode.workspace.getConfiguration("amil");
    const provider = cfg.get("llmProvider", "inhouse");
    const autoHeal = cfg.get("autoHeal", true);
    const aiMutants = cfg.get("aiMutants", false);
    const mode = autoHeal && aiMutants ? "both" : autoHeal ? "auto_heal" : aiMutants ? "ai_mutants" : "none";
    return { type: "sync_settings", provider, mode };
}
function updateLlmStatusBar() {
    const provider = vscode.workspace.getConfiguration("amil").get("llmProvider", "inhouse");
    const icons = { none: "$(circle-slash)", inhouse: "$(home)", claude: "$(sparkle)", gpt: "$(sparkle)", grok: "$(sparkle)" };
    const labels = { none: "AST only", inhouse: "Ollama", claude: "Claude", gpt: "GPT-4o", grok: "Grok" };
    llmStatusBarItem.text = `${icons[provider] ?? "$(sparkle)"} ${labels[provider] ?? provider}`;
}
function deliverPendingJob() {
    if (!pendingJob || !dashboardPanel) {
        return;
    }
    if (jobDeliveryTimer) {
        clearTimeout(jobDeliveryTimer);
        jobDeliveryTimer = undefined;
    }
    dashboardPanel.webview.postMessage({ type: "job_started", ...pendingJob });
    // One retry after 900 ms in case the webview wasn't ready on the first send
    jobDeliveryTimer = setTimeout(() => {
        jobDeliveryTimer = undefined;
        if (pendingJob && dashboardPanel) {
            dashboardPanel.webview.postMessage({ type: "job_started", ...pendingJob });
        }
    }, 900);
}
function getApiKey(config, provider) {
    const keys = {
        claude: config.get("anthropicApiKey", ""),
        gpt: config.get("openaiApiKey", ""),
        grok: config.get("xaiApiKey", ""),
    };
    return keys[provider] || "";
}
function postJson(url, body) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify(body);
        const req = http.request(url, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) },
        }, (res) => {
            let raw = "";
            res.on("data", (c) => raw += c);
            res.on("end", () => {
                try {
                    resolve(JSON.parse(raw));
                }
                catch {
                    reject(new Error(raw));
                }
            });
        });
        req.on("error", reject);
        req.write(data);
        req.end();
    });
}
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
// ── Dashboard HTML (inlined) ──────────────────────────────────────────────────
function getDashboardHtml(port) {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src http://localhost:${port} http://127.0.0.1:${port};">
<title>QAMill Dashboard</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background:var(--vscode-editor-background);color:var(--vscode-editor-foreground);
       font-size:13px;line-height:1.5;padding:16px}
  h2{font-size:15px;font-weight:600;opacity:.9}

  /* ── Provider badge ── */
  .title-row{display:flex;align-items:center;gap:8px;margin-bottom:12px}
  .provider-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;
                  letter-spacing:.06em;text-transform:uppercase}
  .pb-none   {background:#2a2a2a;color:#888}
  .pb-claude {background:#3a2510;color:#e07b39}
  .pb-gpt    {background:#1a3a1e;color:#4ec9a0}
  .pb-grok   {background:#1a2a3a;color:#569cd6}
  .pb-inhouse{background:#2a1a3a;color:#c586c0}

  /* ── File label in title row ── */
  .file-label{font-size:11px;opacity:.45;flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;margin:0 8px}
  /* ── AI widget compact header ── */
  .chat-header-row{display:flex;align-items:center;gap:6px;padding:7px 10px;
                   border-bottom:1px solid var(--vscode-widget-border)}
  .chat-title-text{flex:1;font-size:12px;font-weight:600;opacity:.85}
  .mini-select{background:var(--vscode-input-background);color:var(--vscode-input-foreground);
               border:1px solid var(--vscode-input-border,#555);border-radius:4px;
               padding:2px 5px;font-size:11px;outline:none;cursor:pointer;max-width:110px}
  .mini-select:focus,.mini-select:hover{border-color:var(--vscode-focusBorder,#007fd4)}

  /* ── Score cards ── */
  .score-row{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap}
  .score-card{flex:1;min-width:80px;background:var(--vscode-sideBar-background);
              border:1px solid var(--vscode-widget-border);border-radius:6px;
              padding:9px 12px}
  .score-card .val{font-size:20px;font-weight:700;margin-top:2px}
  .score-card .lbl{font-size:10px;opacity:.6;text-transform:uppercase;letter-spacing:.05em}
  .true-score .val{color:#4ec9a0}
  .raw-score  .val{color:#ce9178}
  .cross-method .val{color:#c586c0}

  /* ── Progress ── */
  .bar-wrap{background:var(--vscode-widget-border);border-radius:3px;height:7px;
            margin-bottom:14px;overflow:hidden}
  .bar-fill{height:100%;border-radius:3px;background:#4ec9a0;width:0;
            transition:width .4s ease}
  .progress-label{font-size:11px;opacity:.5;margin-bottom:4px}

  /* ── Feed ── */
  .feed{max-height:380px;overflow-y:auto;margin-bottom:14px}
  .event{display:flex;align-items:center;gap:6px;padding:3px 0;
         border-bottom:1px solid var(--vscode-widget-border);overflow:hidden}
  .event:last-child{border-bottom:none}
  .mut-line{flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.4}
  .mut-id{font-family:monospace;font-size:10px;opacity:.55}
  .mut-fn{font-weight:600;color:var(--vscode-textLink-foreground,#4ec9a0)}
  .mut-sep{opacity:.3;margin:0 1px}
  .mini-tag{font-size:9px;font-weight:700;padding:1px 4px;border-radius:3px;flex-shrink:0;letter-spacing:.04em}
  .badge{font-size:11px;font-weight:600;padding:2px 7px;border-radius:20px;
         flex-shrink:0;min-width:76px;text-align:center}
  /* ── Pulsing progress bar while running ── */
  @keyframes bar-pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .bar-fill.running{animation:bar-pulse 1.1s ease-in-out infinite}
  .b-killed    {background:#1e3a2f;color:#4ec9a0}
  .b-survived  {background:#3a1e1e;color:#f48771}
  .b-equivalent{background:#2a2a1e;color:#dcdcaa}
  .b-error     {background:#2a1e2a;color:#c586c0}
  .b-info      {background:transparent;color:var(--vscode-descriptionForeground)}
  .b-diff-low  {background:#1e2a3a;color:#569cd6}
  .b-diff-medium{background:#3a2e1e;color:#d7ba7d}
  .b-diff-high {background:#3a1e1e;color:#f48771}
  .b-cross     {background:#2a1e3a;color:#c586c0}
  .event-body{flex:1}
  .event-title{font-weight:500}
  .event-sub{font-size:11px;opacity:.6;margin-top:2px}
  .diff-reason{font-size:11px;opacity:.7;margin-top:3px;font-style:italic}
  .test-block{background:var(--vscode-textCodeBlock-background);border-radius:4px;
              padding:8px;margin-top:6px;font-family:monospace;font-size:11px;
              white-space:pre-wrap;max-height:120px;overflow-y:auto;
              border:1px solid var(--vscode-widget-border)}
  .verified{color:#4ec9a0;font-size:10px;margin-left:6px}
  .status-line{opacity:.5;font-style:italic;padding:6px 0;font-size:12px}
  #waiting{opacity:.5;padding:20px 0;text-align:center}
  .b-ai-mutant  {background:#2a1e3a;color:#c586c0}
  .b-verified   {background:#1e3a2f;color:#4ec9a0}
  .b-unverified {background:#3a2e1e;color:#d7ba7d}
  .explanation-box{background:var(--vscode-textBlockQuote-background,#1e1e2e);
                   border-left:3px solid #569cd6;border-radius:0 4px 4px 0;
                   padding:7px 10px;margin-top:5px;font-size:12px;
                   line-height:1.6;opacity:.9}

  /* ── Post-analysis summary ── */
  .summary-section{background:var(--vscode-sideBar-background);
                   border:1px solid var(--vscode-widget-border);
                   border-radius:6px;margin-bottom:14px;padding:12px 14px;display:none}
  .summary-title{font-size:12px;font-weight:700;margin-bottom:8px;opacity:.8;
                 text-transform:uppercase;letter-spacing:.05em}
  .summary-line{font-size:12px;margin-bottom:4px;opacity:.85}
  .summary-score{color:#4ec9a0;font-weight:600}
  .top-mutant{font-size:11px;opacity:.75;padding:3px 0;
              border-bottom:1px solid var(--vscode-widget-border)}
  .top-mutant:last-child{border-bottom:none}

  /* ── Suggested Tests panel ── */
  .suggested-panel{background:var(--vscode-sideBar-background);
                   border:1px solid var(--vscode-widget-border);
                   border-radius:6px;margin-bottom:14px;overflow:hidden;display:none}
  .suggested-header{display:flex;justify-content:space-between;align-items:center;
                    padding:8px 12px;cursor:pointer;font-size:12px;font-weight:600;
                    opacity:.8;user-select:none}
  .suggested-header:hover{opacity:1}
  .suggested-count{background:#569cd6;color:#fff;font-size:10px;font-weight:700;
                   padding:1px 7px;border-radius:20px}
  .suggested-body{padding:10px 12px;border-top:1px solid var(--vscode-widget-border)}
  .copy-btn{background:var(--vscode-button-background,#0e639c);
            color:var(--vscode-button-foreground,#fff);border:none;border-radius:4px;
            padding:4px 12px;font-size:11px;cursor:pointer;margin-bottom:8px}
  .copy-btn:hover{opacity:.85}
  .all-tests-block{background:var(--vscode-textCodeBlock-background);border-radius:4px;
                   padding:10px;font-family:monospace;font-size:11px;
                   white-space:pre-wrap;max-height:300px;overflow-y:auto;
                   border:1px solid var(--vscode-widget-border)}

  /* ── AI Chat panel ── */
  .chat-panel{background:var(--vscode-sideBar-background);
              border:1px solid var(--vscode-widget-border);
              border-radius:6px;overflow:hidden}
  .chat-title{padding:8px 12px;font-size:12px;font-weight:600;opacity:.8;
              border-bottom:1px solid var(--vscode-widget-border)}
  .chat-response{min-height:48px;max-height:200px;overflow-y:auto;
                 padding:10px 12px;font-size:12px;line-height:1.6;
                 border-bottom:1px solid var(--vscode-widget-border)}
  .chat-placeholder{opacity:.4;font-style:italic}
  .chat-answer{animation:fadeIn .4s ease}
  .chat-thinking{opacity:.5;font-style:italic;animation:pulse 1.2s infinite}
  @keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
  @keyframes pulse{0%,100%{opacity:.5}50%{opacity:.9}}
  .quick-prompts{display:flex;flex-wrap:wrap;gap:6px;padding:8px 12px;
                 border-bottom:1px solid var(--vscode-widget-border)}
  .quick-btn{background:var(--vscode-editor-background);
             border:1px solid var(--vscode-widget-border);
             color:var(--vscode-editor-foreground);border-radius:4px;
             padding:3px 10px;font-size:11px;cursor:pointer;opacity:.8}
  .quick-btn:hover{opacity:1;border-color:var(--vscode-focusBorder,#007fd4)}
  .chat-input-row{display:flex;gap:6px;padding:8px 12px}
  .chat-input{flex:1;background:var(--vscode-input-background);
              color:var(--vscode-input-foreground);
              border:1px solid var(--vscode-input-border,#555);
              border-radius:4px;padding:5px 9px;font-size:12px;outline:none}
  .chat-input:focus{border-color:var(--vscode-focusBorder,#007fd4)}
  .send-btn{background:var(--vscode-button-background,#0e639c);
            color:var(--vscode-button-foreground,#fff);border:none;
            border-radius:4px;padding:5px 14px;font-size:12px;
            cursor:pointer;font-weight:600;white-space:nowrap}
  .send-btn:hover{opacity:.85}
  .send-btn:disabled{opacity:.4;cursor:not-allowed}

  /* ── Backend output terminal ── */
  .term-panel{background:#0d1117;border:1px solid #30363d;border-radius:6px;
              margin-top:10px;overflow:hidden;font-family:'Cascadia Code','Consolas',monospace}
  .term-header{display:flex;align-items:center;gap:8px;padding:5px 10px;
               background:#161b22;border-bottom:1px solid #30363d;font-size:11px;color:#8b949e}
  .term-header-title{font-weight:600;color:#c9d1d9;white-space:nowrap}
  .term-file-chip{flex:1;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
                  background:#21262d;padding:1px 7px;border-radius:10px;border:1px solid #30363d}
  .term-file-chip.warn{border-color:#d29922;color:#d29922}
  .term-clear{background:none;border:1px solid #30363d;color:#8b949e;border-radius:3px;
              padding:1px 7px;font-size:10px;cursor:pointer}
  .term-clear:hover{color:#c9d1d9;border-color:#8b949e}
  .term-body{max-height:220px;overflow-y:auto;padding:8px 10px;font-size:11px;line-height:1.6}
  .tl{margin:0;white-space:pre-wrap;word-break:break-all}
  .tl-info {color:#58a6ff}
  .tl-ok   {color:#3fb950}
  .tl-warn {color:#d29922}
  .tl-error{color:#f85149}
</style>
</head>
<body>

<!-- ── Title row with provider badge ── -->
<div class="title-row">
  <h2>QAMill &mdash; Mutation Analysis</h2>
  <span class="file-label" id="run-file"></span>
  <span class="provider-badge pb-inhouse" id="provider-badge">OLLAMA</span>
</div>

<!-- ── Score cards ── -->
<div class="score-row">
  <div class="score-card true-score">
    <div class="lbl">True score</div>
    <div class="val" id="true-score">&mdash;</div>
  </div>
  <div class="score-card raw-score">
    <div class="lbl">Raw score</div>
    <div class="val" id="raw-score">&mdash;</div>
  </div>
  <div class="score-card">
    <div class="lbl">Killed</div>
    <div class="val" id="killed-count">0</div>
  </div>
  <div class="score-card">
    <div class="lbl">Survived</div>
    <div class="val" id="survived-count">0</div>
  </div>
  <div class="score-card">
    <div class="lbl">Equivalent</div>
    <div class="val" id="equiv-count">0</div>
  </div>
  <div class="score-card cross-method">
    <div class="lbl">Cross-Method</div>
    <div class="val" id="cross-count">0</div>
  </div>
</div>

<!-- ── Post-analysis summary (hidden until complete) ── -->
<div class="summary-section" id="summary-section">
  <div class="summary-title">&#128202; Analysis Summary</div>
  <div class="summary-line" id="summary-counts"></div>
  <div class="summary-line" id="summary-score"></div>
  <div style="margin-top:8px;font-size:11px;font-weight:600;opacity:.7;margin-bottom:4px">TOP 3 MOST DANGEROUS</div>
  <div id="summary-top"></div>
</div>

<div class="progress-label" id="progress-label">Waiting for analysis...</div>
<div class="bar-wrap"><div class="bar-fill" id="bar"></div></div>

<!-- ── Mutation results feed ── -->
<div class="feed" id="feed">
  <div id="waiting">Right-click a file &#8594; Run QAMill Mutation Analysis</div>
</div>

<!-- ── Suggested Tests panel (hidden until tests exist) ── -->
<div class="suggested-panel" id="suggested-panel">
  <div class="suggested-header" id="suggested-header">
    <span>&#128203; Suggested Tests — copy all to your test file</span>
    <span class="suggested-count" id="suggested-count">0</span>
  </div>
  <div class="suggested-body" id="suggested-body" style="display:none">
    <button id="copy-btn" class="copy-btn">&#128203; Copy All Tests</button>
    <pre class="all-tests-block" id="all-tests-block"></pre>
  </div>
</div>

<!-- ── QAMill AI Assistant ── -->
<div class="chat-panel">
  <div class="chat-header-row">
    <span class="chat-title-text">&#129302; QAMill AI Assistant</span>
    <select id="mode-select" class="mini-select" title="Analysis options">
      <option value="auto_heal" selected>Auto-heal</option>
      <option value="ai_mutants">AI mutants</option>
      <option value="both">Both</option>
      <option value="none">None</option>
    </select>
    <select id="llm-select-mini" class="mini-select" title="LLM provider">
      <option value="none">AST only</option>
      <option value="claude">Claude</option>
      <option value="gpt">GPT-4o</option>
      <option value="grok">Grok</option>
      <option value="inhouse" selected>Ollama</option>
    </select>
  </div>
  <div class="chat-response" id="chat-response">
    <span class="chat-placeholder">Answers appear here after analysis completes...</span>
  </div>
  <div class="quick-prompts">
    <button class="quick-btn" data-prompt="Explain the worst survived mutant">Worst survived mutant</button>
    <button class="quick-btn" data-prompt="Which function needs the most work?">Most work needed</button>
    <button class="quick-btn" data-prompt="Summarise my test quality">Test quality summary</button>
    <button class="quick-btn" data-prompt="What should I fix first?">Fix priority</button>
  </div>
  <div class="chat-input-row">
    <input class="chat-input" id="chat-input" type="text"
           placeholder="Ask QAMill about your results...">
    <button class="send-btn" id="send-btn">Send</button>
  </div>
</div>

<!-- ── Output Terminal ── -->
<div class="term-panel">
  <div class="term-header">
    <span class="term-header-title">&#9654; QAMill Output</span>
    <span class="term-file-chip" id="term-file">No file selected — right-click a .py source file</span>
    <button class="term-clear" id="term-clear-btn">Clear</button>
  </div>
  <div class="term-body" id="term-body">
    <div class="tl tl-info">QAMill ready. Right-click a Python source file (e.g. math_utils.py) and select &quot;QAMill: Run Mutation Analysis&quot;.</div>
    <div class="tl tl-warn">Tip: select the SOURCE file, not a test file (test_*.py).</div>
  </div>
</div>

<script>
const vscode = acquireVsCodeApi();
let es = null;           // active fetch reader (or null)
let streamActive = false;
let currentStreamUrl = null;
let mutantResults = [];
let lastSummary = null;
let startInfo = {};
let suggestedTests = [];
let scoreBeforeHeal = null;

// ── Message listener ────────────────────────────────────────────────────────
window.addEventListener('message', e => {
  const msg = e.data;
  if (msg.type === 'job_started') {
    // Ignore duplicate deliveries for the same job
    if (msg.stream_url === currentStreamUrl) return;
    currentStreamUrl = msg.stream_url;
    vscode.postMessage({ type: 'job_received' }); // stop retry timer + polling response
    appendLog('job_started received ✓ — starting analysis', 'ok');
    try {
      mutantResults = [];
      lastSummary = null;
      startInfo = {};
      suggestedTests = [];
      scoreBeforeHeal = null;
      const runFile = document.getElementById('run-file');
      if (runFile) runFile.textContent = msg.file || '';
      const chip = document.getElementById('term-file');
      const isTestFile = msg.file && /^test_|_test\\.py$/i.test(msg.file);
      if (chip) {
        chip.textContent = (isTestFile ? '⚠ TEST FILE: ' : '▶ ') + (msg.file || 'unknown');
        chip.className = 'term-file-chip' + (isTestFile ? ' warn' : '');
      }
      const prog = document.getElementById('progress-label');
      if (prog) prog.textContent = 'Connecting to stream…';
      const barEl = document.getElementById('bar');
      if (barEl) { barEl.style.width = '4%'; barEl.classList.add('running'); }
      clearFeed();
      addStatus('▶ ' + (msg.file || '') + '  ·  LLM: ' + (msg.llm_provider || 'none').toUpperCase());
      appendLog('▶ File: ' + (msg.file || 'unknown') + (isTestFile ? '  ⚠ This is a test file — consider selecting the source file instead' : ''), isTestFile ? 'warn' : 'ok');
      appendLog('LLM: ' + (msg.llm_provider || 'none').toUpperCase() + '  |  Stream: ' + msg.stream_url, 'info');
      connectStream(msg.stream_url);
    } catch(err) {
      const feed = document.getElementById('feed');
      if (feed) feed.innerHTML = '<div style="color:#f48771;padding:8px">Dashboard error: ' + String(err) + '</div>';
    }
  }
  if (msg.type === 'backend_log') {
    appendLog(msg.text, msg.level || 'info');
  }
  if (msg.type === 'run_error') {
    addStatus('Error: ' + msg.message);
    appendLog('Error: ' + msg.message, 'error');
  }
  if (msg.type === 'set_file') {
    const lbl = document.getElementById('run-file');
    if (lbl) lbl.textContent = msg.file || '';
  }
  if (msg.type === 'sync_settings') {
    const llmSel  = document.getElementById('llm-select-mini');
    const modeSel = document.getElementById('mode-select');
    if (llmSel  && msg.provider) llmSel.value  = msg.provider;
    if (modeSel && msg.mode)     modeSel.value = msg.mode;
    updateBadge(msg.provider || 'inhouse');
  }
  if (msg.type === 'ai_response') {
    const area = document.getElementById('chat-response');
    area.innerHTML = '<span class="chat-answer"><strong>QAMill:</strong> ' + esc(msg.answer) + '</span>';
    document.getElementById('send-btn').disabled = false;
  }
});

// ── Settings (auto-apply on change) ─────────────────────────────────────────
function updateBadge(p) {
  const badge = document.getElementById('provider-badge');
  if (!badge) return;
  const labels = {none:'NONE', claude:'CLAUDE', gpt:'GPT-4o', grok:'GROK', inhouse:'OLLAMA'};
  const cls    = {none:'pb-none', claude:'pb-claude', gpt:'pb-gpt', grok:'pb-grok', inhouse:'pb-inhouse'};
  badge.textContent = labels[p] || p.toUpperCase();
  badge.className   = 'provider-badge ' + (cls[p] || 'pb-none');
}

function autoApplySettings() {
  const provider  = document.getElementById('llm-select-mini').value;
  const mode      = document.getElementById('mode-select').value;
  const autoHeal  = mode === 'auto_heal' || mode === 'both';
  const aiMutants = mode === 'ai_mutants' || mode === 'both';
  updateBadge(provider);
  vscode.postMessage({ type: 'save_llm_settings', provider, auto_heal: autoHeal, ai_mutants: aiMutants });
}

// ── AI Chat panel ────────────────────────────────────────────────────────────
function buildContext() {
  if (!lastSummary) return 'No analysis has been run yet. Ask the developer to run an analysis first.';
  const survived = mutantResults.filter(m => m.status === 'survived');
  let ctx =
    'ANALYSIS RESULTS (use only these numbers):\\n' +
    '  Total mutants   : ' + lastSummary.total + '\\n' +
    '  Killed          : ' + lastSummary.killed + '\\n' +
    '  Survived        : ' + lastSummary.survived + '\\n' +
    '  Equivalent      : ' + lastSummary.equivalent + '\\n' +
    '  True score      : ' + lastSummary.true_score + '%\\n' +
    '  Raw score       : ' + lastSummary.raw_score + '%\\n';

  if (survived.length === 0) {
    ctx += '  Survived mutants: NONE — all non-equivalent mutants were killed by the test suite.\\n';
  } else {
    ctx += '  Survived mutants (' + survived.length + ' total):\\n';
    survived.slice(0, 10).forEach(m => {
      ctx += '    - ' + m.mutant_id + ' in ' + m.function + '() line ' + m.line +
             ': ' + m.description +
             (m.difficulty ? ' [difficulty: ' + m.difficulty + ']' : '') + '\\n';
    });
    if (survived.length > 10) ctx += '    ...and ' + (survived.length - 10) + ' more.\\n';
  }
  return ctx;
}

function sendQuick(prompt) {
  document.getElementById('chat-input').value = prompt;
  sendChat();
}

function sendChat() {
  const input = document.getElementById('chat-input');
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = '';
  document.getElementById('send-btn').disabled = true;
  document.getElementById('chat-response').innerHTML =
    '<span class="chat-thinking">QAMill is thinking...</span>';
  vscode.postMessage({
    type: 'ai_query',
    prompt: prompt,
    context: buildContext(),
  });
}

// ── Terminal log helper ───────────────────────────────────────────────────────
function appendLog(text, level) {
  const body = document.getElementById('term-body');
  if (!body) return;
  const d = document.createElement('div');
  d.className = 'tl tl-' + (level || 'info');
  const ts = new Date().toTimeString().slice(0, 8);
  d.textContent = '[' + ts + '] ' + text;
  body.appendChild(d);
  body.scrollTop = body.scrollHeight;
}

// ── Stream handling (fetch-based — EventSource is unreliable in VS Code webviews) ──
async function connectStream(url) {
  if (streamActive && es) { try { es.cancel(); } catch(e) {} }
  streamActive = true; es = null;
  appendLog('Connecting → ' + url, 'info');
  try {
    const resp = await fetch(url);
    if (!resp.ok) {
      const msg = 'HTTP ' + resp.status + ' from stream endpoint';
      addStatus('Stream error: ' + msg);
      appendLog('Stream error: ' + msg, 'error');
      streamActive = false; return;
    }
    appendLog('Stream connected ✓', 'ok');
    const reader = resp.body.getReader();
    es = reader;
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\\n');
      buf = lines.pop() || '';
      for (const line of lines) {
        const trim = line.trim();
        if (trim.startsWith('data:')) {
          try { handleEvent(JSON.parse(trim.slice(5).trim())); } catch(e) {}
        }
      }
    }
    appendLog('Stream closed', 'info');
  } catch (err) {
    const msg = String(err);
    addStatus('Stream error: ' + msg);
    appendLog('Stream exception: ' + msg, 'error');
  }
  streamActive = false; es = null;
}

function handleEvent(e) {
  if (e.type === 'ping') return;
  if (e.type === 'status' || e.type === 'healing') {
    addStatus(e.message);
    appendLog(e.message, 'info');
    return;
  }
  if (e.type === 'start') {
    startInfo = e;
    const aiPart = e.ai_mutant_count ? ' + ' + e.ai_mutant_count + ' AI' : '';
    document.getElementById('progress-label').textContent =
      'Analyzing ' + e.total + ' mutants (' + e.ast_mutant_count + ' AST' + aiPart + ')...';
    appendLog('Found ' + e.total + ' mutants  (' + e.ast_mutant_count + ' AST' + aiPart + ')', 'ok');
    return;
  }
  if (e.type === 'mutant_result') {
    mutantResults.push(e);
    if (e.status === 'survived' && scoreBeforeHeal === null) scoreBeforeHeal = e.true_score;
    if (e.suggested_test) addSuggestedTest(e);
    updateScores(e);
    updateBar(e.index, e.total);
    addMutantRow(e);
    return;
  }
  if (e.type === 'complete') {
    lastSummary = e;
    updateScores(e);
    document.getElementById('progress-label').textContent =
      'Complete — ' + e.total + ' mutants analysed';
    const doneBar = document.getElementById('bar');
    if (doneBar) { doneBar.style.width = '100%'; doneBar.classList.remove('running'); }
    addStatus('✔ Done · True score: ' + e.true_score + '% · Raw: ' + e.raw_score + '%');
    appendLog('Done ✓  killed=' + e.killed + '  survived=' + e.survived + '  equiv=' + e.equivalent + '  score=' + e.true_score + '%', 'ok');
    showSummary(e);
    vscode.postMessage({ type: 'analysis_complete', true_score: e.true_score });
    currentStreamUrl = null;
    if (es) { try { es.cancel(); } catch(err) {} es = null; }
    return;
  }
  if (e.type === 'error') {
    addStatus('Error: ' + e.message);
    appendLog('Backend error: ' + e.message, 'error');
  }
}

function updateScores(e) {
  if (e.true_score !== undefined) document.getElementById('true-score').textContent = e.true_score + '%';
  if (e.raw_score  !== undefined) document.getElementById('raw-score').textContent  = e.raw_score  + '%';
  if (e.killed     !== undefined) document.getElementById('killed-count').textContent   = e.killed;
  if (e.survived   !== undefined) document.getElementById('survived-count').textContent = e.survived;
  if (e.equivalent !== undefined) document.getElementById('equiv-count').textContent    = e.equivalent;
}

function updateBar(index, total) {
  const pct = Math.round(index / total * 100);
  const bar = document.getElementById('bar');
  if (bar) bar.style.width = pct + '%';
  const killed   = parseInt(document.getElementById('killed-count').textContent   || '0', 10);
  const survived = parseInt(document.getElementById('survived-count').textContent || '0', 10);
  document.getElementById('progress-label').textContent =
    index + ' / ' + total + '  ·  ✓ ' + killed + ' killed  ·  ✗ ' + survived + ' survived  (' + pct + '%)';
}

function addMutantRow(e) {
  const feed = document.getElementById('feed');
  const div = document.createElement('div');
  div.className = 'event';

  const badgeClass = {killed:'b-killed', survived:'b-survived', equivalent:'b-equivalent', error:'b-error'}[e.status] || 'b-info';
  const icon = {killed:'✓', survived:'✗', equivalent:'≡', error:'!'}[e.status] || '·';

  const isCross = e.operator && e.operator.startsWith('CMR');
  const isAI    = e.operator === 'AI';

  let tags = '';
  if (e.difficulty) {
    const dc = {low:'b-diff-low', medium:'b-diff-medium', high:'b-diff-high'}[e.difficulty] || 'b-info';
    tags += '<span class="mini-tag ' + dc + '">' + e.difficulty[0].toUpperCase() + '</span>';
  }
  if (isCross) tags += '<span class="mini-tag b-cross" title="Cross-method">X</span>';
  if (isAI)    tags += '<span class="mini-tag b-ai-mutant" title="AI mutant">AI</span>';

  div.innerHTML =
    '<span class="badge ' + badgeClass + '">' + icon + ' ' + e.status.toUpperCase() + '</span>' +
    '<span class="mut-line" title="' + esc(e.description) + (e.difficulty_reason ? ' — ' + esc(e.difficulty_reason) : '') + '">' +
      '<span class="mut-id">' + esc(e.mutant_id) + '</span>' +
      '<span class="mut-sep"> · </span>' +
      '<span class="mut-fn">' + esc(e.function) + ':' + e.line + '</span>' +
      '<span class="mut-sep"> · </span>' +
      esc(e.description) +
    '</span>' +
    tags;

  if (isCross && e.status !== 'equivalent') {
    const el = document.getElementById('cross-count');
    if (el) el.textContent = String((parseInt(el.textContent || '0', 10) || 0) + 1);
  }

  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
}

function addStatus(msg) {
  const feed = document.getElementById('feed');
  const d = document.createElement('div');
  d.className = 'status-line';
  d.textContent = msg;
  feed.appendChild(d);
}

function showSummary(e) {
  const sec = document.getElementById('summary-section');
  sec.style.display = 'block';
  const ast = startInfo.ast_mutant_count || e.total;
  const ai  = startInfo.ai_mutant_count  || 0;
  document.getElementById('summary-counts').innerHTML =
    '<span class="summary-score">' + ast + '</span> AST mutants' +
    (ai > 0 ? ' + <span class="summary-score">' + ai + '</span> AI mutants' : '') +
    ' = <strong>' + e.total + '</strong> total';
  const before = scoreBeforeHeal !== null ? scoreBeforeHeal : e.true_score;
  const improved = e.true_score > before;
  document.getElementById('summary-score').innerHTML =
    'True score: <span class="summary-score">' + e.true_score + '%</span>' +
    (improved ? ' <span style="color:#4ec9a0">(+' + (e.true_score - before).toFixed(1) + '% after healing)</span>' : '');
  const top3 = mutantResults
    .filter(m => m.status === 'survived')
    .sort((a, b) => {
      const rank = {high:0, medium:1, low:2};
      return (rank[a.difficulty] ?? 1) - (rank[b.difficulty] ?? 1);
    })
    .slice(0, 3);
  const topEl = document.getElementById('summary-top');
  if (top3.length === 0) {
    topEl.innerHTML = '<div class="top-mutant" style="color:#4ec9a0">All mutants killed!</div>';
  } else {
    topEl.innerHTML = top3.map(m =>
      '<div class="top-mutant">' +
      esc(m.mutant_id) + ' &middot; ' + esc(m.function) + ':' + m.line +
      ' &middot; ' + esc(m.description) +
      (m.difficulty ? ' <span style="opacity:.6">[' + m.difficulty + ']</span>' : '') +
      '</div>'
    ).join('');
  }
}

function addSuggestedTest(e) {
  suggestedTests.push({ id: e.mutant_id, fn: e.function, code: e.suggested_test });
  const panel = document.getElementById('suggested-panel');
  const count = document.getElementById('suggested-count');
  panel.style.display = 'block';
  count.textContent = String(suggestedTests.length);
  const block = document.getElementById('all-tests-block');
  block.textContent = suggestedTests.map(t =>
    '# --- ' + t.id + ' · ' + t.fn + ' ---\\n' + t.code
  ).join('\\n\\n');
}

function toggleSuggested() {
  const body = document.getElementById('suggested-body');
  body.style.display = body.style.display === 'none' ? 'block' : 'none';
}

function copyAllTests() {
  const text = document.getElementById('all-tests-block').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = '&#10003; Copied!';
    setTimeout(() => { btn.innerHTML = '&#128203; Copy All Tests'; }, 2000);
  });
}

function clearFeed() {
  var g = function(id) { return document.getElementById(id); };
  var feed = g('feed');
  if (feed) feed.innerHTML = '';
  var bar = g('bar');
  if (bar) bar.style.width = '0';
  var ss = g('summary-section');
  if (ss) ss.style.display = 'none';
  var sp = g('suggested-panel');
  if (sp) sp.style.display = 'none';
  var atb = g('all-tests-block');
  if (atb) atb.textContent = '';
  var sc = g('suggested-count');
  if (sc) sc.textContent = '0';
  ['true-score','raw-score','killed-count','survived-count','equiv-count','cross-count']
    .forEach(function(id) {
      var el = g(id);
      if (el) el.textContent = id.indexOf('score') !== -1 ? '—' : '0';
    });
}

function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Wire all event listeners ──────────────────────────────────────────────────
document.getElementById('llm-select-mini').addEventListener('change', autoApplySettings);
document.getElementById('mode-select').addEventListener('change', autoApplySettings);
document.getElementById('term-clear-btn').addEventListener('click', function() {
  const b = document.getElementById('term-body'); if (b) b.innerHTML = '';
});
document.getElementById('suggested-header').addEventListener('click', toggleSuggested);
document.getElementById('copy-btn').addEventListener('click', copyAllTests);
document.getElementById('send-btn').addEventListener('click', sendChat);
document.getElementById('chat-input').addEventListener('keydown', function(ev) {
  if (ev.key === 'Enter') sendChat();
});
document.querySelectorAll('.quick-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    sendQuick(btn.getAttribute('data-prompt'));
  });
});

// Notify extension that the webview is ready — triggers pending job delivery
vscode.postMessage({ type: 'webview_ready' });

// Poll every second: if not streaming, ask extension for any pending job.
// This is the guaranteed delivery path — postMessage after reveal() can be dropped.
setInterval(function() {
  if (!streamActive) { vscode.postMessage({ type: 'request_current_job' }); }
}, 1000);
</script>
</body>
</html>`;
}
//# sourceMappingURL=extension.js.map