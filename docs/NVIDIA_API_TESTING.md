# NVIDIA API Connectivity & Kifayat Routing Verification Guide

This guide provides end-to-end instructions for verifying live NVIDIA NIM API connectivity, testing conversational fast-path routing (Path A) vs. institutional/coding repair ladder (Path B), and diagnosing provider failover in Kifayat.

---

## 1. Environment Configuration

Ensure your `.env` file in the project root contains the NVIDIA NIM configuration:

```ini
LLM_PROVIDER=nvidia
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=meta/llama-3.2-11b-vision-instruct
NVIDIA_API_KEY=nvapi-your-key-here
CHEAP_MODEL_ID=meta/llama-3.2-11b-vision-instruct
STRONG_MODEL_ID=meta/llama-3.2-11b-vision-instruct
JUDGE_MODEL_ID=meta/llama-3.2-11b-vision-instruct
```

> **Security Note:** The NVIDIA API key is loaded into backend memory only. It is never exposed in client logs, frontend receipts, or diagnostic endpoints.

---

## 2. Server Startup

Activate the Python virtual environment and launch the FastAPI server:

### Windows Command Prompt / PowerShell
```powershell
.\venv\Scripts\activate
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
or simply double-click `run.bat`.

---

## 3. Provider Diagnostics Endpoints

Kifayat provides lightweight diagnostic endpoints to verify provider readiness and network reachability without revealing credentials.

### 3.1 Basic Health Check
```powershell
curl -X GET http://127.0.0.1:8000/health
```
**Expected Response:**
```json
{
  "status": "ok",
  "provider": "nvidia",
  "configured": true,
  "app_id": "kit_student_handbook",
  "version": "2025.1"
}
```

### 3.2 Provider Status & Architecture Info
```powershell
curl -X GET http://127.0.0.1:8000/v1/provider/status
```
**Expected Response:**
```json
{
  "provider": "nvidia",
  "configured": true,
  "cheap_model": "meta/llama-3.2-11b-vision-instruct",
  "strong_model": "meta/llama-3.2-11b-vision-instruct",
  "judge_model": "meta/llama-3.2-11b-vision-instruct",
  "supports_caching": true,
  "last_status": "ready",
  "last_latency_ms": null,
  "fallback_count": 0,
  "api_endpoint": "https://integrate.api.nvidia.com/v1"
}
```

### 3.3 Active Connection Probe
Sends a 5-token ping test to NVIDIA NIM to measure live round-trip latency:
```powershell
curl -X POST http://127.0.0.1:8000/v1/provider/test
```
**Expected Response (Connected):**
```json
{
  "status": "healthy",
  "connected": true,
  "provider": "nvidia",
  "model": "meta/llama-3.2-11b-vision-instruct",
  "status_code": 200,
  "latency_ms": 782.4,
  "message": "NVIDIA API connection verified successfully."
}
```

---

## 4. Testing Conversational Fast-Path (Path A)

Conversational messages (`hello`, `hi`, `how are you?`, `thanks`, `bye`, Hinglish pleasantries) bypass handbook context injection and heavy LLM judge verification. They execute directly on Rung 1 with `maximum_rung=1`.

### 4.1 Test Greeting: "hello"
```powershell
curl -X POST http://127.0.0.1:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"hello\", \"mode\": \"kifayat\"}'
```

**Receipt Verification Checklist:**
- `receipt.rung`: **1** (strictly Rung 1, never escalates to Rung 3)
- `receipt.intent`: `"GREETING"`
- `receipt.routing_reason`: `"Simple conversational greeting; maximum_rung=1"`
- `receipt.node_states.semantic_cache`: `"SKIPPED"`
- `receipt.node_states.cheap_model`: `"COMPLETED"`
- `receipt.node_states.rung3_strong`: `"SKIPPED"`
- `receipt.fallback_used`: `false`

### 4.2 Test Casual Inquiry: "how are you?"
```powershell
curl -X POST http://127.0.0.1:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"how are you?\", \"mode\": \"kifayat\"}'
```
- `receipt.rung`: **1**
- `receipt.intent`: `"CASUAL_CONVERSATION"`

### 4.3 Test Gratitude: "thanks a lot"
```powershell
curl -X POST http://127.0.0.1:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"thanks a lot\", \"mode\": \"kifayat\"}'
```
- `receipt.rung`: **1**
- `receipt.intent`: `"GRATITUDE"`

---

## 5. Testing Institutional & Coding Queries (Path B)

Questions requiring handbook facts or structured code utilize the trusted grounding path, semantic cache, and the Three-Rung Repair Ladder.

### 5.1 Embedded Handbook Question: "hello, what is the hostel fee?"
```powershell
curl -X POST http://127.0.0.1:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"hello, what is the hostel fee?\", \"mode\": \"kifayat\"}'
```
- `receipt.intent`: `"HANDBOOK_QUERY"`
- **Response**: Accurately includes handbook hostel fee breakdown (₹42,000 / ₹32,000 / ₹24,000) and informs that mess fees are billed separately.

### 5.2 Embedded Coding Question: "hi, write html and css for a glowing card"
```powershell
curl -X POST http://127.0.0.1:8000/api/chat `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"hi, write html and css for a glowing card\", \"mode\": \"kifayat\"}'
```
- `receipt.intent`: `"CODING"`
- **Response**: Structured markdown code block (` ```html `) rendered with interactive Canvas preview.

---

## 6. Running Automated Verification Suite

Run all automated routing and provider tests:

```powershell
.\venv\Scripts\python.exe -m pytest backend\tests\test_conversation_routing.py -v
```

Run full regression test suite:

```powershell
.\venv\Scripts\python.exe -m pytest -v
```

All 36 unit and integration tests should pass.
