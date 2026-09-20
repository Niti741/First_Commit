const API = {
  baseUrl: window.location.origin,

  async getHealth() {
    const res = await fetch(`${this.baseUrl}/api/health`);
    return res.json();
  },

  async getDashboardStats() {
    const res = await fetch(`${this.baseUrl}/api/dashboard/stats`);
    return res.json();
  },

  async getRecentRequests(limit = 50) {
    const res = await fetch(`${this.baseUrl}/api/dashboard/requests?limit=${limit}`);
    return res.json();
  },

  async getMemory(sessionId = null) {
    const url = sessionId 
      ? `${this.baseUrl}/api/dashboard/memory?session_id=${sessionId}`
      : `${this.baseUrl}/api/dashboard/memory`;
    const res = await fetch(url);
    return res.json();
  },

  async getCacheStats() {
    const res = await fetch(`${this.baseUrl}/api/cache/stats`);
    return res.json();
  },

  async invalidateCache(namespace = null) {
    const res = await fetch(`${this.baseUrl}/api/cache/invalidate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ namespace })
    });
    return res.json();
  },

  async clearCache() {
    const res = await fetch(`${this.baseUrl}/api/cache/clear`, { method: "POST" });
    return res.json();
  },

  async getExemplars(status = null) {
    const url = status 
      ? `${this.baseUrl}/api/exemplars?status=${status}` 
      : `${this.baseUrl}/api/exemplars`;
    const res = await fetch(url);
    return res.json();
  },

  async sendFeedback(feedbackData) {
    const res = await fetch(`${this.baseUrl}/v1/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(feedbackData)
    });
    return res.json();
  },

  getUserApiKey() {
    return sessionStorage.getItem("kifayat_user_api_key") || localStorage.getItem("kifayat_user_api_key") || "";
  },

  setUserApiKey(key) {
    sessionStorage.setItem("kifayat_user_api_key", key);
    localStorage.setItem("kifayat_user_api_key", key);
  },

  clearUserApiKey() {
    sessionStorage.removeItem("kifayat_user_api_key");
    localStorage.removeItem("kifayat_user_api_key");
  },

  async validateApiKey(apiKey, provider = "nvidia") {
    const res = await fetch(`${this.baseUrl}/api/keys/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey, provider })
    });
    return res.json();
  },

  async getAuthStatus() {
    const res = await fetch(`${this.baseUrl}/api/auth/status`);
    return res.json();
  },

  /**
   * Reads SSE stream from /api/chat/stream
   */
  async streamChat(question, sessionId, mode, onChunk, onMetadata, onComplete, onError) {
    try {
      const userKey = this.getUserApiKey();
      const headers = {
        "Content-Type": "application/json",
        "X-Session-Id": sessionId,
        "X-Kifayat-Mode": mode
      };
      if (userKey) {
        headers["X-User-API-Key"] = userKey;
        headers["Authorization"] = `Bearer ${userKey}`;
      }

      const response = await fetch(`${this.baseUrl}/api/chat/stream`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          messages: [{ role: "user", content: question }],
          session_id: sessionId,
          mode: mode
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop(); // keep last incomplete chunk

        for (const block of lines) {
          if (!block.trim()) continue;
          const blockLines = block.split("\n");
          let eventType = "message";
          let dataStr = "";

          for (const line of blockLines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.slice(6).trim();
            }
          }

          if (!dataStr) continue;

          try {
            const parsed = JSON.parse(dataStr);
            if (eventType === "workflow_step") {
              if (window.kifayatWorkflow) window.kifayatWorkflow.handleWorkflowStepEvent(parsed);
            } else if (eventType === "metadata") {
              if (onMetadata) onMetadata(parsed);
            } else if (eventType === "token") {
              if (onChunk) onChunk(parsed.text);
            } else if (eventType === "complete") {
              if (onComplete) onComplete(parsed);
            } else if (eventType === "error") {
              if (onError) onError(parsed.message);
            }
          } catch (e) {
            console.warn("Could not parse SSE JSON:", dataStr, e);
          }
        }
      }
    } catch (err) {
      if (onError) onError(err.message);
    }
  }
};
