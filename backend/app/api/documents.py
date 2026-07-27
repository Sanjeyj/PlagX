"""Document upload and management API routes."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentResponse, DocumentListResponse, DocumentUploadResponse, CheckStatusResponse
from app.services.auth_service import get_current_user, get_guest_or_current_user
from app.services.file_service import FileService

router = APIRouter(prefix="/api", tags=["Documents"])
file_service = FileService()

def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id, original_name=doc.original_name, file_type=doc.file_type,
        file_size=doc.file_size, status=doc.status, word_count=doc.word_count,
        page_count=doc.page_count, upload_date=doc.upload_date,
        processed_at=doc.processed_at, error_message=doc.error_message,
        has_report=doc.report is not None if doc.report else False,
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_guest_or_current_user),
):
    """Upload a document for plagiarism checking."""
    file_info = await file_service.save_upload(file)

    document = Document(
        user_id=user.id,
        filename=file_info["filename"],
        original_name=file_info["original_name"],
        file_type=file_info["file_type"],
        file_size=file_info["file_size"],
        status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    return DocumentUploadResponse(
        id=document.id,
        original_name=document.original_name,
        file_type=document.file_type,
        file_size=document.file_size,
        status=document.status,
    )


@router.post("/check/{document_id}", response_model=CheckStatusResponse)
async def start_check(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_guest_or_current_user),
):
    """Start plagiarism check on a document."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.status not in (DocumentStatus.PENDING.value, DocumentStatus.COMPLETED.value, DocumentStatus.FAILED.value):
        return CheckStatusResponse(
            document_id=doc.id, status=doc.status, progress=doc.progress, message="Already processing"
        )

    from app.config import get_settings
    settings = get_settings()

    if not settings.REDIS_URL or settings.REDIS_URL.strip() == "":
        doc.status = DocumentStatus.QUEUED.value
        doc.progress = 0
        doc.worker_stage = "Queued for processing (Local fallback)"
        await db.commit()
        await db.refresh(doc)
        
        background_tasks.add_task(run_plagiarism_check_bg, document_id)
        
        return CheckStatusResponse(
            document_id=doc.id, status=DocumentStatus.QUEUED.value,
            progress=0, worker_stage="Queued for processing (Local fallback)",
            message="Plagiarism processing queued locally"
        )

    doc.status = DocumentStatus.QUEUED.value
    doc.progress = 0
    doc.worker_stage = "Queued for processing"
    await db.commit()

    # Trigger Celery Distributed Task Chain
    from celery import chain
    from app.tasks.plagiarism_tasks import (
        extract_document_task,
        embedding_generation_task,
        semantic_analysis_task,
        citation_and_scoring_task,
        pdf_generation_task
    )
    
    workflow = chain(
        extract_document_task.s(document_id),
        embedding_generation_task.s(),
        semantic_analysis_task.s(),
        citation_and_scoring_task.s(),
        pdf_generation_task.s()
    )
    
    result = workflow.apply_async()
    
    # Save job_id
    doc.job_id = result.id
    await db.commit()

    return CheckStatusResponse(
        document_id=doc.id, status=DocumentStatus.QUEUED.value,
        progress=0, message="Plagiarism processing queued"
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_guest_or_current_user),
):
    """List user's documents with pagination."""
    offset = (page - 1) * page_size

    count_q = select(func.count(Document.id)).where(Document.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Document)
        .options(selectinload(Document.report))
        .where(Document.user_id == user.id)
        .order_by(desc(Document.upload_date))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[_doc_to_response(d) for d in docs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_guest_or_current_user),
):
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.report))
        .where(Document.id == document_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return _doc_to_response(doc)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_guest_or_current_user),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    file_service.delete_file(doc.filename)
    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted"}


@router.get("/check-status/{document_id}", response_model=CheckStatusResponse)
async def check_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_guest_or_current_user),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    return CheckStatusResponse(
        document_id=doc.id, 
        status=doc.status, 
        progress=doc.progress,
        worker_stage=doc.worker_stage,
        message=doc.error_message or doc.worker_stage or "Processing"
    )


async def run_plagiarism_check_bg(document_id: str):
    """Background task to run plagiarism check."""
    from app.database import AsyncSessionLocal
    from app.engine.pipeline import PlagiarismPipeline
    from app.services.report_service import ReportService
    from app.config import get_settings
    from datetime import datetime, timezone
    import asyncio
    import logging

    settings = get_settings()
    logger = logging.getLogger(__name__)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                return

            file_path = str(settings.upload_path / doc.filename)

            # Run pipeline in thread (it's CPU-bound)
            pipeline = PlagiarismPipeline()
            plag_result = await asyncio.to_thread(
                pipeline.run, file_path, document_id
            )

            # Create report
            report_service = ReportService()
            report = await report_service.create_report(db, document_id, plag_result)

            # Update document
            doc.status = DocumentStatus.COMPLETED.value
            doc.word_count = plag_result.total_words
            doc.page_count = plag_result.total_pages
            doc.extracted_text = plag_result.full_text[:50000]
            doc.processed_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(f"Check complete for {document_id}: {plag_result.overall_score}%")

        except Exception as e:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(e)[:500]
            await db.commit()
            logger.error(f"Check failed for {document_id}: {e}", exc_info=True)
