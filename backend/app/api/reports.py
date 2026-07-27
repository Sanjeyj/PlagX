"""Report API routes."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.report import Report, MatchedSource
from app.schemas.report import (
    ReportResponse, ReportSummaryResponse, HighlightSpan,
    MatchedSourceResponse, ParagraphScore, DashboardStatsResponse,
)
from app.services.auth_service import get_current_user
from app.services.report_service import ReportService

router = APIRouter(prefix="/api", tags=["Reports"])
report_service = ReportService()


@router.get("/report/{report_id}")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full report data."""
    result = await db.execute(
        select(Report).join(Document).where(
            Report.id == report_id, Document.user_id == user.id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    # Get document info
    doc_result = await db.execute(select(Document).where(Document.id == report.document_id))
    doc = doc_result.scalar_one_or_none()

    # Get matched sources
    src_result = await db.execute(
        select(MatchedSource).where(MatchedSource.report_id == report.id)
        .order_by(desc(MatchedSource.match_percentage))
    )
    sources = src_result.scalars().all()

    # Build highlight spans from JSON
    highlights = []
    if report.highlights and "spans" in report.highlights:
        for s in report.highlights["spans"]:
            highlights.append(HighlightSpan(
                start_char=s["start_char"], end_char=s["end_char"],
                match_type=s["match_type"], similarity=s["similarity"],
                source_index=s["source_index"], source_name=s["source_name"],
                group_type=s.get("group_type"),
                overlapping_sources=s.get("overlapping_sources", []),
                top_source_id=s.get("top_source_id"),
            ))
            
    # Add AI suspicious spans as highlights
    if report.ai_suspicious_spans and "spans" in report.ai_suspicious_spans:
        for s in report.ai_suspicious_spans["spans"]:
            highlights.append(HighlightSpan(
                start_char=s["start_char"], end_char=s["end_char"],
                match_type="ai", similarity=s["ai_score"] / 100.0,
                source_index=-1, source_name="AI Detection Engine",
                group_type="ai_writing",
                overlapping_sources=[],
                top_source_id=None,
            ))

    # Build paragraph scores
    para_scores = []
    if report.paragraph_scores and "scores" in report.paragraph_scores:
        for ps in report.paragraph_scores["scores"]:
            para_scores.append(ParagraphScore(
                paragraph_index=ps["paragraph_index"],
                text="", score=ps["score"],
                match_type=ps.get("match_type"),
                source_indices=ps.get("source_indices", []),
            ))

    # Build source responses
    source_responses = []
    for src in sources:
        src_spans = []
        if src.matched_spans:
            spans_list = src.matched_spans.get("spans", []) if isinstance(src.matched_spans, dict) else src.matched_spans
            for s in spans_list:
                src_spans.append(HighlightSpan(
                    start_char=s["start_char"], end_char=s["end_char"],
                    match_type=s["match_type"], similarity=s["similarity"],
                    source_index=s.get("source_index", src.source_index),
                    source_name=s.get("source_name", src.source_name),
                    group_type=s.get("group_type"),
                    overlapping_sources=s.get("overlapping_sources", []),
                    top_source_id=s.get("top_source_id"),
                ))
        source_responses.append(MatchedSourceResponse(
            source_index=src.source_index,
            source_name=src.source_name,
            source_url=src.source_url,
            source_type=src.source_type,
            match_percentage=src.match_percentage,
            color=src.color,
            matched_spans=src_spans,
        ))

    return {
        "id": str(report.id),
        "document_id": str(report.document_id),
        "document_name": doc.original_name if doc else "",
        "overall_score": report.overall_score,
        "exact_score": report.exact_score,
        "semantic_score": report.semantic_score,
        "source_density_score": report.source_density_score,
        "risk_level": report.risk_level,
        "total_words": report.total_words,
        "total_pages": report.total_pages,
        "matched_words": report.matched_words,
        "total_sources": report.total_sources,
        "highlights": [h.model_dump() for h in highlights],
        "matched_sources": [s.model_dump() for s in source_responses],
        "paragraph_scores": [p.model_dump() for p in para_scores],
        "full_text": doc.extracted_text or "" if doc else "",
        "pdf_status": report.pdf_status,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/report/{report_id}/html")
async def get_report_html(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get rendered HTML report."""
    result = await db.execute(
        select(Report).join(Document).where(
            Report.id == report_id, Document.user_id == user.id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    html = report_service.get_html_report(report)
    if not html:
        raise HTTPException(404, "HTML report not available")

    return HTMLResponse(content=html)


@router.get("/report/{report_id}/pdf")
async def download_report_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download PDF report."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"PDF download request received for report_id={report_id} by user={user.username}")
    result = await db.execute(
        select(Report).join(Document).where(
            Report.id == report_id, Document.user_id == user.id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    pdf_path = report_service.get_pdf_path(report)
    
    # If PDF path does not exist on disk or is not configured
    if not pdf_path or not pdf_path.exists():
        logger.warning(f"PDF file missing on disk for report_id={report_id}. Current status: {report.pdf_status}")
        
        if report.pdf_status == "generating":
            raise HTTPException(
                status_code=409,
                detail="PDF report is currently generating. Please try again shortly."
            )
            
        # If missing on disk or failed, trigger automatic synchronous regeneration
        logger.info(f"Triggering synchronous PDF regeneration for report_id={report_id}")
        report = await report_service.regenerate_pdf(db, report_id)
        pdf_path = report_service.get_pdf_path(report)
        
        if not pdf_path or not pdf_path.exists():
            logger.error(f"Failed to regenerate PDF on download request for report_id={report_id}. Status: {report.pdf_status}")
            raise HTTPException(
                status_code=404,
                detail="PDF file not found on disk and regeneration failed."
            )
            
    # PDF is ready
    logger.info(f"Serving PDF report for report_id={report_id}. Path: {pdf_path}, size: {pdf_path.stat().st_size} bytes")
    doc_result = await db.execute(select(Document).where(Document.id == report.document_id))
    doc = doc_result.scalar_one_or_none()
    filename = f"PlagX_Report_{doc.original_name if doc else 'document'}.pdf"

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
    )


@router.post("/report/{report_id}/pdf/regenerate")
async def regenerate_report_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually trigger PDF regeneration for a report."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"Manual PDF regeneration requested for report_id={report_id} by user={user.username}")
    result = await db.execute(
        select(Report).join(Document).where(
            Report.id == report_id, Document.user_id == user.id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
        
    updated_report = await report_service.regenerate_pdf(db, report_id)
    if updated_report.pdf_status == "ready":
        return {
            "status": "success",
            "message": "PDF regenerated successfully",
            "pdf_status": updated_report.pdf_status
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"PDF regeneration failed. Status: {updated_report.pdf_status}"
        )


@router.get("/report-by-document/{document_id}")
async def get_report_by_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get report by document ID."""
    result = await db.execute(
        select(Report).join(Document).where(
            Report.document_id == document_id, Document.user_id == user.id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found for this document")

    # Redirect to full report endpoint
    return await get_report(report.id, db, user)


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get dashboard statistics."""
    # Total documents
    total_docs = (await db.execute(
        select(func.count(Document.id)).where(Document.user_id == user.id)
    )).scalar() or 0

    # Total reports
    total_reports = (await db.execute(
        select(func.count(Report.id)).join(Document).where(Document.user_id == user.id)
    )).scalar() or 0

    # Average score
    avg_score = (await db.execute(
        select(func.avg(Report.overall_score)).join(Document).where(Document.user_id == user.id)
    )).scalar() or 0.0

    # High risk count
    high_risk = (await db.execute(
        select(func.count(Report.id)).join(Document).where(
            Document.user_id == user.id, Report.risk_level == "high"
        )
    )).scalar() or 0

    # Recent reports
    recent_q = (
        select(Report, Document.original_name)
        .join(Document)
        .where(Document.user_id == user.id)
        .order_by(desc(Report.created_at))
        .limit(5)
    )
    recent_result = await db.execute(recent_q)
    recent = []
    for row in recent_result:
        report = row[0]
        doc_name = row[1]
        recent.append(ReportSummaryResponse(
            id=report.id, document_id=report.document_id,
            document_name=doc_name, overall_score=report.overall_score,
            risk_level=report.risk_level, total_sources=report.total_sources,
            created_at=report.created_at,
        ))

    return DashboardStatsResponse(
        total_documents=total_docs, total_reports=total_reports,
        average_score=round(float(avg_score), 1), high_risk_count=high_risk,
        recent_reports=recent,
    )


@router.get("/report/{report_id}/explain")
async def explain_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get structured explainability metadata for every suspicious span in a report."""
    result = await db.execute(
        select(Report).join(Document).where(
            Report.id == report_id, Document.user_id == user.id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    spans_metadata = []
    if report.highlights and "spans" in report.highlights:
        for s in report.highlights["spans"]:
            spans_metadata.append({
                "match_type": s.get("match_type", "exact"),
                "confidence": s.get("confidence_score", 1.0),
                "citation_status": s.get("group_type", "Uncited Copy"),
                "rarity": s.get("rarity_score", 1.0),
                "section": s.get("section", "Body"),
                "primary_source": s.get("source_name", "Unknown Source"),
                "secondary_sources": [o.get("source_name") for o in s.get("overlapping_sources", [])],
                "semantic_score": s.get("similarity", 1.0),
                "token_count": len(s.get("matched_text", "").split()),
                "engine_version": "2.0.0",
                "start_char": s.get("start_char"),
                "end_char": s.get("end_char"),
            })

    return {
        "report_id": report.id,
        "document_id": report.document_id,
        "overall_score": report.overall_score,
        "risk_level": report.risk_level,
        "engine_version": "2.0.0",
        "scoring_version": "2.0.0",
        "spans_explainability": spans_metadata,
    }

