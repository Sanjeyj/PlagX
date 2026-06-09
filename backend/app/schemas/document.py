"""Document Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    original_name: str
    file_type: str
    file_size: int
    status: str
    word_count: int | None = None
    page_count: int | None = None
    upload_date: datetime
    processed_at: datetime | None = None
    error_message: str | None = None
    has_report: bool = False

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentUploadResponse(BaseModel):
    id: str
    original_name: str
    file_type: str
    file_size: int
    status: str
    message: str = "File uploaded successfully"


class CheckStatusResponse(BaseModel):
    document_id: str
    status: str
    progress: int = 0
    worker_stage: str | None = None
    message: str = ""
