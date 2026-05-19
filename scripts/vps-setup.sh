#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# VPS first-time setup script
# Run once on a fresh Ubuntu 22.04 / 24.04 server as root or sudo user.
# Usage: bash vps-setup.sh
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/medical-diagnosis}"

echo "==> Installing Docker..."
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

echo "==> Creating deploy user: ${DEPLOY_USER}"
id -u "${DEPLOY_USER}" &>/dev/null || useradd -m -s /bin/bash "${DEPLOY_USER}"
usermod -aG docker "${DEPLOY_USER}"

echo "==> Creating deploy directory: ${DEPLOY_PATH}"
mkdir -p "${DEPLOY_PATH}"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_PATH}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ VPS setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy your SSH public key to the deploy user:"
echo "     ssh-copy-id ${DEPLOY_USER}@<your-server-ip>"
echo ""
echo "  2. Upload your .env file to the server:"
echo "     scp .env ${DEPLOY_USER}@<your-server-ip>:${DEPLOY_PATH}/.env"
echo ""
echo "  3. Upload docker-compose.prod.yml:"
echo "     scp docker-compose.prod.yml ${DEPLOY_USER}@<your-server-ip>:${DEPLOY_PATH}/"
echo ""
echo "  4. Add these GitHub Secrets to your repository:"
echo "     VPS_HOST      → your server IP or domain"
echo "     VPS_USER      → ${DEPLOY_USER}"
echo "     VPS_SSH_KEY   → contents of ~/.ssh/id_rsa (private key)"
echo "     VPS_PORT      → 22 (or your custom SSH port)"
echo "     DEPLOY_PATH   → ${DEPLOY_PATH}"
echo "     PUBLIC_URL    → https://yourdomain.com"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
