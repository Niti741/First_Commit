let currentSessionId = localStorage.getItem("kifayat_session_id") || "sess-" + Math.random().toString(36).substring(2, 10);
localStorage.setItem("kifayat_session_id", currentSessionId);

/* ==========================================================================
   CANVAS ARTIFACT SANDBOX (Claude / Canvas style)
   ========================================================================== */
const CanvasUI = {
  drawerEl: null,
  receiptEl: null,
  tabShowReceiptBtn: null,
  tabShowCanvasBtn: null,
  activeDot: null,
  emptyStateEl: null,
  titleEl: null,
  langEl: null,
  previewFrame: null,
  codeContainer: null,
  codeContent: null,
  tabPreviewBtn: null,
  tabCodeBtn: null,
  copyBtn: null,
  closeBtn: null,
  expandBtn: null,
  loadDemoBtn: null,
  currentCode: "",
  currentLang: "",

  init() {
    this.drawerEl = document.getElementById("canvasDrawer");
    this.receiptEl = document.getElementById("receiptContainer");
    this.tabShowReceiptBtn = document.getElementById("tabShowReceipt");
    this.tabShowCanvasBtn = document.getElementById("tabShowCanvas");
    this.activeDot = document.getElementById("canvasActiveDot");
    this.emptyStateEl = document.getElementById("canvasEmptyState");
    this.titleEl = document.getElementById("canvasTitle");
    this.langEl = document.getElementById("canvasLang");
    this.previewFrame = document.getElementById("canvasPreviewFrame");
    this.codeContainer = document.getElementById("canvasCodeContainer");
    this.codeContent = document.getElementById("canvasCodeContent");
    this.tabPreviewBtn = document.getElementById("canvasTabPreview");
    this.tabCodeBtn = document.getElementById("canvasTabCode");
    this.copyBtn = document.getElementById("canvasCopyBtn");
    this.closeBtn = document.getElementById("canvasCloseBtn");
    this.expandBtn = document.getElementById("canvasExpandBtn");
    this.loadDemoBtn = document.getElementById("canvasLoadDemoBtn");

    // Header switcher tabs
    if (this.tabShowReceiptBtn) {
      this.tabShowReceiptBtn.addEventListener("click", () => this.switchToReceipt());
    }
    if (this.tabShowCanvasBtn) {
      this.tabShowCanvasBtn.addEventListener("click", () => this.switchToCanvas());
    }

    // Header canvas button
    const openHeaderBtn = document.getElementById("openCanvasHeaderBtn");
    if (openHeaderBtn) {
      openHeaderBtn.addEventListener("click", () => this.switchToCanvas());
    }

    if (this.closeBtn) {
      this.closeBtn.addEventListener("click", () => this.switchToReceipt());
    }

    if (this.expandBtn) {
      this.expandBtn.addEventListener("click", () => {
        if (this.drawerEl) {
          const isExpanded = this.drawerEl.classList.toggle("expanded");
          this.expandBtn.textContent = isExpanded ? "🗗" : "⛶";
          this.expandBtn.title = isExpanded ? "Restore" : "Expand Fullscreen";
        }
      });
    }

    if (this.loadDemoBtn) {
      this.loadDemoBtn.addEventListener("click", () => this.loadDemo());
    }

    if (this.tabPreviewBtn) {
      this.tabPreviewBtn.addEventListener("click", () => this.showTab("preview"));
    }
    if (this.tabCodeBtn) {
      this.tabCodeBtn.addEventListener("click", () => this.showTab("code"));
    }

    if (this.copyBtn) {
      this.copyBtn.addEventListener("click", () => {
        if (this.currentCode) {
          navigator.clipboard.writeText(this.currentCode).then(() => {
            const original = this.copyBtn.textContent;
            this.copyBtn.textContent = "✓";
            setTimeout(() => (this.copyBtn.textContent = original), 1800);
          });
        }
      });
    }

    // Global listener for artifact badges in messages
    document.addEventListener("click", (e) => {
      const badgeBtn = e.target.closest(".artifact-badge-btn");
      if (badgeBtn) {
        const lang = badgeBtn.getAttribute("data-lang") || "html";
        const code = decodeURIComponent(badgeBtn.getAttribute("data-code") || "");
        this.open(code, lang, `Live ${lang.toUpperCase()} Artifact`);
      }
    });
  },

  switchToReceipt() {
    if (this.receiptEl) this.receiptEl.style.display = "flex";
    if (this.drawerEl) this.drawerEl.style.display = "none";
    if (this.tabShowReceiptBtn) this.tabShowReceiptBtn.classList.add("active");
    if (this.tabShowCanvasBtn) this.tabShowCanvasBtn.classList.remove("active");
  },

  close() {
    this.switchToReceipt();
    this.currentCode = "";
    this.currentLang = "";
    if (this.activeDot) this.activeDot.style.display = "none";
    if (this.emptyStateEl) this.emptyStateEl.style.display = "flex";
    if (this.previewFrame) {
      this.previewFrame.style.display = "none";
      this.previewFrame.srcdoc = "";
    }
    if (this.codeContainer) this.codeContainer.style.display = "none";
  },

  switchToCanvas() {
    if (this.receiptEl) this.receiptEl.style.display = "none";
    if (this.drawerEl) this.drawerEl.style.display = "flex";
    if (this.tabShowReceiptBtn) this.tabShowReceiptBtn.classList.remove("active");
    if (this.tabShowCanvasBtn) this.tabShowCanvasBtn.classList.add("active");

    if (!this.currentCode && this.emptyStateEl) {
      this.emptyStateEl.style.display = "flex";
      if (this.previewFrame) this.previewFrame.style.display = "none";
      if (this.codeContainer) this.codeContainer.style.display = "none";
    }
  },

  open(code, lang = "html", title = "Interactive Artifact Preview") {
    this.currentCode = code;
    this.currentLang = lang.toLowerCase();

    if (this.titleEl) this.titleEl.textContent = title;
    if (this.langEl) this.langEl.textContent = lang.toUpperCase() + " Sandbox";
    if (this.codeContent) this.codeContent.textContent = code;
    if (this.emptyStateEl) this.emptyStateEl.style.display = "none";
    if (this.activeDot) this.activeDot.style.display = "inline-block";

    this.switchToCanvas();
    this.renderPreview(code, this.currentLang);
    this.showTab("preview");
  },

  loadDemo() {
    const demoCode = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body {
      margin: 0; min-height: 90vh; display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      background: #0f172a; font-family: -apple-system, sans-serif; color: #f8fafc;
    }
    .demo-card {
      background: #1e293b; padding: 2.2rem; border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.12); text-align: center;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5); width: 280px;
    }
    .badge {
      display: inline-block; padding: 0.25rem 0.65rem; border-radius: 999px;
      background: linear-gradient(135deg, #6366f1, #10b981); font-size: 0.72rem;
      font-weight: 700; text-transform: uppercase; margin-bottom: 0.75rem;
    }
    .counter { font-size: 3.5rem; font-weight: 800; color: #38bdf8; margin: 0.8rem 0; }
    .btn-row { display: flex; gap: 0.6rem; justify-content: center; }
    button {
      padding: 0.6rem 1rem; border: none; border-radius: 8px; font-weight: 700;
      cursor: pointer; transition: transform 0.15s;
    }
    button:hover { transform: scale(1.08); }
    .dec { background: #ef4444; color: #fff; }
    .inc { background: #10b981; color: #fff; }
  </style>
</head>
<body>
  <div class="demo-card">
    <span class="badge">Canvas Live</span>
    <h3 style="margin:0;">Interactive Counter</h3>
    <div class="counter" id="num">0</div>
    <div class="btn-row">
      <button class="dec" onclick="add(-1)">-1</button>
      <button class="inc" onclick="add(1)">+1</button>
    </div>
  </div>
  <script>
    let c = 0;
    function add(d) {
      c += d;
      const el = document.getElementById('num');
      el.textContent = c;
      el.style.color = c > 0 ? '#10b981' : c < 0 ? '#ef4444' : '#38bdf8';
    }
  <\/script>
</body>
</html>`;
    this.open(demoCode, "html", "Interactive Demo Widget");
  },

  showTab(tab) {
    if (this.emptyStateEl && !this.currentCode) return;
    if (tab === "preview") {
      if (this.previewFrame) this.previewFrame.style.display = "block";
      if (this.codeContainer) this.codeContainer.style.display = "none";
      if (this.tabPreviewBtn) {
        this.tabPreviewBtn.style.background = "#eef2ff";
        this.tabPreviewBtn.style.color = "#4f46e5";
        this.tabPreviewBtn.style.borderColor = "#c7d2fe";
      }
      if (this.tabCodeBtn) {
        this.tabCodeBtn.style.background = "";
        this.tabCodeBtn.style.color = "";
        this.tabCodeBtn.style.borderColor = "";
      }
    } else {
      if (this.previewFrame) this.previewFrame.style.display = "none";
      if (this.codeContainer) this.codeContainer.style.display = "block";
      if (this.tabCodeBtn) {
        this.tabCodeBtn.style.background = "#eef2ff";
        this.tabCodeBtn.style.color = "#4f46e5";
        this.tabCodeBtn.style.borderColor = "#c7d2fe";
      }
      if (this.tabPreviewBtn) {
        this.tabPreviewBtn.style.background = "";
        this.tabPreviewBtn.style.color = "";
        this.tabPreviewBtn.style.borderColor = "";
      }
    }
  },

  renderPreview(code, lang) {
    if (!this.previewFrame) return;

    let srcHtml = "";
    if (lang.includes("html") || lang.includes("svg") || lang.includes("xml")) {
      if (code.includes("<!DOCTYPE") || code.includes("<html")) {
        srcHtml = code;
      } else {
        srcHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      margin: 0;
      padding: 2rem;
      background: #f8fafc;
      color: #0f172a;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 90vh;
      box-sizing: border-box;
    }
  </style>
</head>
<body>
  ${code}
</body>
</html>`;
      }
    } else if (lang.includes("javascript") || lang.includes("js")) {
      srcHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: monospace; padding: 1.5rem; background: #0f172a; color: #38bdf8; margin: 0; }
    #log { white-space: pre-wrap; font-size: 0.9rem; line-height: 1.6; }
  </style>
</head>
<body>
  <div id="log">=== JavaScript Artifact Sandbox ===\n</div>
  <script>
    const origLog = console.log;
    const logEl = document.getElementById('log');
    console.log = function(...args) {
      logEl.innerText += args.join(' ') + '\\n';
      origLog.apply(console, args);
    };
    try {
      ${code}
    } catch(err) {
      logEl.innerText += '\\nError: ' + err.message;
      logEl.style.color = '#ef4444';
    }
  <\/script>
</body>
</html>`;
    } else {
      srcHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: monospace; padding: 1.5rem; background: #0f172a; color: #a5f3fc; margin: 0; }
    .header { color: #818cf8; font-weight: bold; margin-bottom: 0.75rem; border-bottom: 1px solid #334155; padding-bottom: 0.4rem; }
    pre { margin: 0; font-size: 0.85rem; line-height: 1.5; color: #e2e8f0; white-space: pre-wrap; }
  </style>
</head>
<body>
  <div class="header">${lang.toUpperCase()} Code Preview</div>
  <pre>${code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
</body>
</html>`;
    }

    this.previewFrame.srcdoc = srcHtml;
  }
};

/* ==========================================================================
   CHAT UI WITH INTERACTIVE ARTIFACTS & A/B BENCHMARK MODE
   ========================================================================== */
const ChatUI = {
  historyEl: null,
  inputEl: null,
  sendBtnEl: null,
  modeSelectEl: null,
  receiptEl: null,
  benchmarkToggleEl: null,
  isGenerating: false,

  init() {
    this.historyEl = document.getElementById("chatHistory");
    this.inputEl = document.getElementById("chatInput");
    this.sendBtnEl = document.getElementById("sendBtn");
    this.modeSelectEl = document.getElementById("gatewayModeSelect");
    this.receiptEl = document.getElementById("receiptContainer");
    this.benchmarkToggleEl = document.getElementById("benchmarkToggle");

    CanvasUI.init();

    if (this.sendBtnEl) {
      this.sendBtnEl.addEventListener("click", () => this.handleSend());
    }
    if (this.inputEl) {
      this.inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.handleSend();
        }
      });
    }

    // Preset query chips
    document.querySelectorAll(".chip-btn[data-query]").forEach(btn => {
      btn.addEventListener("click", () => {
        const text = btn.getAttribute("data-query");
        if (text && this.inputEl) {
          this.inputEl.value = text;
          this.handleSend();
        }
      });
    });

    const newSessBtn = document.getElementById("newSessionBtn");
    if (newSessBtn) {
      newSessBtn.addEventListener("click", () => {
        currentSessionId = "sess-" + Math.random().toString(36).substring(2, 10);
        localStorage.setItem("kifayat_session_id", currentSessionId);
        if (this.historyEl) this.historyEl.innerHTML = "";
        this.renderAssistantMessage(
          "Hello! I am Kifayat AI, your versatile intelligent assistant. Ask me anything—coding, complex reasoning, technical explanations, writing, or general knowledge.",
          null
        );
        this.renderEmptyReceipt();
        CanvasUI.close();
      });
    }

    // Welcome message
    if (this.historyEl && this.historyEl.children.length === 0) {
      this.renderAssistantMessage(
        "Welcome to Kifayat AI! Ask me anything—coding, architecture, complex reasoning, writing, or analysis. Try creating a glowing 3D button or toggle ⚡ A/B Benchmark to compare with raw models.",
        null
      );
    }
  },

  async handleSend() {
    const text = this.inputEl.value.trim();
    if (!text || this.isGenerating) return;

    const isBenchmark = this.benchmarkToggleEl && this.benchmarkToggleEl.checked;
    const mode = this.modeSelectEl ? (this.modeSelectEl.value || "kifayat") : "kifayat";
    this.inputEl.value = "";
    this.isGenerating = true;
    this.sendBtnEl.disabled = true;

    // 1. Render User Bubble
    this.renderUserMessage(text);

    if (isBenchmark) {
      await this.runBenchmarkExecution(text);
    } else {
      await this.runStandardStreamExecution(text, mode);
    }
  },

  async runStandardStreamExecution(text, mode) {
    const assistantBubble = this.createAssistantPlaceholder();
    const textSpan = assistantBubble.querySelector(".msg-text");
    const metaBar = assistantBubble.querySelector(".msg-meta-bar");

    let fullText = "";

    await API.streamChat(
      text,
      currentSessionId,
      mode,
      // On Chunk
      (chunk) => {
        fullText += chunk;
        textSpan.innerHTML = this.formatMarkdown(fullText);
        this.historyEl.scrollTop = this.historyEl.scrollHeight;
      },
      // On Metadata
      (meta) => {
        if (meta.cache_hit) {
          metaBar.innerHTML = `<span class="cache-pill">⚡ Semantic Cache Hit (${Math.round(meta.similarity * 100)}% match)</span>`;
        } else {
          metaBar.innerHTML = `<span class="rung-pill rung-1">Rung 1: Cheap Model</span>`;
        }
      },
      // On Complete
      (completeData) => {
        this.isGenerating = false;
        this.sendBtnEl.disabled = false;
        textSpan.innerHTML = this.formatMarkdown(fullText);
        if (completeData.receipt) {
          this.updateReceipt(completeData.receipt);
          this.updateMessageMeta(metaBar, completeData.receipt, text, fullText);
        }

        // Auto-load interactive artifacts into Canvas
        const codeBlockMatch = fullText.match(/```(html|svg|xml|javascript|js|css)\n([\s\S]*?)```/i);
        if (codeBlockMatch) {
          const lang = codeBlockMatch[1].toLowerCase();
          const code = codeBlockMatch[2].trim();
          CanvasUI.open(code, lang, `Live ${lang.toUpperCase()} Artifact`);
        }

        if (window.DashboardUI) window.DashboardUI.refreshMetrics();
        if (window.kifayatWorkflow) window.kifayatWorkflow.loadData();
      },
      // On Error
      (err) => {
        this.isGenerating = false;
        this.sendBtnEl.disabled = false;
        textSpan.textContent += `\n[Error: ${err}]`;
      }
    );
  },

  async runBenchmarkExecution(text) {
    const assistantBubble = this.createAssistantPlaceholder("A/B Benchmark in Progress (Kifayat vs Unoptimized Raw Model)...");
    const textSpan = assistantBubble.querySelector(".msg-text");
    const metaBar = assistantBubble.querySelector(".msg-meta-bar");

    metaBar.innerHTML = `<span class="rung-pill rung-2">⚡ Running A/B Benchmark Side-by-Side</span>`;

    let kifayatFullText = "";
    let kifayatReceipt = null;
    let baselineReceipt = null;

    // Run Kifayat Stream and Baseline concurrently
    const kifayatPromise = new Promise((resolve) => {
      API.streamChat(
        text,
        currentSessionId,
        "kifayat",
        (chunk) => {
          kifayatFullText += chunk;
          textSpan.innerHTML = `<em>[Streaming Kifayat Solution...]</em><br>` + this.formatMarkdown(kifayatFullText);
          this.historyEl.scrollTop = this.historyEl.scrollHeight;
        },
        null,
        (data) => {
          kifayatReceipt = data.receipt;
          resolve();
        },
        () => resolve()
      );
    });

    const baselinePromise = new Promise((resolve) => {
      API.streamChat(
        text,
        currentSessionId,
        "baseline",
        () => {},
        null,
        (data) => {
          baselineReceipt = data.receipt;
          resolve();
        },
        () => resolve()
      );
    });

    await Promise.all([kifayatPromise, baselinePromise]);

    this.isGenerating = false;
    this.sendBtnEl.disabled = false;

    // Render the Final Dual Comparison Card
    if (kifayatReceipt && baselineReceipt) {
      const activeComputeTokens = Math.max(0, kifayatReceipt.input_tokens - (kifayatReceipt.cache_read_tokens || 0));
      const tokensSaved = Math.max(0, baselineReceipt.input_tokens - activeComputeTokens);
      const tokensSavedPct = baselineReceipt.input_tokens > 0 
        ? Math.max(0, Math.min(99, Math.round((tokensSaved / baselineReceipt.input_tokens) * 100)))
        : 0;
      const costSavedPct = baselineReceipt.cost_usd > 0
        ? Math.max(0, Math.round(((baselineReceipt.cost_usd - kifayatReceipt.cost_usd) / baselineReceipt.cost_usd) * 100))
        : 0;
      const speedup = (baselineReceipt.latency_ms / Math.max(1, kifayatReceipt.latency_ms)).toFixed(1);

      const benchmarkHtml = `
        <div style="margin-bottom: 0.75rem;">${this.formatMarkdown(kifayatFullText)}</div>
        <div class="benchmark-card">
          <div class="benchmark-col">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
              <strong style="color: var(--brand-600);">⚡ Kifayat Gateway</strong>
              <span class="rung-pill rung-${kifayatReceipt.rung || 1}">Rung ${kifayatReceipt.rung === 0 ? "0 (Cache)" : (kifayatReceipt.rung || 1)}</span>
            </div>
            <div class="benchmark-meter"><span>Latency:</span><strong>${kifayatReceipt.latency_ms} ms</strong></div>
            <div class="benchmark-meter"><span>Active Compute:</span><strong style="color:var(--brand-600);">${activeComputeTokens} tokens</strong></div>
            <div class="benchmark-meter"><span>KV Cache Read:</span><strong style="color:var(--success-solid);">${kifayatReceipt.cache_read_tokens || 0} tokens</strong></div>
            <div class="benchmark-meter"><span>Total Prompt:</span><span>${kifayatReceipt.input_tokens} tokens</span></div>
            <div class="benchmark-meter"><span>Output Tokens:</span><strong>${kifayatReceipt.output_tokens}</strong></div>
            <div class="benchmark-meter"><span>Cost:</span><strong>$${kifayatReceipt.cost_usd.toFixed(6)}</strong></div>
            <div class="benchmark-meter"><span>Context Avoided:</span><span style="color:var(--success-solid); font-weight:700;">+${tokensSaved} tokens</span></div>
          </div>
          <div class="benchmark-col">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
              <strong style="color: #64748b;">🐢 Unoptimized Baseline</strong>
              <span style="font-size:0.7rem; background:#f1f5f9; padding:0.1rem 0.4rem; border-radius:4px; color:#475569;">No Gateway</span>
            </div>
            <div class="benchmark-meter"><span>Latency:</span><strong>${baselineReceipt.latency_ms} ms</strong></div>
            <div class="benchmark-meter"><span>Input Tokens:</span><strong>${baselineReceipt.input_tokens} tokens</strong></div>
            <div class="benchmark-meter"><span>Prompt Cache:</span><strong style="color:#ef4444;">0 tokens (0%)</strong></div>
            <div class="benchmark-meter"><span>Compute Load:</span><strong style="color:#ef4444;">100% uncached</strong></div>
            <div class="benchmark-meter"><span>Output Tokens:</span><strong>${baselineReceipt.output_tokens}</strong></div>
            <div class="benchmark-meter"><span>Cost:</span><strong>$${baselineReceipt.cost_usd.toFixed(6)}</strong></div>
            <div class="benchmark-meter"><span>Efficiency:</span><span style="color:#ef4444;">0% saved</span></div>
          </div>
        </div>
        <div style="margin-top:0.6rem; padding:0.5rem 0.85rem; background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25); border-radius:8px; font-size:0.76rem; color:var(--success-solid); font-weight:600; display:flex; justify-content:space-between; flex-wrap:wrap; gap:0.5rem;">
          <span>🎉 Context Savings: +${tokensSaved} tokens (${tokensSavedPct}%)</span>
          <span>💰 Cost Reduction: ${costSavedPct}%</span>
          <span>⚡ Speedup: ${speedup}x faster</span>
        </div>
      `;
      textSpan.innerHTML = benchmarkHtml;
      this.updateReceipt(kifayatReceipt);
      this.updateMessageMeta(metaBar, kifayatReceipt, text, kifayatFullText);
    } else {
      textSpan.innerHTML = this.formatMarkdown(kifayatFullText);
    }

    if (window.DashboardUI) window.DashboardUI.refreshMetrics();
    if (window.kifayatWorkflow) window.kifayatWorkflow.loadData();
  },

  formatMarkdown(text) {
    if (!text) return "";
    
    // Parse fenced code blocks
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    let formatted = text.replace(codeBlockRegex, (match, lang, code) => {
      const safeLang = (lang || 'code').toLowerCase().trim();
      const trimmedCode = code.trim();
      const safeCode = this.escapeHtml(trimmedCode);
      const encoded = encodeURIComponent(trimmedCode);

      const isCanvasRunnable = ["html", "svg", "css", "javascript", "js", "python", "py", "xml"].includes(safeLang);
      const canvasBtn = isCanvasRunnable
        ? `<button class="artifact-badge-btn" data-lang="${safeLang}" data-code="${encoded}">✨ Open in Canvas</button>`
        : "";

      return `<div class="code-block-wrapper" style="position:relative; margin: 0.65rem 0; border-radius:8px; overflow:hidden; border:1px solid #334155;">
        <div style="display:flex; justify-content:space-between; align-items:center; background:#1e293b; color:#94a3b8; padding:0.3rem 0.75rem; font-size:0.72rem; font-family:var(--font-mono);">
          <span>${safeLang.toUpperCase()}</span>
          ${canvasBtn}
        </div>
        <pre style="margin:0; background:#0f172a; color:#f8fafc; padding:0.85rem; overflow-x:auto; font-size:0.8rem; font-family:var(--font-mono); line-height:1.45;"><code>${safeCode}</code></pre>
      </div>`;
    });

    // Simple markdown formatting for inline code and line breaks
    formatted = formatted.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.06); padding:0.15rem 0.35rem; border-radius:4px; font-family:var(--font-mono); font-size:0.85em;">$1</code>');
    formatted = formatted.replace(/\n\n/g, '<br><br>');

    return formatted;
  },

  renderUserMessage(text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "chat-message user";
    msgDiv.innerHTML = `
      <div class="msg-avatar avatar-user" title="You">😎</div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble">${this.escapeHtml(text)}</div>
      </div>
    `;
    this.historyEl.appendChild(msgDiv);
    this.historyEl.scrollTop = this.historyEl.scrollHeight;
  },

  createAssistantPlaceholder(initialText = "Generating...") {
    const msgDiv = document.createElement("div");
    msgDiv.className = "chat-message assistant";
    msgDiv.innerHTML = `
      <div class="msg-avatar avatar-assistant" title="Kifayat AI">
        <svg width="22" height="22" viewBox="0 0 100 100" fill="none">
          <path d="M50 10 L86 30 L50 50 L14 30 Z" fill="#38bdf8" />
          <path d="M14 30 L50 50 L50 90 L14 70 Z" fill="#6366f1" />
          <path d="M50 50 L86 30 L86 70 L50 90 Z" fill="#312e81" />
          <path d="M41 38 L41 64 M41 51 L56 38 M46 47 L58 64" stroke="#ffffff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <div class="msg-content-wrapper" style="width: 100%;">
        <div class="msg-bubble"><span class="msg-text">${this.escapeHtml(initialText)}</span></div>
        <div class="msg-meta-bar"></div>
      </div>
    `;
    this.historyEl.appendChild(msgDiv);
    this.historyEl.scrollTop = this.historyEl.scrollHeight;
    return msgDiv;
  },

  renderAssistantMessage(text, meta) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "chat-message assistant";
    msgDiv.innerHTML = `
      <div class="msg-avatar avatar-assistant" title="Kifayat AI">
        <svg width="22" height="22" viewBox="0 0 100 100" fill="none">
          <path d="M50 10 L86 30 L50 50 L14 30 Z" fill="#38bdf8" />
          <path d="M14 30 L50 50 L50 90 L14 70 Z" fill="#6366f1" />
          <path d="M50 50 L86 30 L86 70 L50 90 Z" fill="#312e81" />
          <path d="M41 38 L41 64 M41 51 L56 38 M46 47 L58 64" stroke="#ffffff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble">${this.formatMarkdown(text)}</div>
      </div>
    `;
    this.historyEl.appendChild(msgDiv);
  },

  updateMessageMeta(metaBar, receipt, question, answer) {
    let pills = [];
    const isConversational = ["GREETING", "CASUAL_CONVERSATION", "GRATITUDE", "FAREWELL", "SIMPLE_CONVERSATION"].includes(receipt.intent);

    if (receipt.cache_hit) {
      pills.push(`<span class="cache-pill">⚡ Semantic Cache (${Math.round((receipt.similarity || 1.0) * 100)}%)</span>`);
    } else if (isConversational) {
      pills.push(`<span class="rung-pill" style="background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0;">💬 ${receipt.intent}</span>`);
      pills.push(`<span class="rung-pill rung-1">Rung 1: Direct</span>`);
    } else {
      if (receipt.intent && receipt.intent !== "UNKNOWN") {
        pills.push(`<span class="rung-pill" style="background:#f8fafc; color:#475569; border:1px solid #cbd5e1;">🎯 ${receipt.intent}</span>`);
      }
      if (receipt.rung === 1) {
        pills.push(`<span class="rung-pill rung-1">Rung 1: Cheap Verified</span>`);
      } else if (receipt.rung === 2) {
        pills.push(`<span class="rung-pill rung-2">Rung 2: Exemplar Rescue</span>`);
      } else {
        pills.push(`<span class="rung-pill rung-3">Rung 3: Strong Fallback</span>`);
      }
    }

    pills.push(`<span>${receipt.latency_ms}ms</span>`);
    if (receipt.saving_pct > 0) {
      pills.push(`<span>Save: ${receipt.saving_pct}%</span>`);
    }
    pills.push(`<button class="chip-btn feedback-btn" style="padding:0.1rem 0.4rem; font-size:0.68rem;" title="Vote helpful for exemplar mining">👍 Helpful</button>`);

    metaBar.innerHTML = pills.join(" ");

    const feedbackBtn = metaBar.querySelector(".feedback-btn");
    if (feedbackBtn) {
      feedbackBtn.addEventListener("click", async () => {
        feedbackBtn.textContent = "✓ Saved";
        feedbackBtn.disabled = true;
        await API.sendFeedback({
          request_id: receipt.request_id,
          question: question,
          answer: answer,
          thumbs_up: true,
          session_id: currentSessionId
        });
      });
    }
  },

  updateReceipt(receipt) {
    if (!this.receiptEl) return;
    const providerBadge = receipt.fallback_used 
      ? `<span style="color:#ef4444; font-weight:600;">${receipt.provider || 'nvidia'} (Fallback Mock)</span>`
      : `<span style="color:var(--success-solid); font-weight:600;">${receipt.provider || 'nvidia'} (Direct Live)</span>`;

    this.receiptEl.innerHTML = `
      <div class="receipt-header">
        <h4>🧾 Kifayat Receipt</h4>
        <span class="code-pill">${receipt.request_id}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Intent</span>
        <span class="val" style="font-weight:700; color:var(--brand-600);">${receipt.intent || "GENERAL"}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Provider</span>
        <span class="val">${providerBadge}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Model Used</span>
        <span class="val">${receipt.model_id}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Repair Rung</span>
        <span class="val">${receipt.rung === 0 ? "0 (Semantic Cache)" : "Rung " + receipt.rung}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Routing Reason</span>
        <span class="val" style="font-size:0.75rem; text-align:right;">${receipt.routing_reason || "Normal Ladder"}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Cache Hit</span>
        <span class="val" style="color: ${receipt.cache_hit ? 'var(--success-solid)' : 'var(--text-muted)'};">
          ${receipt.cache_hit ? "YES (" + Math.round((receipt.similarity || 1) * 100) + "%)" : "NO"}
        </span>
      </div>
      <div class="receipt-divider"></div>
      <div class="receipt-item">
        <span class="label">Input Tokens</span>
        <span class="val">${receipt.input_tokens}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Cache Read Tokens</span>
        <span class="val">${receipt.cache_read_tokens || 0}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Output Tokens</span>
        <span class="val">${receipt.output_tokens}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Tokens Saved</span>
        <span class="val" style="color: var(--success-solid); font-weight:700;">+${receipt.tokens_saved}</span>
      </div>
      <div class="receipt-divider"></div>
      <div class="receipt-item">
        <span class="label">Actual Cost</span>
        <span class="val">$${receipt.cost_usd.toFixed(6)}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Baseline Cost</span>
        <span class="val">$${receipt.baseline_cost_usd.toFixed(6)}</span>
      </div>
      <div class="receipt-item">
        <span class="label">Cost Saved</span>
        <span class="val" style="color: var(--success-solid); font-weight:700;">${receipt.saving_pct}%</span>
      </div>
      <div class="receipt-divider"></div>
      <div class="receipt-item">
        <span class="label">Latency</span>
        <span class="val">${receipt.latency_ms} ms</span>
      </div>
      <div class="receipt-item">
        <span class="label">Judge Score</span>
        <span class="val">${receipt.judge_score || "N/A"}/5</span>
      </div>
      <div class="receipt-item">
        <span class="label">Judge Verdict</span>
        <span class="val" style="font-size:0.75rem; text-align:right;">${receipt.judge_verdict || "Standard"}</span>
      </div>
    `;
  },

  renderEmptyReceipt() {
    if (!this.receiptEl) return;
    this.receiptEl.innerHTML = `
      <div class="receipt-header">
        <h4>🧾 Kifayat Receipt</h4>
      </div>
      <p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 1rem;">
        No queries executed in this session yet. Submit a question to generate a token cost and cache receipt.
      </p>
    `;
  },

  escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
};
