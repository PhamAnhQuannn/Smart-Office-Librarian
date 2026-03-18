# Development Guide

**Last Updated:** 2026-01-01

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Python | 3.11 |
| Node.js | 18 LTS |
| Docker Desktop | 4.x |
| Git | 2.40 |

---

## Quick start

### 1 — Clone and enter the repo

```bash
git clone https://github.com/your-org/embedlyzer.git
cd embedlyzer
```

### 2 — Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy env and fill in secrets
cp ../.env.example .env.local
# Edit .env.local — set OPENAI_API_KEY, PINECONE_API_KEY, DATABASE_URL, etc.

# Start supporting services
docker compose -f ../infra/docker/docker-compose.dev.yml up -d

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### 3 — Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000 and BACKEND_API_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment variables

See `.env.example` in the repository root for the full list.  
Required secrets:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `OPENAI_API_KEY` | OpenAI API key |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX` | Pinecone index name |
| `JWT_SECRET` | HS256 signing secret (min 32 chars) |

---

## Running tests

```bash
cd backend
pytest                       # all tests
pytest tests/unit/           # unit tests only
pytest tests/integration/    # integration tests only
pytest -x -q                 # fail-fast, quiet
pytest --cov=app --cov-report=term-missing   # with coverage
```

```bash
cd frontend
npm test
```

---

## Code style

- **Python:** `black` + `isort` + `ruff`. Run `ruff check .` before committing.
- **TypeScript:** `eslint` + `prettier`. Run `npm run lint` before committing.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:` …).

---

## Docker-based full-stack run

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

This starts: PostgreSQL, Redis, Caddy (reverse proxy), backend API, frontend, Celery worker, Prometheus, Grafana.

---

## Seeding the database

```bash
cd backend
python scripts/seed_db.py                # insert admin user + sample sources
python scripts/seed_db.py --reset        # drop tables first, then seed (DEV ONLY)
```

Default admin credentials: `admin@example.com` / `changeme123!`
