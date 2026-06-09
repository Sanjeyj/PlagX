"""Document database model."""

import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    EMBEDDING = "embedding"
    ANALYZING = "analyzing"
    SCORING = "scoring"
    GENERATING_PDF = "generating_pdf"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=DocumentStatus.PENDING.value, nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    worker_stage: Mapped[str] = mapped_column(String(255), nullable=True)
    job_id: Mapped[str] = mapped_column(String(255), nullable=True)
    
    word_count: Mapped[int] = mapped_column(Integer, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    report = relationship("Report", back_populates="document", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.original_name} ({self.status})>"
