# 📚 Smart Office Librarian — Enterprise AI Knowledge Agent

## 📋 Executive Summary

**Smart Office Librarian** is a production-ready Retrieval-Augmented Generation (RAG) system designed to unify fragmented engineering knowledge. It enables developers to ask natural-language questions across GitHub repositories, Confluence, and Google Docs, receiving AI-generated answers with direct source citations to the original files.

- **Core Purpose:** Eliminate "knowledge silos" and accelerate developer onboarding.
- **Target Users:** Software Engineers, DevOps, and Technical Writers.
- **Key Value:** Provides semantic understanding of documentation with verifiable source attribution, reducing internal search time by an estimated 40%.
- **Architecture:** A modular, distributed system using a RAG pipeline, vector search, and a reranker model for high-precision retrieval.

---

## 🎯 The Problem

In fast-growing engineering teams, knowledge becomes a critical bottleneck.

- **Fragmented Knowledge:** Information is split between code (GitHub), specs (Confluence), and meeting notes (Google Docs). There is no single source of truth.
- **Keyword Failure:** Traditional search fails if the user doesn't know the exact term (e.g., searching "how to scale" won't find docs titled "Horizontal Pod Autoscaler"). It lacks semantic understanding.
- **Onboarding Friction:** New hires spend weeks locating tribal knowledge buried in outdated repositories, asking repetitive questions and slowing down senior engineers.

This system provides a semantic intelligence layer to solve these problems directly.

---

## 🏗️ System Architecture & Flow

The system follows a modular, distributed architecture designed for reliability and verifiable retrieval.

**High-Level Flow:**
1.  **Ingestion:** GitHub API fetches content → Text is extracted and split into 512-token chunks with 50-token overlap to maintain context.
2.  **Embedding:** Chunks are transformed into 768-dimension vectors using `text-embedding-3-small`.
3.  **Storage:** Vectors are stored in Pinecone; metadata (URL, Author, Timestamp) is stored in PostgreSQL.
4.  **Retrieval:** User queries are embedded → Vector similarity search finds top-k relevant chunks → A Reranker model optimizes for precision.
5.  **Generation:** gpt-4o-mini synthesizes an answer using *only* the provided context and cites sources using `[Source N]` notation.

### Core Components

1.  **Ingestion Pipeline:** Connects to data sources (GitHub, Confluence) via API. It uses background workers (Celery) for scheduled and real-time (webhook-based) indexing.
2.  **Text Processing Pipeline:** Implements an intelligent chunking strategy (semantic + token-based) and tags each chunk with metadata (file path, repo, timestamp, owner).
3.  **Embedding Layer:** Converts text chunks into dense vector representations using a chosen model (e.g., OpenAI, Cohere, or a self-hosted SentenceTransformer).
4.  **Vector Database:** Stores and indexes embeddings for fast similarity search. It supports metadata filtering to enforce permissions and narrow search scope.
5.  **Retrieval Engine:** Converts the user's question into an embedding, performs a top-k similarity search, and uses a cross-encoder model to rerank results for relevance before passing them to the LLM.
6.  **Generation Layer (LLM):** Receives the user's question and the top-k retrieved chunks. A carefully engineered prompt instructs the model (e.g., gpt-4o-mini, Claude 3) to generate a structured answer with citations.
7.  **Security Layer:** Enforces Role-Based Access Control (RBAC) by filtering vector search results based on user permissions synced from the source platform (e.g., GitHub team access).

---

## 🛠️ Tech Stack & Tradeoffs

| Component  | Choice     | Why this over the alternatives?                                                                                             |
| :--------- | :--------- | :-------------------------------------------------------------------------------------------------------------------------- |
| **Backend**  | FastAPI    | High performance with Python's async support; native OpenAPI docs for faster internal tool integration.                     |
| **Vector DB**| Pinecone   | Managed serverless scaling. Tradeoff: Higher cost than self-hosted Weaviate, but drastically lower DevOps overhead for MVP. |
| **LLM**      | gpt-4o-mini | Budget-optimized model with strong reasoning and citation accuracy. Tradeoff: Dependency on external API; fallback to local Llama-3 is planned. |
| **Database** | PostgreSQL | Industry standard for relational metadata and audit logs; allows for `pgvector` migration if we consolidate DBs later.      |

### Detailed Stack

- **Backend:** FastAPI, Celery (background jobs), Redis (caching & message broker).
- **AI/ML:** OpenAI/Cohere APIs, SentenceTransformers, LangChain.
- **Frontend:** Next.js, Tailwind CSS, shadcn/ui (for rapid, modern UI development).
- **Infrastructure:** Docker, Kubernetes (optional), AWS (ECS/Lambda/S3), Terraform.

---

## 🚀 MVP Scope vs. Roadmap

To ensure high reliability and engineering trust, the project is divided into prioritized phases:

### ✅ MVP (v1 - Current Focus)

- **GitHub Connector:** Ingests Markdown and `.txt` files from specified repositories.
- **Semantic Search:** Vector-based retrieval with basic metadata filtering.
- **Cited Answers:** UI displays the specific file and line number used for the answer.
- **Basic RBAC:** Admin (ingestion control) vs. User (query only).

### 🚧 Future (v2+)

- **Multi-Source Integration:** Add connectors for Confluence, Google Docs, and Slack to become the single source of truth.
- **AST Code-Awareness:** Parse Java/Python code structures using Tree-sitter to answer questions about logic and implementation details (e.g., "Where is payment validation implemented?").
- **Conversational Memory:** Enable context-aware, multi-turn dialogues for follow-up questions.
- **Analytics Dashboard:** Provide insights on most-asked questions, knowledge gaps, and search time saved.
- **Hallucination Guardrails:** Implement a "Confidence Score" threshold to reject low-quality or non-grounded answers.

---

## 🧪 Target Success Criteria

| Metric                | Target                                                                      | Measurement Method                                       |
| :-------------------- | :-------------------------------------------------------------------------- | :------------------------------------------------------- |
| **Retrieval Precision** | >80%                                                                        | "Golden Questions" must return the correct source in Top-5 |
| **Latency (p95)**       | < 2 seconds                                                                 | End-to-end query response time from user perspective     |
| **Groundedness**        | 100%                                                                        | AI must refuse to answer if context is insufficient      |
- **User Satisfaction:** >4.0/5.0 score from user feedback widgets.
- **Business Impact:** Reduce onboarding time by 30% and internal search time by 40%.

---

## 📂 Repository Structure

```
/backend          # FastAPI app, Ingestion workers, API logic
/frontend         # Next.js UI, Markdown rendering, Source panels
/infra            # Docker Compose, Kubernetes manifests, Terraform
/docs             # /architecture.md, /evaluation.md, /security.md
```

---

## ⚡ Quick Start (Local Dev)

1.  **Clone & Env:** Clone the repository. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY` and `PINECONE_API_KEY`.
2.  **Containers:** Run `docker-compose up --build`. This will start the backend, frontend, and database services.
3.  **Ingest Data:** Send a POST request to `/api/v1/ingest` with a repository URL:
    `POST /api/v1/ingest { "url": "github.com/org/repo" }`
4.  **Query:** Send a POST request to `/api/v1/query` with your question:
    `POST /api/v1/query { "prompt": "How do I setup the DB?" }`

---

## 🔥 How to Position This on a Resume

Instead of: *"Built an AI chatbot using OpenAI API."*

Write: *"Designed and implemented a scalable Retrieval-Augmented Generation (RAG) system for enterprise documentation intelligence, integrating GitHub and Google Docs ingestion pipelines, vector similarity search, and source-attributed LLM responses with role-based access control."*