# Embedlyzer - Smart Office Librarian

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Production-ready AI knowledge management system for enterprise teams.**

Embedlyzer transforms fragmented organizational knowledge into a unified, searchable intelligence layer. Ask natural-language questions across GitHub repositories and internal documentation, and receive AI-generated answers with verifiable source citations.

---

## 🎯 What is Embedlyzer?

Embedlyzer is an **enterprise AI knowledge management system** that transforms how teams access and interact with their internal documentation. Instead of hunting through repositories, wikis, and documents, users simply ask questions in natural language and receive accurate, source-backed answers.

### Key Capabilities

**🔍 Intelligent Document Search**
- Semantic search across GitHub repositories, Confluence, and documentation
- Understands intent beyond exact keyword matches
- Finds relevant information even when you don't know the exact terms

**🤖 AI-Powered Q&A**
- Generates comprehensive answers using advanced RAG (Retrieval-Augmented Generation)
- Combines information from multiple sources into coherent responses
- Refuses to answer when source material is insufficient (no hallucinations)

**📚 Source Citation & Verification**
- Every answer includes direct links to original source documents
- Shows specific file paths, line numbers, and relevant text snippets
- Enables users to verify and dive deeper into source material

**🔒 Enterprise Security & Permissions**
- Role-based access control ensures users only see authorized content
- Multi-tenant workspace isolation for different teams/projects
- Comprehensive audit logging for compliance and security monitoring

**⚡ Production-Grade Performance**
- Sub-2.0 second query response times (p95)
- Real-time streaming responses for immediate feedback
- Horizontal scaling with automated capacity management

## 🎯 Why Embedlyzer?

**The Problem:**
- Knowledge fragmented across GitHub, Confluence, and documentation
- Traditional keyword search fails when you don't know exact terms
- New team members spend weeks hunting for tribal knowledge

**The Solution:**
Embedlyzer provides semantic search with AI-generated answers that:
- **Understand intent** beyond exact keyword matches
- **Cite sources** with direct links to original documents  
- **Refuse hallucination** when context is insufficient
- **Respect permissions** with role-based access control
- **Scale efficiently** with budget-optimized infrastructure ($18-25/month)

### Real-World Impact

**For Engineering Teams:**
- Reduction in time spent searching for technical documentation
- Faster onboarding for new developers
- Eliminates repetitive "where is this documented?" questions

**For Organizations:**
- Centralizes tribal knowledge that typically lives in senior developers' heads
- Reduces context switching between multiple knowledge repositories
- Provides measurable insights into knowledge gaps and frequently asked questions

---

## 🏗️ Architecture Overview

Embedlyzer implements a sophisticated **Retrieval-Augmented Generation (RAG)** pipeline that combines the best of semantic search and large language models:

```
📁 Knowledge Sources → 🔄 Ingestion Pipeline → 🧠 Vector Embeddings → 📊 Vector Database
                                                                              ↓
🔍 User Query → 🎯 Semantic Search → 🔀 Intelligent Reranking → 🤖 LLM Generation → ✅ Verified Answer + Citations
```

### How It Works

1. **Document Ingestion**: Automatically syncs content from GitHub repositories and other sources
2. **Intelligent Chunking**: Breaks documents into semantic chunks optimized for retrieval  
3. **Vector Embeddings**: Creates high-dimensional representations using OpenAI's latest embedding models
4. **Semantic Search**: Finds relevant content based on meaning, not just keywords
5. **Smart Reranking**: Uses cross-encoder models to refine and prioritize results
6. **Grounded Generation**: LLM generates answers using only retrieved context, with strict groundedness enforcement
7. **Source Attribution**: Every answer includes verifiable citations back to original documents

### Core Components

* **Ingestion Pipeline**

  * GitHub-based document ingestion
  * Incremental updates using commit tracking

* **Retrieval**

  * Vector search (Pinecone)
  * Reranking (cross-encoder)

* **Generation**

  * LLM responses (gpt-4o-mini)
  * Grounded answers with source citations

* **Security**

  * JWT authentication
  * Role-based access control

* **Observability**

  * Metrics and tracing
  * Structured logging

---

## 🛠️ Tech Stack

**Backend:** FastAPI + PostgreSQL + Redis + Celery workers  
**AI/ML:** OpenAI (`text-embedding-3-small`, `gpt-4o-mini`) + SentenceTransformers  
**Frontend:** Next.js 14 + TypeScript + Tailwind CSS  
**Infrastructure:** Docker + AWS Lightsail + Terraform + Prometheus/Grafana  
**Vector Storage:** Pinecone (with free tier optimization)

---

## 📋 Project Status

**Current Phase:** Production-ready (v0.9.1) with comprehensive testing and monitoring

### ✅ Production Features
- Core RAG pipeline with sub-2.0s query latency (p95)
- Multi-tenant workspace isolation with budget controls
- JWT authentication + RBAC security layer
- 417+ automated tests with Golden Questions evaluation framework
- AWS infrastructure with Terraform IaC
- Real-time streaming responses (SSE)
- Admin dashboard with analytics and threshold tuning
- Comprehensive observability (Prometheus + Grafana)

### 🎯 Architecture Highlights
- **Performance:** Query latency p95 ≤ 2.0 seconds, 99.9% availability target
- **Security:** Permission-filtered retrieval, audit logging, secrets encryption
- **Scalability:** Horizontal scaling ready, capacity planning with automated triggers
- **Cost-Optimized:** $18-25/month operational costs for 100+ users

---

## 🚀 Getting Started

### Quick Start (Docker)

```bash
# Clone and setup
git clone <repo-url>
cd Smart-Office-Librarian

# Start services
docker-compose up -d

# Access
# Frontend: http://localhost:3101
# Backend API: http://localhost:8000
```

### Development Setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install && npm run dev
```

### Production Deployment

```bash
# Provision AWS infrastructure
cd infra/terraform
terraform init && terraform plan && terraform apply

# Deploy application
# See docs/05_operations/DEPLOYMENT.md
```

---

## 📖 API Usage

### Query Endpoint (with streaming)

```bash
POST /api/v1/query
Content-Type: application/json
Authorization: Bearer <token>

{
  "query": "How does the ingestion pipeline work?",
  "workspace_id": "workspace-123"
}
```

**Streaming Response (SSE):**
```
data: {"type": "token", "content": "The"}
data: {"type": "token", "content": " ingestion"}
data: {"type": "citation", "source_id": "src-1", "text": "..."}
data: {"type": "complete", "confidence": "high"}
```

---

## 🧪 Testing & Evaluation

```bash
# Run full test suite (417+ tests)
pytest tests/ --cov=app --cov-report=html

# Performance baseline evaluation
python evaluation/scripts/evaluate_golden_questions.py
python evaluation/scripts/analyze_failures.py

# Load testing
python evaluation/scripts/run_pqs.py
```

**Test Coverage:**
- Unit tests: Core business logic
- Integration tests: End-to-end workflows  
- Evaluation tests: Golden Questions framework with 8-category failure taxonomy
- Performance tests: Latency and throughput validation

---

## 🔐 Security

* JWT authentication
* Role-based access control
* Permission-filtered retrieval
* Secrets encryption (AES-256)
* Sensitive data redaction in logs

---

## 📊 Observability

* Metrics (Prometheus format)
* Tracing (OpenTelemetry-style)
* Query latency and performance tracking

---

## 📚 Documentation

**Core Documentation:**
```
docs/00_backbone/     # Architecture, requirements, decisions
docs/01_product/      # Product specs, user stories  
docs/02_api/          # API documentation
docs/05_operations/   # Deployment, capacity planning
docs/06_observability/# Monitoring, alerting
docs/07_runbooks/     # Incident response procedures
```

**Key Files:**
- [ARCHITECTURE.md](docs/00_backbone/Backbond/ARCHITECTURE.md) - System design
- [DEPLOYMENT.md](docs/05_operations/DEPLOYMENT.md) - Production deployment
- [API.md](docs/02_api/API.md) - Complete API reference

---

## ⚠️ Production Notes

- **Security:** JWT tokens, RBAC, audit logging, secret redaction in logs
- **Monitoring:** Comprehensive Prometheus metrics with Grafana dashboards  
- **Backup:** Automated PostgreSQL backups with 30-day retention
- **Scaling:** Capacity planning triggers for AWS infrastructure upgrades
- **Budget:** Cost monitoring with $25/month operational target

---

## 📄 License

MIT License

---

## 🎯 Summary

**Embedlyzer** is a production-ready enterprise RAG system with comprehensive testing, monitoring, and AWS infrastructure. Built for teams who need reliable, grounded AI answers from their internal knowledge base.

---
