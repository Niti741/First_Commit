document.addEventListener("DOMContentLoaded", async () => {
  console.log("Initializing Kifayat Web Application...");

  // 1. Initialize Chat UI
  try {
    ChatUI.init();
    console.log("ChatUI initialized.");
  } catch (err) {
    console.error("Error initializing ChatUI:", err);
  }

  // 2. Initialize Dashboard UI
  try {
    await DashboardUI.init();
    console.log("DashboardUI initialized.");
  } catch (err) {
    console.error("Error initializing DashboardUI:", err);
  }

  // 3. Tab Switching Logic
  const tabs = document.querySelectorAll(".tab-btn");

  function switchToTab(targetTab) {
    tabs.forEach(t => {
      if (t.getAttribute("data-tab") === targetTab) {
        t.classList.add("active");
      } else {
        t.classList.remove("active");
      }
    });

    document.querySelectorAll(".tab-panel").forEach(panel => {
      panel.classList.remove("active");
    });

    const activePanel = document.getElementById(targetTab + "Panel");
    if (activePanel) {
      activePanel.classList.add("active");
    }

    // Trigger lazy view loading
    try {
      if (targetTab === "workflow" && window.kifayatWorkflow) {
        window.kifayatWorkflow.loadData();
      } else if (targetTab === "requests") {
        DashboardUI.loadRequestsView();
      } else if (targetTab === "memory") {
        DashboardUI.loadMemoryView();
        DashboardUI.loadCacheView();
      } else if (targetTab === "exemplars") {
        DashboardUI.loadExemplarsView();
      }
    } catch (err) {
      console.warn("View load warning for tab", targetTab, err);
    }
  }

  // Wire tab click handlers
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetTab = tab.getAttribute("data-tab");
      switchToTab(targetTab);
    });
  });

  // 4. Initialize API Key & Security Vault UI
  try {
    ApiKeyModalUI.init();
    console.log("ApiKeyModalUI initialized.");
  } catch (err) {
    console.error("Error initializing ApiKeyModalUI:", err);
  }

  // 5. Health check to update status dot
  try {
    const health = await API.getHealth();
    const providerDisplay = document.getElementById("providerDisplay");
    const statusText = document.getElementById("statusText");
    if (providerDisplay) providerDisplay.textContent = (health.provider || "ONLINE").toUpperCase();
    if (statusText) statusText.textContent = "Online (" + (health.environment || "local") + ")";
  } catch (e) {
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    if (statusDot) statusDot.style.backgroundColor = "var(--danger-solid)";
    if (statusText) statusText.textContent = "Offline";
  }

  console.log("Kifayat Web Application ready.");
});

/* ==========================================================================
   SECURE API KEY & VAULT MODAL CONTROLLER
   ========================================================================== */
const ApiKeyModalUI = {
  modalEl: null,
  openBtn: null,
  closeBtn: null,
  saveBtn: null,
  testBtn: null,
  resetBtn: null,
  keyInput: null,
  toggleVisBtn: null,
  providerSelect: null,
  statusLabel: null,
  activeBadge: null,
  activeMasked: null,
  alertEl: null,

  init() {
    this.modalEl = document.getElementById("apiKeyModal");
    this.openBtn = document.getElementById("apiKeyModalBtn");
    this.closeBtn = document.getElementById("closeApiKeyModalBtn");
    this.saveBtn = document.getElementById("saveApiKeyBtn");
    this.testBtn = document.getElementById("testApiKeyBtn");
    this.resetBtn = document.getElementById("resetDefaultKeyBtn");
    this.keyInput = document.getElementById("userApiKeyInput");
    this.toggleVisBtn = document.getElementById("toggleKeyVisibilityBtn");
    this.providerSelect = document.getElementById("userKeyProviderSelect");
    this.statusLabel = document.getElementById("apiKeyStatusLabel");
    this.activeBadge = document.getElementById("activeKeyBadge");
    this.activeMasked = document.getElementById("activeKeyMasked");
    this.alertEl = document.getElementById("modalAlert");

    if (this.openBtn) {
      this.openBtn.addEventListener("click", () => this.open());
    }
    if (this.closeBtn) {
      this.closeBtn.addEventListener("click", () => this.close());
    }

    if (this.toggleVisBtn) {
      this.toggleVisBtn.addEventListener("click", () => {
        if (this.keyInput.type === "password") {
          this.keyInput.type = "text";
          this.toggleVisBtn.textContent = "🙈 Hide";
        } else {
          this.keyInput.type = "password";
          this.toggleVisBtn.textContent = "👁️ Show";
        }
      });
    }

    if (this.saveBtn) {
      this.saveBtn.addEventListener("click", () => this.saveKey());
    }

    if (this.testBtn) {
      this.testBtn.addEventListener("click", () => this.testKey());
    }

    if (this.resetBtn) {
      this.resetBtn.addEventListener("click", () => this.resetKey());
    }

    this.updateUI();
  },

  open() {
    if (!this.modalEl) return;
    this.modalEl.style.display = "flex";
    this.updateUI();
  },

  close() {
    if (!this.modalEl) return;
    this.modalEl.style.display = "none";
    if (this.alertEl) this.alertEl.style.display = "none";
  },

  maskKey(key) {
    if (!key || key.length < 8) return "****";
    return key.substring(0, 5) + "..." + key.substring(key.length - 4);
  },

  updateUI() {
    const key = API.getUserApiKey();
    if (key) {
      if (this.statusLabel) this.statusLabel.textContent = "Custom Key";
      if (this.activeBadge) {
        this.activeBadge.textContent = "🟢 Custom Key Active";
        this.activeBadge.className = "rung-pill rung-1";
      }
      if (this.activeMasked) {
        this.activeMasked.textContent = `Active Key: ${this.maskKey(key)}`;
      }
      if (this.keyInput && !this.keyInput.value) {
        this.keyInput.value = key;
      }
    } else {
      if (this.statusLabel) this.statusLabel.textContent = "API Key";
      if (this.activeBadge) {
        this.activeBadge.textContent = "⚡ Shared System Default";
        this.activeBadge.className = "rung-pill rung-2";
      }
      if (this.activeMasked) {
        this.activeMasked.textContent = "Using gateway shared server credential";
      }
    }
  },

  showAlert(msg, isSuccess = true) {
    if (!this.alertEl) return;
    this.alertEl.style.display = "block";
    this.alertEl.textContent = msg;
    if (isSuccess) {
      this.alertEl.style.background = "rgba(16, 185, 129, 0.12)";
      this.alertEl.style.color = "#047857";
      this.alertEl.style.border = "1px solid rgba(16, 185, 129, 0.3)";
    } else {
      this.alertEl.style.background = "rgba(239, 68, 68, 0.12)";
      this.alertEl.style.color = "#b91c1c";
      this.alertEl.style.border = "1px solid rgba(239, 68, 68, 0.3)";
    }
  },

  saveKey() {
    const raw = this.keyInput.value.trim();
    if (!raw) {
      this.showAlert("Please enter an API key or click 'Revert to Default'.", false);
      return;
    }
    const regex = /^[a-zA-Z0-9_\-\.]{16,128}$/;
    if (!regex.test(raw)) {
      this.showAlert("Invalid key format. Only alphanumeric characters, dashes, and dots allowed (16-128 chars).", false);
      return;
    }

    API.setUserApiKey(raw);
    this.updateUI();
    this.showAlert(`✓ Personal API Key activated securely (${this.maskKey(raw)}). Future requests will use your quota.`, true);
    setTimeout(() => this.close(), 1500);
  },

  async testKey() {
    const raw = this.keyInput.value.trim() || API.getUserApiKey();
    if (!raw) {
      this.showAlert("Please enter an API key to test.", false);
      return;
    }
    this.testBtn.disabled = true;
    this.testBtn.textContent = "Testing...";
    try {
      const res = await API.validateApiKey(raw, this.providerSelect.value);
      if (res.valid) {
        this.showAlert(`✓ Provider Verified! Key ${res.masked_key} is valid and operational.`, true);
      } else {
        this.showAlert(`✕ Verification failed: ${res.error || 'Invalid credentials'}`, false);
      }
    } catch (e) {
      this.showAlert(`Connection error: ${e.message}`, false);
    } finally {
      this.testBtn.disabled = false;
      this.testBtn.textContent = "⚡ Test Connection";
    }
  },

  resetKey() {
    API.clearUserApiKey();
    if (this.keyInput) this.keyInput.value = "";
    this.updateUI();
    this.showAlert("Reverted to system default shared key.", true);
  }
};

