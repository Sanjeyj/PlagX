"""Report Pydantic schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel


class HighlightSpan(BaseModel):
    start_char: int
    end_char: int
    match_type: str  # "exact", "semantic", "weak"
    group_type: str | None = None
    similarity: float
    source_index: int
    source_name: str
    overlapping_sources: list[dict] = []
    top_source_id: str | None = None


class MatchedSourceResponse(BaseModel):
    source_index: int
    source_name: str
    source_url: str | None = None
    source_type: str = "repository"
    match_percentage: float
    color: str
    matched_spans: list[HighlightSpan] = []

    class Config:
        from_attributes = True


class ParagraphScore(BaseModel):
    paragraph_index: int
    text: str
    score: float
    match_type: str | None
    source_indices: list[int] = []


class ReportResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_name: str = ""
    overall_score: float
    exact_score: float
    semantic_score: float
    source_density_score: float
    risk_level: str
    ai_score: float = 0.0
    ai_confidence: str = "Likely Human"
    ai_suspicious_spans: list[dict] = []
    integrity_flags: list[str] = []
    total_words: int
    total_pages: int
    matched_words: int
    total_sources: int
    highlights: list[HighlightSpan] = []
    matched_sources: list[MatchedSourceResponse] = []
    paragraph_scores: list[ParagraphScore] = []
    full_text: str = ""
    pdf_status: str = "pending"
    created_at: datetime

    class Config:
        from_attributes = True


class ReportSummaryResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    overall_score: float
    risk_level: str
    total_sources: int
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStatsResponse(BaseModel):
    total_documents: int
    total_reports: int
    average_score: float
    high_risk_count: int
    recent_reports: list[ReportSummaryResponse]
