"""
HTML Report Builder
Renders the Jinja2 report template with plagiarism data.
"""

import logging
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

from app.report import HighlightInjector

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


class HTMLReportBuilder:
    """Builds professional HTML plagiarism reports from analysis results."""

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=False,
        )
        self.injector = HighlightInjector()

    def build(self, result, report_id: str = "") -> str:
        """Build complete HTML report from PlagiarismResult."""
        template = self.env.get_template("report.html")

        # Generate highlighted document HTML
        highlighted_html = self.injector.inject_highlights(
            result.full_text,
            result.all_spans,
            result.document_map.paragraphs if result.document_map else None,
        )

        # Generate sources panel HTML (table rows)
        sources_html = self.injector.generate_source_panel_html(result.sources)

        # Build paragraph scores with text preview
        para_scores_with_text = []
        if result.document_map:
            for ps in result.paragraph_scores:
                idx = ps["paragraph_index"]
                text = ""
                if idx < len(result.document_map.paragraphs):
                    text = result.document_map.paragraphs[idx].text
                para_scores_with_text.append({**ps, "text": text})

        html_content = template.render(
            report_id=report_id,
            document_name=result.document_map.source_filename if result.document_map else "Document",
            overall_score=result.overall_score,
            exact_score=result.exact_score,
            semantic_score=result.semantic_score,
            source_density=result.source_density_score,
            risk_level=result.risk_level,
            total_words=result.total_words,
            total_pages=result.total_pages,
            total_sources=len(result.sources),
            matched_words=result.matched_words,
            ai_score=getattr(result, "ai_score", 0) or 0,
            ai_confidence=getattr(result, "ai_confidence", "Unknown") or "Unknown",
            sources_html=sources_html,
            highlighted_html=highlighted_html,
            paragraph_scores=para_scores_with_text,
            report_date=datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            year=datetime.now().year,
        )

        logger.info(f"HTML report built ({len(html_content)} chars)")
        return html_content
