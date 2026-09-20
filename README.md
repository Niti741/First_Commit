# KIFAYAT: Intelligent LLM Context Gateway & College Helpdesk

> **Kifayat** (*noun / Urdu: کفایت*): Economy, thrift, resource optimization, purposeful efficiency.

Kifayat is an enterprise-grade LLM context optimization gateway integrated with an AI-powered college helpdesk for **Kifayat Institute of Technology (KIT)**. It slashes input tokens, cuts model latency, avoids redundant strong-model escalations, and accelerates repeat queries by over **85%**, while maintaining high answer fidelity, long-term memory, and full bilingual support for both English and natural Hinglish.

---

## 1. What Kifayat Is & Why It Exists

Modern LLM applications often exhibit severe context inefficiencies:
1. **Unbounded History Re-transmission**: Every chat turn transmits the entire conversation history back to the model, compounding token costs quadratically.
2. **Expensive Strong Model Overuse**: Sending simple, repetitive questions to expensive 70B+ models when a verified 8B model could answer accurately.
3. **Repeated Queries**: Common institutional queries (e.g. *"Hostel fee?", "Attendance rules?"*) are regenerated repeatedly rather than served securely from semantic response caches.
4. **Prefix Cache Invalidation**: Random prompt rearrangements destroy GPU Key-Value (KV) prefix cache hits across inference requests.

Kifayat solves this by unifying **cache-aware prompt prefix structuring**, **immutable frozen memory blocks**, **vector response caching**, **three-rung model repair escalation**, and **Bayesian exemplar retrieval** into a single cohesive gateway.

---

## 2. Core Architecture

```text
                            USER / BROWSER
                                  │
                       ┌──────────▼──────────┐
                       │   Kifayat Gateway   │
                       └──────────┬──────────┘
                                  │
                      [1. Input Validation]
                                  │
                      [2. Cacheability Guard]
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
      [Cache Safe & High Similarity]         [Cache Miss]
                  │                               │
        ┌─────────┴─────────┐                     ▼
        │ Semantic Response │         [3. Context Builder]
        │   Cache (Hit)     │         - Canonicalized Handbook
        └─────────┬─────────┘         - Frozen Memory Blocks
                  │                   - Recent Raw Turns Window
                  │                   - Checkpoint Hash Positioning
                  │                               │
                  │                   [4. Prompt Repair Ladder]
                  │                   ├── Rung 1: Cheap Model (8B) + Rule Checks
                  │                   │          └── Passed Judge? ──► Return
                  │                   ├── Rung 2: Exemplar-Assisted Rescue (Top 3)
                  │                   │          └── Passed Judge? ──► Return
                  │                   └── Rung 3: Strong Model Fallback (70B)
                  │                               │
                  │                   [5. Asynchronous Compaction]
                  │                   - Background Worker / SQS Queue
                  │                   - Idempotent Block Summarizer
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
                   OpenAI-Compatible Response
                    + Kifayat Token Receipt
```

---

## 3. The 10 Architectural Pillars

1. **Cache-Aware Prompt Restructuring**:
   - Isolates static prompts and canonicalized handbooks prior to `<!-- CACHE_CHECKPOINT_1 -->`.
   - Immutable frozen summaries precede `<!-- CACHE_CHECKPOINT_2 -->`.
   - Raw turns precede `<!-- CACHE_CHECKPOINT_3 -->`. Dynamic tokens and retrieved exemplars are placed strictly at the suffix to preserve KV prefix cache reuse.
2. **Frozen-Block Conversation Memory**:
   - Maintains the newest `RAW_WINDOW_TURNS` (default: 3) verbatim.
   - Older turns group into blocks of `BLOCK_TURNS` (default: 6) and are permanently frozen into immutable summaries.
   - **Critical Invariant**: A finalized frozen block is NEVER re-written or edited, preventing prefix cache churn.
3. **Hierarchical Memory Merging**:
   - When 5 Level-0 blocks accumulate, the background summarizer compacts them into a Level-1 block overview, preventing long sessions from ballooning context.
4. **Memory Token Budget Manager**:
   - Enforces a strict token ceiling (`MAX_MEMORY_TOKENS=4000`) with deterministic priority trimming:
     `Current Question > Recent Raw Turns > Active Block > Frozen Blocks > Overviews > Exemplars`.
5. **Semantic Response Caching**:
   - Dense 384-dimensional vector similarity using cosine distance (threshold $\ge 0.90$).
   - Namespaced by `{app_id}:{handbook_version}:{language}:{model_group}` to prevent cross-app leakage.
   - Zero LLM tokens incurred on cache hits.
6. **Cache Safety Guard (`is_cacheable`)**:
   - Blocks caching for queries with personalized data (*"my roll number"*, *"my fee balance"*), real-time markers (*"today"*, *"current time"*), or deictic references.
7. **Three-Rung Prompt Repair Ladder**:
   - **Rung 1**: Fast generation using Cheap Model (e.g. Llama-3.1-8B) followed by deterministic rule checks and automated QA judge verification.
   - **Rung 2**: If Rung 1 fails, automatically retrieves top-3 high-impact exemplars from the `ExemplarStore` to rescue the cheap model.
   - **Rung 3**: If Rung 2 fails, escalates safely to the Strong Model (e.g. Llama-3.1-70B).
8. **Self-Pruning Exemplar Store**:
   - Stores up to 500 exemplars scored using Bayesian smoothing:
     $$\text{Score} = \frac{\text{Successful Rescues} + 2.5}{\text{Total Trials} + 5.0}$$
   - Prevents 1-trial flukes from outranking battle-tested exemplars.
   - Diversity pruner safeguards representation across core categories (fees, hostel, exams, placements, library) and languages (English / Hinglish).
9. **Real-Time Streaming via Server-Sent Events (SSE)**:
   - Streams chunks at `/v1/chat/completions` (`stream=true`) and `/api/chat/stream`.
   - Emits structured events: `metadata` (cache hit status), `token`, `complete` (with full `kifayat_receipt`), and `error`.
10. **Centralized Cost & Observability Engine**:
    - Generates a `kifayat_receipt` on every response showing exact token breakdowns, latency, model ID, repair rung, and dollar savings vs unoptimized baseline.

---

## 4. Local Quickstart (Windows)

The application runs **100% locally** on Windows with Python 3.10+ and requires **no external database, no Redis, no SQS, and no external API key** out of the box.

### 4.1 Prerequisites
- Python 3.10+ (tested on Python 3.14)
- (Optional) NVIDIA API Key for production inference

### 4.2 Installation
In PowerShell or Command Prompt:
```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the local server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Or simply double-click:
```powershell
scripts\run_local.bat
```

### 4.3 Open the Web Interface
Open your browser and navigate to:
```text
http://127.0.0.1:8000
```
You will see the **Kifayat Helpdesk & Gateway Dashboard** featuring:
- **💬 Chat Demo**: Live interactive bilingual chat with real-time SSE streaming and Kifayat Receipt drawer.
- **📊 Gateway Overview**: Real-time KPI cards for requests, cache hit rate, tokens saved, and cost saved.
- **💰 Cost Analytics**: Dollar comparison of actual optimized cost vs unoptimized baseline.
- **⚡ Semantic Cache**: Cache entries, hit rates, and manual invalidation controls.
- **🧊 Memory Inspector**: Visual tree of active sessions, raw turns, and immutable frozen blocks.
- **🛡️ Repair Ladder**: Rung 1, 2, and 3 architecture statistics.
- **📚 Exemplar Store**: Table of vetted exemplars with Bayesian scores and win rates.
- **📜 Request Audit Log**: Detailed log of all processed queries.

---

## 5. Configuration (`.env`)

Configuration is managed via environment variables defined in `.env`:

```env
ENVIRONMENT=local

# Provider: 'mock' (default offline) | 'nvidia' | 'bedrock'
LLM_PROVIDER=mock

# NVIDIA Configuration (required only when LLM_PROVIDER=nvidia)
NVIDIA_API_KEY=
NVIDIA_MODEL=meta/llama-3.1-8b-instruct
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
CHEAP_MODEL_ID=meta/llama-3.1-8b-instruct
STRONG_MODEL_ID=meta/llama-3.1-70b-instruct
JUDGE_MODEL_ID=meta/llama-3.1-70b-instruct

AWS_REGION=us-east-1

PROJECT_NAME=Kifayat
APP_ID=helpdesk
HANDBOOK_NAME=Kifayat Institute of Technology
HANDBOOK_VERSION=1.0.0
APPLICATION_VERSION=1.0.0

# Memory Configuration
RAW_WINDOW_TURNS=3
BLOCK_TURNS=6
BLOCKS_PER_MERGE=5
MAX_MEMORY_TOKENS=4000

# Semantic Cache Configuration
SEMANTIC_CACHE_ENABLED=true
SEMANTIC_CACHE_THRESHOLD=0.90
SEMANTIC_CACHE_TTL=86400
SEMANTIC_CACHE_MAX_ENTRIES=10000

# Compaction Configuration
COMPACTION_ENABLED=true
COMPACTION_QUEUE_TYPE=local

# Exemplar Store Configuration
MAX_EXEMPLARS=500
EXEMPLAR_MIN_EVALUATIONS=5
EXEMPLAR_STALE_DAYS=90

# Generation Limits
MAX_OUTPUT_TOKENS=500
MAX_QUESTION_LENGTH=2000

STREAMING_ENABLED=true
MODES=baseline,cache_only,naive,kifayat
```

---

## 6. How NVIDIA Integration Works

When switching to live NVIDIA NIM endpoints:
1. Obtain an API key from NVIDIA Build (`https://build.nvidia.com`).
2. Update `.env`:
   ```env
   LLM_PROVIDER=nvidia
   NVIDIA_API_KEY=nvapi-your-real-key-here
   ```
3. Restart the server. The `NVIDIAProvider` seamlessly handles:
   - Inference via OpenAI-compatible endpoints with Bearer authentication.
   - Real-time chunked SSE streaming.
   - NeMo Retriever query embedding vectors.
   - Factual consistency judge evaluations via Llama-3.1-70B.

---

## 7. Running Tests & Benchmarks

### 7.1 Automated Unit & Integration Tests
Run the complete Pytest suite (21 test cases covering all 10 architectural components):
```powershell
python -m pytest backend/tests/ -v
```

### 7.2 Running Benchmark Evaluation
Run the comparative evaluation across Baseline, Naive, Cache-Only, and Kifayat modes:
```powershell
python eval/runner.py
```
Sample benchmark output:
```text
======================================================================
Mode         | Tokens     | Cost (USD)   | Cache Hits  | Strong LLM | Savings % 
----------------------------------------------------------------------
baseline     | 63716      | $0.033264    | 0           | 13         | 0.0       %
naive        | 63716      | $0.004168    | 0           | 0          | 87.5      %
cache_only   | 58900      | $0.003852    | 1           | 0          | 88.4      %
kifayat      | 58900      | $0.003852    | 1           | 0          | 88.4      %
======================================================================
```

---

## 8. Future AWS Deployment Readiness

All interfaces are structured for seamless cloud scaling:
| Local Implementation | Future AWS Cloud Component | Adapter File |
|---|---|---|
| `SQLiteStore` (Sessions) | Amazon DynamoDB (`KifayatSessions`) | `backend/app/storage/aws_adapters.py` |
| `SQLiteStore` (Exemplars)| Amazon DynamoDB (`KifayatExemplars`) | `backend/app/storage/aws_adapters.py` |
| `LocalCompactionQueue` | Amazon SQS + AWS Lambda | `backend/app/memory/compaction_queue.py` |
| `LocalSemanticCache` | Amazon ElastiCache (Valkey/Redis) | `backend/app/cache/redis_cache.py` |
| `MockProvider` / NVIDIA | Amazon Bedrock (Claude / Titan) | `backend/app/providers/bedrock_provider.py` |
| SQLite Request Logs | AWS CloudWatch EMF / DynamoDB | `backend/app/storage/aws_adapters.py` |
| Vanilla Web Frontend | AWS Amplify Hosting | Static web directory `frontend/` |

---

## 9. API Reference

### 9.1 Chat Completion (OpenAI-Compatible)
`POST /v1/chat/completions`
```json
{
  "messages": [
    {"role": "user", "content": "Hostel ka fee kitna hai?"}
  ],
  "stream": false,
  "mode": "kifayat"
}
```
Response contains standard OpenAI choices and the custom `kifayat_receipt`:
```json
{
  "id": "req-9a8f23",
  "object": "chat.completion",
  "model": "meta/llama-3.1-8b-instruct",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "KIT mein hostel fee room type ke hisaab se hoti hai: Single room ka ₹42,000 per semester..."
      }
    }
  ],
  "kifayat_receipt": {
    "request_id": "req-9a8f23",
    "model_id": "meta/llama-3.1-8b-instruct",
    "rung": 1,
    "input_tokens": 1280,
    "output_tokens": 68,
    "tokens_saved": 960,
    "cost_usd": 0.000076,
    "baseline_cost_usd": 0.002672,
    "saving_pct": 97.16,
    "cache_hit": false,
    "latency_ms": 48.2,
    "judge_score": 5
  }
}
```

### 9.2 Feedback Submission
`POST /v1/feedback`
```json
{
  "request_id": "req-9a8f23",
  "question": "What is the hostel fee?",
  "answer": "Single occupancy room fee is ₹42,000 per semester.",
  "thumbs_up": true,
  "category": "hostel"
}
```

---

## 10. Troubleshooting

- **Server fails to start with port already in use**:
  Run `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080` to bind to an alternative port.
- **Testing without NVIDIA credentials**:
  Keep `LLM_PROVIDER=mock` in `.env`. The MockProvider executes full offline factual generation, streaming, embeddings, and judge verification.
