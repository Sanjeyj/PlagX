"""
HTML Highlight Injection Engine
Injects inline highlight spans into document text for plagiarism visualization.
Handles overlapping highlights, nested spans, and CSS integrity.
"""

import html
import logging
from app.engine.offset_mapper import MatchSpan

logger = logging.getLogger(__name__)

SOURCE_COLORS = [
    "#EF4444", "#F97316", "#EAB308", "#22C55E", "#3B82F6",
    "#8B5CF6", "#EC4899", "#14B8A6", "#F43F5E", "#6366F1",
]


def hex_to_rgba(hex_str: str, alpha: float = 0.15) -> str:
    """Convert a hex color string to rgba format."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c*2 for c in hex_str)
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    except Exception:
        return f"rgba(239, 68, 68, {alpha})"


class HighlightInjector:
    """
    Injects inline highlight spans into document HTML.
    Preserves paragraph structure and handles overlapping matches.
    """

    def inject_highlights(
        self,
        full_text: str,
        spans: list[MatchSpan],
        paragraphs: list = None,
    ) -> str:
        """
        Inject highlight spans into the document text and return HTML.
        Each highlight span wraps the matched text with metadata attributes.
        """
        if not spans:
            return self._text_to_html(full_text, paragraphs)

        # Sort spans by start position
        sorted_spans = sorted(spans, key=lambda s: (s.start_char, -(s.end_char - s.start_char)))

        # Build highlighted HTML
        result_parts = []
        last_pos = 0

        for span in sorted_spans:
            start = span.start_char
            end = span.end_char

            # Skip if this span starts before our current position (overlap handled by merge)
            if start < last_pos:
                start = last_pos
            if start >= end:
                continue

            # Add unhighlighted text before this span
            if start > last_pos:
                plain_text = full_text[last_pos:start]
                result_parts.append(html.escape(plain_text))

            # Add highlighted span
            highlighted_text = full_text[start:end]
            
            # Determine color and styling based on source index and match group
            source_color = SOURCE_COLORS[span.source_index % len(SOURCE_COLORS)] if span.source_index >= 0 else "#6B7280"
            bg_color = hex_to_rgba(source_color, 0.15)
            
            # Group type styles
            border_style = f"2px solid {source_color}"
            class_name = f"highlight-source source-{span.source_index}"
            
            if span.group_type in ("cited_and_quoted", "boilerplate", "weak_overlap"):
                # Excluded content / weak overlap: no highlighting
                bg_color = "transparent"
                border_style = "none"
            elif span.group_type == "missing_quotation":
                # Verbatim without quote: orange border warning
                border_style = "2px solid #F97316"
            elif span.group_type == "missing_citation":
                # Quoted without cite: yellow border warning
                border_style = "2px solid #EAB308"

            span_html = (
                f'<span class="{class_name}" '
                f'data-source="{span.source_index}" '
                f'data-source-name="{html.escape(span.source_name)}" '
                f'data-similarity="{span.similarity:.0%}" '
                f'data-match-type="{span.match_type}" '
                f'data-group-type="{span.group_type}" '
                f'style="background-color: {bg_color}; '
                f'border-bottom: {border_style}; '
                f'cursor: pointer; position: relative;"'
                f'>'
                f'{html.escape(highlighted_text)}'
                f'<sup style="color: {source_color}; font-weight: bold; margin-left: 2px; font-size: 10px; pointer-events: none;">'
                f'{span.source_index + 1 if span.source_index >= 0 else "?"}</sup>'
                f'</span>'
            )
            result_parts.append(span_html)
            last_pos = end

        # Add remaining text
        if last_pos < len(full_text):
            result_parts.append(html.escape(full_text[last_pos:]))

        raw_html = "".join(result_parts)

        # Wrap in paragraphs
        return self._wrap_paragraphs(raw_html)

    def _text_to_html(self, text: str, paragraphs: list = None) -> str:
        """Convert plain text to HTML with paragraph structure."""
        parts = text.split("\n")
        html_parts = []
        for part in parts:
            part = part.strip()
            if part:
                html_parts.append(f'<p class="doc-paragraph">{html.escape(part)}</p>')
        return "\n".join(html_parts)

    def _wrap_paragraphs(self, html_content: str) -> str:
        """Wrap line-break-separated content in paragraph tags."""
        lines = html_content.split("\n")
        wrapped = []
        for line in lines:
            line = line.strip()
            if line:
                wrapped.append(f'<p class="doc-paragraph" style="margin: 0.8em 0; line-height: 1.8; position: relative;">{line}</p>')
        return "\n".join(wrapped) if wrapped else html_content

    def generate_source_panel_html(self, sources: list) -> str:
        """Generate the source list panel as table rows for the PDF report."""
        if not sources:
            return '<tr><td colspan="4" style="text-align:center;padding:20px;color:#9ca3af;">No sources detected</td></tr>'

        rows = []
        for src in sources:
            color = src.color if hasattr(src, 'color') else SOURCE_COLORS[src.source_index % len(SOURCE_COLORS)]
            pct = src.match_percentage
            bar_width = min(int(pct * 1.2), 120)  # max 120px at 100%

            rows.append(
                f'<tr>'
                f'<td>'
                f'<span class="src-badge" style="background:{color};">{src.source_index + 1}</span>'
                f'</td>'
                f'<td style="font-size:12px;color:#111827;">{html.escape(src.source_name)}</td>'
                f'<td>'
                f'<div class="src-bar-wrap">'
                f'<div class="src-bar" style="width:{bar_width}px;background:{color};"></div>'
                f'</div>'
                f'</td>'
                f'<td style="text-align:right;font-weight:700;color:{color};font-family:monospace;">'
                f'{pct:.1f}%'
                f'</td>'
                f'</tr>'
            )
        return "\n".join(rows)

