"""Report and MatchedSource database models."""

import uuid
import json
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Scores
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    exact_score: Mapped[float] = mapped_column(Float, default=0.0)
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_density_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Classification
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    ai_score: Mapped[float] = mapped_column(Float, default=0.0)
    ai_confidence: Mapped[str] = mapped_column(String(50), default="Likely Human")

    # Detailed data stored as JSON text
    highlights_json: Mapped[str] = mapped_column(Text, default="{}")
    ai_suspicious_spans_json: Mapped[str] = mapped_column(Text, default="[]")
    matched_sources_json: Mapped[str] = mapped_column(Text, default="{}")
    paragraph_scores_json: Mapped[str] = mapped_column(Text, default="{}")
    document_structure_json: Mapped[str] = mapped_column(Text, default="{}")
    integrity_flags_json: Mapped[str] = mapped_column(Text, default="[]")

    # Stats
    total_words: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=1)
    matched_words: Mapped[int] = mapped_column(Integer, default=0)
    total_sources: Mapped[int] = mapped_column(Integer, default=0)

    # File paths
    html_report_path: Mapped[str] = mapped_column(String(512), nullable=True)
    pdf_report_path: Mapped[str] = mapped_column(String(512), nullable=True)
    pdf_status: Mapped[str] = mapped_column(String(20), default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    document = relationship("Document", back_populates="report")
    matched_sources = relationship("MatchedSource", back_populates="report", cascade="all, delete-orphan")

    @property
    def highlights(self):
        try:
            return json.loads(self.highlights_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    @highlights.setter
    def highlights(self, value):
        self.highlights_json = json.dumps(value) if value else "{}"

    @property
    def ai_suspicious_spans(self):
        try:
            return json.loads(self.ai_suspicious_spans_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @ai_suspicious_spans.setter
    def ai_suspicious_spans(self, value):
        self.ai_suspicious_spans_json = json.dumps(value) if value else "[]"

    @property
    def matched_sources_data(self):
        try:
            return json.loads(self.matched_sources_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    @matched_sources_data.setter
    def matched_sources_data(self, value):
        self.matched_sources_json = json.dumps(value) if value else "{}"

    @property
    def paragraph_scores(self):
        try:
            return json.loads(self.paragraph_scores_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    @paragraph_scores.setter
    def paragraph_scores(self, value):
        self.paragraph_scores_json = json.dumps(value) if value else "{}"

    @property
    def document_structure(self):
        try:
            return json.loads(self.document_structure_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    @document_structure.setter
    def document_structure(self, value):
        self.document_structure_json = json.dumps(value) if value else "{}"

    @property
    def integrity_flags(self):
        try:
            return json.loads(self.integrity_flags_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @integrity_flags.setter
    def integrity_flags(self, value):
        self.integrity_flags_json = json.dumps(value) if value else "[]"

    def __repr__(self):
        return f"<Report {self.id} score={self.overall_score:.1f}%>"


class MatchedSource(Base):
    __tablename__ = "matched_sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    source_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="repository")
    match_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    color: Mapped[str] = mapped_column(String(7), default="#EF4444")

    # Matched spans stored as JSON text
    matched_spans_json: Mapped[str] = mapped_column(Text, default="[]")

    # Relationships
    report = relationship("Report", back_populates="matched_sources")

    @property
    def matched_spans(self):
        try:
            return json.loads(self.matched_spans_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    @matched_spans.setter
    def matched_spans(self, value):
        self.matched_spans_json = json.dumps(value) if value else "[]"

    def __repr__(self):
        return f"<MatchedSource {self.source_name} {self.match_percentage:.1f}%>"
