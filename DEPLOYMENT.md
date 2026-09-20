# 🚀 KIFAYAT AI — PRODUCTION DEPLOYMENT GUIDE

Comprehensive guide for deploying **Kifayat AI** across **Amazon Web Services (AWS EC2)**, **Docker & Docker Compose**, **Linux VPS (Ubuntu/Debian)**, and **Local Production Environments**.

---

## 📑 TABLE OF CONTENTS
1. [Architecture & Request Flow](#-architecture--request-flow)
2. [Amazon EC2 Deployment (Recommended)](#-amazon-ec2-deployment-recommended)
   - [Step 1: Launch EC2 Instance](#step-1-launch-ec2-instance)
   - [Step 2: Security Group Configuration](#step-2-security-group-configuration)
   - [Step 3: Connect via SSH](#step-3-connect-via-ssh)
   - [Step 4: 1-Click Automated Installer](#step-4-1-click-automated-installer)
   - [Step 5: Configure Production Environment](#step-5-configure-production-environment)
   - [Step 6: Free SSL/HTTPS with Let's Encrypt](#step-6-free-sslhttps-with-lets-encrypt)
3. [Docker & Docker Compose Deployment](#-docker--docker-compose-deployment)
4. [Manual Linux VPS Deployment (Systemd + Nginx)](#-manual-linux-vps-deployment-systemd--nginx)
5. [Critical Nginx Configuration for Real SSE Streaming](#-critical-nginx-configuration-for-real-sse-streaming)
6. [Environment Variables Reference](#-environment-variables-reference)
7. [Health Checks & Verification](#-health-checks--verification)
8. [Maintenance, Logging & Operations](#-maintenance-logging--operations)
9. [Troubleshooting & FAQ](#-troubleshooting--faq)

---

## 🏛️ ARCHITECTURE & REQUEST FLOW

```
                          [ END USER BROWSER ]
                                   │
                                   │ HTTPS (443) / HTTP (80)
                                   ▼
                   [ AWS EC2 / CLOUD FIREWALL / SG ]
                   (Inbound: 22 SSH, 80 HTTP, 443 HTTPS)
                                   │
                                   ▼
┌───────────────────────── CLOUD HOST / SERVER ──────────────────────────┐
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                      NGINX REVERSE PROXY                       │   │
│   │  - SSL Termination (Let's Encrypt Certbot)                     │   │
│   │  - Zero-Buffering SSE Streaming (proxy_buffering off)          │   │
│   │  - Gzip Compression & Static Asset Caching                     │   │
│   └──────────────────────────────┬─────────────────────────────────┘   │
│                                  │ http://127.0.0.1:8000               │
│                                  ▼                                     │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │              SYSTEMD SERVICE (kifayat.service)                 │   │
│   │  - 2 Async Uvicorn Worker Processes (FastAPI Gateway)          │   │
│   │  - Auto-restart on crash or reboot (Restart=always)            │   │
│   │  - Resource limits: LimitNOFILE=65535                          │   │
│   └──────────────────────────────┬─────────────────────────────────┘   │
│                                  │                                     │
│            ┌─────────────────────┴─────────────────────┐               │
│            ▼                                           ▼               │
│   [ EMBEDDED SQLITE DB ]                     [ 2GB SWAP MEMORY ]       │
│   (Sessions, Audit, Cache)                   (OOM Crash Protection)    │
│                                                                        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   │ Outbound TLS API Requests
                                   ▼
                      [ NVIDIA NIM CLOUD API ]
                    (integrate.api.nvidia.com)
```

---

## ☁️ AMAZON EC2 DEPLOYMENT (RECOMMENDED)

### Step 1: Launch EC2 Instance
1. Open the [AWS EC2 Management Console](https://console.aws.amazon.com/ec2/).
2. Click **Launch Instance**.
3. **Name**: `kifayat-ai-production`
4. **AMI**: **Ubuntu Server 24.04 LTS** or **22.04 LTS (HVM)**, SSD Volume Type (64-bit x86).
5. **Instance Type**:
   - **Recommended**: `t3.medium` (2 vCPUs, 4 GB RAM) — optimal performance for concurrent users.
   - **Minimum**: `t3.small` (2 vCPUs, 2 GB RAM) — supported via our automated 2GB swap file.
6. **Key Pair**: Create or select an RSA `.pem` key pair (e.g. `kifayat-key.pem`).
7. **Storage**: `20 GiB` to `30 GiB` gp3 SSD.

### Step 2: Security Group Configuration
In the **Network Settings** section, configure the firewall rules:
| Type | Protocol | Port Range | Source | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | TCP | `22` | My IP (or `0.0.0.0/0`) | Secure terminal access |
| **HTTP** | TCP | `80` | `0.0.0.0/0` | Web application traffic |
| **HTTPS** | TCP | `443` | `0.0.0.0/0` | Secure SSL web traffic |

*(Optional)* Attach an **Elastic IP** in EC2 console (*Network & Security -> Elastic IPs*) to prevent the public IP from changing upon reboot.

### Step 3: Connect via SSH
```bash
# On your local machine (macOS / Linux / Windows PowerShell)
chmod 400 kifayat-key.pem
ssh -i "kifayat-key.pem" ubuntu@YOUR_EC2_PUBLIC_IP
```

### Step 4: 1-Click Automated Installer
Clone the repository and run the production setup script:

```bash
# 1. Clone repository
git clone https://github.com/Niti741/First_Commit.git first_commit
cd first_commit

# 2. Make setup script executable and run
chmod +x deploy/ec2_setup.sh
./deploy/ec2_setup.sh
```

#### What the script handles automatically:
- Installs Python 3, `python3-venv`, build tools, Nginx, UFW firewall, and Certbot.
- Allocates a **2GB swap file** to protect small instances against Out-of-Memory crashes.
- Creates and configures Python virtual environment and installs `requirements.txt`.
- Registers and starts the `kifayat.service` systemd daemon (`Restart=always`).
- Configures Nginx with **zero-buffering SSE streaming** flags.
- Configures UFW firewall rules for ports 22, 80, and 443.
- Runs an automated health check against `http://127.0.0.1:8000/health`.

### Step 5: Configure Production Environment
Open `.env` to configure your live credentials:
```bash
nano .env
```
Update with your NVIDIA API key:
```ini
ENVIRONMENT=production
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-real-key-here
NVIDIA_MODEL=meta/llama-3.2-11b-vision-instruct
```
Save with `Ctrl + O` -> `Enter`, exit with `Ctrl + X`, and restart:
```bash
sudo systemctl restart kifayat
```

### Step 6: Free SSL/HTTPS with Let's Encrypt
If you have a domain pointing to your EC2 instance (e.g. `ai.yourdomain.com`):
```bash
# 1. Update domain in Nginx
sudo nano /etc/nginx/sites-available/kifayat
# Replace 'server_name _;' with 'server_name ai.yourdomain.com;'
sudo systemctl restart nginx

# 2. Run Certbot to generate and install SSL
sudo certbot --nginx -d ai.yourdomain.com
```

---

## 🐳 DOCKER & DOCKER COMPOSE DEPLOYMENT

For containerized deployment on any cloud host:

### 1. Install Docker & Docker Compose
```bash
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Configure Environment
```bash
cd first_commit
cp .env.production.example .env
nano .env
```

### 3. Launch Stack
```bash
# Build and start in background
docker compose up -d --build

# Verify container status
docker compose ps

# View live container logs
docker compose logs -f
```

---

## ⚙️ CRITICAL NGINX CONFIGURATION FOR REAL SSE STREAMING

When proxying Server-Sent Events (SSE) from FastAPI through Nginx, **buffering MUST be disabled**. If Nginx buffers responses, users will not receive streaming tokens in real time; instead, output will appear all at once after a long delay.

The configuration in [`deploy/nginx.conf`](file:///c:/Users/hi/Desktop/first_commit/first_commit/deploy/nginx.conf) enforces:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;

    # Headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # ZERO-BUFFERING FOR SERVER-SENT EVENTS (SSE)
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding on;
    proxy_set_header Connection '';

    # Extended timeouts for long-form generation & reasoning
    proxy_connect_timeout 60s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
}
```

---

## 🔑 ENVIRONMENT VARIABLES REFERENCE

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Environment mode (`production`, `local`, `testing`) |
| `LLM_PROVIDER` | `nvidia` | Active LLM inference provider (`nvidia`, `mock`, `bedrock`) |
| `NVIDIA_API_KEY` | *(None)* | Your NVIDIA NIM API key (`nvapi-...`) |
| `NVIDIA_MODEL` | `meta/llama-3.2-11b-vision-instruct` | Default fast model ID |
| `CHEAP_MODEL_ID` | `meta/llama-3.2-11b-vision-instruct` | Rung 1 fast repair model |
| `STRONG_MODEL_ID` | `meta/llama-3.1-70b-instruct` | Rung 3 frontier fallback model |
| `SQLITE_DB_PATH` | `backend/kifayat.db` | Path to persistent SQLite ACID database |
| `SEMANTIC_CACHE_ENABLED` | `true` | Enables 0-token vector response cache |
| `SEMANTIC_CACHE_THRESHOLD`| `0.90` | Cosine similarity threshold for cache hit |
| `STREAMING_ENABLED` | `true` | Enables native SSE token streaming |
| `MAX_OUTPUT_TOKENS` | `2048` | Maximum completion token ceiling |

---

## 🔍 HEALTH CHECKS & VERIFICATION

### 1. Check Gateway Health
```bash
curl http://localhost/health
```
Response:
```json
{
  "status": "ok",
  "provider": "multi_provider_router",
  "status_state": "Connecting",
  "configured": true,
  "app_id": "assistant",
  "version": "2.5.0"
}
```

### 2. Live NVIDIA NIM API Probe
```bash
curl -X POST http://localhost/v1/provider/test
```
Response:
```json
{
  "status": "healthy",
  "provider": "nvidia",
  "model": "meta/llama-3.2-11b-vision-instruct",
  "connected": true,
  "latency_ms": 1068
}
```

### 3. Test Native Real-Time Streaming
```bash
curl -N -X POST http://localhost/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello Kifayat, tell me one interesting fact about space.", "stream": true}'
```

---

## 🛠️ MAINTENANCE, LOGGING & OPERATIONS

| Task | Command |
| :--- | :--- |
| **Check service status** | `sudo systemctl status kifayat` |
| **View live logs (tail)** | `journalctl -u kifayat -f` |
| **Restart gateway** | `sudo systemctl restart kifayat` |
| **Stop gateway** | `sudo systemctl stop kifayat` |
| **Test Nginx syntax** | `sudo nginx -t` |
| **Restart Nginx** | `sudo systemctl restart nginx` |
| **View system resources** | `htop` |
| **Check memory & swap** | `free -h` |
| **Check disk space** | `df -h` |

---

## ❓ TROUBLESHOOTING & FAQ

### Q1: The browser cannot connect to `http://YOUR_IP/`
- **Cause**: Inbound ports are blocked in the AWS EC2 Security Group.
- **Solution**: Open AWS Console -> EC2 -> Instances -> Click your instance -> **Security** -> Edit Inbound Rules -> Add **HTTP (Port 80)** and **HTTPS (Port 443)** with source `0.0.0.0/0`.

### Q2: Tokens arrive all at once instead of streaming word-by-word
- **Cause**: Nginx response buffering is enabled.
- **Solution**: Ensure `/etc/nginx/sites-available/kifayat` contains `proxy_buffering off;` and `proxy_cache off;`, then run `sudo nginx -t && sudo systemctl restart nginx`.

### Q3: Server crashes with "Killed" or Out-of-Memory during setup
- **Cause**: The EC2 instance ran out of physical RAM while installing heavy wheels (e.g. numpy, scikit-learn).
- **Solution**: The setup script automatically creates a **2GB swap file** (`/swapfile`). If setting up manually, create swap space with:
  ```bash
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  ```

### Q4: 502 Bad Gateway error
- **Cause**: The FastAPI / Uvicorn service is stopped or failed to start.
- **Solution**: Check the traceback with `journalctl -u kifayat -n 50` and ensure your Python virtual environment and `.env` permissions are correct.
