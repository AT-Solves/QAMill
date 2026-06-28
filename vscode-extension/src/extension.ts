/**
 * extension.ts
 * VS Code extension entry point for AMIL.
 * Spawns Python backend, opens live dashboard webview.
 */
import * as vscode from "vscode";
import * as path from "path";
import * as cp from "child_process";
import * as http from "http";
import * as fs from "fs";

let backendProcess: cp.ChildProcess | undefined;
let dashboardPanel: vscode.WebviewPanel | undefined;
let studioPanel: vscode.WebviewPanel | undefined;       // QAMill Test Studio
let statusBarItem: vscode.StatusBarItem;
let llmStatusBarItem: vscode.StatusBarItem;
let lastFilePath: string | undefined;
let jobDeliveryTimer: ReturnType<typeof setTimeout> | undefined;
let lastProjectRoot: string | undefined;
let pendingJob: { stream_url: string; file: string; llm_provider: string } | undefined;
let activeStreamReq: import("http").ClientRequest | undefined;  // Node.js HTTP stream reader
let streamEventsReceived = 0;                        // for SSE resume on reconnect
let lastIdentityEmail: string | undefined;          // tracks last-known signed-in account
let signInNotified = false;                          // ensures the "signed in" toast fires once per session
let identityPollTimer: ReturnType<typeof setInterval> | undefined;  // polls backend while dashboard open

export function activate(context: vscode.ExtensionContext) {
  // Status bar pill
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusBarItem.text = "$(beaker) QAMill";
  statusBarItem.tooltip = "QAMill QA Governance — click to analyze test quality";
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

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(e => {
      if (e.affectsConfiguration("amil.llmProvider")) { updateLlmStatusBar(); }
    })
  );

  // ── Commands ──────────────────────────────────────────────────────────────
  // uri is passed automatically when invoked from Explorer right-click
  context.subscriptions.push(
    vscode.commands.registerCommand("amil.runAnalysis", (uri?: vscode.Uri) => runAnalysis(context, uri)),
    vscode.commands.registerCommand("amil.stopAnalysis", stopAnalysis),
    vscode.commands.registerCommand("amil.selectLLM", selectLLM),
    vscode.commands.registerCommand("amil.setIdentity", setIdentity),
    vscode.commands.registerCommand("amil.generateUnitTests",   (uri?: vscode.Uri) => openTestStudio(context, uri, "unit")),
    vscode.commands.registerCommand("amil.generateManualTests", (uri?: vscode.Uri) => openTestStudio(context, uri, "test_case")),
    vscode.commands.registerCommand("amil.openTestStudio",      (uri?: vscode.Uri) => openTestStudio(context, uri)),
  );
}

export function deactivate() {
  stopAnalysis();
}

// ── Run Analysis ─────────────────────────────────────────────────────────────

async function runAnalysis(context: vscode.ExtensionContext, uri?: vscode.Uri) {
  const config   = vscode.workspace.getConfiguration("amil");
  const port: number = config.get("backendPort", 8765);

  // ── Resolve file path ────────────────────────────────────────────────────
  let filePath: string | undefined;
  let projectRoot: string | undefined = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

  if (uri) {
    const stat = fs.statSync(uri.fsPath);
    if (stat.isDirectory()) {
      // Folder right-click — find first source file (Python, JS, TS, etc)
      filePath = findSourceFile(uri.fsPath);
      if (!filePath) {
        vscode.window.showErrorMessage("QAMill: No source files found in this folder. Supported: .py, .js, .ts, .jsx, .tsx");
        return;
      }
      projectRoot = uri.fsPath;
    } else {
      filePath    = uri.fsPath;
      projectRoot = projectRoot || path.dirname(uri.fsPath);
    }
  } else {
    // Fallback: active editor
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage("QAMill: Open or right-click a Python (.py) file to open Test Studio.");
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
  // Support Python (test_*.py, *_test.py) and JS/TS (*.test.js, *.spec.js, etc) test patterns
  if (/^test_|_test\.(py|js|ts|jsx|tsx)$|\.test\.(js|ts|jsx|tsx)$|\.spec\.(js|ts|jsx|tsx)$/i.test(basename)) {
    const pick = await vscode.window.showWarningMessage(
      `QAMill: "${basename}" looks like a test file. Select the SOURCE file for meaningful mutation testing.`,
      "Analyze Anyway", "Cancel"
    );
    if (pick !== "Analyze Anyway") {
      statusBarItem.text = "$(beaker) QAMill";
      return;
    }
  }

  lastFilePath    = filePath;
  lastProjectRoot = projectRoot;

  const llmProvider: string = config.get("llmProvider", "inhouse");

  // ── Open the dashboard FIRST so its shell paints instantly ───────────────
  // The webview is independent of the backend; showing it immediately removes
  // the multi-second blank wait while Python boots. It renders a "starting"
  // state and hydrates once the stream arrives.
  openDashboard(context, port);
  dashboardPanel?.webview.postMessage({ type: "set_file", file: path.basename(filePath) });
  dashboardPanel?.webview.postMessage({ type: "engine_starting" });

  // ── Ensure backend is running (in the background, dashboard already shown) ─
  statusBarItem.text = "$(sync~spin) QAMill Starting...";
  const backendReady = await ensureBackendRunning(context, port);
  if (!backendReady) {
    const m = "Could not start the analysis engine. Check that Python is on your PATH.";
    vscode.window.showErrorMessage(`QAMill: ${m}`);
    dashboardPanel?.webview.postMessage({ type: "run_error", message: m });
    statusBarItem.text = "$(beaker) QAMill";
    return;
  }

  // ── Start analysis ───────────────────────────────────────────────────────
  const payload = {
    file_path:          filePath,
    project_root:       projectRoot,
    llm_provider:       llmProvider,
    llm_api_key:        getApiKey(config, llmProvider),
    auto_heal:          config.get("autoHeal", true),
    detect_equivalents: config.get("detectEquivalents", true),
    ai_mutants:         config.get("aiMutants", false),
  };

  let jobResp: any;
  try {
    jobResp = await postJson(`http://localhost:${port}/analyze`, payload);
  } catch (err) {
    const m = friendlyConnError(err, port);
    vscode.window.showErrorMessage(m, "Retry")
      .then(choice => { if (choice === "Retry") { runAnalysis(context, uri); } });
    dashboardPanel?.webview.postMessage({ type: "run_error", message: m });
    statusBarItem.text = "$(beaker) QAMill";
    return;
  }

  // Store job metadata for the dashboard
  pendingJob = {
    stream_url:   jobResp.stream_url,
    file:         path.basename(filePath),
    llm_provider: llmProvider,
  };
  deliverPendingJob();

  // Stream via Node.js http — bypasses VS Code webview proxy buffering.
  // Each event is forwarded to the webview via postMessage as it arrives.
  startExtensionStream(jobResp.stream_url);
  statusBarItem.text = "$(sync~spin) QAMill Running...";
  vscode.window.showInformationMessage(`QAMill: Analysing ${path.basename(filePath)}…`);
}

// ── Source file discovery (Python, JS, TS, etc) ────────────────────────────────

function findSourceFile(dir: string): string | undefined {
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    // Prefer files at the top level first (Python, JS, TS, etc)
    for (const e of entries) {
      if (e.isFile()) {
        const n = e.name;
        // Support .py, .js, .ts, .jsx, .tsx extensions
        if (/\.(py|js|ts|jsx|tsx)$/i.test(n)) {
          // Skip test files: test_*.py, *_test.py, *.test.js, *.spec.js, etc
          if (!/^test_|_test\.(py|js|ts|jsx|tsx)$|\.test\.(js|ts|jsx|tsx)$|\.spec\.(js|ts|jsx|tsx)$|conftest\.py$/i.test(n)) {
            return path.join(dir, n);
          }
        }
      }
    }
    // Recurse into subdirectories (skip hidden / cache / node_modules)
    for (const e of entries) {
      if (e.isDirectory() && !e.name.startsWith(".") && e.name !== "__pycache__" && e.name !== "node_modules" && e.name !== "tests") {
        const found = findSourceFile(path.join(dir, e.name));
        if (found) { return found; }
      }
    }
  } catch { /* ignore permission errors */ }
  return undefined;
}

// ── Backend lifecycle ─────────────────────────────────────────────────────────

async function ensureBackendRunning(context: vscode.ExtensionContext,
                                    port: number): Promise<boolean> {
  // Check if already running and healthy
  if (await isPortOpen(port)) {
    try {
      const ctrl = new AbortController();
      const timeoutId = setTimeout(() => ctrl.abort(), 2000);
      const resp = await fetch(`http://localhost:${port}/health`, { signal: ctrl.signal });
      clearTimeout(timeoutId);
      if (resp.ok) return true;
    } catch { /* port might be stuck, continue to restart */ }
  }

  // Port is in use but not responding — kill stuck process
  if (await isPortOpen(port)) {
    try {
      const { exec } = require("child_process");
      if (process.platform === "win32") {
        exec(`netstat -ano | find ":${port}"`, (err: any, stdout: string) => {
          const lines = stdout.split("\n");
          for (const line of lines) {
            const parts = line.trim().split(/\s+/);
            if (parts.length > 0 && parts[parts.length - 1] !== "0") {
              const pid = parts[parts.length - 1];
              try { process.kill(parseInt(pid)); } catch { /* ignore */ }
            }
          }
        });
      }
      await sleep(1000);
    } catch { /* ignore cleanup errors */ }
  }

  // Spawn fresh backend
  const backendDir = path.join(context.extensionPath, "..", "backend");
  backendProcess = cp.spawn("python", ["main.py"], {
    cwd: backendDir,
    detached: false,
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendProcess.stdout?.on("data", (d) => {
    const text = d.toString().trim();
    if (text) { dashboardPanel?.webview.postMessage({ type: "backend_log", text, level: "info" }); }
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
    if (await isPortOpen(port)) return true;
  }

  // Failed to start backend
  vscode.window.showErrorMessage(
    "QAMill: Backend failed to start. " +
    "Port 8765 may be in use. " +
    "Try: Restart VS Code or check 'netstat -ano | find \":8765\"' to find blocking processes."
  );
  return false;
}

function stopAnalysis() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = undefined;
  }
  statusBarItem.text = "$(beaker) QAMill";
}

function isPortOpen(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(500, () => { req.destroy(); resolve(false); });
  });
}

// ── Dashboard Webview ─────────────────────────────────────────────────────────

function openDashboard(context: vscode.ExtensionContext, port: number) {
  if (dashboardPanel) {
    dashboardPanel.reveal(vscode.ViewColumn.Beside);
    return;
  }

  const logoUri = vscode.Uri.joinPath(context.extensionUri, "media", "qamill-logo.png");

  dashboardPanel = vscode.window.createWebviewPanel(
    "amilDashboard",
    "QAMill QA Governance — Test Quality",
    vscode.ViewColumn.Beside,
    {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: [
        vscode.Uri.joinPath(context.extensionUri, "media"),
      ],
    }
  );

  // Logo in the VS Code tab
  dashboardPanel.iconPath = logoUri;

  // Webview-safe URI so the HTML <img> can load the logo
  const webviewLogoUri = dashboardPanel.webview.asWebviewUri(logoUri);
  const cspSource      = dashboardPanel.webview.cspSource;
  dashboardPanel.webview.html = getDashboardHtml(port, webviewLogoUri.toString(), cspSource);

  // Tell dashboard which file and LLM are active on first open
  setTimeout(() => {
    if (lastFilePath) {
      dashboardPanel?.webview.postMessage({
        type: "set_file",
        file: path.basename(lastFilePath!),
      });
    }
    const currentProvider = vscode.workspace.getConfiguration("amil").get<string>("llmProvider", "inhouse");
    dashboardPanel?.webview.postMessage({ type: "sync_settings", provider: currentProvider });
  }, 500);

  // Handle messages from webview
  dashboardPanel.webview.onDidReceiveMessage(async (msg) => {
    // Shared header messages (sign in / set LLM / sign out)
    if (msg.type?.startsWith("sh_")) {
      const cfg = vscode.workspace.getConfiguration("amil");
      const backendPort: number = cfg.get("backendPort", 8765);
      await handleSharedHeaderMessage(dashboardPanel, msg, context, backendPort);
      return;
    }

    if (msg.type === "webview_ready") {
      // Webview just (re)loaded — deliver any pending job immediately
      if (lastFilePath) {
        dashboardPanel?.webview.postMessage({
          type: "set_file",
          file: path.basename(lastFilePath),
        });
      }
      dashboardPanel?.webview.postMessage(buildSyncPayload());
      refreshIdentity(port);          // sync signed-in account from backend
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
      if (jobDeliveryTimer) { clearTimeout(jobDeliveryTimer); jobDeliveryTimer = undefined; }
      return;
    }

    if (msg.type === "analysis_complete") {
      pendingJob = undefined;
      if (jobDeliveryTimer) { clearTimeout(jobDeliveryTimer); jobDeliveryTimer = undefined; }
      statusBarItem.text = `$(beaker) QAMill ${msg.true_score}%`;

      // Show notification with Open Report / Email Report buttons
      const reportPath: string | undefined = msg.report_path;
      const notifMsg = `QAMill analysis complete — True score: ${msg.true_score}%`;
      if (reportPath && !reportPath.startsWith("error:")) {
        vscode.window.showInformationMessage(notifMsg, "Open Report", "Email Report")
          .then(action => {
            if (action === "Open Report") {
              vscode.env.openExternal(vscode.Uri.file(reportPath));
            } else if (action === "Email Report") {
              dashboardPanel?.webview.postMessage({ type: "open_email_modal" });
            }
          });
      } else {
        vscode.window.showInformationMessage(notifMsg);
      }

      // Auto-email if configured
      const cfg2 = vscode.workspace.getConfiguration("amil");
      const autoSend = cfg2.get<boolean>("email.autoSend", false);
      const ec = readEmailConfig();
      if (autoSend && ec.recipient && ec.sender && ec.appPassword && ec.smtp_host && msg.job_id) {
        dashboardPanel?.webview.postMessage({ type: "email_sending" });
        postJson(`http://localhost:${port}/email`, {
          job_id: msg.job_id, to_address: ec.recipient,
          sender_email: ec.sender,
          smtp_host: ec.smtp_host, smtp_port: ec.smtp_port,
          smtp_user: ec.sender, smtp_password: ec.appPassword,
          use_tls: ec.use_tls,
        }).then(r => {
          dashboardPanel?.webview.postMessage({ type: "email_sent", to: r.to });
          vscode.window.showInformationMessage(`QAMill report auto-sent to ${r.to}`);
        }).catch(err => {
          const errMsg = String(err).replace(/^Error: HTTP \d+: /, "");
          dashboardPanel?.webview.postMessage({ type: "email_error", error: errMsg });
        });
      }
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
      lastFilePath    = targetFile;
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
      const llmProvider = config.get<string>("llmProvider", "inhouse");
      const payload = {
        file_path:          targetFile,
        project_root:       targetRoot,
        llm_provider:       llmProvider,
        llm_api_key:        getApiKey(config, llmProvider),
        auto_heal:          msg.auto_heal  ?? config.get("autoHeal", true),
        detect_equivalents: config.get("detectEquivalents", true),
        ai_mutants:         msg.ai_mutants ?? config.get("aiMutants", false),
      };
      try {
        const jobResp = await postJson(`http://localhost:${port}/analyze`, payload);
        pendingJob = { stream_url: jobResp.stream_url, file: path.basename(targetFile), llm_provider: llmProvider };
        deliverPendingJob();
        statusBarItem.text = "$(sync~spin) QAMill Running...";
      } catch (err) {
        const msg2 = `POST to backend failed: ${err}`;
        vscode.window.showErrorMessage(`QAMill: ${msg2}`);
        dashboardPanel?.webview.postMessage({ type: "run_error", message: msg2 });
        statusBarItem.text = "$(beaker) QAMill";
      }
    }

    if (msg.type === "save_llm_settings") {
      const config = vscode.workspace.getConfiguration("amil");
      await config.update("llmProvider", msg.provider, vscode.ConfigurationTarget.Workspace);
      if (msg.auto_heal  !== undefined) { await config.update("autoHeal",  msg.auto_heal,  vscode.ConfigurationTarget.Workspace); }
      if (msg.ai_mutants !== undefined) { await config.update("aiMutants", msg.ai_mutants, vscode.ConfigurationTarget.Workspace); }
      updateLlmStatusBar();
    }

    if (msg.type === "save_report") {
      const saveUri = await vscode.window.showSaveDialog({
        defaultUri: vscode.Uri.file(`qamill-report-${(msg.job_id as string).slice(0, 8)}.html`),
        filters: { "HTML Report": ["html"] },
        title: "Save QAMill Report",
      });
      if (saveUri) {
        try {
          const html = await getText(`http://localhost:${port}/export/${msg.job_id}`);
          fs.writeFileSync(saveUri.fsPath, html, "utf8");
          vscode.window.showInformationMessage(
            `QAMill report saved to ${saveUri.fsPath}`, "Open in Browser"
          ).then(a => { if (a === "Open in Browser") { vscode.env.openExternal(saveUri); } });
        } catch (err) {
          vscode.window.showErrorMessage(`QAMill: Failed to save report — ${err}`);
        }
      }
      return;
    }

    if (msg.type === "email_report") {
      // Is an OAuth email account (Google/Microsoft) connected? Then no SMTP needed.
      let oauthConnected = false;
      try {
        const st = await getJson(`http://127.0.0.1:${port}/auth/status`);
        oauthConnected = !!(st?.primary && st.primary.can_email);
      } catch { /* backend may be busy — fall back to SMTP rules */ }

      const ec = readEmailConfig();
      const sender      = (msg.sender      || ec.sender).trim();
      const appPassword =  msg.appPassword || ec.appPassword;
      const recipient   = (msg.recipient   || ec.recipient).trim();
      const smtpHost    =  msg.smtp_host   || ec.smtp_host;
      const smtpPort    =  msg.smtp_port   ?? ec.smtp_port;
      const useTls      =  msg.use_tls     ?? ec.use_tls;

      // Recipient is always required; SMTP creds only required without OAuth.
      if (!recipient || (!oauthConnected && (!sender || !appPassword || !smtpHost))) {
        dashboardPanel?.webview.postMessage({ type: "open_email_modal" });
        return;
      }

      dashboardPanel?.webview.postMessage({ type: "email_sending" });
      try {
        // When OAuth is connected the backend sends via Gmail/Graph; SMTP fields ignored.
        const result = await postJson(`http://localhost:${port}/email`, {
          job_id:        msg.job_id,
          to_address:    recipient,
          sender_email:  sender,
          smtp_host:     smtpHost,
          smtp_port:     smtpPort,
          smtp_user:     sender,
          smtp_password: oauthConnected ? "" : appPassword,
          use_tls:       useTls,
        });
        const via = result.method === "oauth" ? ` via ${result.provider || "your account"}` : "";
        dashboardPanel?.webview.postMessage({ type: "email_sent",         to: result.to });
        dashboardPanel?.webview.postMessage({ type: "email_modal_result", success: true,
                                             message: `Report sent to ${result.to}${via}` });
        vscode.window.showInformationMessage(`QAMill report sent to ${result.to}${via}`);
      } catch (err) {
        const errMsg = String(err).replace(/^Error: HTTP \d+: /, "");
        dashboardPanel?.webview.postMessage({ type: "email_error",        error: errMsg });
        dashboardPanel?.webview.postMessage({ type: "email_modal_result", success: false, message: errMsg });
        vscode.window.showErrorMessage(`QAMill: Email failed — ${errMsg}`);
      }
      return;
    }

    if (msg.type === "ai_query") {
      const config = vscode.workspace.getConfiguration("amil");
      const llmProvider = config.get<string>("llmProvider", "inhouse");
      const llmApiKey = getApiKey(config, llmProvider);
      try {
        const resp = await postJson(`http://localhost:${port}/ask`, {
          prompt: msg.prompt,
          context: msg.context,
          llm_provider: llmProvider,
          llm_api_key: llmApiKey,
        });
        dashboardPanel?.webview.postMessage({ type: "ai_response", answer: resp.answer });
      } catch (err) {
        dashboardPanel?.webview.postMessage({
          type: "ai_response",
          answer: `QAMill assistant unavailable — make sure a LLM provider is configured. (${err})`,
        });
      }
    }

    // ── Email settings ────────────────────────────────────────────────────────

    if (msg.type === "email_settings_save") {
      const cfg = vscode.workspace.getConfiguration("amil");
      const t = vscode.ConfigurationTarget.Workspace;
      if (msg.provider)    { await cfg.update("email.provider",    msg.provider,    t); }
      if (msg.sender)      { await cfg.update("email.sender",      msg.sender,      t); }
      if (msg.appPassword) { await cfg.update("email.appPassword", msg.appPassword, t); }
      if (msg.recipient)   { await cfg.update("email.recipient",   msg.recipient,   t); }
      if (msg.smtp_host)   { await cfg.update("email.smtpHost",    msg.smtp_host,   t); }
      if (msg.smtp_port)   { await cfg.update("email.smtpPort",    msg.smtp_port,   t); }
      return;
    }

    if (msg.type === "email_send_test") {
      try {
        const result = await postJson(`http://localhost:${port}/email/test`, {
          to_address:    msg.recipient,
          sender_email:  msg.sender,
          smtp_host:     msg.smtp_host,
          smtp_port:     msg.smtp_port,
          smtp_user:     msg.sender,
          smtp_password: msg.appPassword,
          use_tls:       msg.use_tls ?? true,
        });
        dashboardPanel?.webview.postMessage({
          type: "email_test_result", success: true, message: result.message,
        });
      } catch (err) {
        const errMsg = String(err).replace(/^Error: HTTP \d+: /, "");
        dashboardPanel?.webview.postMessage({
          type: "email_test_result", success: false, message: errMsg,
        });
      }
      return;
    }

    if (msg.type === "open_external") {
      vscode.env.openExternal(vscode.Uri.parse(msg.url));
      return;
    }

    if (msg.type === "set_identity_prompt") {
      await vscode.commands.executeCommand("amil.setIdentity");
      return;
    }

    if (msg.type === "open_auth_modal") {
      // Fallback path (command palette). The dashboard now opens its own popup.
      await vscode.commands.executeCommand("amil.setIdentity");
      return;
    }

    if (msg.type === "auth_submit") {
      // Email sign in / sign up from the dashboard popup
      const endpoint = msg.mode === "signup" ? "/auth/signup" : "/auth/signin";
      const body = msg.mode === "signup"
        ? { email: msg.email, password: msg.password, name: msg.name }
        : { email: msg.email, password: msg.password };
      try {
        const resp = await postJson(`http://127.0.0.1:${port}${endpoint}`, body);
        const user = resp.user;
        const cfg = vscode.workspace.getConfiguration("amil");
        const t   = vscode.ConfigurationTarget.Workspace;
        try {
          await cfg.update("userEmail",    user.email, t);
          await cfg.update("email.sender", user.email, t);
        } catch { /* no workspace */ }
        lastIdentityEmail = user.email;
        dashboardPanel?.webview.postMessage({ type: "auth_result", success: true, name: user.name });
        dashboardPanel?.webview.postMessage({ type: "apply_identity",
          identity: { email: user.email, name: user.name, can_email: user.can_email, type: "work" } });
      } catch (err) {
        const m = String(err).replace(/^Error: HTTP \d+: /, "");
        dashboardPanel?.webview.postMessage({ type: "auth_result", success: false, error: m });
      }
      return;
    }

    if (msg.type === "auth_oauth") {
      // Social sign-in: open the provider in the system browser, then poll for the session
      await vscode.env.openExternal(vscode.Uri.parse(`http://localhost:${port}/auth/login/${msg.provider}`));
      const started = Date.now();
      const poll = async (): Promise<void> => {
        if (Date.now() - started > 300_000) { return; }
        try {
          const me = await getJson(`http://127.0.0.1:${port}/auth/me`);
          if (me.user) {
            const u = me.user;
            const cfg = vscode.workspace.getConfiguration("amil");
            const t   = vscode.ConfigurationTarget.Workspace;
            try {
              await cfg.update("userEmail",    u.email, t);
              await cfg.update("email.sender", u.email, t);
            } catch { /* no workspace */ }
            lastIdentityEmail = u.email;
            dashboardPanel?.webview.postMessage({ type: "auth_result", success: true, name: u.name });
            dashboardPanel?.webview.postMessage({ type: "apply_identity",
              identity: { email: u.email, name: u.name, provider: msg.provider,
                          can_email: u.can_email, type: "work" } });
            return;
          }
        } catch { /* keep polling */ }
        setTimeout(poll, 1500);
      };
      setTimeout(poll, 1500);
      return;
    }

    if (msg.type === "sign_out") {
      try {
        // End QAMill session + disconnect OAuth tokens
        await postJson(`http://127.0.0.1:${port}/auth/signout?everywhere=true`, {});
      } catch { /* best-effort */ }
      // Clear saved identity from settings
      const cfg = vscode.workspace.getConfiguration("amil");
      const t   = vscode.ConfigurationTarget.Workspace;
      try {
        await cfg.update("userEmail",    "", t);
        await cfg.update("email.sender", "", t);
      } catch { /* no workspace */ }
      lastIdentityEmail = "";
      signInNotified    = false;
      dashboardPanel?.webview.postMessage({ type: "apply_identity", identity: null });
      vscode.window.showInformationMessage("QAMill: Signed out successfully.");
      return;
    }
  });

  // Poll the backend for sign-in changes while the dashboard is open, so an
  // OAuth login completed in the browser popup reflects in VS Code within ~3s.
  if (identityPollTimer) { clearInterval(identityPollTimer); }
  identityPollTimer = setInterval(() => {
    if (dashboardPanel) { refreshIdentity(port); }
  }, 5000);

  dashboardPanel.onDidDispose(() => {
    dashboardPanel = undefined;
    statusBarItem.text = "$(beaker) QAMill";
    if (identityPollTimer) { clearInterval(identityPollTimer); identityPollTimer = undefined; }
    if (activeStreamReq)   { try { activeStreamReq.destroy(); } catch {} activeStreamReq = undefined; }
  });
}

// ── LLM selector quick-pick ───────────────────────────────────────────────────

async function selectLLM() {
  const choice = await vscode.window.showQuickPick(
    [
      { label: "$(circle-slash) None — in-house AST only", value: "none" },
      { label: "$(sparkle) Claude (Anthropic)",            value: "claude" },
      { label: "$(sparkle) GPT-4o (OpenAI)",              value: "gpt" },
      { label: "$(sparkle) Grok (xAI)",                   value: "grok" },
      { label: "$(home) Ollama — fully offline",           value: "inhouse" },
    ],
    { placeHolder: "Select LLM provider for QAMill" }
  );
  if (choice) {
    await vscode.workspace.getConfiguration("amil").update(
      "llmProvider", choice.value, vscode.ConfigurationTarget.Workspace
    );
    updateLlmStatusBar();
    dashboardPanel?.webview.postMessage(buildSyncPayload());
    vscode.window.showInformationMessage(`QAMill: LLM set to ${choice.label}`);
  }
}

// ── Identity (sender email) ───────────────────────────────────────────────────

async function setIdentity() {
  const port: number = vscode.workspace.getConfiguration("amil").get("backendPort", 8765);

  const choice = await vscode.window.showQuickPick(
    [
      { label: "$(account) Continue with Google",        value: "google",    group: "social" },
      { label: "$(window) Continue with Microsoft",      value: "microsoft", group: "social" },
      { label: "$(globe) Continue with Atlassian (Jira)", value: "atlassian", group: "social" },
      { label: "$(github) Continue with GitHub",         value: "github",    group: "social" },
      { label: "$(person) LinkedIn",                     value: "linkedin",  group: "dev"    },
      { label: "$(comment) Slack workspace",             value: "slack",     group: "dev"    },
      { label: "$(mail) Sign in with email",             value: "__signin__", group: "email" },
      { label: "$(person-add) Create account with email", value: "__signup__", group: "email" },
    ],
    { placeHolder: "Sign in or sign up…", title: "QAMill — Sign in" }
  );
  if (!choice) { return; }

  // ── Email sign in / sign up ──────────────────────────────────────────────
  if (choice.value === "__signin__" || choice.value === "__signup__") {
    const isSignup = choice.value === "__signup__";
    let name = "";
    if (isSignup) {
      name = await vscode.window.showInputBox({
        prompt: "Your name", placeHolder: "Jane Developer",
      }) ?? "";
    }
    const email = await vscode.window.showInputBox({
      prompt: "Email address", placeHolder: "you@company.com",
      validateInput: (v) => (v && v.includes("@") ? null : "Enter a valid email address"),
    });
    if (!email) { return; }
    const password = await vscode.window.showInputBox({
      prompt: isSignup ? "Choose a password (min 8 chars)" : "Password",
      password: true,
      validateInput: (v) => (isSignup && (!v || v.length < 8) ? "At least 8 characters" : null),
    });
    if (!password) { return; }

    try {
      const endpoint = isSignup ? "/auth/signup" : "/auth/signin";
      const resp = await postJson(`http://localhost:${port}${endpoint}`,
        isSignup ? { email, password, name } : { email, password });
      const user = resp.user;
      const cfg = vscode.workspace.getConfiguration("amil");
      const t   = vscode.ConfigurationTarget.Workspace;
      await cfg.update("userEmail",    user.email, t);
      await cfg.update("email.sender", user.email, t);
      lastIdentityEmail = user.email;
      dashboardPanel?.webview.postMessage(buildSyncPayload());
      dashboardPanel?.webview.postMessage({ type: "apply_identity",
        identity: { email: user.email, name: user.name, type: "work" } });
      vscode.window.showInformationMessage(
        `QAMill: ${isSignup ? "Account created" : "Signed in"} as ${user.email}`);
    } catch (err) {
      const m = String(err).replace(/^Error: HTTP \d+: /, "");
      vscode.window.showErrorMessage(`QAMill: ${m}`);
    }
    return;
  }

  // OAuth flow — open system browser
  const loginUrl = `http://localhost:${port}/auth/login/${choice.value}`;
  await vscode.env.openExternal(vscode.Uri.parse(loginUrl));

  // Poll until connected or timeout
  vscode.window.showInformationMessage(
    `QAMill: Sign in to ${choice.label.replace(/\$\([^)]+\)\s*/g, "")} in your browser…`
  );

  const started = Date.now();
  const poll = async (): Promise<void> => {
    if (Date.now() - started > 300_000) { return; } // 5 min timeout
    try {
      const status = await getJson(`http://localhost:${port}/auth/status/${choice.value}`);
      if (status.connected) {
        const name = status.name || status.email || choice.value;
        // Sync identity to VS Code settings
        const cfg = vscode.workspace.getConfiguration("amil");
        const t   = vscode.ConfigurationTarget.Workspace;
        if (status.email) {
          await cfg.update("userEmail",    status.email, t);
          await cfg.update("email.sender", status.email, t);
        }
        dashboardPanel?.webview.postMessage(buildSyncPayload());
        dashboardPanel?.webview.postMessage({
          type: "auth_connected",
          provider: choice.value,
          name, email: status.email,
        });
        vscode.window.showInformationMessage(
          `QAMill: Connected to ${choice.label.replace(/\$\([^)]+\)\s*/g, "")} as ${name}`
        );
        return;
      }
    } catch { /* backend may be busy */ }
    setTimeout(poll, 1500);
  };
  setTimeout(poll, 1500);
}

// ── QAMill Test Studio (webview: select LLM + format, Generate, live progress) ─

let studioTarget: { filePath: string; presetFormat?: string } | undefined;

function openTestStudio(context: vscode.ExtensionContext,
                        uri: vscode.Uri | undefined,
                        presetFormat?: string) {
  // Resolve the target .py file
  let filePath = uri?.fsPath;
  if (!filePath) {
    const ed = vscode.window.activeTextEditor;
    if (ed && ed.document.languageId === "python") { filePath = ed.document.uri.fsPath; }
  }
  if (!filePath || !filePath.endsWith(".py")) {
    vscode.window.showErrorMessage("QAMill: Open or right-click a Python (.py) file to open Test Studio.");
    return;
  }
  studioTarget = { filePath, presetFormat };

  if (studioPanel) {
    studioPanel.reveal(vscode.ViewColumn.Active);
    studioPanel.webview.postMessage({ type: "studio_init", ...buildStudioInit() });
    return;
  }

  const logoUri = vscode.Uri.joinPath(context.extensionUri, "media", "qamill-logo.png");
  studioPanel = vscode.window.createWebviewPanel(
    "amilTestStudio", "QAMill QA Governance — Test Authoring", vscode.ViewColumn.Active,
    { enableScripts: true, retainContextWhenHidden: true,
      localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, "media")] });
  studioPanel.iconPath = logoUri;
  const webLogo = studioPanel.webview.asWebviewUri(logoUri).toString();
  studioPanel.webview.html = getTestStudioHtml(studioPanel.webview.cspSource, webLogo);

  studioPanel.webview.onDidReceiveMessage(async (msg) => {
    // Shared header messages (sign in / set LLM / sign out)
    if (msg.type?.startsWith("sh_")) {
      const cfg = vscode.workspace.getConfiguration("amil");
      const port: number = cfg.get("backendPort", 8765);
      await handleSharedHeaderMessage(studioPanel, msg, context, port);
      return;
    }
    if (msg.type === "studio_ready") {
      studioPanel?.webview.postMessage({ type: "studio_init", ...buildStudioInit() });
      return;
    }
    if (msg.type === "studio_generate") { await runStudioGeneration(context, msg); return; }
    if (msg.type === "studio_save")     { await saveStudioResult(msg); return; }
  });

  studioPanel.onDidDispose(() => { studioPanel = undefined; });
}

function buildStudioInit() {
  const cfg = vscode.workspace.getConfiguration("amil");
  return {
    file:     studioTarget ? path.basename(studioTarget.filePath) : "",
    provider: cfg.get<string>("llmProvider", "inhouse"),
    preset:   studioTarget?.presetFormat || "test_case",
  };
}

async function runStudioGeneration(context: vscode.ExtensionContext, msg: any) {
  const cfg  = vscode.workspace.getConfiguration("amil");
  const port: number = cfg.get("backendPort", 8765);
  const filePath = studioTarget?.filePath;
  if (!filePath) { return; }

  const provider = msg.provider || "inhouse";
  const fmt      = msg.format   || "test_case";
  const folder   = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || path.dirname(filePath);
  const prog = (m: string) => studioPanel?.webview.postMessage({ type: "studio_progress", message: m });

  prog("Starting analysis engine…");
  const ready = await ensureBackendRunning(context, port);
  if (!ready) { studioPanel?.webview.postMessage({ type: "studio_error", message: "Could not start the backend." }); return; }

  prog(`Reading ${path.basename(filePath)} and building the ${fmt} prompt…`);
  prog(`Asking ${provider.toUpperCase()} to generate the suite… (this can take a while on local Ollama)`);
  if (fmt === "unit") { prog("Will verify the suite against your original code after generation…"); }

  try {
    const isStreamFormat = fmt === "test_case" || fmt === "table";

    // Fetch the stored API key from backend auth vault
    let apiKey = "";
    try {
      const keyResp = await fetch(`http://localhost:${port}/auth/llm/get-key/${provider}`);
      if (keyResp.ok) {
        const keyData = (await keyResp.json()) as any;
        apiKey = keyData?.api_key || "";
      }
    } catch (e) {
      // Silently continue - key will be empty and backend will handle
    }

    prog(`[DEBUG-FRONTEND] Provider: ${provider}`);
    prog(`[DEBUG-FRONTEND] API Key from backend vault: ${apiKey ? apiKey.substring(0, 10) + '***' : 'NOT_FOUND'}`);

    if (isStreamFormat) {
      // Stream results for manual test formats
      const requestBody = {
        file_path: filePath, project_root: folder,
        llm_provider: provider, llm_api_key: apiKey,
        format: fmt, verify: true,
      };
      prog(`[DEBUG-FRONTEND] Sending request with llm_api_key: ${apiKey ? 'YES' : 'NO'}`);

      const resp = await fetch(`http://localhost:${port}/generate/test-suite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      if (!resp.ok) {
        studioPanel?.webview.postMessage({ type: "studio_error", message: `HTTP ${resp.status}` });
        return;
      }

      const reader = resp.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let testCount = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        const lines = text.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const json_str = line.slice(6).trim();
            if (!json_str) continue;
            try {
              const evt = JSON.parse(json_str);
              if (evt.type === "start") {
                prog("Generating tests… streaming results:");
              } else if (evt.type === "test") {
                testCount++;
                prog(`✓ Test ${evt.index}: ${evt.case.id || evt.case.name || "Test " + evt.index}`);
              } else if (evt.type === "complete") {
                prog(`Done: ${evt.count || testCount} test(s) generated.`);
              } else if (evt.type === "error") {
                studioPanel?.webview.postMessage({ type: "studio_error", message: evt.message });
                return;
              }
            } catch (e) {
              /* ignore parse errors */
            }
          }
        }
      }

      // Fetch the final result (streaming doesn't include complete content)
      const finalResp = await postJson(`http://localhost:${port}/generate/test-suite`, {
        file_path: filePath, project_root: folder,
        llm_provider: provider, llm_api_key: getApiKey(cfg, provider),
        format: fmt, verify: true,
      });
      studioPanel?.webview.postMessage({ type: "studio_result", result: finalResp });
    } else {
      // Non-streaming formats (unit, gherkin, traceability)
      const resp = await postJson(`http://localhost:${port}/generate/test-suite`, {
        file_path: filePath, project_root: folder,
        llm_provider: provider, llm_api_key: getApiKey(cfg, provider),
        format: fmt, verify: true,
      });
      if (!resp.success) {
        studioPanel?.webview.postMessage({ type: "studio_error", message: resp.message || "Generation failed." });
        return;
      }
      if (fmt === "unit" && resp.verified !== undefined) {
        prog(resp.verified ? `Verified — ${resp.passed} test(s) passed against the original.`
                           : `Generated, but ${resp.failed} test(s) did not pass — review before committing.`);
      }
      prog("Done.");
      studioPanel?.webview.postMessage({ type: "studio_result", result: resp });
    }
  } catch (err) {
    studioPanel?.webview.postMessage({ type: "studio_error",
      message: String(err).replace(/^Error: HTTP \d+: /, "") });
  }
}

async function saveStudioResult(msg: any) {
  const filePath = studioTarget?.filePath;
  if (!filePath || !msg.content) { return; }
  const dest = vscode.Uri.file(path.join(path.dirname(filePath), msg.filename || "qamill-suite.txt"));
  await vscode.workspace.fs.writeFile(dest, Buffer.from(msg.content, "utf8"));
  await vscode.window.showTextDocument(dest, { preview: false });
  vscode.window.showInformationMessage(`QAMill: Saved ${msg.filename}`);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** SMTP host/port for a given provider name. */
const SMTP_PRESETS: Record<string, {host: string; port: number; tls: boolean}> = {
  gmail:   { host: "smtp.gmail.com",          port: 587, tls: true },
  outlook: { host: "smtp-mail.outlook.com",   port: 587, tls: true },
};

/** Read the email settings from VS Code config, merging new + legacy keys. */
function readEmailConfig() {
  const cfg = vscode.workspace.getConfiguration("amil");
  const provider    = cfg.get<string>("email.provider", "gmail");
  const sender      = cfg.get<string>("email.sender",      cfg.get<string>("email.smtpUser", ""));
  const appPassword = cfg.get<string>("email.appPassword", cfg.get<string>("email.smtpPassword", ""));
  const recipient   = cfg.get<string>("email.recipient",   cfg.get<string>("email.to", ""));
  const smtpHost    = cfg.get<string>("email.smtpHost", "");
  const smtpPort    = cfg.get<number>("email.smtpPort", 587);
  const useTls      = cfg.get<boolean>("email.smtpTls", true);
  const preset      = SMTP_PRESETS[provider];
  return {
    provider,
    sender:      sender.trim(),
    appPassword,
    recipient:   recipient.trim(),
    smtp_host:   preset ? preset.host : smtpHost.trim(),
    smtp_port:   preset ? preset.port : smtpPort,
    use_tls:     preset ? preset.tls  : useTls,
  };
}

/**
 * Pull the live signed-in identity from the backend and update the dashboard badge.
 * The poll runs silently; the "signed in" toast fires at most ONCE per session,
 * only on a genuine transition to a new account. Config writes are best-effort
 * and can never break the detection loop.
 */
async function refreshIdentity(port: number): Promise<void> {
  let status: any;
  try {
    status = await getJson(`http://127.0.0.1:${port}/auth/status`);
  } catch {
    return; // backend not up yet — nothing to sync
  }
  // Prefer the signed-in QAMill user; fall back to first OAuth identity.
  const user    = status?.user || null;
  const primary = status?.primary || null;
  const id      = user || primary;
  const email   = id?.email || "";

  // Always update the dashboard badge (silent — no notification)
  dashboardPanel?.webview.postMessage({
    type: "apply_identity",
    identity: id
      ? { email, provider: (id.providers && id.providers[0]) || id.provider,
          label: id.label, name: id.name, picture: id.picture,
          can_email: id.can_email, type: "work" }
      : null,
  });
  if (email) { statusBarItem.tooltip = `QAMill — signed in as ${email}`; }

  // Detect a genuine change. Advance the guard IMMEDIATELY (before any await)
  // so a slow/failed config write can never cause repeat notifications.
  if (email === lastIdentityEmail) { return; }
  const isNewSignIn = !!email && email !== lastIdentityEmail;
  lastIdentityEmail = email;
  if (!email) { signInNotified = false; }  // signed out — allow one toast on next sign-in

  if (isNewSignIn && !signInNotified) {
    signInNotified = true;   // one toast per session, full stop
    const label = id.label || (id.providers && id.providers[0]) || id.provider || "QAMill";
    vscode.window.showInformationMessage(
      `QAMill: Signed in as ${email}` +
      (id.can_email ? " — reports will send from this address." : "")
    );
  }

  // Mirror into config (best-effort — failures must not affect the loop)
  if (email) {
    try {
      const cfg = vscode.workspace.getConfiguration("amil");
      await cfg.update("userEmail", email, vscode.ConfigurationTarget.Workspace);
      await cfg.update("email.sender", email, vscode.ConfigurationTarget.Workspace);
    } catch { /* no workspace / read-only settings — badge still works */ }
  }
}

function buildSyncPayload() {
  const cfg = vscode.workspace.getConfiguration("amil");
  const provider  = cfg.get<string>("llmProvider", "inhouse");
  const autoHeal  = cfg.get<boolean>("autoHeal", true);
  const aiMutants = cfg.get<boolean>("aiMutants", false);
  const mode        = autoHeal && aiMutants ? "both" : autoHeal ? "auto_heal" : aiMutants ? "ai_mutants" : "none";
  const userEmail   = cfg.get<string>("userEmail", "");
  const emailType   = cfg.get<string>("emailType", "work");
  return { type: "sync_settings", provider, mode, email: readEmailConfig(),
           identity: { email: userEmail, type: emailType } };
}

function updateLlmStatusBar() {
  const provider = vscode.workspace.getConfiguration("amil").get<string>("llmProvider", "inhouse");
  const icons:  Record<string, string> = { none: "$(circle-slash)", inhouse: "$(home)", claude: "$(sparkle)", gpt: "$(sparkle)", grok: "$(sparkle)" };
  const labels: Record<string, string> = { none: "AST only", inhouse: "Ollama", claude: "Claude", gpt: "GPT-4o", grok: "Grok" };
  llmStatusBarItem.text = `${icons[provider] ?? "$(sparkle)"} ${labels[provider] ?? provider}`;
}

function deliverPendingJob() {
  if (!pendingJob || !dashboardPanel) { return; }
  if (jobDeliveryTimer) { clearTimeout(jobDeliveryTimer); jobDeliveryTimer = undefined; }
  dashboardPanel.webview.postMessage({ type: "job_started", ...pendingJob });
  // One retry after 900 ms in case the webview wasn't ready on the first send
  jobDeliveryTimer = setTimeout(() => {
    jobDeliveryTimer = undefined;
    if (pendingJob && dashboardPanel) {
      dashboardPanel.webview.postMessage({ type: "job_started", ...pendingJob });
    }
  }, 900);
}

function getApiKey(config: vscode.WorkspaceConfiguration, provider: string): string {
  // Map provider names to their setting keys
  const settingKeys: Record<string, string> = {
    claude:     "anthropicApiKey",
    gpt:        "openaiApiKey",
    grok:       "xaiApiKey",
    gemini:     "geminiApiKey",
    openrouter: "openrouterApiKey",
    deepseek:   "deepseekApiKey",
    mistral:    "mistralApiKey",
  };

  const settingKey = settingKeys[provider];
  if (!settingKey) return "";

  // Try to get the key using the setting name
  let key = config.get(settingKey, "");

  console.log(`[getApiKey] Provider: ${provider}`);
  console.log(`[getApiKey] Setting key: amil.${settingKey}`);
  console.log(`[getApiKey] Value found: ${key ? `YES (length: ${key.length})` : "NO"}`);

  // If not found, try reading directly from VS Code settings using inspect
  if (!key) {
    try {
      const inspected = config.inspect(settingKey);
      console.log(`[getApiKey] Inspect result:`, inspected);

      if (inspected?.globalValue) {
        key = inspected.globalValue as string;
        console.log(`[getApiKey] Found in GLOBAL settings`);
      } else if (inspected?.workspaceValue) {
        key = inspected.workspaceValue as string;
        console.log(`[getApiKey] Found in WORKSPACE settings`);
      } else if (inspected?.workspaceFolderValue) {
        key = inspected.workspaceFolderValue as string;
        console.log(`[getApiKey] Found in FOLDER settings`);
      }
    } catch (e) {
      console.log(`[getApiKey] Inspect failed:`, e);
    }
  }

  return key;
}

/**
 * Force IPv4 loopback. The backend binds 127.0.0.1 only; Node resolves
 * "localhost" to ::1 first on Windows, so a stray IPv6 attempt turns a
 * simple "backend not up yet" into a confusing AggregateError. Pinning the
 * host to 127.0.0.1 makes every Node request hit the socket that exists.
 */
function ipv4(url: string): string {
  return url.replace("//localhost:", "//127.0.0.1:");
}

function postJson(url: string, body: object): Promise<any> {
  url = ipv4(url);
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = http.request(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) },
    }, (res) => {
      let raw = "";
      res.on("data", (c) => raw += c);
      res.on("end", () => {
        // Reject on HTTP errors so callers get a proper Error, not a partial response
        if ((res.statusCode ?? 0) >= 400) {
          let detail = raw;
          try { detail = JSON.parse(raw).detail ?? raw; } catch { /* use raw */ }
          reject(new Error(`HTTP ${res.statusCode}: ${detail}`));
          return;
        }
        try { resolve(JSON.parse(raw)); }
        catch { reject(new Error(raw)); }
      });
    });
    req.on("error", reject);
    req.write(data);
    req.end();
  });
}

function getJson(url: string): Promise<any> {
  url = ipv4(url);
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      let raw = "";
      res.on("data", (c) => raw += c);
      res.on("end", () => { try { resolve(JSON.parse(raw)); } catch { reject(new Error(raw)); } });
    });
    req.on("error", reject);
    req.setTimeout(8000, () => { req.destroy(); reject(new Error("timeout")); });
  });
}

function getText(url: string): Promise<string> {
  url = ipv4(url);
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      if ((res.statusCode ?? 0) >= 400) {
        reject(new Error(`HTTP ${res.statusCode}`));
        return;
      }
      let raw = "";
      res.on("data", (c) => raw += c);
      res.on("end", () => resolve(raw));
    });
    req.on("error", reject);
    req.setTimeout(30000, () => { req.destroy(); reject(new Error("Request timed out")); });
  });
}

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

function deleteRequest(url: string): Promise<any> {
  url = ipv4(url);
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method: "DELETE" }, (res) => {
      let raw = "";
      res.on("data", (c) => raw += c);
      res.on("end", () => { try { resolve(JSON.parse(raw)); } catch { resolve({}); } });
    });
    req.on("error", reject);
    req.setTimeout(5000, () => { req.destroy(); reject(new Error("timeout")); });
    req.end();
  });
}

/**
 * Read the SSE stream via Node.js http (not webview fetch) to avoid the VS Code
 * webview proxy buffering the entire response before delivering it. Each event is
 * forwarded to the webview via postMessage as soon as it arrives off the wire.
 */
async function startExtensionStream(rawUrl: string): Promise<void> {
  // Cancel any in-progress stream from a previous job
  if (activeStreamReq) {
    try { activeStreamReq.destroy(); } catch {}
    activeStreamReq = undefined;
  }
  streamEventsReceived = 0;

  const MAX_ATTEMPTS = 20;
  let attempt        = 0;
  let retryDelay     = 2000;

  const forward = (event: any) => {
    dashboardPanel?.webview.postMessage({ type: "stream_event", event });
  };

  while (attempt <= MAX_ATTEMPTS) {
    if (attempt > 0) {
      forward({ type: "status", message: `Reconnecting… (attempt ${attempt}/${MAX_ATTEMPTS})` });
      await new Promise(r => setTimeout(r, retryDelay));
      retryDelay = Math.min(Math.round(retryDelay * 1.6), 30000);
    }

    const resumeUrl = ipv4(rawUrl) + (streamEventsReceived > 0 ? `?from_event=${streamEventsReceived}` : "");
    const done = await new Promise<boolean>((resolve) => {
      let buf = "";
      const req = http.get(resumeUrl, (res) => {
        if ((res.statusCode ?? 0) === 404) {
          forward({ type: "status", message: "Job not found (404) — analysis may have expired." });
          resolve(true);  // don't retry 404
          return;
        }
        res.on("data", (chunk: Buffer) => {
          buf += chunk.toString("utf8");
          const lines = buf.split("\n");
          buf = lines.pop() ?? "";
          for (const line of lines) {
            const t = line.trim();
            if (!t.startsWith("data:")) { continue; }
            try {
              const event = JSON.parse(t.slice(5).trim());
              streamEventsReceived++;
              forward(event);
              if (event.type === "complete" || event.type === "error") {
                req.destroy();
                resolve(true);   // clean finish
              }
            } catch { /* skip malformed line */ }
          }
        });
        res.on("end",   () => resolve(false));  // server closed — retry
        res.on("error", () => resolve(false));
      });
      req.on("error", () => resolve(false));
      // Backend pings every 10s; only give up after 90s of true silence so a
      // slow mutant phase (Ollama equivalence checks) never triggers a reconnect.
      req.setTimeout(90000, () => { req.destroy(); resolve(false); });
      activeStreamReq = req;
    });

    if (done) { break; }
    attempt++;
  }

  activeStreamReq = undefined;
}

/** Turn a raw Node connection error (AggregateError / ECONNREFUSED) into a clear message. */
function friendlyConnError(err: any, port: number): string {
  const msg  = String(err?.message ?? err);
  const code = err?.code ?? "";
  const isConn = err?.name === "AggregateError" ||
                 code === "ECONNREFUSED" || code === "ECONNRESET" ||
                 /aggregate|ECONNREFUSED|timeout/i.test(msg);
  if (isConn) {
    return `QAMill: Can't reach the analysis engine on port ${port}. ` +
           `It may still be starting up, or Python failed to launch — ` +
           `check that Python is on your PATH. Click Retry in a moment.`;
  }
  return `QAMill: Failed to start analysis — ${msg}`;
}

// ── Shared header message handler (used by both dashboard + studio) ────────────

async function handleSharedHeaderMessage(panel: vscode.WebviewPanel | undefined, msg: any,
                                         context: vscode.ExtensionContext, port: number) {
  if (msg.type === "sh_ready") {
    // Header JS loaded — send current LLM provider
    const cfg = vscode.workspace.getConfiguration("amil");
    const provider = cfg.get<string>("llmProvider", "inhouse");
    panel?.webview.postMessage({ type: "sh_llm_list", provider });
    // Send current identity if available
    const identity = lastIdentityEmail ? { email: lastIdentityEmail } : null;
    panel?.webview.postMessage({ type: "sh_set_identity", identity });
    return;
  }
  if (msg.type === "sh_set_llm") {
    // User changed LLM in header — update config
    const cfg = vscode.workspace.getConfiguration("amil");
    try {
      await cfg.update("llmProvider", msg.provider, vscode.ConfigurationTarget.Global);
      updateLlmStatusBar();
      // Broadcast the new value to the panel
      panel?.webview.postMessage({ type: "sh_llm_list", provider: msg.provider });
    } catch (e) { /* no workspace */ }
    return;
  }
  if (msg.type === "sh_open_auth") {
    // User clicked Sign in — run the identity command
    await vscode.commands.executeCommand("amil.setIdentity");
    return;
  }
  if (msg.type === "sh_sign_out") {
    // User clicked the identity chip to sign out
    try {
      const ready = await ensureBackendRunning(context, port);
      if (ready) { await postJson(`http://127.0.0.1:${port}/auth/signout?everywhere=true`, {}); }
    } catch { /* best-effort */ }
    const cfg = vscode.workspace.getConfiguration("amil");
    try {
      await cfg.update("userEmail", "", vscode.ConfigurationTarget.Workspace);
      await cfg.update("email.sender", "", vscode.ConfigurationTarget.Workspace);
    } catch { /* no workspace */ }
    lastIdentityEmail = "";
    signInNotified = false;
    panel?.webview.postMessage({ type: "sh_set_identity", identity: null });
    vscode.window.showInformationMessage("QAMill: Signed out.");
    return;
  }
  if (msg.type === "sh_connect_provider") {
    const { provider, api_key, model } = msg;
    if (!api_key) return;
    try {
      const ready = await ensureBackendRunning(context, port);
      if (!ready) return;
      const result = await postJson(`http://127.0.0.1:${port}/auth/llm/validate`, { provider, api_key });
      if (result.valid) {
        // Now store it with selected model
        const connectPayload: any = { provider, api_key };
        if (model) { connectPayload.model = model; }
        await postJson(`http://127.0.0.1:${port}/auth/llm/connect`, connectPayload);
        const modelStr = model ? ` (${model})` : '';
        vscode.window.showInformationMessage(`QAMill: ${provider.toUpperCase()} connected!${modelStr}`);
        panel?.webview.postMessage({ type: "sh_refresh_providers" });
      } else {
        vscode.window.showErrorMessage(`QAMill: Invalid ${provider.toUpperCase()} API key.`);
      }
    } catch (e) {
      vscode.window.showErrorMessage(`QAMill: Failed to connect ${provider.toUpperCase()}: ${e}`);
    }
    return;
  }
  if (msg.type === "sh_disconnect_provider") {
    const { provider } = msg;
    try {
      const ready = await ensureBackendRunning(context, port);
      if (ready) { await postJson(`http://127.0.0.1:${port}/auth/llm/disconnect`, { provider }); }
      vscode.window.showInformationMessage(`QAMill: ${provider.toUpperCase()} disconnected.`);
      panel?.webview.postMessage({ type: "sh_refresh_providers" });
    } catch (e) {
      vscode.window.showErrorMessage(`QAMill: Failed to disconnect ${provider.toUpperCase()}.`);
    }
    return;
  }
  if (msg.type === "sh_set_active_provider") {
    const { provider } = msg;
    try {
      const ready = await ensureBackendRunning(context, port);
      if (ready) { await postJson(`http://127.0.0.1:${port}/auth/llm/set-active`, { provider }); }
      panel?.webview.postMessage({ type: "sh_refresh_providers" });
    } catch (e) {
      vscode.window.showErrorMessage(`QAMill: Failed to switch provider.`);
    }
    return;
  }
  if (msg.type === "sh_add_custom_provider") {
    const { name, endpoint, api_key } = msg;
    try {
      const ready = await ensureBackendRunning(context, port);
      if (!ready) return;
      const result = await postJson(`http://127.0.0.1:${port}/auth/llm/custom/add`, {
        name, api_endpoint: endpoint, api_key
      });
      if (result.success) {
        vscode.window.showInformationMessage(`QAMill: Custom provider "${name}" added!`);
        panel?.webview.postMessage({ type: "sh_refresh_providers" });
      }
    } catch (e) {
      vscode.window.showErrorMessage(`QAMill: Failed to add custom provider: ${e}`);
    }
    return;
  }
  if (msg.type === "sh_delete_custom_provider") {
    const { provider_id } = msg;
    try {
      const ready = await ensureBackendRunning(context, port);
      if (ready) {
        await fetch(`http://127.0.0.1:${port}/auth/llm/custom/${provider_id}`, {
          method: "DELETE"
        });
        vscode.window.showInformationMessage("QAMill: Custom provider deleted.");
        panel?.webview.postMessage({ type: "sh_refresh_providers" });
      }
    } catch (e) {
      vscode.window.showErrorMessage("QAMill: Failed to delete custom provider.");
    }
    return;
  }
}

// ── Shared header (both tabs) ──────────────────────────────────────────────────

function getSharedHeaderHtml(tabType: "mutation" | "generation", logoUri: string): string {
  const subtitles = {
    mutation:   "Test Quality Metrics · coverage analysis · mutation detection · test weakness discovery",
    generation: "Test Authoring & Auto-Healing · unit tests · BDD scenarios · manual cases · traceability",
  };
  const subtitle = subtitles[tabType] || subtitles.mutation;
  return `
<div class="shared-header">
  <div class="sh-left">
    <img src="${logoUri}" alt="QAMill" class="sh-logo">
    <div class="sh-brand">
      <h1 class="sh-title">QAMill QA Governance</h1>
      <div class="sh-subtitle">${subtitle}</div>
    </div>
  </div>
  <div class="sh-right">
    <div id="sh-usage" class="sh-usage" title="Daily LLM usage quota"></div>
    <div id="sh-llm-badge" class="sh-llm-badge" onclick="shOpenProviderSwitcher()" title="Click to switch LLM provider">
      <span id="sh-llm-icon">🏠</span>
      <span id="sh-llm-name">Ollama</span>
      <span class="sh-llm-indicator">✓</span>
    </div>
    <button id="sh-providers-btn" class="sh-providers-btn" onclick="shOpenProviderModal()" title="Configure LLM providers">⚙️ Preferences</button>
    <div id="sh-identity" class="sh-identity"></div>
  </div>
</div>`;
}

function getSharedHeaderCSS(): string {
  return `
.shared-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-bottom: 1px solid var(--vscode-widget-border);
  background: linear-gradient(to right, var(--vscode-editor-background), var(--vscode-editor-background) 95%, rgba(14,99,156,.04));
  gap: 24px; box-shadow: 0 2px 8px rgba(0,0,0,.12);
}
.sh-left { display: flex; align-items: center; gap: 16px; flex: 1; }
.sh-logo {
  height: 52px; width: 52px; border-radius: 10px; flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(14,99,156,.15); object-fit: contain; padding: 2px;
  background: rgba(14,99,156,.06);
}
.sh-brand h1 {
  font-size: 17px; font-weight: 800; margin: 0; line-height: 1.2;
  color: var(--vscode-editor-foreground); letter-spacing: -.3px;
}
.sh-subtitle {
  font-size: 10.5px; opacity: .62; margin-top: 3px; font-weight: 500;
  letter-spacing: .4px;
}
.sh-right { display: flex; align-items: center; gap: 12px; }
.sh-llm-badge {
  display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  background: rgba(14,99,156,.08); border: 1px solid rgba(14,99,156,.15);
  border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
  color: #0e639c; transition: all .15s ease; user-select: none;
  position: relative;
}
.sh-llm-badge:hover {
  background: rgba(14,99,156,.12);
  border-color: rgba(14,99,156,.25);
  box-shadow: 0 2px 6px rgba(14,99,156,.12);
}
.sh-llm-icon { font-size: 13px; }
.sh-llm-name { font-weight: 700; }
.sh-llm-indicator {
  display: inline-flex; align-items: center; justify-content: center;
  width: 14px; height: 14px; background: #4ec9a0; color: #000;
  border-radius: 50%; font-size: 9px; font-weight: 800; margin-left: 2px;
}
.sh-identity { font-size: 11px; }
.sh-auth-chip {
  background: #0e639c; color: #fff; padding: 4px 12px; border-radius: 14px;
  font-weight: 700; display: flex; align-items: center; gap: 6px; cursor: pointer;
  box-shadow: 0 2px 6px rgba(14,99,156,.2); transition: all .15s ease;
  font-size: 11px;
}
.sh-auth-chip:hover { opacity: .9; transform: translateY(-1px); box-shadow: 0 3px 8px rgba(14,99,156,.3); }
.sh-signin-btn {
  background: #0e639c; color: #fff; border: none; border-radius: 6px;
  padding: 6px 14px; font-size: 12px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(14,99,156,.2); transition: all .15s ease;
}
.sh-signin-btn:hover { opacity: .9; transform: translateY(-1px); box-shadow: 0 3px 8px rgba(14,99,156,.3); }
.sh-usage {
  font-size: 11px; font-weight: 600; color: #666;
  background: rgba(14,99,156,.08); padding: 4px 10px; border-radius: 12px;
  min-width: 90px; text-align: center;
}
.sh-usage.quota-warning { background: rgba(255,152,0,.12); color: #ff9800; }
.sh-usage.quota-exceeded { background: rgba(244,67,54,.12); color: #f44336; }
.sh-providers-btn {
  background: transparent; border: none; color: var(--vscode-editor-foreground);
  font-size: 14px; cursor: pointer; padding: 4px 8px; border-radius: 4px;
  transition: all .15s ease;
}
.sh-providers-btn:hover { background: rgba(14,99,156,.1); }
.sh-switcher-modal {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,.2); display: none; z-index: 9999;
  align-items: flex-start; justify-content: center; padding-top: 70px;
}
.sh-switcher-modal.show { display: flex; }
.sh-switcher-content {
  background: var(--vscode-editor-background); border: 1px solid var(--vscode-widget-border);
  border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,.3); width: 260px;
  animation: slideDown .15s ease;
}
@keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
.sh-switcher-header {
  padding: 12px 14px; border-bottom: 1px solid var(--vscode-widget-border);
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
  opacity: .6;
}
.sh-switcher-list { max-height: 320px; overflow-y: auto; }
.sh-provider-item {
  padding: 10px 14px; cursor: pointer; font-size: 12px; display: flex;
  align-items: center; gap: 8px; transition: background .1s ease;
  border-left: 2px solid transparent;
}
.sh-provider-item:hover { background: rgba(14,99,156,.08); }
.sh-provider-item.active {
  background: rgba(14,99,156,.12); border-left-color: #0e639c; font-weight: 700;
}
.sh-provider-item-icon { font-size: 13px; flex-shrink: 0; }
.sh-provider-item-name { flex: 1; }
.sh-provider-item-check {
  display: none; width: 14px; height: 14px; background: #4ec9a0;
  color: #000; border-radius: 50%; font-size: 9px; font-weight: 800;
  align-items: center; justify-content: center;
}
.sh-provider-item.active .sh-provider-item-check { display: flex; }
.provider-modal {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,.5); display: none; align-items: center; justify-content: center;
  z-index: 10000;
}
.provider-modal.show { display: flex; }
.provider-modal-content {
  background: var(--vscode-editor-background); border: 1px solid var(--vscode-widget-border);
  border-radius: 8px; padding: 20px; min-width: 500px; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0,0,0,.3);
}
.provider-modal-header { font-size: 16px; font-weight: 700; margin-bottom: 16px; }
.provider-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
.provider-item {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--vscode-input-background); border: 1px solid var(--vscode-widget-border);
  border-radius: 6px; padding: 12px 14px;
}
.provider-info { display: flex; flex-direction: column; gap: 3px; flex: 1; }
.provider-label { font-weight: 600; font-size: 12px; }
.provider-status { font-size: 10px; opacity: .6; }
.provider-status.connected { color: #4ec9a0; }
.provider-actions { display: flex; gap: 8px; }
.provider-btn {
  background: #0e639c; color: #fff; border: none; border-radius: 4px;
  padding: 5px 12px; font-size: 11px; cursor: pointer; font-weight: 600;
}
.provider-btn:hover { opacity: .85; }
.provider-btn.disconnect {
  background: rgba(244,67,54,.2); color: #f44336;
}
.provider-modal-footer {
  display: flex; gap: 8px; justify-content: flex-end; border-top: 1px solid var(--vscode-widget-border);
  padding-top: 16px;
}
.modal-btn {
  background: #0e639c; color: #fff; border: none; border-radius: 4px;
  padding: 7px 16px; font-size: 12px; cursor: pointer; font-weight: 600;
}
.modal-btn:hover { opacity: .85; }
.modal-btn.close { background: var(--vscode-button-secondaryBackground); color: var(--vscode-editor-foreground); }
.provider-section {
  margin-bottom: 20px;
}
.provider-section-title {
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
  opacity: .6; margin-bottom: 10px;
}
.provider-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px;
}
.provider-card {
  background: var(--vscode-input-background); border: 2px solid var(--vscode-widget-border);
  border-radius: 8px; padding: 16px; text-align: center; cursor: pointer;
  transition: all .15s ease; user-select: none;
}
.provider-card:hover {
  border-color: #0e639c;
  background: rgba(14,99,156,.05);
  box-shadow: 0 2px 8px rgba(14,99,156,.2);
}
.provider-card.connected {
  border-color: #4ec9a0;
  background: rgba(78,201,160,.05);
}
.provider-icon {
  font-size: 36px; margin-bottom: 12px; display: block;
}
.provider-name {
  font-weight: 700; font-size: 13px;
  color: var(--vscode-editor-foreground);
}
.provider-connected-badge {
  display: inline-block; font-size: 9px; padding: 3px 8px; border-radius: 12px;
  background: #4ec9a0; color: #000; margin-top: 8px; font-weight: 700;
}
`;
}

function getSharedHeaderJS(): string {
  return `
async function shFetchUsage() {
  try {
    const resp = await fetch('http://localhost:8765/usage/today');
    if (!resp.ok) return;
    const data = await resp.json();
    const usageDiv = document.getElementById('sh-usage');
    if (!usageDiv) return;

    const remaining = data.quota_remaining || 0;
    const limit = data.quota_limit || 50;
    const used = limit - remaining;
    const text = used + '/' + limit;
    usageDiv.textContent = text;

    if (data.quota_exceeded) {
      usageDiv.className = 'sh-usage quota-exceeded';
      usageDiv.title = 'Daily quota exceeded. Upgrade or try again tomorrow.';
    } else if (remaining <= 5) {
      usageDiv.className = 'sh-usage quota-warning';
      usageDiv.title = remaining + ' requests remaining today';
    } else {
      usageDiv.className = 'sh-usage';
    }
  } catch (e) {
    document.getElementById('sh-usage').textContent = '—';
  }
}


function shSetIdentity(identity) {
  const div = document.getElementById('sh-identity');
  if (!div) return;
  if (!identity || !identity.email) {
    div.innerHTML = '<button class="sh-signin-btn" onclick="shOpenAuth()">Sign in</button>';
  } else {
    const initials = (identity.name || identity.email).split(' ')[0][0].toUpperCase();
    div.innerHTML = '<div class="sh-auth-chip" title="Signed in: ' + identity.email + '" onclick="shSignOut()">' +
      '<span>' + initials + '</span><span>' + (identity.email || 'Account').split('@')[0] + '</span>' +
      '</div>';
  }
}

function shOpenAuth() { vscode.postMessage({ type: 'sh_open_auth' }); }
function shSignOut() {
  if (confirm('Sign out from QAMill?')) {
    vscode.postMessage({ type: 'sh_sign_out' });
  }
}

window.addEventListener('message', e => {
  const m = e.data;
  if (m.type === 'sh_set_identity') { shSetIdentity(m.identity); }
  if (m.type === 'sh_llm_list') {
    const sel = document.getElementById('sh-llm-selector');
    if (sel && m.provider) { sel.value = m.provider; }
  }
});

async function shOpenProviderSwitcher() {
  const modal = document.getElementById('sh-switcher-modal');
  const list = document.getElementById('sh-switcher-list');

  try {
    const resp = await fetch('http://localhost:8765/auth/status');
    if (!resp.ok) return;
    const data = await resp.json();
    const allProviders = data.llm || [];
    const activeProvider = data.active_llm;

    const icons = {
      claude: '🤖', gpt: '🟢', gemini: '🔵', grok: '⚡', github: '🐙',
      openrouter: '📡', deepseek: '🔮', mistral: '🌟', ollama: '🏠'
    };

    // Show ONLY connected providers in the switcher
    const connectedProviders = allProviders.filter(p => p.connected);

    if (connectedProviders.length === 0) {
      list.innerHTML = '<div style="padding: 12px; opacity: 0.6;">No providers configured. Click ⚙️ Preferences to add.</div>';
    } else {
      list.innerHTML = connectedProviders.map(p => {
        const icon = icons[p.provider] || '🔧';
        const isActive = p.provider === activeProvider;
        return \`
          <div class="sh-provider-item \${isActive ? 'active' : ''}"
            onclick="shSwitchProvider('\${p.provider}', '\${p.label}', '\${icon}')">
            <span class="sh-provider-item-icon">\${icon}</span>
            <span class="sh-provider-item-name">\${p.label}</span>
            <span class="sh-provider-item-check">\${isActive ? '✓' : ''}</span>
          </div>
        \`;
      }).join('');
    }

    if (modal) { modal.classList.add('show'); }
  } catch (e) {
    console.log('Failed to load providers:', e);
  }
}

function shCloseProviderSwitcher() {
  const modal = document.getElementById('sh-switcher-modal');
  if (modal) { modal.classList.remove('show'); }
}

function shSwitchProvider(provider, label, icon) {
  // If already active, just close
  const badge = document.getElementById('sh-llm-badge');
  const currentName = document.getElementById('sh-llm-name').textContent;
  if (currentName === label) {
    shCloseProviderSwitcher();
    return;
  }

  // If disconnected provider, open connect modal
  const connected = true; // Assuming all shown are connected
  if (!connected) {
    shCloseProviderSwitcher();
    shConnectProvider(provider, '');
    return;
  }

  // Switch to provider
  vscode.postMessage({ type: 'sh_set_active_provider', provider });

  // Update UI immediately for snappy feel
  document.getElementById('sh-llm-icon').textContent = icon;
  document.getElementById('sh-llm-name').textContent = label;

  shCloseProviderSwitcher();
  setTimeout(() => shLoadProviders(), 200);
}

function updateLLMBadge(provider, label, icon) {
  document.getElementById('sh-llm-icon').textContent = icon;
  document.getElementById('sh-llm-name').textContent = label;
}

function shOpenProviderModal() {
  const modal = document.getElementById('sh-provider-modal');
  if (modal) { modal.classList.add('show'); }
  shLoadProviders();
}

window.addEventListener('message', e => {
  const m = e.data;
  if (m.type === 'sh_refresh_providers') {
    shLoadProviders();
  }
});

function shCloseProviderModal() {
  const modal = document.getElementById('sh-provider-modal');
  if (modal) { modal.classList.remove('show'); }
}

async function shLoadProviders() {
  try {
    const resp = await fetch('http://localhost:8765/auth/status');
    if (!resp.ok) return;
    const data = await resp.json();
    const allProviders = data.llm || [];
    const list = document.getElementById('sh-provider-list');
    if (!list) return;

    // Just show all providers in a simple grid
    const html = \`
      <div class="provider-grid">
        \${allProviders.map(p => {
          const icon = shGetProviderIcon(p.provider);
          const badgeHtml = p.connected ? '<div class="provider-connected-badge">✓ Connected</div>' : '';
          return \`
            <div class="provider-card \${p.connected ? 'connected' : ''}"
              onclick="\${p.connected ? \`shOpenDisconnectModal('\${p.provider}')\` : \`shConnectProvider('\${p.provider}', '\${p.key_placeholder || ''}')\`}">
              <div class="provider-icon">\${icon}</div>
              <div class="provider-name">\${p.label}</div>
              \${badgeHtml}
            </div>
          \`;
        }).join('')}
      </div>
    \`;

    list.innerHTML = html;
  } catch (e) {
    console.log('Failed to load providers:', e);
  }
}

function shGetProviderIcon(provider) {
  const icons = {
    claude: '🤖', gpt: '🟢', gemini: '🔵', grok: '⚡', github: '🐙',
    openrouter: '📡', deepseek: '🔮', mistral: '🌟', ollama: '🏠'
  };
  return icons[provider] || '🔧';
}

async function shConnectProvider(provider, placeholder) {
  // Ollama doesn't need an API key - connect directly
  if (provider === 'ollama') {
    vscode.postMessage({ type: 'sh_connect_provider', provider: 'ollama', api_key: '' });
    shCloseProviderModal();
    setTimeout(shLoadProviders, 300);
    return;
  }

  shCurrentProvider = provider;
  const title = document.getElementById('sh-apikey-title');
  const hint = document.getElementById('sh-apikey-hint');
  const input = document.getElementById('sh-apikey-input');
  const modelSelect = document.getElementById('sh-model-select');
  const modelHint = document.getElementById('sh-model-hint');

  title.textContent = \`Connect \${provider.toUpperCase()}\`;
  hint.textContent = \`(\${placeholder})\`;
  input.value = '';

  // Fetch available models for this provider
  try {
    const resp = await fetch(\`http://localhost:8765/auth/llm/models/\${provider}\`);
    if (resp.ok) {
      const data = await resp.json();
      const models = data.models || [];
      const defaultModel = data.default_model || '';

      // Populate model dropdown
      modelSelect.innerHTML = '';
      models.forEach(m => {
        const option = document.createElement('option');
        option.value = m.name;
        option.textContent = m.label;
        if (m.name === defaultModel) { option.selected = true; }
        modelSelect.appendChild(option);
      });
      modelHint.textContent = \`Recommended: \${models[0]?.label || ''}\`;
    }
  } catch (e) {
    modelSelect.innerHTML = '<option value="">Could not load models</option>';
  }

  input.focus();
  const modal = document.getElementById('sh-apikey-modal');
  if (modal) { modal.classList.add('show'); }
}

function shDisconnectProvider(provider) {
  vscode.postMessage({ type: 'sh_disconnect_provider', provider });
  setTimeout(shLoadProviders, 500);
}

function shCloseApiKeyModal() {
  const modal = document.getElementById('sh-apikey-modal');
  if (modal) { modal.classList.remove('show'); }
  shCurrentProvider = null;
}

function shConfirmApiKey() {
  const input = document.getElementById('sh-apikey-input');
  const modelSelect = document.getElementById('sh-model-select');
  const key = (input.value || '').trim();
  const model = (modelSelect.value || '').trim();

  if (!key) { alert('Please enter an API key'); return; }
  if (shCurrentProvider) {
    vscode.postMessage({
      type: 'sh_connect_provider',
      provider: shCurrentProvider,
      api_key: key,
      model: model
    });
    shCloseApiKeyModal();
    setTimeout(shLoadProviders, 1000);
  }
}

function shOpenDisconnectModal(provider) {
  shCurrentDisconnectProvider = provider;
  shCurrentDisconnectIsCustom = false;
  const modal = document.getElementById('sh-disconnect-modal');
  const title = document.getElementById('sh-disconnect-title');
  title.textContent = 'Disconnect Provider?';
  const msg = document.getElementById('sh-disconnect-msg');
  msg.textContent = 'You can reconnect anytime.';
  if (modal) { modal.classList.add('show'); }
}

function shCloseDisconnectModal() {
  const modal = document.getElementById('sh-disconnect-modal');
  if (modal) { modal.classList.remove('show'); }
  shCurrentDisconnectProvider = null;
  shCurrentDisconnectIsCustom = false;
}

function shConfirmDisconnect() {
  if (!shCurrentDisconnectProvider) return;

  if (shCurrentDisconnectIsCustom) {
    vscode.postMessage({ type: 'sh_delete_custom_provider', provider_id: shCurrentDisconnectProvider });
  } else {
    vscode.postMessage({ type: 'sh_disconnect_provider', provider: shCurrentDisconnectProvider });
  }

  shCloseDisconnectModal();
  setTimeout(shLoadProviders, 500);
}

let shCurrentProvider = null;
let shCurrentDisconnectProvider = null;
let shCurrentDisconnectIsCustom = false;

setInterval(shFetchUsage, 5000);
shFetchUsage();

async function initBadge() {
  try {
    const resp = await fetch('http://localhost:8765/auth/status');
    if (!resp.ok) return;
    const data = await resp.json();
    const active = data.active_llm || 'ollama';
    const providers = data.llm || [];
    const activeProvider = providers.find(p => p.provider === active);

    if (activeProvider) {
      const icons = {
        claude: '🤖', gpt: '🟢', gemini: '🔵', grok: '⚡', github: '🐙',
        openrouter: '📡', deepseek: '🔮', mistral: '🌟', ollama: '🏠'
      };
      const icon = icons[active] || '🔧';
      updateLLMBadge(active, activeProvider.label, icon);
    }
  } catch (e) {
    console.log('Failed to init badge:', e);
  }
}

initBadge();

document.addEventListener('click', e => {
  const modal = document.getElementById('sh-provider-modal');
  const switcher = document.getElementById('sh-switcher-modal');
  if (modal && e.target === modal) { shCloseProviderModal(); }
  if (switcher && e.target === switcher) { shCloseProviderSwitcher(); }
});
vscode.postMessage({ type: 'sh_ready' });
`;
}

// ── Test Studio HTML ───────────────────────────────────────────────────────────

function getTestStudioHtml(cspSource: string, logoUri: string): string {
  return `<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src http://localhost:8765 http://127.0.0.1:8765; img-src ${cspSource} data:;">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:var(--vscode-font-family);background:var(--vscode-editor-background);
       color:var(--vscode-editor-foreground);font-size:13px;padding:0;line-height:1.5}
  ${getSharedHeaderCSS()}
  .content{padding:16px;}
  .target{font-family:var(--vscode-editor-font-family,monospace);font-size:12px;
          background:var(--vscode-input-background);border:1px solid var(--vscode-widget-border);
          border-radius:6px;padding:8px 12px;margin-bottom:16px;display:inline-block}
  .controls{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;margin-bottom:8px}
  .ctl{display:flex;flex-direction:column;gap:4px}
  .ctl label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;opacity:.6}
  select{background:var(--vscode-dropdown-background);color:var(--vscode-dropdown-foreground);
         border:1px solid var(--vscode-dropdown-border,#555);border-radius:5px;padding:7px 10px;
         font-family:var(--vscode-font-family);font-size:13px;min-width:190px;cursor:pointer}
  .gen-btn{background:#0e639c;color:#fff;border:none;border-radius:6px;padding:9px 22px;
           font-size:13px;font-weight:600;cursor:pointer}
  .gen-btn:hover{opacity:.88}
  .gen-btn:disabled{opacity:.4;cursor:not-allowed}
  .fmt-hint{font-size:11px;opacity:.55;margin:6px 0 16px}
  /* Progress log */
  .progress{background:var(--vscode-input-background);border:1px solid var(--vscode-widget-border);
            border-radius:8px;padding:0;margin-bottom:16px;display:none;max-height:500px;overflow:hidden;display:flex;flex-direction:column}
  .progress.show{display:flex}
  .progress-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;opacity:.6;padding:12px 14px;border-bottom:1px solid var(--vscode-widget-border)}
  .plog{font-family:var(--vscode-editor-font-family,monospace);font-size:11px;line-height:1.5;flex:1;overflow-y:auto;padding:10px 14px;background:rgba(0,0,0,.3)}
  .plog .step{opacity:.9;margin:1px 0;word-break:break-word;padding:2px 0}
  .plog .step.info::before{content:'ℹ ';color:#4ec9a0;font-weight:700}
  .plog .step.success::before{content:'✓ ';color:#4ec9a0;font-weight:700}
  .plog .step.error::before{content:'✕ ';color:#ff6b6b;font-weight:700}
  .plog .step.warning::before{content:'⚠ ';color:#ffd700;font-weight:700}
  .plog .err{color:#f48771}
  .plog .err::before{content:'✗ ';}
  .spin{display:inline-block;width:12px;height:12px;border:2px solid var(--vscode-widget-border);
        border-top-color:#4ec9a0;border-radius:50%;animation:sp .8s linear infinite;vertical-align:middle;margin-left:6px}
  @keyframes sp{to{transform:rotate(360deg)}}
  /* Result */
  .result{display:none}
  .result.show{display:block}
  .result-bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
  .result-title{font-size:14px;font-weight:700}
  .verdict{font-size:11px;padding:2px 10px;border-radius:20px;font-weight:600}
  .verdict.ok{background:#1e3a2f;color:#4ec9a0}
  .verdict.warn{background:#3a2f1e;color:#dcdcaa}
  .result-actions{display:flex;gap:8px}
  .act{background:var(--vscode-button-secondaryBackground,#3a3d41);color:var(--vscode-button-secondaryForeground,#ccc);
       border:none;border-radius:5px;padding:6px 14px;font-size:12px;cursor:pointer}
  .act.primary{background:#0e639c;color:#fff}
  .act:hover{opacity:.85}
  pre.code{background:var(--vscode-textCodeBlock-background,#1e1e1e);border:1px solid var(--vscode-widget-border);
           border-radius:8px;padding:14px;overflow:auto;font-family:var(--vscode-editor-font-family,monospace);
           font-size:12px;white-space:pre;max-height:60vh}
  table.qt{border-collapse:collapse;width:100%;font-size:12px;margin-top:4px}
  table.qt th,table.qt td{border:1px solid var(--vscode-widget-border);padding:7px 10px;text-align:left;vertical-align:top}
  table.qt th{background:var(--vscode-input-background);font-weight:700}
  table.qt tr:nth-child(even){background:rgba(127,127,127,.05)}
</style></head>
<body>
  ${getSharedHeaderHtml("generation", logoUri)}
  <div class="content">
    <div class="sub">AI-powered test authoring & generation in multiple formats (unit tests, BDD, manual QA cases, traceability matrices).</div>

    <div class="target" id="target">No file selected</div>

    <div class="controls">
    <div class="ctl">
      <label>Output Format</label>
      <select id="sel-fmt">
        <option value="unit">Unit Tests (pytest)</option>
        <option value="test_case">Test Case format</option>
        <option value="table">Table format</option>
        <option value="gherkin">Gherkin (BDD)</option>
        <option value="traceability">Traceability matrix</option>
      </select>
    </div>
    <button class="gen-btn" id="gen-btn" onclick="generate()">⚡ Generate</button>
  </div>
  <div class="fmt-hint" id="fmt-hint"></div>

  <div class="progress" id="progress">
    <div class="progress-title">Progress <span class="spin" id="spin"></span></div>
    <div class="plog" id="plog"></div>
  </div>

  <div class="result" id="result">
    <div class="result-bar">
      <span class="result-title" id="result-title">Result</span>
      <span class="result-actions">
        <span class="verdict" id="verdict" style="display:none"></span>
        <button class="act" onclick="copyResult()">Copy</button>
        <button class="act primary" id="save-btn" onclick="saveResult()">Save to file</button>
      </span>
    </div>
    <div id="result-body"></div>
  </div>
  </div>

<script>
  const vscode = acquireVsCodeApi();
  let lastResult = null;

  ${getSharedHeaderJS()}

  const FMT_HINTS = {
    unit: "Runnable pytest suite — generated then VERIFIED against your original code.",
    test_case: "Detailed manual cases: ID, preconditions, steps, expected result.",
    table: "Manual cases laid out as a compact table for spreadsheets/reviews.",
    gherkin: "Given/When/Then scenarios for BDD tools (Cucumber, behave).",
    traceability: "Requirements → Test Case mapping matrix for audits/coverage.",
  };

  function updateHint() {
    document.getElementById('fmt-hint').textContent = FMT_HINTS[document.getElementById('sel-fmt').value] || '';
  }
  document.getElementById('sel-fmt').addEventListener('change', updateHint);

  async function generate() {
    try {
      // Get active provider from backend
      const resp = await fetch('http://localhost:8765/auth/status');
      if (!resp.ok) {
        alert('Failed to get active provider');
        return;
      }
      const data = await resp.json();
      const provider = data.active_llm || 'ollama';
      const format = document.getElementById('sel-fmt').value;
      const file = document.getElementById('target').textContent.replace('📄 ', '').trim();

      document.getElementById('gen-btn').disabled = true;
      document.getElementById('progress').classList.add('show');
      document.getElementById('spin').style.display = 'inline-block';
      document.getElementById('plog').innerHTML = '';
      document.getElementById('result').classList.remove('show');

      // Log generation details
      addStep('═══ QAMill Test Generation ═══', '', 'info');
      addStep('Provider: ' + provider.toUpperCase(), '', 'info');
      addStep('Format: ' + format, '', 'info');
      addStep('File: ' + file, '', 'info');
      addStep('─────────────────────────────', '', 'info');

      vscode.postMessage({ type: 'studio_generate', provider, format });
    } catch (e) {
      addStep('FATAL ERROR: ' + e.message, 'err', 'error');
      document.getElementById('gen-btn').disabled = false;
    }
  }

  function addStep(msg, cls, type = 'info') {
    const d = document.createElement('div');
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    d.className = 'step ' + (cls||'') + ' ' + type;
    d.textContent = '[' + time + '] ' + msg;
    const plog = document.getElementById('plog');
    plog.appendChild(d);
    // Auto-scroll to bottom
    plog.scrollTop = plog.scrollHeight;
  }

  function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

  // Render a markdown table into a real HTML table; else preformatted text.
  function renderContent(fmt, content) {
    const body = document.getElementById('result-body');
    if (fmt === 'table' || fmt === 'traceability') {
      const lines = content.split('\\n').filter(l => l.trim().startsWith('|'));
      if (lines.length >= 2) {
        const cells = l => l.split('|').slice(1,-1).map(c => c.trim());
        const head = cells(lines[0]);
        const rows = lines.slice(2).map(cells);
        let html = '<table class="qt"><thead><tr>' + head.map(h=>'<th>'+esc(h)+'</th>').join('') + '</tr></thead><tbody>';
        html += rows.map(r => '<tr>' + r.map(c=>'<td>'+esc(c.replace(/<br>/g,'\\n')).replace(/\\n/g,'<br>')+'</td>').join('') + '</tr>').join('');
        html += '</tbody></table>';
        body.innerHTML = html;
        return;
      }
    }
    body.innerHTML = '<pre class="code">' + esc(content) + '</pre>';
  }

  window.addEventListener('message', e => {
    const m = e.data;
    if (m.type === 'studio_init') {
      document.getElementById('target').textContent = '📄 ' + (m.file || 'No file');
      // Provider is now managed via badge, not dropdown
      if (m.preset) document.getElementById('sel-fmt').value = m.preset;
      updateHint();
    }
    if (m.type === 'studio_progress') { addStep(m.message); }
    if (m.type === 'studio_error') {
      document.getElementById('spin').style.display = 'none';
      addStep('ERROR: ' + m.message, 'err', 'error');
      if (m.details) {
        addStep('Details: ' + m.details, '', 'debug');
      }
      addStep('Generation failed. Try a different provider or check logs.', '', 'warning');
      document.getElementById('gen-btn').disabled = false;
    }
    if (m.type === 'studio_result') {
      document.getElementById('spin').style.display = 'none';
      const last = document.querySelector('#plog .step:last-child');
      if (last) last.className = 'step done';
      document.getElementById('gen-btn').disabled = false;
      lastResult = m.result;
      const r = m.result;
      document.getElementById('result').classList.add('show');
      document.getElementById('result-title').textContent = (r.module || 'Suite') + ' — ' + r.format;
      const v = document.getElementById('verdict');
      if (r.format === 'unit') {
        v.style.display = 'inline-block';
        v.className = 'verdict ' + (r.verified ? 'ok' : 'warn');
        v.textContent = r.verified ? '✓ Verified · ' + r.passed + ' passed' : '⚠ Review needed';
      } else { v.style.display = 'none'; }
      renderContent(r.format, r.content);
    }
  });

  function copyResult(){ if(lastResult){ navigator.clipboard.writeText(lastResult.content); } }
  function saveResult(){ if(lastResult){ vscode.postMessage({ type:'studio_save', content:lastResult.content, filename:lastResult.filename }); } }

  vscode.postMessage({ type: 'studio_ready' });
</script>

<!-- Provider Management Modal -->
<div id="sh-provider-modal" class="provider-modal" onclick="shCloseProviderModal()">
  <div class="provider-modal-content" onclick="event.stopPropagation()">
    <div class="provider-modal-header">🔑 Manage LLM Providers</div>
    <div class="provider-list" id="sh-provider-list">
      <!-- Populated by JavaScript -->
    </div>
    <div class="provider-modal-footer">
      <button class="modal-btn close" onclick="shCloseProviderModal()">Close</button>
    </div>
  </div>
</div>

<!-- API Key Input Modal -->
<div id="sh-apikey-modal" class="provider-modal" onclick="shCloseApiKeyModal()">
  <div class="provider-modal-content" style="min-width: 450px;" onclick="event.stopPropagation()">
    <div class="provider-modal-header" id="sh-apikey-title">Enter API Key</div>
    <div style="margin: 16px 0;">
      <label style="display: block; font-size: 12px; margin-bottom: 8px; opacity: 0.7;">API Key</label>
      <input type="password" id="sh-apikey-input" placeholder="Paste your API key here..."
        style="width: 100%; padding: 8px; background: var(--vscode-input-background); color: var(--vscode-editor-foreground); border: 1px solid var(--vscode-widget-border); border-radius: 4px; font-family: monospace; font-size: 12px;">
      <div id="sh-apikey-hint" style="font-size: 10px; opacity: 0.6; margin-top: 6px;"></div>
    </div>
    <div style="margin: 16px 0;">
      <label style="display: block; font-size: 12px; margin-bottom: 8px; opacity: 0.7;">Model</label>
      <select id="sh-model-select"
        style="width: 100%; padding: 8px; background: var(--vscode-input-background); color: var(--vscode-editor-foreground); border: 1px solid var(--vscode-widget-border); border-radius: 4px; font-size: 12px;">
        <option value="">Loading models...</option>
      </select>
      <div id="sh-model-hint" style="font-size: 10px; opacity: 0.6; margin-top: 6px;"></div>
    </div>
    <div class="provider-modal-footer">
      <button class="modal-btn close" onclick="shCloseApiKeyModal()">Cancel</button>
      <button class="modal-btn" onclick="shConfirmApiKey()">Connect</button>
    </div>
  </div>
</div>

<!-- Provider Switcher Modal -->
<div id="sh-switcher-modal" class="sh-switcher-modal" onclick="shCloseProviderSwitcher()">
  <div class="sh-switcher-content" onclick="event.stopPropagation()">
    <div class="sh-switcher-header">Active LLM Provider</div>
    <div class="sh-switcher-list" id="sh-switcher-list">
      <!-- Populated by JavaScript -->
    </div>
  </div>
</div>

<!-- Disconnect Confirmation Modal -->
<div id="sh-disconnect-modal" class="provider-modal" onclick="shCloseDisconnectModal()">
  <div class="provider-modal-content" style="min-width: 400px;" onclick="event.stopPropagation()">
    <div class="provider-modal-header" id="sh-disconnect-title">Disconnect Provider?</div>
    <div style="margin: 16px 0; font-size: 13px; line-height: 1.6;" id="sh-disconnect-msg">
      You can reconnect anytime.
    </div>
    <div class="provider-modal-footer">
      <button class="modal-btn close" onclick="shCloseDisconnectModal()">Cancel</button>
      <button class="modal-btn disconnect" style="background: #f44336; color: #fff;" onclick="shConfirmDisconnect()">Disconnect</button>
    </div>
  </div>
</div>

</body></html>`;
}

// ── Dashboard HTML (inlined) ──────────────────────────────────────────────────

function getDashboardHtml(port: number, logoUri: string = "", cspSource: string = ""): string {
  const imgSrc = [cspSource, "data:"].filter(Boolean).join(" ");
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src http://localhost:${port} http://127.0.0.1:${port}; img-src ${imgSrc};">
<title>QAMill Dashboard</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background:var(--vscode-editor-background);color:var(--vscode-editor-foreground);
       font-size:13px;line-height:1.5;padding:0}
  h2{font-size:15px;font-weight:600;opacity:.9}

  ${getSharedHeaderCSS()}

  .dashboard-content{padding:16px}

  /* ── Provider badge ── */
  .title-row{display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap}
  .title-brand h2{font-size:16px;font-weight:700;opacity:.95;line-height:1.1}
  .title-purpose{font-size:10.5px;opacity:.6;margin-top:2px;display:flex;align-items:center;gap:6px}
  .title-tag{background:#0e639c;color:#fff;font-weight:700;font-size:9px;
             text-transform:uppercase;letter-spacing:.05em;padding:1px 7px;border-radius:20px;opacity:1}
  .provider-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;
                  letter-spacing:.06em;text-transform:uppercase}
  /* ── Identity chip + sign-out dropdown ── */
  .dash-identity{display:flex;align-items:center;gap:6px;margin-left:auto;flex-shrink:0;position:relative}
  .dash-id-chip{display:none;align-items:center;gap:6px;padding:3px 10px 3px 4px;
                border-radius:20px;cursor:pointer;border:1px solid var(--vscode-widget-border);
                background:var(--vscode-input-background);user-select:none}
  .dash-id-chip:hover{border-color:var(--vscode-focusBorder,#4ec9a0)}
  .dash-id-avatar{width:22px;height:22px;border-radius:50%;background:#4ec9a0;
                  color:#0d1117;font-size:10px;font-weight:700;display:flex;
                  align-items:center;justify-content:center;flex-shrink:0;overflow:hidden}
  .dash-id-avatar img{width:100%;height:100%;border-radius:50%;object-fit:cover}
  .dash-id-name{font-size:11px;max-width:140px;overflow:hidden;text-overflow:ellipsis;
                white-space:nowrap;color:var(--vscode-foreground);opacity:.85}
  .dash-id-caret{font-size:9px;opacity:.5}
  /* Dropdown */
  .dash-id-menu{position:absolute;top:calc(100% + 6px);right:0;min-width:200px;z-index:9999;
                background:var(--vscode-editorWidget-background,var(--vscode-editor-background));
                border:1px solid var(--vscode-widget-border);border-radius:6px;
                box-shadow:0 4px 20px rgba(0,0,0,.5);display:none;overflow:hidden}
  .dash-id-chip.open .dash-id-menu{display:block}
  .dim-user{padding:10px 12px 8px;border-bottom:1px solid var(--vscode-widget-border)}
  .dim-name{font-size:12px;font-weight:600;color:var(--vscode-foreground)}
  .dim-email{font-size:11px;opacity:.6;word-break:break-all;margin-top:2px}
  .dim-via{font-size:10px;color:#4ec9a0;margin-top:4px;font-weight:600;letter-spacing:.04em}
  .dim-item{display:block;width:100%;text-align:left;background:none;border:none;
            color:var(--vscode-foreground);font-size:12px;padding:8px 12px;
            cursor:pointer;font-family:var(--vscode-font-family)}
  .dim-item:hover{background:var(--vscode-list-hoverBackground)}
  .dim-signout{color:#f48771!important}
  /* ── Auth modal (sign in / sign up) ── */
  .auth-seg{display:flex;background:var(--vscode-input-background);border-radius:8px;
            padding:3px;margin-bottom:14px;border:1px solid var(--vscode-widget-border)}
  .auth-seg-btn{flex:1;padding:7px 0;border:none;background:none;cursor:pointer;
                font-family:var(--vscode-font-family);font-size:12px;font-weight:600;
                color:var(--vscode-descriptionForeground);border-radius:6px}
  .auth-seg-btn.active{background:#0e639c;color:#fff}
  .auth-social{display:flex;flex-direction:column;gap:7px}
  .auth-social-btn{display:flex;align-items:center;gap:8px;width:100%;padding:9px 12px;
                   border-radius:7px;cursor:pointer;background:var(--vscode-input-background);
                   border:1px solid var(--vscode-widget-border);color:var(--vscode-foreground);
                   font-family:var(--vscode-font-family);font-size:12px;text-align:left}
  .auth-social-btn:hover{border-color:#4ec9a0}
  .auth-or{display:flex;align-items:center;gap:10px;margin:14px 0 12px;
           color:var(--vscode-descriptionForeground);font-size:11px;opacity:.7}
  .auth-or::before,.auth-or::after{content:'';flex:1;height:1px;background:var(--vscode-widget-border)}
  /* Log in button (signed out) */
  .dash-id-btn{background:none;border:1px dashed var(--vscode-widget-border);
               color:var(--vscode-descriptionForeground);border-radius:4px;
               padding:2px 8px;font-size:10px;cursor:pointer;white-space:nowrap}
  .dash-id-btn:hover{border-color:var(--vscode-focusBorder,#007fd4);
                     color:var(--vscode-textLink-foreground,#4ec9a0)}
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
  /* ── Progress bar animations ── */
  @keyframes bar-pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .bar-fill.running{animation:bar-pulse 1.1s ease-in-out infinite}
  @keyframes bar-shimmer{
    0%  {background-position:-400px 0}
    100%{background-position:calc(400px + 100%) 0}
  }
  /* Indeterminate shimmer — pre-result phases (baseline, generating) */
  .bar-fill.shimmer{
    width:100%!important;
    background:linear-gradient(90deg,#4ec9a022 20%,#4ec9a0bb 50%,#4ec9a022 80%);
    background-size:400px 100%;
    animation:bar-shimmer 1.5s ease-in-out infinite;
  }
  /* Phase label colours */
  .phase-baseline{color:#569cd6}
  .phase-generate{color:#dcdcaa}
  .phase-testing {color:#4ec9a0}
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

  /* ── Report action buttons ── */
  .report-actions{display:none;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap}
  .report-actions.show{display:flex}
  .rpt-btn{display:flex;align-items:center;gap:5px;border:none;border-radius:5px;
           padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;transition:opacity .2s}
  .rpt-btn:hover{opacity:.82}
  .rpt-btn:disabled{opacity:.4;cursor:not-allowed}
  .rpt-save{background:#0e639c;color:#fff}
  .rpt-email{background:#6f42c1;color:#fff}
  .email-status{font-size:11px;opacity:.7;flex:1}

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

  /* ── Survived priority panel ── */
  .surv-panel{background:var(--vscode-sideBar-background);
              border:2px solid #f48771;border-radius:6px;
              margin-bottom:14px;overflow:hidden;display:none}
  .surv-panel-hdr{display:flex;align-items:center;justify-content:space-between;
                  padding:8px 12px;background:rgba(244,135,113,.08);
                  border-bottom:1px solid rgba(244,135,113,.3)}
  .surv-panel-title{font-size:12px;font-weight:700;color:#f48771}
  .surv-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;flex-shrink:0}
  .sp-high  {background:#3a1e1e;color:#f48771}
  .sp-medium{background:#3a2e1e;color:#d7ba7d}
  .sp-low   {background:#1e2a3a;color:#569cd6}
  .surv-cards{padding:6px 8px;max-height:240px;overflow-y:auto}
  .surv-card{display:flex;flex-direction:column;gap:3px;padding:7px 10px;
             border-radius:5px;margin-bottom:5px;
             background:var(--vscode-editor-background);
             border:1px solid var(--vscode-widget-border)}
  .surv-card.high  {border-left:3px solid #f48771}
  .surv-card.medium{border-left:3px solid #d7ba7d}
  .surv-card.low   {border-left:3px solid #569cd6}
  .surv-card-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
  .surv-card-id{font-family:monospace;font-size:10px;opacity:.5}
  .surv-card-fn{font-weight:600;color:var(--vscode-textLink-foreground,#4ec9a0);font-size:12px}
  .surv-card-desc{font-size:11px;opacity:.7;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .surv-card-hint{font-size:11px;color:#d7ba7d;line-height:1.5;padding-top:1px}
  .ask-ai-btn{background:none;border:1px solid var(--vscode-focusBorder,#007fd4);
              color:var(--vscode-textLink-foreground,#4ec9a0);border-radius:3px;
              padding:2px 8px;font-size:10px;cursor:pointer;white-space:nowrap;flex-shrink:0}
  .ask-ai-btn:hover{background:var(--vscode-textLink-foreground,#4ec9a0);color:#1e1e1e}
  /* ── Killer test info (shown in feed for killed mutants) ── */
  .killer-info{font-size:10px;color:#4ec9a0;font-family:monospace;
               overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  /* ── Hint text (shown in feed for survived mutants) ── */
  .surv-hint{font-size:10px;color:#d7ba7d;font-style:italic;
             overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

  /* ── Email modal ── */
  .email-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:200;
                 display:none;align-items:center;justify-content:center;padding:12px}
  .email-modal{background:var(--vscode-editor-background);
               border:1px solid var(--vscode-widget-border);border-radius:8px;
               width:min(420px,100%);max-height:92vh;overflow-y:auto;
               box-shadow:0 12px 40px rgba(0,0,0,.6)}
  .email-modal-hdr{display:flex;align-items:center;justify-content:space-between;
                   padding:12px 16px;border-bottom:1px solid var(--vscode-widget-border);
                   font-size:13px;font-weight:700}
  .email-close-btn{background:none;border:none;color:var(--vscode-editor-foreground);
                   cursor:pointer;font-size:18px;opacity:.55;line-height:1;padding:0 2px}
  .email-close-btn:hover{opacity:1}
  .email-body{padding:14px 16px 18px}
  .email-label{display:block;font-size:11px;font-weight:600;opacity:.65;
               text-transform:uppercase;letter-spacing:.05em;margin:12px 0 4px}
  .email-label:first-child{margin-top:0}
  .email-field{width:100%;background:var(--vscode-input-background);
               color:var(--vscode-input-foreground);
               border:1px solid var(--vscode-input-border,#555);
               border-radius:4px;padding:6px 9px;font-size:12px;outline:none;
               box-sizing:border-box}
  .email-field:focus{border-color:var(--vscode-focusBorder,#007fd4)}
  /* OAuth-first email send */
  .em-via-box{display:flex;align-items:center;gap:10px;
              background:rgba(78,201,160,.08);border:1px solid rgba(78,201,160,.25);
              border-radius:6px;padding:10px 12px;margin-bottom:12px}
  .em-via-icon{width:32px;height:32px;border-radius:6px;display:flex;
               align-items:center;justify-content:center;flex-shrink:0;overflow:hidden}
  .em-via-icon svg{width:20px;height:20px}
  .em-via-detail{flex:1;min-width:0}
  .em-via-lbl{font-size:12px;font-weight:600;color:#4ec9a0}
  .em-via-addr{font-size:11px;opacity:.65;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .em-no-account{background:rgba(86,156,214,.06);border:1px solid rgba(86,156,214,.2);
                 border-radius:6px;padding:12px;margin-bottom:12px;text-align:center}
  .em-no-account p{font-size:12px;opacity:.75;margin-bottom:8px}
  .em-connect-btn{background:#0e639c;color:#fff;border:none;border-radius:4px;
                  padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer}
  .em-connect-btn:hover{opacity:.85}
  .em-divider{font-size:11px;opacity:.4;text-align:center;margin:10px 0;
              position:relative}
  .em-divider::before,.em-divider::after{content:'';position:absolute;
    top:50%;width:42%;height:1px;background:var(--vscode-widget-border)}
  .em-divider::before{left:0}.em-divider::after{right:0}
  .email-note{background:rgba(210,153,34,.1);border:1px solid rgba(210,153,34,.4);
              border-radius:4px;padding:8px 10px;font-size:11px;
              color:#d29922;line-height:1.6;margin-bottom:2px}
  .email-note a{color:#4ec9a0;text-decoration:none;cursor:pointer}
  .email-actions{display:flex;gap:8px;margin-top:14px;justify-content:flex-end;flex-wrap:wrap}
  .email-btn{border:none;border-radius:5px;padding:7px 16px;font-size:12px;
             font-weight:600;cursor:pointer;transition:opacity .18s;white-space:nowrap}
  .email-btn:disabled{opacity:.38;cursor:not-allowed}
  .email-btn:hover:not(:disabled){opacity:.82}
  .email-btn-primary  {background:#0e639c;color:#fff}
  .email-btn-secondary{background:var(--vscode-button-secondaryBackground,#3a3d41);
                       color:var(--vscode-button-secondaryForeground,#ccc)}
  .email-modal-status{font-size:11px;padding:7px 9px;border-radius:4px;
                      margin-top:10px;display:none;line-height:1.5}
  .ems-ok   {background:#1e3a2f;color:#4ec9a0;border:1px solid #2e5a3f;display:block!important}
  .ems-error{background:#3a1e1e;color:#f48771;border:1px solid #5a2e2e;display:block!important}
  .ems-info {background:rgba(86,156,214,.12);color:#569cd6;border:1px solid rgba(86,156,214,.3);display:block!important}
</style>
</head>
<body>

${getSharedHeaderHtml("mutation", logoUri)}

<div class="dashboard-content">
<!-- ── Title row with provider badge + identity ── -->
<div class="title-row">
  <div class="title-brand">
    <h2>QAMill Test Studio</h2>
    <div class="title-purpose"><span class="title-tag">Mutation Analysis</span>find test gaps · scoring · survived mutants</div>
  </div>
  <span class="file-label" id="run-file"></span>
  <span class="provider-badge pb-inhouse" id="provider-badge">OLLAMA</span>
  <div class="dash-identity">
    <!-- Signed-in chip with dropdown -->
    <div class="dash-id-chip" id="dash-id-chip" onclick="toggleDashIdMenu(event)">
      <div class="dash-id-avatar" id="dash-id-avatar"></div>
      <span class="dash-id-name" id="dash-id-name"></span>
      <span class="dash-id-caret">▾</span>
      <div class="dash-id-menu" id="dash-id-menu">
        <div class="dim-user">
          <div class="dim-name" id="dim-name"></div>
          <div class="dim-email" id="dim-email"></div>
          <div class="dim-via" id="dim-via"></div>
        </div>
        <button class="dim-item" onclick="event.stopPropagation();openDashAuthModal();closeDashIdMenu()">Manage accounts</button>
        <button class="dim-item dim-signout" onclick="event.stopPropagation();vscode.postMessage({type:'sign_out'});closeDashIdMenu()">Sign out</button>
      </div>
    </div>
    <!-- Log in button (signed out) -->
    <button class="dash-id-btn" id="dash-id-btn" onclick="openDashAuthModal()">Log in</button>
  </div>
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

<!-- ── Survived priority panel (populated after all mutants run) ── -->
<div class="surv-panel" id="surv-panel">
  <div class="surv-panel-hdr">
    <span class="surv-panel-title">&#9888; Survived Mutants — Priority Order</span>
    <span class="surv-badge sp-high" id="surv-count">0</span>
  </div>
  <div class="surv-cards" id="surv-cards"></div>
</div>

<!-- ── Mutation results feed ── -->
<div class="feed" id="feed">
  <div id="waiting">Right-click a file &#8594; Run QAMill Mutation Analysis</div>
</div>

<!-- ── Email modal (OAuth-first) ── -->
<div class="email-overlay" id="email-overlay">
  <div class="email-modal" id="email-modal-card">
    <div class="email-modal-hdr">
      <span>&#128231; Send Report</span>
      <button class="email-close-btn" id="email-close-btn">&#215;</button>
    </div>
    <div class="email-body" id="email-body">

      <!-- OAuth sender (shown when Google/Microsoft connected) -->
      <div class="em-via-box" id="em-via-box" style="display:none">
        <div class="em-via-icon" id="em-via-icon"></div>
        <div class="em-via-detail">
          <div class="em-via-lbl" id="em-via-lbl">Sending via Google</div>
          <div class="em-via-addr" id="em-via-addr">user@gmail.com</div>
        </div>
        <button class="email-btn email-btn-secondary" style="padding:4px 10px;font-size:11px"
                onclick="closeEmailModal();openDashAuthModal()">Change</button>
      </div>

      <!-- No account: connect CTA + SMTP fallback -->
      <div id="em-no-account-area">
        <div class="em-no-account">
          <p>Connect Google or Microsoft to send without App Password</p>
          <button class="em-connect-btn"
                  onclick="closeEmailModal();openDashAuthModal()">
            Connect account &#8594;
          </button>
        </div>
        <div class="em-divider">or enter SMTP settings</div>
        <div class="email-note" id="email-provider-note">
          <strong>Gmail:</strong> Use an <strong>App Password</strong>, not your regular password.
          <a id="email-help-link">Create App Password &#8594;</a>
        </div>
        <label class="email-label">SMTP Provider</label>
        <select id="email-provider" class="email-field">
          <option value="gmail">Gmail</option>
          <option value="outlook">Outlook / Office 365</option>
          <option value="custom">Custom SMTP</option>
        </select>
        <label class="email-label">Your Email (Sender)</label>
        <input type="email" id="email-sender" class="email-field" placeholder="you@gmail.com" autocomplete="email">
        <label class="email-label">App Password</label>
        <input type="password" id="email-apppassword" class="email-field" placeholder="xxxx xxxx xxxx xxxx" autocomplete="new-password">
        <div id="email-custom-fields" style="display:none">
          <label class="email-label">SMTP Host</label>
          <input type="text" id="email-smtp-host" class="email-field" placeholder="smtp.example.com">
          <label class="email-label">SMTP Port</label>
          <input type="number" id="email-smtp-port" class="email-field" value="587">
        </div>
      </div>

      <!-- Always: recipient -->
      <label class="email-label">Send Report To</label>
      <input type="email" id="email-recipient" class="email-field" placeholder="recipient@example.com">

      <div class="email-modal-status" id="email-modal-status"></div>
      <div class="email-actions">
        <button class="email-btn email-btn-secondary" id="email-test-btn">&#9889; Test</button>
        <button class="email-btn email-btn-primary"   id="email-send-btn">&#128231; Send Report</button>
      </div>
    </div>
  </div>
</div>

<!-- ── Auth modal (sign in / sign up popup) ── -->
<div class="email-overlay" id="auth-overlay">
  <div class="email-modal" id="auth-modal-card" style="width:min(400px,100%)">
    <div class="email-modal-hdr">
      <span>&#128274; Sign in to QAMill</span>
      <button class="email-close-btn" id="auth-close-btn">&#215;</button>
    </div>
    <div class="email-body">
      <div class="auth-seg">
        <button class="auth-seg-btn active" id="auth-seg-signin" onclick="dashSetAuthMode('signin')">Sign in</button>
        <button class="auth-seg-btn"        id="auth-seg-signup" onclick="dashSetAuthMode('signup')">Sign up</button>
      </div>
      <div class="auth-social">
        <button class="auth-social-btn" onclick="dashOAuth('google')">&#128272; Continue with Google</button>
        <button class="auth-social-btn" onclick="dashOAuth('microsoft')">&#128273; Continue with Microsoft</button>
        <button class="auth-social-btn" onclick="dashOAuth('atlassian')">&#129513; Continue with Atlassian (Jira)</button>
        <button class="auth-social-btn" onclick="dashOAuth('github')">&#128025; Continue with GitHub</button>
      </div>
      <div class="auth-or"><span>or</span></div>
      <div id="auth-name-row" style="display:none">
        <label class="email-label">Name</label>
        <input type="text" id="auth-name" class="email-field" placeholder="Your name">
      </div>
      <label class="email-label">Email</label>
      <input type="email" id="auth-email" class="email-field" placeholder="you@company.com" autocomplete="email">
      <label class="email-label">Password</label>
      <input type="password" id="auth-pass" class="email-field" placeholder="At least 8 characters">
      <div class="email-modal-status" id="auth-status"></div>
      <div class="email-actions">
        <button class="email-btn email-btn-primary" id="auth-submit-btn" style="width:100%;text-align:center"
                onclick="dashSubmitAuth()">Sign in</button>
      </div>
      <div style="font-size:10px;opacity:.5;text-align:center;margin-top:10px">
        Password is hashed and stored only on this machine.
      </div>
    </div>
  </div>
</div>

<!-- ── Report actions (shown after analysis completes) ── -->
<div class="report-actions" id="report-actions">
  <button class="rpt-btn rpt-save"  id="rpt-save-btn">&#128190; Save Report</button>
  <button class="rpt-btn rpt-email" id="rpt-email-btn">&#128231; Email Report</button>
  <span class="email-status" id="email-status"></span>
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
let es = null;              // active fetch ReadableStreamDefaultReader (or null)
let streamActive = false;
let currentStreamUrl = null;
let eventsReceived = 0;     // count of non-ping events processed — used for reconnect resume
let currentJobId = null;    // job_id of the active or most-recently-completed analysis
let mutantResults = [];
let lastSummary = null;
let startInfo = {};
let suggestedTests = [];
let scoreBeforeHeal = null;
let emailSettings = {};     // synced from VS Code config via sync_settings

// ── Message listener ────────────────────────────────────────────────────────
window.addEventListener('message', e => {
  const msg = e.data;
  if (msg.type === 'job_started') {
    // Ignore duplicate deliveries for the same job
    if (msg.stream_url === currentStreamUrl) return;
    currentStreamUrl = msg.stream_url;
    eventsReceived = 0;
    phaseResultsStarted = false;
    currentJobId = (msg.stream_url || '').split('/').pop().split('?')[0] || null;
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
      appendLog('LLM: ' + (msg.llm_provider || 'none').toUpperCase(), 'info');
      // Extension streams via Node.js http and forwards events here as 'stream_event' messages.
      // Do NOT call connectStream() — webview fetch() is buffered by VS Code's proxy.
    } catch(err) {
      const feed = document.getElementById('feed');
      if (feed) feed.innerHTML = '<div style="color:#f48771;padding:8px">Dashboard error: ' + String(err) + '</div>';
    }
  }
  if (msg.type === 'stream_event') {
    // Each SSE event forwarded from the extension's Node.js HTTP reader — no proxy buffering.
    handleEvent(msg.event);
    return;
  }
  if (msg.type === 'backend_log') {
    appendLog(msg.text, msg.level || 'info');
  }
  if (msg.type === 'run_error') {
    addStatus('Error: ' + msg.message);
    appendLog('Error: ' + msg.message, 'error');
  }
  if (msg.type === 'email_sending') {
    const el = document.getElementById('email-status');
    const btn = document.getElementById('rpt-email-btn');
    if (el) el.textContent = 'Sending...';
    if (btn) btn.disabled = true;
  }
  if (msg.type === 'email_sent') {
    const el = document.getElementById('email-status');
    const btn = document.getElementById('rpt-email-btn');
    if (el) el.textContent = '\\u2713 Sent to ' + msg.to;
    if (btn) { btn.disabled = false; btn.textContent = '\\u2713 Resend'; }
    appendLog('Report emailed to ' + msg.to, 'ok');
  }
  if (msg.type === 'email_error') {
    const el = document.getElementById('email-status');
    const btn = document.getElementById('rpt-email-btn');
    if (el) el.textContent = 'Failed: ' + msg.error;
    if (btn) btn.disabled = false;
    appendLog('Email error: ' + msg.error, 'error');
    // Also surface in the modal if it is open
    const overlay = document.getElementById('email-overlay');
    if (overlay && overlay.style.display !== 'none') {
      const sendBtn = document.getElementById('email-send-btn');
      if (sendBtn) sendBtn.disabled = false;
      setEmailModalStatus(msg.error, 'error');
    }
  }
  if (msg.type === 'set_file') {
    const lbl = document.getElementById('run-file');
    if (lbl) lbl.textContent = msg.file || '';
  }
  if (msg.type === 'engine_starting') {
    var pl = document.getElementById('progress-label');
    if (pl) pl.textContent = 'Starting analysis engine…';
    var barEl = document.getElementById('bar');
    if (barEl) { barEl.style.width = '8%'; barEl.classList.add('running'); }
    var w = document.getElementById('waiting');
    if (w) w.textContent = 'Booting the QAMill engine — this takes a moment on first run…';
  }
  if (msg.type === 'sync_settings') {
    const llmSel  = document.getElementById('llm-select-mini');
    const modeSel = document.getElementById('mode-select');
    if (llmSel  && msg.provider) llmSel.value  = msg.provider;
    if (modeSel && msg.mode)     modeSel.value = msg.mode;
    updateBadge(msg.provider || 'inhouse');
    if (msg.email) { emailSettings = msg.email; }
    // Apply identity to dashboard header
    if (msg.identity) { applyIdentity(msg.identity); }
  }
  if (msg.type === 'open_email_modal') {
    openEmailModal();
    return;
  }
  if (msg.type === 'email_test_result') {
    const btn = document.getElementById('email-test-btn');
    if (btn) btn.disabled = false;
    setEmailModalStatus(msg.message, msg.success ? 'ok' : 'error');
    return;
  }
  if (msg.type === 'email_modal_result') {
    const sendBtn = document.getElementById('email-send-btn');
    if (sendBtn) sendBtn.disabled = false;
    if (msg.success) {
      setEmailModalStatus(msg.message, 'ok');
      setTimeout(closeEmailModal, 2800);
    } else {
      setEmailModalStatus(msg.message, 'error');
    }
    return;
  }
  if (msg.type === 'apply_identity') {
    // Live identity pushed from backend (catches sign-ins done in the browser popup)
    applyIdentity(msg.identity);
    // If the auth modal is open and we just signed in, close it
    if (msg.identity && document.getElementById('auth-overlay').style.display === 'flex') {
      closeDashAuthModal();
    }
    return;
  }
  if (msg.type === 'auth_result') {
    var st = document.getElementById('auth-status');
    if (msg.success) {
      if (st) { st.textContent = '\\u2713 Welcome' + (msg.name ? ', ' + msg.name : '') + '!'; st.className = 'email-modal-status ems-ok'; }
      setTimeout(closeDashAuthModal, 800);
    } else if (st) {
      st.textContent = '\\u2717 ' + (msg.error || 'Failed'); st.className = 'email-modal-status ems-error';
    }
    return;
  }
  if (msg.type === 'auth_connected') {
    // OAuth completed in system browser — refresh identity badge + email modal
    applyIdentity({ email: msg.email || '', type: 'work', provider: msg.provider });
    // If email modal is open, switch to OAuth path
    var viaBox = document.getElementById('em-via-box');
    var noAcct = document.getElementById('em-no-account-area');
    if (viaBox && noAcct && document.getElementById('email-overlay').style.display === 'flex') {
      var icon = document.getElementById('em-via-icon');
      var lbl  = document.getElementById('em-via-lbl');
      var addr = document.getElementById('em-via-addr');
      if (icon) icon.innerHTML  = emViaIcons[msg.provider] || '';
      if (lbl)  lbl.textContent = 'Sending via ' + (msg.provider || '');
      if (addr) addr.textContent = msg.email || '';
      viaBox.style.display = 'flex';
      noAcct.style.display = 'none';
    }
    return;
  }
  if (msg.type === 'ai_response') {
    const area = document.getElementById('chat-response');
    area.innerHTML = '<span class="chat-answer"><strong>QAMill:</strong> ' + esc(msg.answer) + '</span>';
    document.getElementById('send-btn').disabled = false;
  }
});

// ── Identity chip + dropdown ──────────────────────────────────────────────────
function toggleDashIdMenu(e) {
  var chip = document.getElementById('dash-id-chip');
  if (chip) chip.classList.toggle('open');
  e.stopPropagation();
}
function closeDashIdMenu() {
  var chip = document.getElementById('dash-id-chip');
  if (chip) chip.classList.remove('open');
}
document.addEventListener('click', function() { closeDashIdMenu(); });

function applyIdentity(identity) {
  var chip = document.getElementById('dash-id-chip');
  var btn  = document.getElementById('dash-id-btn');
  if (!chip || !btn) return;

  if (identity && identity.email) {
    chip.style.display = 'inline-flex';
    btn.style.display  = 'none';

    // Avatar
    var av = document.getElementById('dash-id-avatar');
    if (av) {
      if (identity.picture) {
        var img = document.createElement('img');
        img.src = identity.picture;
        img.onerror = function() { av.textContent = identity.email.charAt(0).toUpperCase(); };
        av.innerHTML = ''; av.appendChild(img);
      } else {
        av.textContent = identity.email.charAt(0).toUpperCase();
      }
    }
    // Chip label
    var nm = document.getElementById('dash-id-name');
    if (nm) nm.textContent = identity.name || identity.email;

    // Dropdown details
    var dn = document.getElementById('dim-name');
    if (dn) dn.textContent = identity.name || '';
    var de = document.getElementById('dim-email');
    if (de) de.textContent = identity.email;
    var dv = document.getElementById('dim-via');
    if (dv) {
      var lbl = identity.label || identity.provider || '';
      dv.textContent = lbl ? 'Signed in with ' + lbl : '';
      dv.style.display = lbl ? '' : 'none';
    }
  } else {
    chip.style.display = 'none';
    chip.classList.remove('open');
    btn.style.display  = '';
    btn.textContent    = 'Log in';
  }
  // Pre-fill sender in email modal
  var senderField = document.getElementById('email-sender');
  if (senderField && identity && identity.email && !senderField.value) {
    senderField.value = identity.email;
  }
}

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
             (m.priority ? ' [priority: ' + m.priority + ']' : '') + '\\n';
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

// ── Stream handling — fetch-based with automatic reconnect ──────────────────
async function connectStream(url) {
  if (streamActive && es) { try { es.cancel(); } catch(e) {} }
  streamActive = true; es = null;

  const MAX_ATTEMPTS = 20;
  let attempt = 0;
  let retryDelay = 2000; // ms, doubles up to 30s cap

  while (streamActive && attempt <= MAX_ATTEMPTS) {
    // ── Reconnect wait (skipped on first attempt) ──
    if (attempt > 0) {
      const secs = Math.round(retryDelay / 1000);
      const msg = 'Network error — reconnecting in ' + secs + 's (attempt ' + attempt + '/' + MAX_ATTEMPTS + ')';
      addStatus(msg);
      appendLog(msg, 'warn');
      await new Promise(r => setTimeout(r, retryDelay));
      retryDelay = Math.min(Math.round(retryDelay * 1.6), 30000);
    }

    // ── Build URL with resume offset ──
    const resumeUrl = eventsReceived > 0 ? url + '?from_event=' + eventsReceived : url;
    const isReconnect = attempt > 0;
    appendLog((isReconnect ? 'Reconnecting → ' : 'Connecting → ') + resumeUrl, 'info');

    try {
      const resp = await fetch(resumeUrl);

      if (!resp.ok) {
        if (resp.status === 404) {
          appendLog('Job not found on server (404) — analysis may have expired or completed', 'warn');
          break; // don't retry a 404
        }
        throw new Error('HTTP ' + resp.status);
      }

      // ── Successful connection ──
      if (isReconnect) {
        addStatus('Stream reconnected — resuming from event ' + eventsReceived);
        appendLog('Reconnected ✓ resuming from event ' + eventsReceived, 'ok');
        const bar = document.getElementById('bar');
        if (bar) bar.classList.add('running'); // re-pulse the bar
      } else {
        appendLog('Stream connected ✓', 'ok');
      }
      attempt = 0;      // reset attempt count on success
      retryDelay = 2000;

      const reader = resp.body.getReader();
      es = reader;
      const dec = new TextDecoder();
      let buf = '';
      let serverClosed = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) { serverClosed = true; break; }
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

      // ── Stream ended cleanly ──
      if (!streamActive) return;    // handleEvent('complete') already closed things
      if (serverClosed) {
        appendLog('Stream closed by server — retrying', 'warn');
        attempt++;
        continue;
      }

    } catch (err) {
      const msg = String(err);
      addStatus('Stream error: ' + msg);
      appendLog('Stream error: ' + msg, 'error');
      attempt++;
      es = null;
    }
  }

  if (attempt > MAX_ATTEMPTS) {
    appendLog('Max reconnection attempts reached. Analysis continues on backend — restart the dashboard to reconnect.', 'warn');
    addStatus('Stream disconnected after ' + MAX_ATTEMPTS + ' retries');
    const bar = document.getElementById('bar');
    if (bar) bar.classList.remove('running');
  }
  streamActive = false; es = null;
}

// Phase tracking — drives the bar through pre-result stages
var phaseResultsStarted = false;

function setPhaseBar(widthPct, label, labelClass) {
  var bar = document.getElementById('bar');
  var pl  = document.getElementById('progress-label');
  if (bar) {
    bar.classList.remove('shimmer', 'running');
    if (widthPct === null) {
      // Indeterminate — use shimmer
      bar.classList.add('shimmer');
    } else {
      bar.style.width = widthPct + '%';
      bar.classList.add('running');
    }
  }
  if (pl && label) {
    pl.innerHTML = '<span class="' + (labelClass || '') + '">' + label + '</span>';
  }
}

function handleEvent(e) {
  if (e.type === 'ping') return;
  eventsReceived++;
  if (e.type === 'status') {
    addStatus(e.message);
    // Drive bar through named phases so it never looks frozen
    if (!phaseResultsStarted) {
      var m = e.message || '';
      if (/baseline|running.*test/i.test(m)) {
        setPhaseBar(null, '⏳ Running baseline tests…', 'phase-baseline');
      } else if (/generat.*mutant|creat.*mutant/i.test(m)) {
        setPhaseBar(null, '⚙ Generating mutants…', 'phase-generate');
      } else if (/test.*mutant|applying|analys/i.test(m)) {
        setPhaseBar(null, '🔬 Testing mutants…', 'phase-testing');
      } else {
        // Unknown status — keep shimmer, update label
        var bar = document.getElementById('bar');
        if (bar && !phaseResultsStarted) bar.classList.add('shimmer');
      }
    }
    appendLog(e.message, 'info');
    return;
  }
  if (e.type === 'start') {
    startInfo = e;
    phaseResultsStarted = false;
    const aiPart = e.ai_mutant_count ? ' + ' + e.ai_mutant_count + ' AI' : '';
    const totalStr = e.total + ' mutants (' + e.ast_mutant_count + ' AST' + aiPart + ')';
    setPhaseBar(null, '🔬 Testing ' + totalStr + '…', 'phase-testing');
    appendLog('Found ' + totalStr, 'ok');
    return;
  }
  if (e.type === 'survived_priority') {
    renderSurvivedPanel(e.mutants || []);
    return;
  }
  if (e.type === 'mutant_result') {
    if (!phaseResultsStarted) {
      // First real result — exit shimmer, switch to deterministic progress
      phaseResultsStarted = true;
      var bar = document.getElementById('bar');
      if (bar) { bar.classList.remove('shimmer'); bar.classList.add('running'); }
    }
    mutantResults.push(e);
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
    const actBar = document.getElementById('report-actions');
    if (actBar) actBar.classList.add('show');
    vscode.postMessage({ type: 'analysis_complete', true_score: e.true_score, job_id: currentJobId, report_path: e.report_path || '' });
    currentStreamUrl = null;
    streamActive = false; // signals reconnect loop to stop
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
  div.style.flexDirection = 'column';
  div.style.alignItems    = 'stretch';
  div.style.gap           = '2px';

  const badgeClass = {killed:'b-killed', survived:'b-survived', equivalent:'b-equivalent', error:'b-error'}[e.status] || 'b-info';
  const icon       = {killed:'✓', survived:'✗', equivalent:'≡', error:'!'}[e.status] || '·';
  const isCross    = e.operator && e.operator.startsWith('CMR');
  const isAI       = e.operator === 'AI';

  let tags = '';
  if (e.priority) {
    const pc = {low:'b-diff-low', medium:'b-diff-medium', high:'b-diff-high'}[e.priority] || 'b-info';
    tags += '<span class="mini-tag ' + pc + '" title="Priority: ' + e.priority + '">' + e.priority[0].toUpperCase() + '</span>';
  }
  if (isCross) tags += '<span class="mini-tag b-cross" title="Cross-method">X</span>';
  if (isAI)    tags += '<span class="mini-tag b-ai-mutant" title="AI mutant">AI</span>';

  // Secondary info line: killer test name for killed, hint for survived
  let infoHtml = '';
  if (e.status === 'killed' && e.killer_test_name) {
    const loc = e.killer_test_file ? ' @ ' + esc(e.killer_test_file) : '';
    infoHtml = '<div style="padding-left:84px"><span class="killer-info" title="Test that caught this mutant">' +
      '&#10003; ' + esc(e.killer_test_name) + loc + '</span></div>';
  } else if (e.status === 'survived' && e.hint) {
    infoHtml = '<div style="padding-left:84px"><span class="surv-hint" title="' + esc(e.hint) + '">' +
      esc(e.hint) + '</span></div>';
  }

  div.innerHTML =
    '<div style="display:flex;align-items:center;gap:6px">' +
      '<span class="badge ' + badgeClass + '">' + icon + ' ' + e.status.toUpperCase() + '</span>' +
      '<span class="mut-line" title="' + esc(e.description) + '">' +
        '<span class="mut-id">' + esc(e.mutant_id) + '</span>' +
        '<span class="mut-sep"> · </span>' +
        '<span class="mut-fn">' + esc(e.function) + ':' + e.line + '</span>' +
        '<span class="mut-sep"> · </span>' +
        esc(e.description) +
      '</span>' +
      tags +
    '</div>' +
    infoHtml;

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
      return (rank[a.priority] ?? 1) - (rank[b.priority] ?? 1);
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
      (m.priority ? ' <span style="opacity:.6">[' + m.priority + ']</span>' : '') +
      '</div>'
    ).join('');
  }
}

function renderSurvivedPanel(mutants) {
  const panel = document.getElementById('surv-panel');
  const cards = document.getElementById('surv-cards');
  const count = document.getElementById('surv-count');
  if (!panel || !cards) return;
  if (mutants.length === 0) { panel.style.display = 'none'; return; }

  cards.innerHTML = '';
  if (count) count.textContent = String(mutants.length);
  panel.style.display = 'block';

  const prioLabel = {high:'HIGH', medium:'MED', low:'LOW'};
  const prioClass = {high:'sp-high', medium:'sp-medium', low:'sp-low'};

  mutants.forEach(function(m) {
    const card = document.createElement('div');
    card.className = 'surv-card ' + (m.priority || 'medium');
    const pl = prioLabel[m.priority] || 'MED';
    const pc = prioClass[m.priority] || 'sp-medium';

    card.innerHTML =
      '<div class="surv-card-row">' +
        '<span class="surv-badge ' + pc + '">' + pl + '</span>' +
        '<span class="surv-card-id">' + esc(m.mutant_id) + '</span>' +
        '<span class="surv-card-fn">' + esc(m.function) + ':' + m.line + '</span>' +
        '<span class="surv-card-desc" title="' + esc(m.description) + '">' + esc(m.description) + '</span>' +
        '<button class="ask-ai-btn"' +
          ' data-id="'   + esc(m.mutant_id)    + '"' +
          ' data-fn="'   + esc(m.function)      + '"' +
          ' data-line="' + m.line               + '"' +
          ' data-op="'   + esc(m.operator)      + '"' +
          ' data-desc="' + esc(m.description)   + '">Ask AI &#8594;</button>' +
      '</div>' +
      (m.hint ? '<div class="surv-card-hint">' + esc(m.hint) + '</div>' : '');

    const btn = card.querySelector('.ask-ai-btn');
    if (btn) {
      btn.addEventListener('click', function() {
        const prompt =
          'How do I write a test to kill mutant ' + btn.getAttribute('data-id') +
          ' in function ' + btn.getAttribute('data-fn') + '() at line ' + btn.getAttribute('data-line') +
          '? The mutation is: ' + btn.getAttribute('data-desc') +
          ' (operator: ' + btn.getAttribute('data-op') + ')';
        const inp = document.getElementById('chat-input');
        if (inp) { inp.value = prompt; inp.focus(); }
        sendChat();
      });
    }
    cards.appendChild(card);
  });
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
  var ra = g('report-actions');
  if (ra) { ra.classList.remove('show'); }
  var es2 = g('email-status'); if (es2) es2.textContent = '';
  var eb = g('rpt-email-btn'); if (eb) { eb.disabled = false; eb.innerHTML = '&#128231; Email Report'; }
  var feed = g('feed');
  if (feed) feed.innerHTML = '';
  var bar = g('bar');
  if (bar) bar.style.width = '0';
  var ss = g('summary-section');
  if (ss) ss.style.display = 'none';
  // Survived priority panel
  var survPanel = g('surv-panel');
  if (survPanel) survPanel.style.display = 'none';
  var survCards = g('surv-cards');
  if (survCards) survCards.innerHTML = '';
  var survCount = g('surv-count');
  if (survCount) survCount.textContent = '0';
  // Suggested tests panel (legacy, kept for compatibility)
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

// ── Email settings modal ──────────────────────────────────────────────────────
const EMAIL_PRESETS = {
  gmail:   {host:'smtp.gmail.com',         port:587, tls:true},
  outlook: {host:'smtp-mail.outlook.com',  port:587, tls:true},
  custom:  {host:'',                        port:587, tls:true},
};

var emViaIcons = {
  google:    '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>',
  microsoft: '<svg viewBox="0 0 21 21" width="20" height="20"><rect x="1" y="1" width="9" height="9" fill="#f25022"/><rect x="11" y="1" width="9" height="9" fill="#7fba00"/><rect x="1" y="11" width="9" height="9" fill="#00a4ef"/><rect x="11" y="11" width="9" height="9" fill="#ffb900"/></svg>',
};

function openEmailModal() {
  const overlay = document.getElementById('email-overlay');
  if (!overlay) return;
  clearEmailModalStatus();
  overlay.style.display = 'flex';

  // Pre-fill SMTP fields from saved settings (fallback)
  const s = emailSettings;
  var el;
  el = document.getElementById('email-provider');   if (el) el.value = s.provider || 'gmail';
  el = document.getElementById('email-sender');      if (el && !el.value) el.value = s.sender      || '';
  el = document.getElementById('email-apppassword'); if (el && !el.value) el.value = s.appPassword || '';
  el = document.getElementById('email-recipient');   if (el && !el.value) el.value = s.recipient   || '';
  el = document.getElementById('email-smtp-host');   if (el) el.value = s.smtp_host || '';
  el = document.getElementById('email-smtp-port');   if (el) el.value = String(s.smtp_port || 587);
  updateEmailProviderUI();

  // Check OAuth status — show OAuth path if connected, else SMTP form
  var viaBox     = document.getElementById('em-via-box');
  var noAcctArea = document.getElementById('em-no-account-area');
  fetch('http://localhost:${port}/auth/status')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var primary = d.primary;
      if (primary && primary.can_email) {
        if (viaBox)     viaBox.style.display     = 'flex';
        if (noAcctArea) noAcctArea.style.display  = 'none';
        var icon = document.getElementById('em-via-icon');
        var lbl  = document.getElementById('em-via-lbl');
        var addr = document.getElementById('em-via-addr');
        if (icon) icon.innerHTML  = emViaIcons[primary.provider] || '';
        if (lbl)  lbl.textContent = 'Sending via ' + (primary.label || primary.provider);
        if (addr) addr.textContent = primary.email || '';
      } else {
        if (viaBox)     viaBox.style.display     = 'none';
        if (noAcctArea) noAcctArea.style.display  = '';
      }
    })
    .catch(function() {
      if (viaBox)     viaBox.style.display    = 'none';
      if (noAcctArea) noAcctArea.style.display = '';
    });
}

function closeEmailModal() {
  var overlay = document.getElementById('email-overlay');
  if (overlay) overlay.style.display = 'none';
}

// ── Auth modal (sign in / sign up popup in the dashboard) ──────────────────
var dashAuthMode = 'signin';
function openDashAuthModal() {
  var ov = document.getElementById('auth-overlay');
  if (ov) ov.style.display = 'flex';
  dashSetAuthMode('signin');
  var st = document.getElementById('auth-status');
  if (st) { st.textContent = ''; st.className = 'email-modal-status'; }
}
function closeDashAuthModal() {
  var ov = document.getElementById('auth-overlay');
  if (ov) ov.style.display = 'none';
}
function dashSetAuthMode(mode) {
  dashAuthMode = mode;
  var inSign = mode === 'signin';
  document.getElementById('auth-seg-signin').classList.toggle('active', inSign);
  document.getElementById('auth-seg-signup').classList.toggle('active', !inSign);
  document.getElementById('auth-name-row').style.display = inSign ? 'none' : '';
  document.getElementById('auth-submit-btn').textContent = inSign ? 'Sign in' : 'Create account';
}
function dashSubmitAuth() {
  var email = document.getElementById('auth-email').value || '';
  var pass  = document.getElementById('auth-pass').value || '';
  var name  = (document.getElementById('auth-name')||{}).value || '';
  var st = document.getElementById('auth-status');
  st.textContent = 'Please wait…'; st.className = 'email-modal-status ems-info';
  vscode.postMessage({ type: 'auth_submit', mode: dashAuthMode, email: email, password: pass, name: name });
}
function dashOAuth(provider) {
  var st = document.getElementById('auth-status');
  st.textContent = 'Opening ' + provider + ' sign-in in your browser…';
  st.className = 'email-modal-status ems-info';
  vscode.postMessage({ type: 'auth_oauth', provider: provider });
}

function updateEmailProviderUI() {
  var sel = document.getElementById('email-provider');
  if (!sel) return;
  var prov = sel.value;
  var cf = document.getElementById('email-custom-fields');
  if (cf) cf.style.display = prov === 'custom' ? 'block' : 'none';
  var note = document.getElementById('email-provider-note');
  if (!note) return;
  if (prov === 'gmail') {
    note.style.display = 'block';
    note.innerHTML =
      '<strong>Gmail:</strong> You must use an <strong>App Password</strong>, not your regular ' +
      'Gmail password &mdash; regular passwords are blocked by Google for SMTP access. ' +
      '<a id="email-help-link" style="color:#4ec9a0;text-decoration:none;cursor:pointer">' +
      'Create App Password &#8594;</a>';
    var lnk = document.getElementById('email-help-link');
    if (lnk) lnk.onclick = function(e) {
      e.preventDefault();
      vscode.postMessage({type:'open_external',url:'https://myaccount.google.com/apppasswords'});
    };
  } else if (prov === 'outlook') {
    note.style.display = 'block';
    note.innerHTML =
      '<strong>Outlook / Office 365:</strong> Use an <strong>App Password</strong> if ' +
      '2-Factor Authentication is enabled on your Microsoft account. ' +
      '<a id="email-help-link" style="color:#4ec9a0;text-decoration:none;cursor:pointer">' +
      'Microsoft App Passwords &#8594;</a>';
    var lnk2 = document.getElementById('email-help-link');
    if (lnk2) lnk2.onclick = function(e) {
      e.preventDefault();
      vscode.postMessage({type:'open_external',url:'https://account.microsoft.com/security'});
    };
  } else {
    // Custom SMTP — typically corporate. Guide them to OAuth or their real relay.
    note.style.display = 'block';
    note.innerHTML =
      '<strong>Work / corporate email:</strong> enter your organisation&rsquo;s SMTP server ' +
      '(ask IT — it is NOT smtp.gmail.com). If your company uses Google&nbsp;Workspace or ' +
      'Microsoft&nbsp;365, the easiest path is <strong>Connect account</strong> above — ' +
      'OAuth works for work accounts and needs no password.';
  }
}

function getEmailFormSettings() {
  var prov = (document.getElementById('email-provider') || {}).value || 'gmail';
  var preset = EMAIL_PRESETS[prov] || EMAIL_PRESETS.custom;
  var isCustom = prov === 'custom';
  function val(id) { var e = document.getElementById(id); return e ? e.value : ''; }
  return {
    provider:    prov,
    sender:      val('email-sender').trim(),
    appPassword: val('email-apppassword'),
    recipient:   val('email-recipient').trim(),
    smtp_host:   isCustom ? val('email-smtp-host').trim() : preset.host,
    smtp_port:   isCustom ? parseInt(val('email-smtp-port') || '587') : preset.port,
    use_tls:     preset.tls !== false,
  };
}

function sendTestEmail() {
  var settings = getEmailFormSettings();
  if (!settings.sender || !settings.appPassword || !settings.recipient) {
    setEmailModalStatus('Fill in Sender, App Password, and Recipient first.', 'error');
    return;
  }
  var btn = document.getElementById('email-test-btn');
  if (btn) btn.disabled = true;
  setEmailModalStatus('Sending test email...', 'info');
  vscode.postMessage(Object.assign({type:'email_send_test'}, settings));
}

function sendEmailReport() {
  if (!currentJobId) {
    setEmailModalStatus('No completed analysis — run an analysis first.', 'error');
    return;
  }
  var settings = getEmailFormSettings();
  if (!settings.sender || !settings.appPassword || !settings.recipient) {
    setEmailModalStatus('Fill in Sender, App Password, and Recipient before sending.', 'error');
    return;
  }
  emailSettings = settings;
  vscode.postMessage(Object.assign({type:'email_settings_save'}, settings));
  var btn = document.getElementById('email-send-btn');
  if (btn) btn.disabled = true;
  setEmailModalStatus('Sending report...', 'info');
  vscode.postMessage(Object.assign({type:'email_report', job_id: currentJobId}, settings));
}

function setEmailModalStatus(text, level) {
  var el = document.getElementById('email-modal-status');
  if (!el) return;
  el.textContent = text;
  el.className = 'email-modal-status ems-' + (level || 'info');
}

function clearEmailModalStatus() {
  var el = document.getElementById('email-modal-status');
  if (el) { el.textContent = ''; el.className = 'email-modal-status'; el.style.display = 'none'; }
}

// ── Wire all event listeners ──────────────────────────────────────────────────
document.getElementById('llm-select-mini').addEventListener('change', autoApplySettings);
document.getElementById('mode-select').addEventListener('change', autoApplySettings);
document.getElementById('rpt-save-btn').addEventListener('click', function() {
  if (!currentJobId) return;
  vscode.postMessage({ type: 'save_report', job_id: currentJobId });
});
document.getElementById('rpt-email-btn').addEventListener('click', function() {
  openEmailModal();
});
// Email modal controls
document.getElementById('email-close-btn').addEventListener('click', closeEmailModal);
document.getElementById('email-overlay').addEventListener('click', function(e) {
  if (e.target === this) closeEmailModal();
});
// Auth modal controls
document.getElementById('auth-close-btn').addEventListener('click', closeDashAuthModal);
document.getElementById('auth-overlay').addEventListener('click', function(e) {
  if (e.target === this) closeDashAuthModal();
});
document.getElementById('auth-pass').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') dashSubmitAuth();
});
document.getElementById('email-provider').addEventListener('change', updateEmailProviderUI);
document.getElementById('email-test-btn').addEventListener('click', sendTestEmail);
document.getElementById('email-send-btn').addEventListener('click', sendEmailReport);
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


<!-- Provider Management Modal -->
<div id="sh-provider-modal" class="provider-modal" onclick="shCloseProviderModal()">
  <div class="provider-modal-content" onclick="event.stopPropagation()">
    <div class="provider-modal-header">🔑 Manage LLM Providers</div>

    <div class="provider-list" id="sh-provider-list">
      <!-- Populated by JavaScript -->
    </div>

    <div class="provider-modal-footer">
      <button class="modal-btn close" onclick="shCloseProviderModal()">Close</button>
    </div>
  </div>
</div>

${getSharedHeaderJS()}
</script>
</div>
</body>
</html>`;
}
