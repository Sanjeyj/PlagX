"""Report service for CRUD operations and PDF caching."""

import uuid
import json
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.report import Report, MatchedSource
from app.engine.pipeline import PlagiarismResult, SourceInfo
from app.report.html_builder import HTMLReportBuilder
from app.report.pdf_generator import PDFGenerator

settings = get_settings()
logger = logging.getLogger(__name__)


class ReportService:
    """Manages report creation, storage, and retrieval."""

    def __init__(self):
        self.html_builder = HTMLReportBuilder()
        self.pdf_generator = PDFGenerator()
        self.reports_dir = settings.reports_path

    async def create_report(
        self, db: AsyncSession, document_id: str, result: PlagiarismResult
    ) -> Report:
        """Create a report from plagiarism analysis results."""
        report_id = str(uuid.uuid4())

        # Build highlight data for JSON storage
        highlights_data = [
            {
                "start_char": s.start_char,
                "end_char": s.end_char,
                "match_type": s.match_type,
                "similarity": round(s.similarity, 3),
                "source_index": s.source_index,
                "source_name": s.source_name,
                "paragraph_index": s.paragraph_index,
                "group_type": s.group_type,
                "overlapping_sources": s.overlapping_sources,
                "top_source_id": s.top_source_id,
            }
            for s in result.all_spans
        ]

        # Build sources data
        sources_data = [
            {
                "source_index": s.source_index,
                "source_name": s.source_name,
                "match_percentage": s.match_percentage,
                "color": s.color,
                "exact_matches": s.exact_matches,
                "semantic_matches": s.semantic_matches,
            }
            for s in result.sources
        ]

        # Generate HTML report
        html_content = self.html_builder.build(result, report_id)
        html_path = self.reports_dir / f"{report_id}.html"
        html_path.write_text(html_content, encoding="utf-8")

        # Generate PDF report
        pdf_path = self.reports_dir / f"{report_id}.pdf"
        pdf_status = "generating"
        try:
            self.pdf_generator.generate_in_thread(html_content, str(pdf_path), report_id=report_id)
            if pdf_path.exists():
                pdf_status = "ready"
                logger.info(f"PDF generated successfully during report creation for {report_id}")
            else:
                pdf_status = "failed"
                logger.error(f"PDF generation finished but file was not created for {report_id}")
        except Exception as e:
            pdf_status = "failed"
            logger.error(f"PDF generation failed during report creation for {report_id}: {e}", exc_info=True)

        # Create DB record
        report = Report(
            id=report_id,
            document_id=document_id,
            overall_score=result.overall_score,
            exact_score=result.exact_score,
            semantic_score=result.semantic_score,
            source_density_score=result.source_density_score,
            risk_level=result.risk_level,
            ai_score=result.ai_probability,
            ai_confidence=result.ai_confidence,
            ai_suspicious_spans={"spans": result.ai_suspicious_spans},
            highlights={"spans": highlights_data},
            matched_sources_data={"sources": sources_data},
            paragraph_scores={"scores": result.paragraph_scores},
            document_structure=result.exclusion_stats,
            integrity_flags=result.integrity_flags,
            total_words=result.total_words,
            total_pages=result.total_pages,
            matched_words=result.matched_words,
            total_sources=len(result.sources),
            html_report_path=str(html_path),
            pdf_report_path=str(pdf_path) if pdf_path.exists() and pdf_status == "ready" else None,
            pdf_status=pdf_status,
        )
        db.add(report)

        # Create matched source records
        for src in result.sources:
            matched_src = MatchedSource(
                report_id=report_id,
                source_index=src.source_index,
                source_name=src.source_name,
                source_type="repository",
                match_percentage=src.match_percentage,
                color=src.color,
                matched_spans={
                    "spans": [
                        {
                            "start_char": s.start_char, "end_char": s.end_char,
                            "match_type": s.match_type, "similarity": round(s.similarity, 3),
                            "source_index": s.source_index, "source_name": s.source_name,
                            "group_type": s.group_type, "overlapping_sources": s.overlapping_sources,
                            "top_source_id": s.top_source_id
                        }
                        for s in src.matched_spans
                    ]
                },
            )
            db.add(matched_src)

        await db.flush()
        await db.refresh(report)
        logger.info(f"Report created: {report_id} (score: {result.overall_score}%)")
        return report

    def get_html_report(self, report: Report) -> str | None:
        """Get HTML report content."""
        if report.html_report_path:
            path = Path(report.html_report_path)
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None

    def get_pdf_path(self, report: Report) -> Path | None:
        """Get PDF report file path."""
        if report.pdf_report_path:
            path = Path(report.pdf_report_path)
            if path.exists():
                return path
        return None

    async def generate_pdf_for_report(self, report: Report, db: AsyncSession = None) -> bool:
        """Generate PDF for an existing report, updating DB status."""
        logger.info(f"Generating PDF for report {report.id} from existing HTML")
        report.pdf_status = "generating"
        if db:
            await db.commit()

        html_content = self.get_html_report(report)
        if not html_content:
            logger.error(f"HTML report file not found for report {report.id}")
            report.pdf_status = "failed"
            if db:
                await db.commit()
            return False

        pdf_path = self.reports_dir / f"{report.id}.pdf"
        try:
            self.pdf_generator.generate_in_thread(html_content, str(pdf_path), report_id=report.id)
            if pdf_path.exists():
                report.pdf_report_path = str(pdf_path)
                report.pdf_status = "ready"
                logger.info(f"PDF generation successful for report {report.id}")
                if db:
                    await db.commit()
                return True
            else:
                logger.error(f"PDF file does not exist after generation for report {report.id}")
                report.pdf_status = "failed"
                if db:
                    await db.commit()
                return False
        except Exception as e:
            logger.error(f"PDF generation failed for report {report.id}: {e}", exc_info=True)
            report.pdf_status = "failed"
            if db:
                await db.commit()
            return False

    async def regenerate_pdf(self, db: AsyncSession, report_id: str) -> Report | None:
        """Trigger PDF regeneration for a report."""
        report = await db.get(Report, report_id)
        if not report:
            return None

        report.pdf_status = "generating"
        await db.commit()

        try:
            html_content = self.get_html_report(report)
            if not html_content:
                logger.error(f"Cannot regenerate PDF: HTML report file missing for {report_id}")
                report.pdf_status = "failed"
                await db.commit()
                return report

            pdf_path = self.reports_dir / f"{report_id}.pdf"
            self.pdf_generator.generate_in_thread(html_content, str(pdf_path), report_id=report_id)

            if pdf_path.exists():
                report.pdf_report_path = str(pdf_path)
                report.pdf_status = "ready"
                logger.info(f"PDF regenerated successfully for report {report_id}")
            else:
                report.pdf_status = "failed"
                logger.error(f"PDF file does not exist after regeneration for report {report_id}")

            await db.commit()
            return report
        except Exception as e:
            logger.error(f"Regeneration failed for report {report_id}: {e}", exc_info=True)
            report.pdf_status = "failed"
            await db.commit()
            return report
