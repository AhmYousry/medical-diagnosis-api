# Deployment Guide

## Architecture

```
GitHub Push (main)
    │
    ├─► Run tests  (test.yml)
    ├─► Build API image  → ghcr.io/<org>/medical-diagnosis-api:latest
    ├─► Build UI  image  → ghcr.io/<org>/medical-diagnosis-ui:latest
    └─► SSH into VPS → docker compose pull → docker compose up -d
```

---

## First-time VPS setup

```bash
# 1. On a fresh Ubuntu 22.04/24.04 server (as root):
bash scripts/vps-setup.sh

# 2. Upload your production .env
scp .env deploy@<VPS_IP>:/opt/medical-diagnosis/.env

# 3. Upload docker-compose.prod.yml
scp docker-compose.prod.yml deploy@<VPS_IP>:/opt/medical-diagnosis/
```

---

## Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `VPS_HOST` | Your server IP or domain |
| `VPS_USER` | `deploy` (created by setup script) |
| `VPS_SSH_KEY` | Private SSH key (`cat ~/.ssh/id_rsa`) |
| `VPS_PORT` | `22` |
| `DEPLOY_PATH` | `/opt/medical-diagnosis` |
| `PUBLIC_URL` | `https://yourdomain.com` |

---

## Deploying

CI/CD runs automatically on every push to `main`.

Manual deploy (from local machine):

```bash
cd /opt/medical-diagnosis   # on the VPS

# Set image tags (CI sets these automatically via env vars)
export API_IMAGE=ghcr.io/<org>/medical-diagnosis-api:latest
export UI_IMAGE=ghcr.io/<org>/medical-diagnosis-ui:latest

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

---

## Generating a JWT secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Useful commands on VPS

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f celery-worker

# Run migrations manually
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Restart a single service
docker compose -f docker-compose.prod.yml restart api

# Full teardown (keeps volumes / data safe)
docker compose -f docker-compose.prod.yml down
```
