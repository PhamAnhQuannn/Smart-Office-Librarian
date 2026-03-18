# Troubleshooting Guide

**Last Updated:** 2026-01-01

---

## Backend won't start

### `ModuleNotFoundError: No module named 'app'`
Run from the `backend/` directory with the virtual environment active:
```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
```

### `sqlalchemy.exc.OperationalError: could not connect to server`
PostgreSQL is not running. Start it:
```bash
docker compose -f infra/docker/docker-compose.dev.yml up -d postgres
```

### `redis.exceptions.ConnectionError`
Redis is not running:
```bash
docker compose -f infra/docker/docker-compose.dev.yml up -d redis
```

---

## Tests failing

### `pytest` cannot find conftest fixtures
Ensure you run pytest from the `backend/` directory.

### `ImportError: email-validator is not installed`
Use `str` instead of `EmailStr` in Pydantic models, or install the package:
```bash
pip install "pydantic[email]"
```

### Integration tests fail with `Connection refused`
Integration tests that require live services will fail without Docker running.  
Use `pytest tests/unit/` to run only unit tests.

---

## Frontend issues

### `npm run dev` fails with missing env
Copy the example env file:
```bash
cp frontend/.env.local.example frontend/.env.local
```
Fill in `NEXT_PUBLIC_API_URL` and `BACKEND_API_URL`.

### TypeScript errors after pulling
Run `npm install` — a dependency may have changed.

### SSE stream doesn't load
Check the browser console. Common causes:
- Backend not running on expected port
- `BACKEND_API_URL` not set in `frontend/.env.local`
- CORS misconfiguration — check `ALLOWED_ORIGINS` in backend config

---

## Pinecone / embedding issues

### `pinecone.core.client.exceptions.NotFoundException`
The index does not exist. Create it in the Pinecone console matching `PINECONE_INDEX` env var.

### `openai.AuthenticationError`
`OPENAI_API_KEY` is missing or invalid.

### Queries return no results
- Check that ingestion has run at least once: `GET /api/v1/ingest/runs`
- Verify the namespace matches between ingest and query requests
- Lower the similarity threshold if it's too strict: `POST /api/v1/thresholds`

---

## Common Docker issues

### Port already in use
A previous container is still running. Find and stop it:
```bash
docker ps | grep 8000
docker stop <container_id>
```

### Volume permissions on Linux
```bash
sudo chown -R $USER:$USER ./data
```

---

## Celery worker not processing tasks

1. Check worker logs: `docker logs embedlyzer-worker`
2. Verify Redis is reachable: `redis-cli -u $REDIS_URL ping`
3. Check task queue: `celery -A app.workers.celery_app inspect active`
4. Restart worker: `docker compose restart worker`
