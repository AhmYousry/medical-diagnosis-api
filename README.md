# Medical Diagnosis API

Production-oriented FastAPI backend scaffold for an AI medical image classification platform.

This repository currently contains architecture and infrastructure only. No domain or AI business logic is implemented yet.

## Stack

- FastAPI
- PostgreSQL
- SQLAlchemy 2.0 async ORM
- Alembic
- Redis
- Docker Compose
- Pydantic v2

## Project Layout

```text
.
|-- ai_service/              # Separately deployable AI service shell
|-- alembic/                 # Database migration environment
|-- app/
|   |-- api/                 # Versioned API routers
|   |-- core/                # Settings and infrastructure config
|   |-- db/                  # Database base, session, metadata
|   |-- infrastructure/      # External service clients
|   |-- modules/             # Future domain modules
|   `-- main.py              # FastAPI application factory
|-- docker-compose.yml
|-- Dockerfile
|-- requirements.txt
`-- .env.example
```

## Run Locally With Docker

```bash
docker compose up --build
```

> **First time?** After containers start, apply database migrations:
> ```bash
> docker compose run --rm api alembic upgrade head
> ```

API:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/api/v1/health`
- Readiness check: `http://localhost:8000/api/v1/health/ready`

AI service shell:

- Health check: `http://localhost:8001/health`

## Migrations

Create a migration:

```bash
docker compose run --rm api alembic revision --autogenerate -m "initial"
```

Apply migrations:

```bash
docker compose run --rm api alembic upgrade head
```

## Configuration

Environment variables are loaded from `.env`. Use `.env.example` as the template for deployment-specific values.

## Architecture Rules

- Routes handle HTTP concerns only.
- Services own use-case orchestration.
- Repositories own persistence.
- Schemas define API contracts.
- SQLAlchemy models stay in module-level `models.py` files.
- AI integration should be isolated behind an infrastructure service/client.
