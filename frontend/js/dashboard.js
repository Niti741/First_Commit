const DashboardUI = {
  async init() {
    await this.refreshMetrics();
    this.bindEvents();
  },

  bindEvents() {
    document.getElementById("refreshStatsBtn")?.addEventListener("click", () => this.refreshMetrics());
    document.getElementById("clearCacheBtn")?.addEventListener("click", async () => {
      if (confirm("Clear entire semantic response cache?")) {
        await API.clearCache();
        await this.loadCacheView();
        await this.refreshMetrics();
      }
    });
  },

  async refreshMetrics() {
    try {
      const stats = await API.getDashboardStats();
      const setTxt = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
      };

      setTxt("metricTotalRequests", stats.total_requests || 0);
      setTxt("metricCacheHitRate", Math.round((stats.cache_hit_rate || 0) * 100) + "%");
      setTxt("metricTokensSaved", Number(stats.total_tokens_saved || 0).toLocaleString());
      setTxt("metricCostSaved", "$" + (stats.total_cost_saved_usd || 0).toFixed(3));
      setTxt("metricSavingsPct", (stats.savings_pct || 0).toFixed(1) + "%");
      setTxt("metricAvgLatency", (stats.average_latency_ms || 0).toFixed(0) + "ms");
      setTxt("metricActiveExemplars", stats.active_exemplars || 0);
      setTxt("metricFrozenBlocks", stats.total_blocks_frozen || 0);

      // Cost comparison cards
      setTxt("costActual", "$" + (stats.actual_cost_usd || 0).toFixed(4));
      setTxt("costBaseline", "$" + (stats.baseline_cost_usd || 0).toFixed(4));
      setTxt("costSavings", "$" + ((stats.baseline_cost_usd || 0) - (stats.actual_cost_usd || 0)).toFixed(4));
    } catch (e) {
      console.warn("Could not refresh dashboard metrics:", e);
    }
  },


  async loadRequestsView() {
    try {
      const logs = await API.getRecentRequests(50);
      const tbody = document.getElementById("requestsTableBody");
      if (!tbody) return;
      tbody.innerHTML = "";

      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--text-muted);">No requests logged yet. Ask questions in the Chat Demo tab.</td></tr>`;
        return;
      }

      logs.forEach(log => {
        const tr = document.createElement("tr");
        const cachePill = log.cache_hit 
          ? `<span class="badge-success metric-badge">HIT (${Math.round((log.similarity || 1) * 100)}%)</span>`
          : `<span class="metric-badge" style="background:var(--bg-subtle);">MISS</span>`;
        
        const rungPill = log.rung === 0 ? "Cache" : `Rung ${log.rung}`;
        const costStr = "$" + Number(log.cost_usd).toFixed(6);

        tr.innerHTML = `
          <td><span class="code-pill">${log.request_id}</span></td>
          <td>${log.mode}</td>
          <td>${log.model_id}</td>
          <td>${rungPill}</td>
          <td>${cachePill}</td>
          <td>${log.input_tokens + log.output_tokens}</td>
          <td>${costStr}</td>
          <td>${log.latency_ms} ms</td>
          <td><span class="badge-info metric-badge">${log.saving_pct}%</span></td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.error("Failed to load request logs:", e);
    }
  },

  async loadMemoryView() {
    try {
      const data = await API.getMemory();
      const sessionsList = document.getElementById("memorySessionsList");
      const detailsBox = document.getElementById("memoryDetailsContainer");
      if (!sessionsList) return;

      sessionsList.innerHTML = "";
      if (!data.sessions || data.sessions.length === 0) {
        sessionsList.innerHTML = `<div style="font-size:0.85rem; color:var(--text-muted); padding:1rem;">No conversation sessions stored.</div>`;
        return;
      }

      data.sessions.forEach(s => {
        const item = document.createElement("div");
        item.className = "memory-block-card";
        item.style.cursor = "pointer";
        item.innerHTML = `
          <div class="memory-block-header">
            <span>Session: ${s.session_id.substring(0, 16)}</span>
            <span class="code-pill">${s.turn_count} turns</span>
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted);">Updated: ${new Date(s.updated_at).toLocaleTimeString()}</div>
        `;
        item.addEventListener("click", async () => {
          const detail = await API.getMemory(s.session_id);
          this.renderSessionDetail(detail);
        });
        sessionsList.appendChild(item);
      });

      // Load first session by default
      if (data.sessions.length > 0) {
        const first = await API.getMemory(data.sessions[0].session_id);
        this.renderSessionDetail(first);
      }
    } catch (e) {
      console.error("Failed to load memory view:", e);
    }
  },

  renderSessionDetail(session) {
    const box = document.getElementById("memoryDetailsContainer");
    if (!box) return;

    let frozenHtml = "";
    if (session.frozen_blocks && session.frozen_blocks.length > 0) {
      frozenHtml = session.frozen_blocks.map(b => `
        <div class="memory-block-card" style="border-left: 3px solid var(--brand-600);">
          <div class="memory-block-header">
            <span>🧊 Frozen Block #${b.block_id} (Turns ${b.start_turn}–${b.end_turn})</span>
            <span class="badge-success metric-badge">IMMUTABLE</span>
          </div>
          <p style="font-size:0.8rem; margin-top:0.25rem;">${b.summary}</p>
        </div>
      `).join("");
    } else {
      frozenHtml = `<p style="font-size:0.8rem; color:var(--text-muted);">No frozen blocks formed yet (forms after raw window exceeds threshold).</p>`;
    }

    let rawHtml = "";
    if (session.raw_turns && session.raw_turns.length > 0) {
      rawHtml = session.raw_turns.map(t => `
        <div class="memory-block-card" style="border-left: 3px solid var(--info-solid);">
          <div class="memory-block-header">
            <span>Turn #${t.turn_index}</span>
            <span class="code-pill">VERBATIM RAW</span>
          </div>
          <div style="font-size:0.78rem;"><strong>User:</strong> ${t.user}</div>
          <div style="font-size:0.78rem; margin-top:0.2rem;"><strong>Assistant:</strong> ${t.assistant.substring(0, 120)}...</div>
        </div>
      `).join("");
    } else {
      rawHtml = `<p style="font-size:0.8rem; color:var(--text-muted);">No recent raw turns.</p>`;
    }

    box.innerHTML = `
      <h4 style="margin-bottom:0.75rem; font-size:0.95rem;">Session: ${session.session_id}</h4>
      <div style="margin-bottom:1.25rem;">
        <h5 style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.5rem;">Frozen Blocks (Level 0 Summaries)</h5>
        ${frozenHtml}
      </div>
      <div>
        <h5 style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.5rem;">Recent Raw Window (Verbatim)</h5>
        ${rawHtml}
      </div>
    `;
  },

  async loadCacheView() {
    try {
      const stats = await API.getCacheStats();
      document.getElementById("cacheEntriesCount").textContent = stats.entries_stored;
      document.getElementById("cacheLifetimeHits").textContent = stats.lifetime_hits;
      document.getElementById("cacheThresholdDisplay").textContent = stats.threshold;
    } catch (e) {
      console.error("Failed to load cache view:", e);
    }
  },

  async loadExemplarsView() {
    try {
      const exemplars = await API.getExemplars();
      const tbody = document.getElementById("exemplarsTableBody");
      if (!tbody) return;
      tbody.innerHTML = "";

      exemplars.forEach(ex => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><span class="code-pill">${ex.id}</span></td>
          <td><strong>${ex.question}</strong></td>
          <td><span class="badge-info metric-badge">${ex.category}</span></td>
          <td><span class="code-pill">${ex.language}</span></td>
          <td>${ex.times_selected}</td>
          <td>${ex.successful_rescues}</td>
          <td>${Math.round(ex.win_rate * 100)}%</td>
          <td>${ex.quality_score.toFixed(2)}</td>
          <td><span class="badge-success metric-badge">${ex.status}</span></td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.error("Failed to load exemplars view:", e);
    }
  }
};

window.DashboardUI = DashboardUI;
