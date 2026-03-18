"""Pydantic schema package — request/response models for all API routes."""
from app.api.v1.schemas.auth import LoginRequest, TokenClaims, TokenResponse
from app.api.v1.schemas.common import ErrorResponse, HealthStatus, PaginationMeta
from app.api.v1.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.api.v1.schemas.ingest import IngestRequest, IngestResponse, IngestRunStatus
from app.api.v1.schemas.query import QueryRequest, QueryResponse, SourceCitation
from app.api.v1.schemas.source import DeleteSourceResponse, SourceListResponse, SourceRecord

__all__ = [
    # auth
    "LoginRequest",
    "TokenClaims",
    "TokenResponse",
    # common
    "ErrorResponse",
    "HealthStatus",
    "PaginationMeta",
    # feedback
    "FeedbackRequest",
    "FeedbackResponse",
    # ingest
    "IngestRequest",
    "IngestResponse",
    "IngestRunStatus",
    # query
    "QueryRequest",
    "QueryResponse",
    "SourceCitation",
    # source
    "DeleteSourceResponse",
    "SourceListResponse",
    "SourceRecord",
]
