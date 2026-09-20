/**
 * Kifayat Workflow & Observability Visualizer
 * Real-time node-based execution graph, token accounting charts,
 * interactive node inspection, and request execution timeline.
 */

class KifayatWorkflowVisualizer {
  constructor() {
    this.activeRequestId = null;
    this.selectedNodeId = "semantic_cache";
    this.currentTrace = null;
    this.filterType = null;
    this.searchQuery = "";
    this.tokenRange = 10;
    this.refreshTimer = null;
    this.init();
  }

  init() {
    this.bindEvents();
    this.loadData();
    // Auto-refresh when tab is visible
    this.refreshTimer = setInterval(() => {
      const panel = document.getElementById("workflowPanel");
      if (panel && panel.classList.contains("active")) {
        this.loadData(false);
      }
    }, 4000);
  }

  bindEvents() {
    // Range selector for token chart
    const rangeBtns = document.querySelectorAll(".token-range-btn");
    rangeBtns.forEach(btn => {
      btn.addEventListener("click", (e) => {
        rangeBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.tokenRange = parseInt(btn.dataset.range, 10) || 10;
        this.renderTokenChart();
      });
    });

    // Request filter dropdown & search input
    const filterSelect = document.getElementById("workflowFilterSelect");
    if (filterSelect) {
      filterSelect.addEventListener("change", (e) => {
        this.filterType = e.target.value || null;
        this.loadRequestsList();
      });
    }

    const searchInput = document.getElementById("workflowSearchInput");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.searchQuery = e.target.value.trim();
        this.loadRequestsList();
      });
    }

    // Workflow node click inspection
    const workflowNodes = document.querySelectorAll(".wf-node");
    workflowNodes.forEach(node => {
      node.addEventListener("click", () => {
        workflowNodes.forEach(n => n.classList.remove("selected"));
        node.classList.add("selected");
        this.selectedNodeId = node.dataset.nodeId;
        this.renderNodeDetails();
      });
    });

    // Close node details modal/drawer
    const closeBtn = document.getElementById("closeNodeDrawerBtn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        const drawer = document.getElementById("nodeDetailsDrawer");
        if (drawer) drawer.style.display = "none";
      });
    }
  }

  async loadData(showLoading = true) {
    try {
      await Promise.all([
        this.loadSummary(),
        this.loadTokenSeries(),
        this.loadRequestsList()
      ]);
    } catch (err) {
      console.error("Failed to load workflow data:", err);
    }
  }

  async loadSummary() {
    try {
      const res = await fetch("/api/analytics/summary");
      if (!res.ok) return;
      const data = await res.json();
      this.renderSummaryCards(data);
      this.renderDistributionChart(data.repair_distribution);
      this.renderModelUsageChart(data.model_usage);
    } catch (e) {
      console.warn("Summary fetch error:", e);
    }
  }

  renderSummaryCards(data) {
    const el = (id) => document.getElementById(id);
    if (el("wfTotalSaved")) el("wfTotalSaved").textContent = (data.total_tokens_saved || 0).toLocaleString();
    if (el("wfTokensActual")) el("wfTokensActual").textContent = (data.tokens_saved_actual || 0).toLocaleString() + " actual";
    if (el("wfTokensEst")) el("wfTokensEst").textContent = (data.tokens_saved_estimated || 0).toLocaleString() + " estimated";
    if (el("wfTotalUsed")) el("wfTotalUsed").textContent = (data.total_tokens_used || 0).toLocaleString();
    if (el("wfSavingsPct")) el("wfSavingsPct").textContent = (data.token_savings_pct || 0).toFixed(1) + "%";
    if (el("wfCallsAvoided")) el("wfCallsAvoided").textContent = data.llm_calls_avoided || 0;
    if (el("wfHitRate")) el("wfHitRate").textContent = ((data.cache_hit_rate || 0) * 100).toFixed(1) + "%";
    if (el("wfContextReduction")) el("wfContextReduction").textContent = (data.context_reduction_pct || 0).toFixed(1) + "%";
    if (el("wfCostSaved")) el("wfCostSaved").textContent = "$" + (data.total_cost_saved_usd || 0).toFixed(4);
  }

  async loadTokenSeries() {
    try {
      const res = await fetch(`/api/analytics/token-savings?limit=${this.tokenRange}`);
      if (!res.ok) return;
      const data = await res.json();
      this.tokenSeriesData = data.series || [];
      this.renderTokenChart();
    } catch (e) {
      console.warn("Token series fetch error:", e);
    }
  }

  renderTokenChart() {
    const canvas = document.getElementById("tokensChartCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width = canvas.parentElement.clientWidth || 550;
    const height = canvas.height = 200;

    ctx.clearRect(0, 0, width, height);
    const series = this.tokenSeriesData || [];
    if (series.length === 0) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "13px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No request token telemetry yet. Ask questions in Chat Demo!", width / 2, height / 2);
      return;
    }

    const maxVal = Math.max(...series.map(s => Math.max(s.tokens_used || 0, s.tokens_saved || 0)), 500);
    const padding = { top: 25, right: 20, bottom: 35, left: 45 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    // Grid lines
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      const val = Math.round(maxVal - (maxVal / 4) * i);
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px Inter, sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(val.toString(), padding.left - 8, y + 3);
    }

    const barGroupW = chartW / series.length;
    const barW = Math.min(Math.max(barGroupW * 0.35, 6), 18);

    series.forEach((d, i) => {
      const xCenter = padding.left + barGroupW * i + barGroupW / 2;
      const hUsed = (d.tokens_used / maxVal) * chartH;
      const hSaved = (d.tokens_saved / maxVal) * chartH;

      // Used Bar (Indigo)
      ctx.fillStyle = "#6366f1";
      ctx.fillRect(xCenter - barW - 2, padding.top + chartH - hUsed, barW, hUsed);

      // Saved Bar (Emerald)
      ctx.fillStyle = "#10b981";
      ctx.fillRect(xCenter + 2, padding.top + chartH - hSaved, barW, hSaved);

      // X labels
      if (series.length <= 15 || i % Math.ceil(series.length / 10) === 0) {
        ctx.fillStyle = "#64748b";
        ctx.font = "9px Inter, sans-serif";
        ctx.textAlign = "center";
        const label = "#" + (i + 1);
        ctx.fillText(label, xCenter, height - 12);
      }
    });

    // Legend
    ctx.fillStyle = "#6366f1";
    ctx.fillRect(width - 160, 8, 10, 10);
    ctx.fillStyle = "#475569";
    ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("Used", width - 145, 17);

    ctx.fillStyle = "#10b981";
    ctx.fillRect(width - 95, 8, 10, 10);
    ctx.fillText("Saved", width - 80, 17);
  }

  renderDistributionChart(dist) {
    const canvas = document.getElementById("distributionChartCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width = canvas.parentElement.clientWidth || 280;
    const height = canvas.height = 200;
    ctx.clearRect(0, 0, width, height);

    if (!dist) return;
    const items = [
      { label: "Cache Hit", count: dist.cache_hit || 0, color: "#10b981" },
      { label: "Rung 1 (Cheap)", count: dist.rung_1_cheap || 0, color: "#6366f1" },
      { label: "Rung 2 (Rescue)", count: dist.rung_2_rescue || 0, color: "#f59e0b" },
      { label: "Rung 3 (Strong)", count: dist.rung_3_strong || 0, color: "#ef4444" }
    ];

    const total = items.reduce((acc, item) => acc + item.count, 0);
    const centerX = width / 2;
    const centerY = height / 2 - 10;
    const radius = 55;
    const innerRadius = 35;

    if (total === 0) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "12px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No requests recorded", centerX, centerY);
      return;
    }

    let startAngle = -Math.PI / 2;
    items.forEach(item => {
      if (item.count === 0) return;
      const sliceAngle = (item.count / total) * 2 * Math.PI;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
      ctx.arc(centerX, centerY, innerRadius, startAngle + sliceAngle, startAngle, true);
      ctx.closePath();
      ctx.fillStyle = item.color;
      ctx.fill();
      startAngle += sliceAngle;
    });

    // Center text
    ctx.fillStyle = "#0f172a";
    ctx.font = "bold 14px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(total.toString(), centerX, centerY + 5);

    // Legend
    let legY = height - 35;
    ctx.font = "10px Inter, sans-serif";
    items.forEach((item, idx) => {
      const legX = 15 + (idx % 2) * 130;
      const rowY = legY + Math.floor(idx / 2) * 16;
      ctx.fillStyle = item.color;
      ctx.fillRect(legX, rowY - 8, 8, 8);
      ctx.fillStyle = "#475569";
      ctx.textAlign = "left";
      ctx.fillText(`${item.label}: ${item.count}`, legX + 12, rowY);
    });
  }

  renderModelUsageChart(usage) {
    const canvas = document.getElementById("modelUsageChartCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width = canvas.parentElement.clientWidth || 280;
    const height = canvas.height = 200;
    ctx.clearRect(0, 0, width, height);

    if (!usage) return;
    const models = [
      { name: "Cheap Model", calls: usage.cheap_model_calls || 0, color: "#6366f1" },
      { name: "Strong Model", calls: usage.strong_model_calls || 0, color: "#f43f5e" },
      { name: "Judge Calls", calls: usage.judge_calls || 0, color: "#8b5cf6" },
      { name: "Embedding", calls: usage.embedding_calls || 0, color: "#06b6d4" }
    ];

    const maxCalls = Math.max(...models.map(m => m.calls), 5);
    const startY = 30;
    const barHeight = 18;
    const spacing = 38;

    models.forEach((m, idx) => {
      const y = startY + idx * spacing;
      ctx.fillStyle = "#475569";
      ctx.font = "11px Inter, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(m.name, 15, y - 5);

      ctx.textAlign = "right";
      ctx.fillText(m.calls.toString(), width - 15, y - 5);

      // Background track
      ctx.fillStyle = "#f1f5f9";
      ctx.fillRect(15, y, width - 30, barHeight);

      // Bar fill
      const barW = ((m.calls / maxCalls) * (width - 30));
      ctx.fillStyle = m.color;
      ctx.fillRect(15, y, barW, barHeight);
    });
  }

  async loadRequestsList() {
    try {
      let url = `/api/analytics/requests?limit=40`;
      if (this.filterType) url += `&filter_type=${encodeURIComponent(this.filterType)}`;
      if (this.searchQuery) url += `&search_id=${encodeURIComponent(this.searchQuery)}`;

      const res = await fetch(url);
      if (!res.ok) return;
      const logs = await res.json();
      this.renderRequestsTable(logs);

      if (logs.length > 0 && !this.activeRequestId) {
        this.selectRequest(logs[0].request_id);
      }
    } catch (e) {
      console.warn("Requests list fetch error:", e);
    }
  }

  renderRequestsTable(logs) {
    const tbody = document.getElementById("wfRequestsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#94a3b8; padding: 2rem;">No matching requests found.</td></tr>`;
      return;
    }

    logs.forEach(log => {
      const tr = document.createElement("tr");
      tr.style.cursor = "pointer";
      if (log.request_id === this.activeRequestId) {
        tr.classList.add("selected-row");
      }

      const isHit = log.cache_hit === 1 || log.cache_hit === true;
      const cacheBadge = isHit
        ? `<span class="badge badge-success">HIT (0 tokens)</span>`
        : `<span class="badge badge-neutral">MISS</span>`;

      const rungBadge = isHit
        ? `<span class="badge badge-info">Rung 0 Cache</span>`
        : log.rung === 1
        ? `<span class="badge badge-info">Rung 1 Cheap</span>`
        : log.rung === 2
        ? `<span class="badge badge-warning">Rung 2 Rescue</span>`
        : `<span class="badge badge-danger">Rung 3 Strong</span>`;

      tr.innerHTML = `
        <td style="font-family: monospace; font-weight: 600; color: var(--brand-600);">${log.request_id}</td>
        <td>${cacheBadge}</td>
        <td>${rungBadge}</td>
        <td><strong>${(log.tokens_saved || 0).toLocaleString()}</strong></td>
        <td>${log.latency_ms ? log.latency_ms.toFixed(1) + "ms" : "-"}</td>
        <td style="color: #10b981; font-weight: 600;">${(log.saving_pct || 0).toFixed(1)}%</td>
        <td style="font-size: 0.75rem; color: #64748b;">${new Date(log.timestamp).toLocaleTimeString()}</td>
      `;

      tr.addEventListener("click", () => {
        document.querySelectorAll("#wfRequestsTableBody tr").forEach(r => r.classList.remove("selected-row"));
        tr.classList.add("selected-row");
        this.selectRequest(log.request_id);
      });

      tbody.appendChild(tr);
    });
  }

  async selectRequest(requestId) {
    this.activeRequestId = requestId;
    const reqDisplay = document.getElementById("activeReqIdDisplay");
    if (reqDisplay) reqDisplay.textContent = requestId;

    try {
      const res = await fetch(`/api/analytics/request/${requestId}`);
      if (!res.ok) return;
      const reqDetail = await res.json();
      this.currentTrace = reqDetail;
      this.updateWorkflowNodes(reqDetail);
      this.renderTimeline(reqDetail.timeline || []);
      this.renderNodeDetails();
    } catch (e) {
      console.warn("Failed to load request detail:", e);
    }
  }

  updateWorkflowNodes(trace) {
    const states = trace.node_states || {};
    const nodes = document.querySelectorAll(".wf-node");

    nodes.forEach(node => {
      const nodeId = node.dataset.nodeId;
      const statusBadge = node.querySelector(".wf-node-status");
      const state = states[nodeId] || (trace.cache_hit && nodeId.startsWith("cheap") ? "SKIPPED" : "WAITING");

      // Clear existing state classes
      node.classList.remove("state-waiting", "state-running", "state-completed", "state-skipped", "state-failed", "state-cache-hit");

      if (state === "CACHE HIT") {
        node.classList.add("state-cache-hit");
        if (statusBadge) statusBadge.textContent = "⚡ CACHE HIT";
      } else if (state === "COMPLETED") {
        node.classList.add("state-completed");
        if (statusBadge) statusBadge.textContent = "✓ COMPLETED";
      } else if (state === "SKIPPED") {
        node.classList.add("state-skipped");
        if (statusBadge) statusBadge.textContent = "○ SKIPPED";
      } else if (state === "FAILED") {
        node.classList.add("state-failed");
        if (statusBadge) statusBadge.textContent = "✕ FAILED";
      } else if (state === "RUNNING") {
        node.classList.add("state-running");
        if (statusBadge) statusBadge.textContent = "⏳ RUNNING";
      } else {
        node.classList.add("state-waiting");
        if (statusBadge) statusBadge.textContent = "WAITING";
      }
    });
  }

  renderTimeline(timeline) {
    const container = document.getElementById("wfTimelineContainer");
    if (!container) return;
    container.innerHTML = "";

    if (!timeline || timeline.length === 0) {
      container.innerHTML = `<div style="color: #94a3b8; font-size: 0.85rem; padding: 1rem;">No granular execution steps recorded for this request.</div>`;
      return;
    }

    timeline.forEach(step => {
      const item = document.createElement("div");
      item.className = "timeline-item";

      const detailsStr = step.details && Object.keys(step.details).length > 0
        ? `<div class="timeline-details">${JSON.stringify(step.details)}</div>`
        : "";

      item.innerHTML = `
        <div class="timeline-dot"></div>
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="timeline-event">${step.event}</span>
            <span class="timeline-time">${step.offset_ms ? "+" + step.offset_ms + "ms" : step.timestamp}</span>
          </div>
          <div class="timeline-comp">Component: <code>${step.component}</code></div>
          ${detailsStr}
        </div>
      `;
      container.appendChild(item);
    });
  }

  renderNodeDetails() {
    const drawer = document.getElementById("nodeDetailsDrawer");
    const titleEl = document.getElementById("nodeDrawerTitle");
    const contentEl = document.getElementById("nodeDrawerContent");
    if (!drawer || !titleEl || !contentEl) return;

    drawer.style.display = "block";
    const nodeId = this.selectedNodeId;
    titleEl.textContent = "Node Inspection: " + nodeId.toUpperCase();

    const trace = this.currentTrace || {};
    const details = (trace.node_details && trace.node_details[nodeId]) || {};
    const state = (trace.node_states && trace.node_states[nodeId]) || "WAITING";

    let html = `
      <div style="margin-bottom: 0.75rem;">
        <strong>Status:</strong> <span class="badge badge-info">${state}</span>
      </div>
    `;

    if (nodeId === "semantic_cache") {
      html += `
        <div class="detail-kv"><span>Status:</span> <strong>${trace.cache_hit ? "CACHE HIT" : "CACHE MISS"}</strong></div>
        <div class="detail-kv"><span>Similarity:</span> <strong>${details.similarity !== undefined ? details.similarity : (trace.similarity || "N/A")}</strong></div>
        <div class="detail-kv"><span>Configured Threshold:</span> <strong>${details.threshold || "0.90"}</strong></div>
        <div class="detail-kv"><span>Lookup Latency:</span> <strong>${details.lookup_ms ? details.lookup_ms + " ms" : "Fast Local Vector Cosine"}</strong></div>
        <div class="detail-kv"><span>Tokens Saved:</span> <strong>${trace.cache_hit ? (trace.tokens_saved || 0) : 0}</strong></div>
        <div class="detail-kv"><span>LLM Calls Avoided:</span> <strong>${trace.cache_hit ? 1 : 0}</strong></div>
      `;
    } else if (nodeId === "cheap_model") {
      html += `
        <div class="detail-kv"><span>Role:</span> <strong>CHEAP_MODEL_ID</strong></div>
        <div class="detail-kv"><span>Configured Model:</span> <code>${details.model || trace.model_id || "meta/llama-3.2-11b-vision-instruct"}</code></div>
        <div class="detail-kv"><span>Tokens Used:</span> <strong>${trace.input_tokens || 0} in / ${trace.output_tokens || 0} out</strong></div>
        <div class="detail-kv"><span>Execution Rung:</span> <strong>Rung ${trace.rung || 1}</strong></div>
      `;
    } else if (nodeId === "judge" || nodeId === "judge_rung2") {
      html += `
        <div class="detail-kv"><span>Automated Judge:</span> <strong>Llama-3.2 Structured Verifier</strong></div>
        <div class="detail-kv"><span>Judge Score:</span> <strong>${trace.judge_score || 5} / 5</strong></div>
        <div class="detail-kv"><span>Verdict:</span> <em>"${trace.judge_verdict || "Complies with official handbook guidelines."}"</em></div>
      `;
    } else if (nodeId === "async_compaction") {
      html += `
        <div class="detail-kv"><span>Compaction State:</span> <strong>${details.status || "IDLE / QUEUED"}</strong></div>
        <div class="detail-kv"><span>Worker:</span> <strong>LocalCompactionQueue (Background Async Worker)</strong></div>
        <div class="detail-kv"><span>Client Delay:</span> <strong>0ms (Fully Non-Blocking)</strong></div>
      `;
    } else {
      html += `
        <div style="font-size: 0.85rem; color: #64748b;">
          ${Object.keys(details).length > 0 ? `<pre style="background:#f8fafc; padding:0.5rem; border-radius:4px;">${JSON.stringify(details, null, 2)}</pre>` : "Execution metrics recorded successfully for this node."}
        </div>
      `;
    }

    contentEl.innerHTML = html;
  }

  handleWorkflowStepEvent(data) {
    // Called when SSE delivers real-time workflow event
    if (!data || !data.node) return;
    const node = document.querySelector(`.wf-node[data-node-id="${data.node}"]`);
    if (node) {
      node.classList.remove("state-waiting", "state-running", "state-completed", "state-skipped", "state-failed", "state-cache-hit");
      const badge = node.querySelector(".wf-node-status");
      if (data.state === "CACHE HIT") {
        node.classList.add("state-cache-hit");
        if (badge) badge.textContent = "⚡ CACHE HIT";
      } else if (data.state === "COMPLETED") {
        node.classList.add("state-completed");
        if (badge) badge.textContent = "✓ COMPLETED";
      } else if (data.state === "RUNNING") {
        node.classList.add("state-running");
        if (badge) badge.textContent = "⏳ RUNNING";
      }
    }
  }
}

// Instantiate visualizer when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.kifayatWorkflow = new KifayatWorkflowVisualizer();
});
