# 🧰 Tech Stack — Smart Office Librarian

**Deployment Model:** Budget-Optimized Production Setup  
**Target Cost:** $18-25/month for 100 users  
**Infrastructure:** Amazon Lightsail VPS (Single Instance)

Detailed listing of the production environment for the Enterprise Knowledge Agent optimized for cost-efficiency while maintaining production-grade quality.

> **Note:** This tech stack is designed for startups and small teams prioritizing cost efficiency. For enterprise scale (>500 users, >50k queries/month), see the [Upgrade Path & Scaling Strategy](#upgrade-path--scaling-strategy) section.

---

## Backend Architecture

| Technology | Version/Type | Purpose |
|------------|--------------|---------|
| **Python** | 3.11+ | Primary backend language for API and ML pipelines |
| **FastAPI** | Latest | High-performance async web framework |
| **Uvicorn / Gunicorn** | Latest | Production-grade ASGI server for handling concurrent requests |
| **Celery + Redis** | Latest | Asynchronous task queue for document ingestion and background processing |
| **PostgreSQL + Alembic** | 15+ | Relational storage for metadata and audit logs, with Alembic for versioned database migrations |
| **Pydantic** | v2+ | Strict type validation and settings management |
| **tiktoken** | Latest | Precise token counting for LLM budget enforcement |

### Key Backend Dependencies

- FastAPI, Uvicorn, Gunicorn for API serving
- Celery, Redis for background job processing
- SQLAlchemy, Alembic, asyncpg, psycopg2 for database operations
- OpenAI SDK, tiktoken, LangChain, SentenceTransformers for AI/ML
- Python-jose, Passlib for authentication and security
- HTTPX for async HTTP client operations

---

## Frontend & UI

| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 14+ (App Router) | Modern frontend framework for responsive, type-safe user interface |
| **React** | 18+ | UI component framework |
| **TypeScript** | 5+ | Type-safe JavaScript development |
| **Tailwind CSS** | 3+ | Utility-first styling for rapid, consistent UI development |
| **shadcn/ui** | Latest | Accessible, high-quality UI components built on Radix UI |
| **Server-Sent Events (SSE)** | Native | Real-time streaming of LLM-generated responses |

### Key Frontend Dependencies

**Core Framework:**
- Next.js 14+, React 18+, TypeScript 5+
- Tailwind CSS for styling

**UI Components:**
- Radix UI primitives (Dialog, Dropdown Menu, Select)
- Lucide React for icons
- shadcn/ui component library

**Development Tools:**
- ESLint, Prettier for code quality
- TypeScript type definitions for Node, React, and React DOM

---

## AI & Machine Learning

| Technology | Model/Version | Purpose |
|------------|---------------|---------|
| **OpenAI Embeddings** | `text-embedding-3-small` (768d) | Cost-effective semantic representation with 62% lower cost than large model |
| **LLM Layer (Primary)** | `gpt-4o-mini` | Budget-friendly model with strong performance for RAG tasks |
| **LLM Layer (Fallback)** | Disabled (for cost control) | Can be enabled with `claude-3-haiku` if needed |
| **Reranker** | Cross-Encoder (SentenceTransformers) | Self-hosted inference within backend worker for improved precision |
| **LangChain** | 0.1+ | RAG chain orchestration (may be replaced by direct SDK calls for production stability) |

### Model Selection Rationale (Budget-Optimized)

| Component | Choice | Why? |
|-----------|--------|------|
| **Embedding Model** | OpenAI `text-embedding-3-small` | 768 dimensions, 62% cheaper than large model, sufficient for most use cases |
| **Primary LLM** | gpt-4o-mini | 60% cheaper than gpt-4o, optimized for efficiency while maintaining quality |
| **Fallback LLM** | Disabled | To control costs; can enable `claude-3-haiku` if high availability is critical |
| **Reranker** | SentenceTransformers Cross-Encoder | Self-hosted for $0 cost; significantly improves top-k precision |

**Cost vs. Premium Setup:**
- Embedding cost: **-62%** (small vs. large model)
- LLM cost: **-60%** (gpt-4o-mini vs. gpt-4o)
- Total AI/ML savings: ~**$280/month** compared to premium setup

---

## Data Storage

| Technology | Type | Purpose |
|------------|------|---------|
| **Pinecone (Free Tier)** | Vector Database (Managed) | Free tier: 1 index, 100k vectors, serverless pod - sufficient for MVP and small teams |
| **PostgreSQL** | Relational Database | User sessions, source metadata, audit logs running in Docker on Lightsail |
| **Redis** | In-Memory Store | Multi-purpose: cache, Celery message broker, rate-limiting - running in Docker |

### Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│          Lightsail VPS (All services containerized)          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Application Layer (FastAPI)              │  │
│  └─────────────────────┬───────────────────────────────┬─┘  │
│                        │                               │    │
│        ┌───────────────┼───────────────┐               │    │
│        │               │               │               │    │
│  ┌─────▼────────┐ ┌───▼────────┐ ┌───▼──────────┐    │    │
│  │  PostgreSQL  │ │   Redis    │ │ Pinecone API │────┼────┼─→ External
│  │   (Docker)   │ │  (Docker)  │ │  (Free Tier) │    │    │
│  └──────────────┘ └────────────┘ └──────────────┘    │    │
└─────────────────────────────────────────────────────────────┘
```

### Pinecone Free Tier Limits

- **Vectors:** Up to 100,000 vectors (sufficient for ~200-300 documents)
- **Indexes:** 1 index
- **Queries:** Unlimited reads
- **Performance:** Serverless pod with cold starts (may add 1-2s latency)
- **Upgrade Path:** When exceeding 80k vectors, upgrade to Starter plan ($70/month) for 1M vectors

### Database Schema (PostgreSQL)

**Core Tables:**
- **users** - Authentication and role management (admin/user)
- **sources** - Document source configuration (GitHub, Confluence, Google Docs)
- **chunks** - Document chunk metadata with vector IDs and content hashes
- **query_logs** - Query performance metrics and user feedback
- **audit_logs** - Security audit trail for all system actions

**Key Fields:**
- UUID primary keys for all entities
- Foreign key relationships with CASCADE delete for data integrity
- Timestamp tracking for created_at and updated_at
- Indexed fields for high-performance queries (source_id, vector_id, user_id, created_at)

---

## Cloud & DevOps (Budget-Friendly Setup)

### Infrastructure Components

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Docker & Docker Compose** | Containerization | Local development and production deployment |
| **Amazon Lightsail** | VPS Hosting | Single 2GB instance hosting all services (API, Worker, PostgreSQL, Redis) |
| **Caddy / Nginx** | Reverse Proxy | SSL termination, static file serving, rate limiting |
| **S3** | (Optional) Object Storage | Document backups, logs archival if needed |
| **CloudWatch** | (Optional) Monitoring | Minimal logging with low retention |
| **GitHub Actions** | CI/CD Pipeline | Automated deployment via SSH to Lightsail instance |

### Lightsail Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet Users                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTPS (Let's Encrypt)
                            │
┌───────────────────────────▼─────────────────────────────────┐
│            Amazon Lightsail VPS (2GB RAM)                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Caddy/Nginx (Reverse Proxy + SSL)                     │ │
│  └──────────┬──────────────────────────────────────────────┘ │
│             │                                                  │
│  ┌──────────▼──────────┐  ┌──────────────┐                  │
│  │  FastAPI (Uvicorn)  │  │ Celery Worker│                  │
│  └──────────┬──────────┘  └──────┬───────┘                  │
│             │                     │                           │
│  ┌──────────▼─────────────────────▼───────┐                 │
│  │  PostgreSQL 15 + Redis 7  (Docker)     │                 │
│  └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ API Calls
                            │
                 ┌──────────▼──────────┐
                 │  Pinecone (External)│
                 │  OpenAI API         │
                 └─────────────────────┘
```

### Infrastructure Setup (Docker Compose on Lightsail)

**Deployment Approach:**
- Single Lightsail VPS instance (2GB RAM, 60GB SSD)
- Docker Compose orchestrating all services
- Caddy for automatic HTTPS with Let's Encrypt
- Environment variables stored in `.env` file
- Automated backups to S3 (optional)
- GitHub Actions for CI/CD via SSH deployment

### CI/CD Pipeline (GitHub Actions)

**Pipeline Stages:**
1. **Code Quality** - Linting (ruff, black, eslint, prettier)
2. **Testing** - Backend unit tests (pytest), Frontend tests (Jest)
3. **Build** - Docker image creation locally on Lightsail
4. **Deploy** - SSH into Lightsail, pull latest code, restart Docker Compose services

**Deployment Method:**
- GitHub Actions connects to Lightsail via SSH
- Pulls latest code from repository
- Runs `docker-compose pull && docker-compose up -d --build`
- Zero-downtime deployment with health checks

**Branching Strategy:**
- `main` branch → Production deployment to Lightsail
- Feature branches → Run tests only, no deployment

---

## Quality & Observability

### Testing & Code Quality

| Tool | Purpose | Target Coverage |
|------|---------|----------------|
| **pytest** | Backend unit and integration testing | >80% code coverage |
| **ruff / black** | Python linting and formatting | Zero linting violations |
| **mypy** | Static type checking for Python | Strict mode enabled |
| **eslint / prettier** | Frontend linting and formatting | Enforced via pre-commit hooks |
| **Jest** | Frontend unit testing | >70% component coverage |

### Monitoring & Observability Stack

| Technology | Purpose | Integration |
|------------|---------|-------------|
| **Sentry (Free Tier)** | Error tracking | Frontend and backend error monitoring (5k events/month free) |
| **Application Logs** | Basic logging | JSON logs stored locally, rotated daily |
| **UptimeRobot (Free)** | Uptime monitoring | External health check pings every 5 minutes |
| **CloudWatch (Optional)** | Minimal logging | Low retention for critical alerts only |

### Logging Configuration

**Logging Strategy:**
- Structured JSON logging to stdout/stderr
- Docker Compose log driver with rotation (max 10MB per file, 3 files retained)
- Critical errors sent to Sentry (free tier)
- Daily log aggregation script for analysis

**Monitored Metrics:**
- API request counts and latency (logged locally)
- Error rates tracked via Sentry
- Disk usage and memory via basic system monitoring
- External uptime checks via UptimeRobot

### Key Metrics Tracked

- **API Performance:**
  - Request rate (req/sec)
  - p50, p95, p99 latency
  - Error rate (4xx, 5xx)
  - Concurrent connections

- **RAG Pipeline:**
  - Retrieval latency (vector search + reranking)
  - Embedding generation time
  - LLM call latency (TTFT and total)
  - Token consumption (input/output)

- **Business Metrics:**
  - Query success rate
  - Retrieval refusal rate (no matches found)
  - User feedback scores (thumbs up/down ratio)
  - Daily/monthly active users

- **Infrastructure:**
  - VPS CPU/memory utilization (via `htop` or system logs)
  - PostgreSQL connection pool usage
  - Redis cache hit/miss ratio
  - Pinecone query latency

### Alerting Rules

**Critical Alerts (Email/Slack):**
- Service Down: UptimeRobot detects failures (email notification)
- Critical Errors: Sentry alerts for unhandled exceptions
- Disk Space: >80% usage triggers email alert

**Monitoring Tools:**
- UptimeRobot (Free) for external uptime monitoring
- Sentry (Free Tier) for error tracking
- Custom script for disk/memory alerts via email
- Manual log review for performance issues

---

## Environment Configuration

### Development & Production Environment

**Docker Compose Services (Same for Dev & Prod):**
- **caddy** - Reverse proxy with automatic HTTPS (production only)
- **api** - FastAPI backend (Uvicorn)
- **worker** - Celery background worker
- **db** - PostgreSQL 15 database with persistent volume
- **redis** - Redis 7 for caching and message broker
- **frontend** - Next.js production build (served by Caddy in production)

**Local Setup Requirements:**
- Docker and Docker Compose installed
- Environment variables configured in `.env` file
- OPENAI_API_KEY and PINECONE_API_KEY provided
- Local volume mounting for hot-reload during development

**Production Setup (Lightsail):**
- Same Docker Compose configuration
- Caddy enabled for automatic HTTPS
- Persistent volumes for database and logs
- Automated daily backups to S3 (optional)

### Production Environment Variables

**Secrets (.env file on Lightsail):**
- DATABASE_URL=postgresql://user:pass@db:5432/librarian
- REDIS_URL=redis://redis:6379
- OPENAI_API_KEY - OpenAI API credentials
- PINECONE_API_KEY, PINECONE_ENVIRONMENT - Vector database access
- GITHUB_TOKEN - Source repository access
- SENTRY_DSN - Error tracking configuration (optional)

**Application Configuration:**
- ENVIRONMENT=production
- LOG_LEVEL=INFO
- MAX_QUERY_RATE_PER_USER=50 (per DECISIONS.md section 11)
- TOKEN_BUDGET_MAX=2000 (reduced for cost control)
- EMBEDDING_MODEL=text-embedding-3-small (cheaper alternative)
- LLM_PRIMARY=gpt-4o-mini (budget-friendly model)
- LLM_FALLBACK=disabled (to control costs)

**Cost Optimization Settings:**
- Strict rate limiting per user
- Reduced token budgets
- Smaller embedding model (768d vs 1536d)
- Query caching aggressively in Redis

---

## Cost Estimation (Monthly, 100 Users)

| Service                       | Estimated Cost    | Notes                                           |
| ----------------------------- | ----------------- | ----------------------------------------------- |
| **Amazon Lightsail (2GB)**    | $10               | Single VPS hosting API, Worker, Postgres, Redis |
| **OpenAI API (Mini Tier)**    | $8–12             | text-embedding-3-small + gpt-4o-mini with strict limits |
| **Data Transfer**             | Included          | Covered under Lightsail bundle (within limits)  |
| **Pinecone Starter**          | $0                | Free tier: 1 index, 100k vectors (upgrade for scale) |
| **Sentry Free Tier**          | $0                | 5k events/month error tracking                  |
| **UptimeRobot Free**          | $0                | 50 monitors, 5-min checks                       |
| **S3 (Backups, Optional)**    | $2–5              | Optional DB backups, ~10GB storage              |
| **Domain + SSL**              | $0                | Let's Encrypt (free), domain $12/year           |
| **Total**                     | **~$18–25/month** | For 100 users, ~5k–10k light queries            |

**Cost per Query:** ~$0.003 (3× cheaper than full AWS setup)  
**ROI Analysis:** 15 min saved × $50/hr engineer = $12.50 value per query → **4,167× ROI**


---

## Upgrade Path & Scaling Strategy

### When to Upgrade from Lightsail

**Indicators for Migration:**
- Consistent >80% CPU/memory usage
- >500 concurrent users
- >50k queries/month
- Need for high availability (99.9%+ uptime)

### Upgrade Options

| Current (Lightsail) | Next Tier | Enterprise Scale |
|---------------------|-----------|------------------|
| $10/month VPS | $40 (4GB Lightsail) or $150 (AWS ECS) | $770/month (Full AWS stack) |
| Single instance | Load-balanced instances | Multi-region, auto-scaling |
| Local PostgreSQL | RDS PostgreSQL (Multi-AZ) | Aurora Serverless |
| Pinecone free tier | Pinecone Starter ($70/month) | Pinecone Enterprise |
| Manual monitoring | CloudWatch + Sentry Pro | Full observability stack |

**Gradual Migration Path:**
1. **Phase 1 (Current):** Lightsail + Budget APIs (~$20/month)
2. **Phase 2 ($100–200/month):** Upgrade to 4GB Lightsail, Pinecone Starter, increase API budgets
3. **Phase 3 ($300–500/month):** Move to AWS ECS, RDS, ElastiCache for better performance
4. **Phase 4 ($500–1000/month):** Full enterprise setup with multi-region, advanced monitoring

---

## Security & Compliance

### Security Tools & Practices

| Tool/Practice | Purpose | Implementation |
|---------------|---------|----------------|
| **Let's Encrypt SSL** | Free HTTPS certificates | Automatic via Caddy reverse proxy |
| **Fail2ban** | Brute force protection | Installed on Lightsail instance |
| **Docker Security** | Container isolation | Non-root users, security scanning |
| **Environment Variables** | Secrets management | Stored in `.env` file (secure file permissions) |
| **Regular Updates** | Vulnerability patching | Automated security updates enabled |
| **Sentry** | Error tracking (free tier) | Monitors application exceptions |

### Security Best Practices

- **Encryption:** All traffic encrypted via HTTPS (Let's Encrypt)
- **Database Security:** PostgreSQL with strong passwords, not exposed to internet
- **API Authentication:** JWT tokens with proper expiration
- **Rate Limiting:** Per-user query limits enforced at application level
- **Firewall:** Lightsail firewall rules restrict access to essential ports only (80, 443, 22)
- **Backups:** Automated daily PostgreSQL backups to S3 (optional)

### Compliance Considerations

- **GDPR:** User data export and deletion endpoints implemented
- **Data Privacy:** Query logs retained for 90 days, then automatically purged
- **Audit Trail:** All admin actions logged in PostgreSQL audit_logs table
- **Note:** For SOC 2 or HIPAA compliance, migration to managed AWS services is recommended

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-15 | Initial tech stack definition |
| v1.1 | 2026-02-20 | Added Claude fallback, updated dependencies |
| v1.2 | 2026-03-10 | **Major revision:** Migrated to budget-optimized Lightsail deployment, updated to gpt-4o-mini and text-embedding-3-small, simplified infrastructure for $18-25/month operation |

---

**Document Owner:** Engineering Team  
**Last Updated:** March 10, 2026  
**Next Review:** June 10, 2026  
**Deployment Model:** Budget-Optimized (Lightsail VPS)
