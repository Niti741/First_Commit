# 🚀 KIFAYAT AI — COMPLETE AMAZON EC2 PRODUCTION DEPLOYMENT GUIDE

This guide provides a comprehensive, step-by-step walkthrough for deploying **Kifayat AI** onto an **Amazon Web Services (AWS) EC2** instance with high availability, automated process recovery, real-time Server-Sent Events (SSE) streaming, and free SSL/HTTPS encryption.

---

## 🏗️ ARCHITECTURE OVERVIEW ON AWS

```
                            [ USER BROWSER ]
                                   │
                                   │ HTTPS (443) / HTTP (80)
                                   ▼
                       [ AWS INTERNET GATEWAY ]
                                   │
                                   ▼
                   [ EC2 SECURITY GROUP FIREWALL ]
                   (Inbound: 22 SSH, 80 HTTP, 443 HTTPS)
                                   │
                                   ▼
┌───────────────────────── AMAZON EC2 INSTANCE ──────────────────────────┐
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

## 📌 PREREQUISITES

1. An **AWS Account** ([aws.amazon.com](https://aws.amazon.com/)).
2. An SSH client (Terminal on macOS/Linux, PowerShell or PuTTY on Windows).
3. Your **NVIDIA API Key** (`nvapi-...`).
4. *(Optional but recommended)* A custom domain name (e.g. `ai.yourdomain.com`).

---

## STEP 1: LAUNCH THE AMAZON EC2 INSTANCE

1. Log in to the [AWS Management Console](https://console.aws.amazon.com/).
2. In the search bar, type **EC2** and navigate to the **EC2 Dashboard**.
3. Click the orange **Launch Instance** button.
4. Configure the instance parameters as follows:
   - **Name**: `kifayat-ai-production`
   - **Application and OS Images (AMI)**: Select **Ubuntu** -> **Ubuntu Server 24.04 LTS** or **22.04 LTS (HVM), SSD Volume Type** (64-bit x86).
   - **Instance Type**:
     - *Recommended*: `t3.medium` (2 vCPUs, 4 GB RAM) — ideal for production multi-worker gateway.
     - *Minimum*: `t3.small` (2 vCPUs, 2 GB RAM) — works when paired with our automated 2GB swap space.
   - **Key Pair (login)**:
     - Click **Create new key pair**.
     - Name: `kifayat-key`
     - Key pair type: **RSA**
     - Private key file format: `.pem` (for OpenSSH / macOS / Linux / Windows PowerShell).
     - Click **Create key pair** and save the downloaded `kifayat-key.pem` file securely.
   - **Network Settings (Firewall / Security Group)**:
     - Check **Allow SSH traffic from** -> Select *My IP* (or *Anywhere 0.0.0.0/0* if working from multiple locations).
     - Check **Allow HTTP traffic from the internet** (Port 80).
     - Check **Allow HTTPS traffic from the internet** (Port 443).
   - **Configure Storage**:
     - Size: **20 GiB** to **30 GiB**
     - Volume type: **gp3** (General Purpose SSD).
5. Click **Launch Instance** at the bottom right.

---

## STEP 2: ATTACH AN ELASTIC IP (RECOMMENDED)

By default, an EC2 instance's public IP changes every time you stop and start it. An Elastic IP gives you a permanent, static IPv4 address.

1. In the EC2 console left sidebar, click **Elastic IPs** (under *Network & Security*).
2. Click **Allocate Elastic IP address** -> click **Allocate**.
3. Select your newly allocated IP -> click **Actions** -> **Associate Elastic IP address**.
4. Choose your `kifayat-ai-production` instance and click **Associate**.

---

## STEP 3: CONNECT TO YOUR EC2 INSTANCE VIA SSH

### On Windows (PowerShell) / macOS / Linux:
Open your terminal, navigate to the folder where your `kifayat-key.pem` is stored, and run:

```bash
# 1. Set correct read-only permissions on your private key (required by SSH)
chmod 400 kifayat-key.pem

# 2. Connect to your EC2 instance (replace with your Elastic IP)
ssh -i "kifayat-key.pem" ubuntu@YOUR_EC2_ELASTIC_IP
```

> **Tip for Windows users:** If you receive a *bad permissions* error on Windows, right-click `kifayat-key.pem` -> Properties -> Security -> Advanced -> Disable Inheritance -> Remove all permissions -> Add only your user with Read permission.

---

## STEP 4: TRANSFER YOUR CODE TO EC2

Choose **Option A** (Git Clone) or **Option B** (Direct SCP Upload):

### Option A: Via Git (Recommended)
On your EC2 terminal:
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git first_commit
cd first_commit
```

### Option B: Upload from Local Machine via SCP
Run this command from your local development machine:
```bash
# Run this on your local computer (PowerShell / Terminal)
scp -i "path/to/kifayat-key.pem" -r "c:\Users\hi\Desktop\first_commit\first_commit" ubuntu@YOUR_EC2_ELASTIC_IP:~/first_commit
```

---

## STEP 5: 1-CLICK AUTOMATED DEPLOYMENT (FASTEST)

We have provided an automated production installer script in [`deploy/ec2_setup.sh`](file:///c:/Users/hi/Desktop/first_commit/first_commit/deploy/ec2_setup.sh).

Once your code is on the EC2 instance, run:

```bash
# Navigate to the project directory
cd ~/first_commit

# Make the setup script executable and run it
chmod +x deploy/ec2_setup.sh
./deploy/ec2_setup.sh
```

### What This Script Automatically Does:
1. Updates system packages (`apt-get update && upgrade`).
2. Installs Python 3, virtual environment tools, build tools, Nginx, UFW firewall, and Certbot.
3. Allocates a **2GB swap file** to protect the instance against Out-of-Memory crashes during heavy dependency builds.
4. Creates the Python virtual environment (`venv`) and installs `requirements.txt`.
5. Sets up the `.env` production file.
6. Installs and registers the `kifayat.service` systemd daemon with automatic recovery (`Restart=always`).
7. Configures Nginx with **zero-buffering SSE streaming** flags.
8. Configures the UFW firewall for ports 22, 80, and 443.
9. Executes a local gateway health check against `http://127.0.0.1:8000/health`.

---

## STEP 6: CONFIGURE YOUR NVIDIA API KEY

After running the setup script, configure your real credentials:

```bash
# Open the .env file in nano editor
nano ~/first_commit/.env
```

Set your production settings:
```ini
ENVIRONMENT=production
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-actual-nvidia-api-key-here
NVIDIA_MODEL=meta/llama-3.2-11b-vision-instruct
```

Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit.

Then restart the service to apply the new key:
```bash
sudo systemctl restart kifayat
```

---

## STEP 7: VERIFY DEPLOYMENT & STREAMING

### 1. Test Gateway Health:
```bash
curl http://localhost/health
```
Expected output:
```json
{"status":"ok","provider":"multi_provider_router","status_state":"Connecting","configured":true,"app_id":"assistant","version":"2.5.0"}
```

### 2. Test Real Token Streaming via curl:
```bash
curl -N -X POST http://localhost/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello Kifayat, tell me one interesting fact about space.", "stream": true}'
```

### 3. Open in Browser:
Open your browser and navigate to:
```
http://YOUR_EC2_ELASTIC_IP/
```
You will see the full Kifayat AI interface running live!

---

## STEP 8: FREE SSL/HTTPS SETUP WITH LET'S ENCRYPT (OPTIONAL)

If you have a domain name pointed to your EC2 Elastic IP (e.g. `ai.yourdomain.com` with an `A` record):

1. Update the server name in Nginx:
   ```bash
   sudo nano /etc/nginx/sites-available/kifayat
   ```
   Change `server_name _;` to:
   ```nginx
   server_name ai.yourdomain.com;
   ```
   Save and restart Nginx:
   ```bash
   sudo systemctl restart nginx
   ```

2. Run Certbot to automatically issue and install the free Let's Encrypt SSL certificate:
   ```bash
   sudo certbot --nginx -d ai.yourdomain.com
   ```
   - Enter your email address for renewal notices.
   - Agree to the Terms of Service.
   - Certbot will automatically rewrite your Nginx configuration for HTTPS (Port 443) and set up automatic 90-day certificate renewals!

Now access your app securely at: `https://ai.yourdomain.com/`

---

## STEP 9: DOCKER COMPOSE ALTERNATIVE (CONTAINER DEPLOYMENT)

If you prefer deploying via Docker on EC2:

1. Install Docker on EC2:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2
   sudo usermod -aG docker ubuntu
   newgrp docker
   ```

2. Configure `.env`:
   ```bash
   cp .env.production.example .env
   nano .env
   ```

3. Launch with Docker Compose:
   ```bash
   docker compose up -d --build
   ```

4. Check container status:
   ```bash
   docker compose ps
   docker compose logs -f
   ```

---

## 🛠️ USEFUL PRODUCTION OPERATIONS & COMMANDS

| Action | Command |
| :--- | :--- |
| **Check Gateway Status** | `sudo systemctl status kifayat` |
| **View Live Streamed Logs** | `journalctl -u kifayat -f` |
| **Restart Application** | `sudo systemctl restart kifayat` |
| **Stop Application** | `sudo systemctl stop kifayat` |
| **Check Nginx Status** | `sudo systemctl status nginx` |
| **Test Nginx Config** | `sudo nginx -t` |
| **Restart Nginx** | `sudo systemctl restart nginx` |
| **View Server Resource Usage** | `htop` or `top` |
| **Check Disk & Swap Space** | `free -h` and `df -h` |

---

## 🔍 TROUBLESHOOTING & FAQ

### Q1: The browser times out and cannot connect to http://YOUR_IP/
- **Cause**: AWS EC2 Security Group is blocking inbound traffic.
- **Fix**: Go to AWS Console -> EC2 -> Instances -> Click your instance -> **Security** tab -> Click the Security Group link -> **Edit inbound rules** -> Add Rule:
  - Type: **HTTP** | Port: **80** | Source: **Anywhere-IPv4 (0.0.0.0/0)**
  - Type: **HTTPS** | Port: **443** | Source: **Anywhere-IPv4 (0.0.0.0/0)**
  - Save rules.

### Q2: Tokens appear all at once instead of streaming word-by-word
- **Cause**: Nginx response buffering is enabled.
- **Fix**: Verify [`deploy/nginx.conf`](file:///c:/Users/hi/Desktop/first_commit/first_commit/deploy/nginx.conf) contains:
  ```nginx
  proxy_buffering off;
  proxy_cache off;
  chunked_transfer_encoding on;
  proxy_set_header Connection '';
  ```
  Run `sudo nginx -t && sudo systemctl restart nginx`.

### Q3: `pip install` fails or server crashes with "Killed" (Out-of-Memory)
- **Cause**: Small instances (`t3.micro` or `t3.small`) ran out of physical RAM.
- **Fix**: The `deploy/ec2_setup.sh` script automatically creates a **2GB swap file** to solve this. If setting up manually, create swap space with:
  ```bash
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  ```

### Q4: 502 Bad Gateway error in browser
- **Cause**: Uvicorn is not running or crashed.
- **Fix**: Run `sudo systemctl status kifayat` and `journalctl -u kifayat -n 50` to inspect the exact Python traceback. Usually, this is caused by a missing package or incorrect file permissions on `.env`.
