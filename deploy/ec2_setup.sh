#!/usr/bin/env bash
# ==============================================================================
# KIFAYAT AI — ONE-CLICK AMAZON EC2 AUTOMATED PRODUCTION SETUP SCRIPT
# Target OS: Ubuntu 22.04 LTS / Ubuntu 24.04 LTS on AWS EC2
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}   KIFAYAT AI — AMAZON EC2 PRODUCTION INSTALLER & SETUP         ${NC}"
echo -e "${BLUE}================================================================${NC}"

# Check if running as non-root user with sudo capability
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}[ERROR] Please run this script as a normal user (e.g. 'ubuntu'), NOT as root.${NC}"
    echo -e "${YELLOW}The script will use 'sudo' internally when elevated privileges are required.${NC}"
    exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_USER="$(whoami)"

echo -e "${GREEN}[1/8] Updating system packages...${NC}"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo -e "${GREEN}[2/8] Installing core system dependencies, Python, and Nginx...${NC}"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    nginx \
    curl \
    git \
    ufw \
    certbot \
    python3-certbot-nginx

# 3. Create 2GB Swap file to prevent Out-Of-Memory (OOM) on smaller EC2 instances (e.g. t3.micro/t3.medium)
if [ ! -f /swapfile ]; then
    echo -e "${GREEN}[3/8] Allocating 2GB swap space for memory protection...${NC}"
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo -e "${GREEN}✓ 2GB swap file enabled.${NC}"
else
    echo -e "${GREEN}[3/8] Swap file already present. Skipping.${NC}"
fi

# 4. Set up Python virtual environment
echo -e "${GREEN}[4/8] Setting up Python virtual environment at ${APP_DIR}/venv...${NC}"
cd "${APP_DIR}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment and install packages
"${APP_DIR}/venv/bin/pip" install --upgrade pip setuptools wheel
"${APP_DIR}/venv/bin/pip" install -r requirements.txt

# 5. Configure environment variables
echo -e "${GREEN}[5/8] Checking production environment file...${NC}"
if [ ! -f "${APP_DIR}/.env" ]; then
    if [ -f "${APP_DIR}/.env.production.example" ]; then
        cp "${APP_DIR}/.env.production.example" "${APP_DIR}/.env"
        echo -e "${YELLOW}Created .env from .env.production.example.${NC}"
        echo -e "${YELLOW}IMPORTANT: Remember to edit ${APP_DIR}/.env and set your real NVIDIA_API_KEY!${NC}"
    else
        cat << 'EOF' > "${APP_DIR}/.env"
ENVIRONMENT=production
PROJECT_NAME="Kifayat AI"
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_MODEL=meta/llama-3.2-11b-vision-instruct
SQLITE_DB_PATH=backend/kifayat.db
STREAMING_ENABLED=true
EOF
    fi
    chmod 600 "${APP_DIR}/.env"
fi

# 6. Install systemd service
echo -e "${GREEN}[6/8] Configuring systemd service (kifayat.service)...${NC}"
sudo cp "${APP_DIR}/deploy/kifayat.service" /etc/systemd/system/kifayat.service

# Adjust user and working directory in service file if not default 'ubuntu'
sudo sed -i "s|User=ubuntu|User=${CURRENT_USER}|g" /etc/systemd/system/kifayat.service
sudo sed -i "s|Group=ubuntu|Group=${CURRENT_USER}|g" /etc/systemd/system/kifayat.service
sudo sed -i "s|/home/ubuntu/first_commit|${APP_DIR}|g" /etc/systemd/system/kifayat.service

sudo systemctl daemon-reload
sudo systemctl enable kifayat.service
sudo systemctl restart kifayat.service

# 7. Configure Nginx Reverse Proxy with Zero-Buffering SSE
echo -e "${GREEN}[7/8] Configuring Nginx reverse proxy...${NC}"
sudo cp "${APP_DIR}/deploy/nginx.conf" /etc/nginx/sites-available/kifayat
sudo ln -sf /etc/nginx/sites-available/kifayat /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration syntax
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# 8. Configure UFW Firewall
echo -e "${GREEN}[8/8] Configuring firewall rules (SSH, HTTP, HTTPS)...${NC}"
sudo ufw allow 22/tcp || true
sudo ufw allow 80/tcp || true
sudo ufw allow 443/tcp || true
sudo ufw --force enable || true

# Wait 3 seconds and verify service health
sleep 3
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}   VERIFYING LOCAL GATEWAY HEALTH                               ${NC}"
echo -e "${BLUE}================================================================${NC}"

HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8000/health || echo "FAILED")
echo "Gateway Health Response: ${HEALTH_RESPONSE}"

if [[ "$HEALTH_RESPONSE" == *"ok"* ]]; then
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${GREEN}🎉 KIFAYAT AI IS SUCCESSFULLY RUNNING ON YOUR EC2 INSTANCE!     ${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo -e "Access your application at: http://$(curl -s http://checkip.amazonaws.com || echo '<your-ec2-public-ip>')"
    echo ""
    echo -e "Next steps:"
    echo -e "1. Edit your NVIDIA API key in .env: ${YELLOW}nano ${APP_DIR}/.env${NC}"
    echo -e "   Then restart service: ${YELLOW}sudo systemctl restart kifayat${NC}"
    echo -e "2. Check service logs: ${YELLOW}journalctl -u kifayat -f${NC}"
    echo -e "3. Add Free HTTPS/SSL Domain: ${YELLOW}sudo certbot --nginx -d yourdomain.com${NC}"
else
    echo -e "${YELLOW}[NOTICE] Gateway is starting up. Check status using:${NC}"
    echo -e "  sudo systemctl status kifayat"
    echo -e "  journalctl -u kifayat -f"
fi
