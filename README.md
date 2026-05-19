<div align="center">

# 🧠 MedScan AI — Medical Diagnosis Platform

**AI-powered medical scan analysis with real-time results**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![CI](https://img.shields.io/github/actions/workflow/status/AhmYousry/medical-diagnosis-api/test.yml?style=flat-square&label=tests)](https://github.com/AhmYousry/medical-diagnosis-api/actions)

[Features](#-features) · [Architecture](#-architecture) · [Tech Stack](#-tech-stack) · [Quick Start](#-quick-start) · [API Docs](#-api-docs)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔴 **Real-time Results** | WebSocket + Redis pub/sub — results stream to the browser the moment the AI finishes, zero polling |
| 🧠 **AI Diagnosis** | Deep learning model (CheXNet) analyzes chest X-rays with per-class confidence scoring |
| 👨‍⚕️ **Doctor Verification** | Role-based system with admin approval workflow for verified doctors |
| 🔐 **JWT Auth** | Access + refresh token rotation with automatic silent refresh |
| 📧 **Email Verification** | One-time token flow with branded HTML emails; secure password reset with 2-hour expiry |
| 📁 **Secure Uploads** | MIME + magic-bytes validation, SHA-256 checksums, configurable size limits |
| ☁️ **S3/Cloudflare R2 Storage** | Pluggable storage backend — swap local disk for S3-compatible object storage with one env var |
| 🛡️ **Production-grade Security** | Rate limiting, security headers (HSTS/CSP), CORS, Swagger disabled in prod |
| 📊 **Admin Dashboard** | Full admin panel — user management, prediction monitoring, doctor approvals |
| 🔍 **Sentry Monitoring** | Full-stack error tracking (FastAPI + React) with performance tracing and session replay |
| 🚀 **CI/CD Pipeline** | Tests → Docker build → GHCR push → SSH deploy on every push to `main` |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│  React 19 + TypeScript + Framer Motion + TanStack Query     │
└────────────────────┬──────────────────┬─────────────────────┘
                     │ HTTP/REST         │ WebSocket
                     ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    nginx (reverse proxy)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI  (4 Uvicorn workers)                    │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Auth Module │  │ Predictions  │  │   Admin Module    │  │
│  │  JWT + RBAC  │  │  WebSocket   │  │   Users/Doctors   │  │
│  └─────────────┘  └──────┬───────┘  └───────────────────┘  │
└────────────────────────── │ ────────────────────────────────┘
                            │ publish
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                   ▼
   ┌──────────┐      ┌──────────┐       ┌─────────────┐
   │PostgreSQL│      │  Redis   │       │Celery Worker│
   │  (data)  │      │(pub/sub) │◄──────│ (AI tasks)  │
   └──────────┘      └──────────┘       └──────┬──────┘
                                               │ HTTP
                                               ▼
                                        ┌─────────────┐
                                        │  AI Model   │
                                        │  (PyTorch)  │
                                        └─────────────┘
```

### Real-time WebSocket Flow
```
1. POST /api/v1/uploads              → upload scan
2. POST /api/v1/predict/{file_id}    → queue Celery task, return prediction id
3. WS   /api/v1/predict/{id}/ws      → browser subscribes to Redis channel
4. Celery processes scan             → publishes {status: "processing"} to Redis
5. AI model returns result           → publishes {status: "completed", label, confidence}
6. FastAPI streams to WebSocket      → browser updates live, no refresh needed
```

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 (async) |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Task Queue | Celery 5 + Redis 7 |
| Real-time | WebSockets + Redis pub/sub |
| Validation | Pydantic v2 |
| Auth | PyJWT + bcrypt |
| Server | Uvicorn (4 workers) |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | React 19 + TypeScript 6 |
| State | TanStack Query v5 + Zustand |
| Animation | Framer Motion 11 |
| Build | Vite 8 |
| Serving | nginx 1.27 |

### Infrastructure
| Concern | Tool |
|---------|------|
| Containerization | Docker + Compose |
| Reverse Proxy | nginx |
| CI/CD | GitHub Actions |
| Registry | GitHub Container Registry (GHCR) |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose v2
- Node.js 20+ (frontend dev only)

### Local development

```bash
# 1. Clone both repos
git clone https://github.com/AhmYousry/medical-diagnosis-api
git clone https://github.com/AhmYousry/medical-diagnosis-ui

# 2. Start backend services
cd medical-diagnosis-api
cp .env.example .env          # edit passwords & JWT secret
docker compose up -d

# 3. Run migrations (first time)
docker compose exec api alembic upgrade head

# 4. Start frontend
cd ../medical-diagnosis-ui
npm install && npm run dev
```

→ Frontend: [http://localhost:5173](http://localhost:5173)
→ API docs:  [http://localhost:8000/docs](http://localhost:8000/docs)

### Production deploy

```bash
cd medical-diagnosis-api
cp .env.example .env   # set strong secrets + PUBLIC_URL
docker compose -f docker-compose.prod.yml up -d
```

See [DEPLOY.md](./DEPLOY.md) for automated CI/CD + VPS setup guide.

---

## 📡 API Reference

Swagger UI available at `/docs` (local environment only).

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/auth/register` | — | Register new user |
| `POST` | `/api/v1/auth/login` | — | Login → tokens |
| `POST` | `/api/v1/auth/refresh` | — | Refresh access token |
| `POST` | `/api/v1/auth/verify-email` | — | Verify email with one-time token |
| `POST` | `/api/v1/auth/resend-verification` | — | Resend verification email |
| `POST` | `/api/v1/auth/forgot-password` | — | Send password reset link |
| `POST` | `/api/v1/auth/reset-password` | — | Reset password with token |
| `POST` | `/api/v1/uploads` | ✓ | Upload medical scan |
| `GET`  | `/api/v1/uploads/{id}` | ✓ | Get upload details |
| `POST` | `/api/v1/predict/{file_id}` | ✓ | Start AI prediction |
| `GET`  | `/api/v1/predict` | ✓ | List my predictions |
| `GET`  | `/api/v1/predict/{id}` | ✓ | Get prediction result |
| `WS`   | `/api/v1/predict/{id}/ws` | ✓ | **Real-time updates** |
| `GET`  | `/api/v1/admin/users` | Admin | List all users |
| `GET`  | `/api/v1/admin/predictions` | Admin | List all predictions |
| `GET`  | `/api/v1/health/live` | — | Health check |

---

## 🔒 Security Highlights

- JWT access tokens (15 min expiry) + rotating refresh tokens (30 days)
- Passwords hashed with bcrypt (cost factor 12)
- Rate limiting: 100 req/min global · 20 req/min on auth endpoints
- Security headers: `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- File uploads: MIME type + magic bytes validation + SHA-256 integrity check
- CORS: restricted to configured origins — no wildcard in production
- Swagger/ReDoc: disabled in production (`ENVIRONMENT != local`)

---

## 🧪 Running Tests

```bash
cd medical-diagnosis-api
pip install -r requirements.txt -r tests/requirements-dev.txt
pytest --cov=app --cov-report=term -v
```

---

## 📁 Repository Structure

```
medical-diagnosis-api/
├── app/
│   ├── api/v1/          # Routers + route definitions
│   ├── core/            # Config, logging, middleware, WebSocket manager
│   ├── db/              # SQLAlchemy models, session, enums
│   ├── infrastructure/  # AI HTTP client, file storage, retry logic
│   └── modules/         # Feature modules
│       ├── auth/        # JWT, login, register, refresh
│       ├── predictions/ # Prediction CRUD + WebSocket endpoint
│       ├── uploaded_files/
│       ├── doctors/
│       ├── admin/
│       └── notifications/
├── alembic/             # Database migration scripts
├── tests/               # pytest test suite
├── scripts/             # VPS setup script
├── Dockerfile           # Multi-stage production image
├── docker-compose.yml         # Local dev
├── docker-compose.prod.yml    # Production
└── .github/workflows/
    ├── test.yml         # Run tests on every PR
    └── deploy.yml       # Build → push → deploy on main
```

---

<div align="center">
  <sub>Built by <a href="https://github.com/AhmYousry">Ahmed Yousry</a></sub>
</div>
