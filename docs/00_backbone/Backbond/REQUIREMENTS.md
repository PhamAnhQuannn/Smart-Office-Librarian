# 📚 Smart Office Librarian — System Requirements v1.5

This document defines the complete functional and non-functional requirements for the Smart Office Librarian production-grade RAG system.

---

## Part 1: Functional Requirements (FRS v1.3)

These requirements define the specific behaviors, features, and functions of the system.

---

### 1. User Management & Security (RBAC)

- **FR-1.1 Auth:** Authenticate users via JWT/API key (MVP) or GitHub OAuth (v2).
- **FR-1.2 RBAC:** Support **Admin** (Ingestion control) and **User** (Query only) roles.
- **FR-1.3 Permission-Filtered Retrieval:** The system **must** inject user-permission metadata into the vector search query. Users shall only retrieve chunks from sources they have explicit access to.
- **FR-1.4 Secrets Management:** All third-party tokens (GitHub, Confluence) **must** be encrypted at rest in PostgreSQL using AES-256.
- **FR-1.5 Logging Hygiene:** Sensitive credentials and third-party tokens **shall never** appear in application logs, error messages, or telemetry.

---

### 2. Ingestion & Data Lifecycle

- **FR-2.1 Source Connectors:** Ingest Markdown (`.md`), Text (`.txt`), and Code docs (`.rst`) from GitHub.
- **FR-2.2 Incremental Sync:** Track changes by Commit SHA. The system shall only process diffs from the last known commit to ensure efficient updates.
- **FR-2.3 Stale Content Purge:** If a file is deleted or renamed in the source repository, the system **must** trigger a background job to delete the associated vectors and metadata from the database.
- **FR-2.4 Exclusion Lists:** Admins shall have the ability to define a `.librarianignore` file or a regex-based blacklist to prevent sensitive or irrelevant files (e.g., `LICENSE`, `node_modules/`) from being indexed.

---

### 3. The RAG Pipeline (Retrieval & Generation)

- **FR-3.1 Semantic Chunking:** Split documents into a maximum of 512 tokens per chunk with a 50-token overlap (~10%). Each chunk **must** preserve parent-file metadata (e.g., URL, file path).
- **FR-3.2 Multi-Stage Retrieval:**
    1.  **Vector Search:** Retrieve a broad set of top-k (e.g., 20) candidates from the vector database.
    2.  **Reranking:** Use a more sophisticated Cross-Encoder model to filter the candidates down to the top-n (e.g., 5) most relevant results.
- **FR-3.3 Threshold Refusal:** The system **shall** refuse to generate an answer if no retrieved chunk's similarity score exceeds a configurable threshold. This threshold must be adjustable per embedding model to account for varying score distributions.
- **FR-3.4 Groundedness Enforcement:** The LLM prompt **must** contain a strict system instruction to refuse any question that is not answerable solely based on the provided context chunks.
- **FR-3.5 Context Deduplication:** The system **shall** detect and suppress near-duplicate chunks during the retrieval process (e.g., using hash-based fingerprinting) to prevent redundant information from consuming the LLM's token budget.
- **FR-3.6 Token Budgeting:** The system **shall** enforce a maximum context token budget per query to ensure cost-efficiency and prevent "context stuffing," which can degrade LLM reasoning capabilities.
- **FR-3.7 Fact-Check (v2):** A secondary "LLM Judge" shall be implemented to verify the generated answer against the source chunks to detect potential hallucinations. To manage costs, this feature will be sampled in production or triggered only when confidence scores are low.

---

### 4. Index Maintenance & Lifecycle

- **FR-4.1 Embedding Versioning:** Every vector stored in the database **must** be tagged with a model ID (e.g., `text-embedding-3-small-v1`).
- **FR-4.2 Cross-Version Safety:** The system **shall** prevent a query using one embedding model (Model A) from searching an index created by a different model (Model B).
- **FR-4.3 Atomic Reindexing:** The system **must** support "Blue-Green" reindexing. This involves keeping the old index live while building a new one in the background, then atomically swapping the pointer upon successful completion to ensure zero-downtime updates.

---

### 5. Operations & Observability

- **FR-5.1 Rate Limiting:** Enforce query limits per User ID (e.g., 50 queries/hour) to prevent abuse and manage costs.
- **FR-5.2 Observability:** Log "Retrieval Failures" (queries with no high-similarity matches) to an Admin Dashboard. This data is critical for identifying knowledge gaps in the documentation.
- **FR-5.3 Feedback Loop:** Users **must** be able to provide feedback on answers ("Thumbs Up/Down"). Downvotes must trigger a log entry for human review and potential fine-tuning.

---

### 6. Frontend Requirements

- **FR-6.1 Streaming UI:** The user interface **must** display the LLM's output character-by-character via Server-Sent Events (SSE) to provide a responsive, real-time experience.
- **FR-6.2 Citation Panel:** Each generated answer **must** be accompanied by a clickable list of sources, showing the file name, a direct URL to the source, and the specific text snippet used for generation.
- **FR-6.3 Confidence Indicators:** The UI **shall** display a "High/Medium/Low" confidence badge based on the similarity scores of the retrieved chunks to give users a sense of the answer's reliability.

---

### 7. Multi-Tenancy (Future Scope)

- **FR-7.1 Tenant Isolation:** Future SaaS iterations of the platform **shall** ensure strict logical isolation of tenant data. This will be achieved through namespace-level separation in the Vector DB and tenant-scoped metadata in PostgreSQL to prevent any data leakage between organizations.

---

## Part 2: Non-Functional Requirements (NFR v1.5)

These requirements define quality attributes and operational constraints for a production-grade, enterprise-oriented RAG system.

---

### 1. Performance & Latency

- **NFR-1.1 Query Latency:** The system shall achieve **p95 end-to-end query latency ≤ 2.0 seconds** for typical queries under normal load. Normal load is defined as ≤ 100 concurrent users and ≤ 10 QPS sustained traffic in MVP configuration.
- **NFR-1.2 Retrieval Latency:** Vector search + reranking shall complete within **≤ 500ms p95** for indexes up to 200k chunks, as measured via application-level OpenTelemetry metrics.
- **NFR-1.3 Streaming Responsiveness:** Time-to-First-Token (TTFT) shall be **≤ 500ms** after the LLM request is initiated.
- **NFR-1.4 Ingestion Throughput:** The pipeline shall process **≥ 200 documents/minute** (subject to external API rate limits).
- **NFR-1.5 Load Shedding:** Under extreme system load, the system shall prioritize existing admin/ingestion tasks and may temporarily throttle or reject non-critical user queries. Load shedding shall trigger when p95 latency (measured at the API Gateway) exceeds 2.5s for 3 consecutive 1-minute rolling measurement windows OR average CPU utilization across API service instances exceeds 80%.

---

### 2. Scalability

- **NFR-2.1 Horizontal Scaling:** The backend API and background workers shall scale horizontally independently.
- **NFR-2.2 Index Growth:** The architecture shall support growth to **1M+ chunks** (v2 target) without core redesign.
- **NFR-2.3 Concurrency:** The system shall support **100 concurrent active users** in MVP, scaling to **500+** in v2.
- **NFR-2.4 Multi-Region Readiness (v2):** The architecture shall allow for future regional deployments to satisfy data residency requirements and minimize geographic latency.

---

### 3. Reliability & Availability

- **NFR-3.1 Availability:** Target **99.9% monthly uptime** for the API layer. Availability calculations shall exclude third-party dependency outages (e.g., OpenAI, Pinecone) and pre-announced scheduled maintenance windows.
- **NFR-3.2 Graceful Degradation:** If the LLM provider is unavailable, the system shall:
    - Return top retrieved source excerpts.
    - Return a clear "LLM temporarily unavailable" status message.
    - Log the failure event for observability.
- **NFR-3.3 Job Reliability:** Ingestion jobs shall use exponential backoff; failed runs must not corrupt the existing index state.
- **NFR-3.4 Atomic Swaps:** Index pointer updates must be atomic and support instant rollback.
- **NFR-3.5 Backup & Recovery:**
    - PostgreSQL metadata shall be backed up daily with a **7-day minimum retention**.
    - Vector database state shall be recoverable via provider-level backups or periodic metadata export snapshots.
    - **Recovery Drills:** The system shall document and validate recovery procedures for vector index restoration at least once per quarter (simulated recovery drill).
    - **RPO (Recovery Point Objective):** ≤ 24 hours.
    - **RTO (Recovery Time Objective):** ≤ 1 hour for the API/metadata layer; ≤ 4 hours for full vector index restoration (v2 target).
- **NFR-3.6 Incident Management:** All production incidents exceeding SLA thresholds (e.g., availability drops, latency spikes) shall require a documented postmortem and root cause analysis (RCA).

---

### 4. Security & Privacy

- **NFR-4.1 Encryption:** **TLS 1.3** for data in transit; **AES-256** for data (tokens/secrets) at rest.
- **NFR-4.2 Least Privilege:** API tokens shall be scoped only to required repositories/scopes.
- **NFR-4.3 Logging Hygiene:** Credentials and PII shall never appear in application logs or telemetry. Operational logs shall be retained for a minimum of **14 days** for debugging and compliance.
- **NFR-4.4 Sensitive Data Exclusion:** Explicit support for `.librarianignore` to prevent indexing of blacklisted paths.
- **NFR-4.5 Data Retention:** Query logs and feedback data shall have a configurable retention period (default **90 days**), after which data is purged unless flagged for evaluation.
- **NFR-4.6 Security Auditability:** The system shall maintain audit logs of all permission changes and source configuration updates for traceability.

---

### 5. Maintainability & Modularity

- **NFR-5.1 Clean Architecture:** Strict separation between API, Ingestion Workers, and Retrieval/Generation logic.
- **NFR-5.2 Configuration Management:** All configuration parameters (thresholds, token limits, chunk sizes) shall be version-controlled and environment-specific to prevent configuration drift.
- **NFR-5.3 Environment Isolation:** The system must maintain strict logical and physical separation between `dev`, `staging`, and `production` environments.
- **NFR-5.4 API Stability:** Public API endpoints shall be versioned (e.g., `/api/v1/`). Breaking changes require a new version namespace.
- **NFR-5.5 Deployment Safety:** All production releases must pass automated integration and evaluation suites. Database migrations must be backward-compatible to support rolling updates.

---

### 6. Observability & Monitoring

- **NFR-6.1 Metrics:** Track request rates, p95 latency, retrieval success/refusal rates, and token consumption.
- **NFR-6.2 Tracing:** Implement **OpenTelemetry** for distributed tracing across the API and workers.
- **NFR-6.3 Alerting:** Automated alerts for elevated error rates, ingestion failures, or latency regressions.

---

### 7. Cost & Budget Controls

- **NFR-7.1 Spend Caps:** Monthly spend limits for LLM/Embedding APIs shall be enforced. Upon reaching caps, the system shall initiate graceful suspension: disabling LLM generation while still permitting source retrieval and displaying a cost-limit warning.
- **NFR-7.2 Token Budgets:** Enforce maximum context and output tokens per query to control costs.

---

## Requirements Traceability Matrix

| Category | Functional Requirements | Non-Functional Requirements |
|----------|------------------------|----------------------------|
| **Security** | FR-1.1 through FR-1.5 | NFR-4.1 through NFR-4.6 |
| **Performance** | FR-3.2 (Multi-Stage Retrieval) | NFR-1.1 through NFR-1.5 |
| **Scalability** | FR-4.3 (Atomic Reindexing) | NFR-2.1 through NFR-2.4 |
| **Reliability** | FR-2.3 (Stale Content Purge) | NFR-3.1 through NFR-3.6 |
| **Observability** | FR-5.2, FR-5.3 | NFR-6.1 through NFR-6.3 |
| **Cost Management** | FR-3.6 (Token Budgeting) | NFR-7.1, NFR-7.2 |

---

## Acceptance Criteria Summary

### MVP (v1) Must Have:
- ✅ All FR-1.x (Security & Auth)
- ✅ FR-2.1, FR-2.2, FR-2.4 (Basic Ingestion)
- ✅ FR-3.1 through FR-3.6 (Core RAG Pipeline)
- ✅ FR-4.1, FR-4.2 (Embedding Versioning)
- ✅ FR-5.1, FR-5.3 (Rate Limiting & Feedback)
- ✅ FR-6.1, FR-6.2, FR-6.3 (Core UI Features)
- ✅ NFR-1.1, NFR-1.2, NFR-1.3 (Performance Targets)
- ✅ NFR-3.1, NFR-3.3 (Basic Reliability)
- ✅ NFR-4.1, NFR-4.2, NFR-4.3 (Core Security)

### v2 (Future):
- 🔮 FR-2.3 (Stale Content Purge - Advanced)
- 🔮 FR-3.7 (Fact-Check with LLM Judge)
- 🔮 FR-4.3 (Blue-Green Reindexing)
- 🔮 FR-7.1 (Multi-Tenancy)
- 🔮 NFR-2.2 (1M+ chunks support)
- 🔮 NFR-2.4 (Multi-Region Deployment)
- 🔮 NFR-3.5 (Advanced Backup & Recovery)

---

## Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| v1.0 | 2026-01-15 | Initial requirements document | Team |
| v1.3 | 2026-02-10 | Added FR-3.7 (Fact-Check), refined chunking strategy | Team |
| v1.5 | 2026-03-10 | Added NFR-3.5 (Backup & Recovery), NFR-1.5 (Load Shedding) | Team |

---

## Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| **Product Owner** | [Name] | _________ | ______ |
| **Technical Lead** | [Name] | _________ | ______ |
| **Security Officer** | [Name] | _________ | ______ |
| **QA Lead** | [Name] | _________ | ______ |

---

**Document Status:** ✅ Approved for Implementation  
**Last Updated:** March 10, 2026  
**Next Review:** June 10, 2026
