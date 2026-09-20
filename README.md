<div align="center">

# ⚡ KIFAYAT AI
### Intelligent AI Inference Gateway, Prompt Repair Ladder & Assistant
**Slashes Token Bills by up to 85% • Real-Time SSE Streaming • Autonomous Active Learning • OpenAI Drop-In Compatible**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB.svg?style=flat&logo=Python&logoColor=white)](https://www.python.org/)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM%20Inference-76B900.svg?style=flat&logo=NVIDIA&logoColor=white)](https://build.nvidia.com)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?style=flat&logo=Docker&logoColor=white)](https://www.docker.com/)
[![AWS EC2](https://img.shields.io/badge/AWS-EC2%20Ready-FF9900.svg?style=flat&logo=AmazonAWS&logoColor=white)](https://aws.amazon.com/ec2/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*“Kifayat” (كفايت / کفایت) — An Urdu & Hindi principle representing frugality, thoughtful efficiency, and wise resource management.*

[🚀 Quickstart](#-quickstart-in-60-seconds) • [☁️ EC2 Deployment](#-production-deployment-amazon-ec2--docker) • [🏛️ Architecture](#-core-architecture) • [💡 Features](#-key-features) • [📖 Documentation](#-project-documentation)

</div>

---

## 📌 The Problem Kifayat Solves

Deploying Large Language Models (LLMs) like GPT-4o, Claude 3.5, or LLaMA 3.1 directly into production user-facing apps leads to four critical bottlenecks:

| Problem | Traditional LLM Apps | With Kifayat AI |
| :--- | :--- | :--- |
| **Runaway Costs** | Re-transmits static handbooks and full history on every turn. | **14-Intent Router** isolates conversational queries (125 tokens vs 920). |
| **High Latency (TTFT)** | 4-12 seconds spent processing heavy prefill tokens. | **Real SSE streaming** delivers Time-to-First-Token in **~1.1s**. |
| **Model Overkill** | Expensive 70B/400B models answer greetings and simple edits. | **3-Rung Repair Ladder** verifies cheap 11B models first; escalates only when needed. |
| **Broken Caching** | Whitespace and conversation filler shatter KV prefix caches. | **AST-Aware Squeezer** and **0-token Semantic Vector Cache** (~30ms hits). |

---

## 🏛️ Core Architecture

```
                             [ USER QUERY ]
                                   │
                                   ▼
             [ STEP 1: SECURITY & SSRF SANITIZATION ]
                                   │
                                   ▼
             [ STEP 2: 14-INTENT CLASSIFICATION ROUTER ]
          (GREETING, CODING, HANDBOOK, TECHNICAL, CANVAS...)
                                   │
                                   ▼
             [ STEP 3: RUNG 0 - VECTOR SEMANTIC CACHE ]
                    │
            ┌───────┴───────┐
            │ Similarity    │ >= 0.90
            │ Check         ├─────────────► [ INSTANT RETURN ]
            └───────┬───────┘               0 Tokens • 30ms • 100% Saved
                    │ < 0.90
                    ▼
             [ STEP 4: CONTEXT BUILDER & KV CHECKPOINTS ]
          - Conversational Fast Path (125 tokens) OR
          - Handbook Policy Grounding (875 tokens)
          - Sliding window + hierarchical block compaction
                                   │
                                   ▼
             [ STEP 5: DYNAMIC AST-AWARE SQUEEZER ]
          - 100% Code syntax, math, and table preservation
          - Prunes conversational boilerplate and filler
                                   │
                                   ▼
             [ STEP 6: 3-RUNG PROMPT REPAIR LADDER ]
          ├── RUNG 1: Cheap Model (LLaMA-3.2-11B) + Real SSE Stream
          │          └── Passes LLM Judge (>= 3.0/5)? ──► Return
          ├── RUNG 2: Few-Shot Exemplar Rescue Loop
          │          └── Passes LLM Judge (>= 3.0/5)? ──► Return
          └── RUNG 3: Frontier Fallback Model (LLaMA-3.1-70B)
                     └── [ Autonomous Active Learning Miner ]
                         (Captures & registers new rescue exemplar)
                                   │
                                   ▼
             [ STEP 7: SEMANTIC CACHE WRITE & HISAB RECEIPT ]
          - Verified output cached for future 0-token hits
          - Emits auditable receipt with exact micro-dollar accounting
```

---

## ⚡ Quickstart in 60 Seconds

### Prerequisites
- Python 3.11, 3.12, or 3.14
- Git

### 1. Clone & Install
```bash
# Clone the repository
git clone https://github.com/Niti741/First_Commit.git
cd First_Commit

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example configuration
cp .env.example .env

# Edit .env and insert your NVIDIA NIM API key
# Windows: notepad .env | Linux/macOS: nano .env
```

```ini
ENVIRONMENT=local
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_MODEL=meta/llama-3.2-11b-vision-instruct
```

### 3. Launch Local Server
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in Google Chrome or Microsoft Edge.

---

## ☁️ Production Deployment: Amazon EC2 & Docker

Kifayat AI includes a complete automated deployment suite with zero-buffering SSE streaming, systemd service self-healing, and SSL termination.

### Option A: 1-Click Amazon EC2 Installer (Fastest)

Launch an **Ubuntu 24.04 / 22.04 LTS** instance on AWS EC2 (`t3.medium` recommended), SSH into your instance, and run:

```bash
# Clone repository
git clone https://github.com/Niti741/First_Commit.git first_commit
cd first_commit

# Run automated production setup script
chmod +x deploy/ec2_setup.sh
./deploy/ec2_setup.sh
```

**What the installer does automatically:**
- Sets up Python 3, virtual environment, and dependencies.
- Creates a **2GB swap file** to protect small instances from Out-of-Memory crashes.
- Registers and starts the `kifayat.service` systemd daemon with automatic recovery (`Restart=always`).
- Configures **Nginx with zero-buffering** (`proxy_buffering off;`) to guarantee real-time SSE streaming.
- Configures UFW firewall for ports 22, 80, and 443.

For the complete AWS walkthrough with step-by-step console screenshots, see [`EC2_DEPLOYMENT_GUIDE.md`](EC2_DEPLOYMENT_GUIDE.md).

---

### Option B: Docker & Docker Compose

Deploy on any Linux server with a single command:

```bash
# 1. Configure production environment
cp .env.production.example .env
nano .env

# 2. Build and launch container stack
docker compose up -d --build

# 3. Monitor container logs
docker compose logs -f
```

For full VPS, Nginx, and SSL instructions, read [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## 💡 Key Features

### 1. 14 Fine-Grained Routing Intents
Replaces binary routing with precise classification:
`GREETING`, `CASUAL_CONVERSATION`, `EMOTIONAL_CONVERSATION`, `FOLLOW_UP`, `GENERAL_QA`, `COLLEGE`, `HANDBOOK`, `TECHNICAL`, `CODING`, `CANVAS`, `DOCUMENT`, `CURRENT_INFO`, `CREATIVE`, `COMPLEX_REASONING`.

### 2. Conversational Fast-Path (Saves ~795 Tokens/Turn)
Casual conversations skip the 875-token handbook system prompt, using a lean 125-token prompt. Input token volume drops from **~920 to 125 tokens**, delivering sub-1.2s TTFT.

### 3. Prompt Repair Ladder & Autonomous Exemplar Mining
- **Rung 0**: Vector Semantic Cache (0 tokens, ~30ms).
- **Rung 1**: High-throughput cheap model with real-time SSE streaming and automated LLM Judge quality evaluation.
- **Rung 2**: Few-shot exemplar rescue.
- **Rung 3**: Strong frontier model fallback.
- **Active Learning**: Difficult queries resolved at Rung 3 are automatically analyzed and saved to `ExemplarStore` so future requests succeed at Rung 2!

### 4. Interactive Canvas Workspace
Integrated live code execution sandbox:
- **Synchronized Line 1**: Editor and line-number gutter always start at Line 1.
- **Auto-Run (400ms)**: Real-time debounced live preview in an isolated sandboxed iframe.
- **Console Log Bridge**: Captures standard console outputs and errors via postMessage bridge.
- **Code Export & Universal Copy**: One-click download and clipboard feedback.

### 5. Dual A/B Telemetry Benchmark Mode
Toggle **A/B Benchmark** in the chat header to compare Kifayat against an unoptimized baseline side-by-side with live meters for latency, tokens, and cost.

### 6. Drop-In OpenAI Compatibility
Point any external app (LangChain, LlamaIndex, Cursor, OpenWebUI) to Kifayat:
```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kifayat-gateway",
    "messages": [{"role": "user", "content": "Explain prefix caching"}]
  }'
```

---

## 📁 Repository Directory Structure

```text
First_Commit/
├── backend/
│   ├── app/
│   │   ├── api/                 # API endpoints (chat, v1_proxy, analytics)
│   │   ├── context/             # Squeezer, builder, canonicalizer
│   │   ├── core/                # Security, key masking, SSRF defense
│   │   ├── exemplars/           # Active learning miner & Bayesian store
│   │   ├── memory/              # Sliding window & compaction manager
│   │   ├── providers/           # NVIDIA NIM, mock provider, router
│   │   ├── repair/              # 3-Rung repair ladder, LLM Judge
│   │   ├── storage/             # Domain repository contracts & SQLite store
│   │   ├── gateway.py           # Central gateway orchestrator
│   │   ├── router.py            # 14-intent classifier & fast path
│   │   └── main.py              # FastAPI application entrypoint
│   ├── data/                    # Handbook context and seed exemplars
│   └── tests/                   # Pytest automated test suites
├── frontend/
│   ├── index.html               # React 18 single-page application
│   ├── css/                     # HSL design tokens and styles
│   └── js/                      # Chat, Canvas, and Dashboard controllers
├── deploy/
│   ├── ec2_setup.sh             # 1-click automated EC2 setup script
│   ├── kifayat.service          # Production systemd daemon
│   └── nginx.conf               # Nginx reverse proxy with zero-buffering SSE
├── Dockerfile                   # Production container image
├── docker-compose.yml           # 1-command Docker Compose stack
├── .dockerignore                # Docker build exclusions
├── .env.example                 # Local environment template
├── .env.production.example      # Production environment template
├── EC2_DEPLOYMENT_GUIDE.md      # Complete step-by-step AWS EC2 guide
├── DEPLOYMENT.md                # Multi-platform deployment manual
├── hisab_kitab.txt              # Master project manual (v2.5.0)
├── promptt.md                   # Video presentation walkthrough script
└── requirements.txt             # Python dependencies
```

---

## 📖 Project Documentation

- **[EC2 Deployment Guide](EC2_DEPLOYMENT_GUIDE.md)**: Complete step-by-step guide for deploying onto AWS EC2 with systemd and Nginx.
- **[Deployment Manual](DEPLOYMENT.md)**: Multi-platform deployment instructions covering Docker, EC2, VPS, and SSL.
- **[Hisab-Kitab Manual (`hisab_kitab.txt`)](hisab_kitab.txt)**: Exhaustive technical manual detailing architectural innovations and accounting mathematics.
- **[Video Presentation Guide (`promptt.md`)](promptt.md)**: Timed presentation script (0:00 - 8:45), visual cues, and hackathon Q&A defense points.

---

## 🧪 Testing & Verification

Run the automated test suite:
```bash
python -m pytest backend/tests/ -v
```

Test live NVIDIA NIM provider reachability:
```bash
curl -X POST http://127.0.0.1:8000/v1/provider/test
```

---

## 📄 License
This project is open-source and licensed under the [MIT License](LICENSE).
