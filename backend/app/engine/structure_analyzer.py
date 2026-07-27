"""
Document Structure Analyzer for PlagX Enterprise Similarity Engine v2
Parses structural zones of academic and technical documents and assigns processing policies.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

from app.engine.config import DocumentStructureConfig, default_config

logger = logging.getLogger(__name__)


@dataclass
class DocumentSection:
    section_type: str  # title, authors, affiliations, emails, abstract, keywords, intro, methodology, results, discussion, conclusion, references, appendix, header_footer, table, caption, code_block
    start_char: int
    end_char: int
    text: str
    policy: str  # "primary", "suppress", "exclude"
    weight_modifier: float = 1.0


class DocumentStructureAnalyzer:
    """
    Identifies academic document structure zones (Metadata, Abstract, Intro,
    Methodology, Results, Discussion, Conclusion, References, Code Blocks, etc.)
    and assigns section-specific scoring policies.
    """

    # Section patterns
    SECTION_PATTERNS = [
        ("title", r'^(?:title|paper title)[:\s]*', "suppress", 0.1),
        ("authors", r'^(?:authors?|by)[:\s]+[A-Z][a-z]+', "exclude", 0.0),
        ("emails", r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "exclude", 0.0),
        ("abstract", r'^(?:abstract|summary)[:\s]*', "primary", 1.0),
        ("keywords", r'^(?:keywords|index terms)[:\s]*', "suppress", 0.1),
        ("introduction", r'^(?:\d+[\.\s]+)?(?:introduction|background|overview)[:\s]*', "primary", 1.0),
        ("related_work", r'^(?:\d+[\.\s]+)?(?:related work|literature review|prior work)[:\s]*', "primary", 0.9),
        ("methodology", r'^(?:\d+[\.\s]+)?(?:methodology|methods|system model|proposed approach|architecture)[:\s]*', "primary", 1.0),
        ("results", r'^(?:\d+[\.\s]+)?(?:results|evaluation|experiments|performance)[:\s]*', "primary", 1.0),
        ("discussion", r'^(?:\d+[\.\s]+)?(?:discussion|analysis|limitation)[:\s]*', "primary", 1.0),
        ("conclusion", r'^(?:\d+[\.\s]+)?(?:conclusion|concluding remarks|future work)[:\s]*', "primary", 1.0),
        ("references", r'^(?:\d+[\.\s]+)?(?:references|bibliography|works cited|literature cited)[:\s]*', "exclude", 0.0),
        ("appendix", r'^(?:\d+[\.\s]+)?(?:appendix|supplementary material)[:\s]*', "exclude", 0.0),
    ]

    def __init__(self, config: Optional[DocumentStructureConfig] = None):
        self.config = config or default_config.structure

    def analyze(self, text: str) -> List[DocumentSection]:
        """Classify regions of full_text into structural sections with assigned policies."""
        sections: List[DocumentSection] = []
        lines = text.splitlines(keepends=True)
        current_offset = 0

        current_section_type = "introduction"  # Default assumption for body
        current_policy = "primary"
        current_modifier = 1.0
        section_start_char = 0

        for line in lines:
            line_len = len(line)
            line_strip = line.strip().lower()

            # Check header/footer patterns
            if re.match(r'^(?:page\s+\d+|header|footer|\d+\s+of\s+\d+)\b', line_strip):
                sections.append(DocumentSection(
                    section_type="header_footer",
                    start_char=current_offset,
                    end_char=current_offset + line_len,
                    text=line,
                    policy="exclude",
                    weight_modifier=0.0
                ))
                current_offset += line_len
                continue

            # Check code block markers
            if line_strip.startswith("```") or line_strip.startswith("def ") or line_strip.startswith("class "):
                sections.append(DocumentSection(
                    section_type="code_block",
                    start_char=current_offset,
                    end_char=current_offset + line_len,
                    text=line,
                    policy="suppress",
                    weight_modifier=0.2
                ))
                current_offset += line_len
                continue

            # Check section heading patterns
            matched_heading = False
            for s_type, pattern, policy, modifier in self.SECTION_PATTERNS:
                if re.search(pattern, line_strip, re.IGNORECASE):
                    # Close previous section
                    if current_offset > section_start_char:
                        sections.append(DocumentSection(
                            section_type=current_section_type,
                            start_char=section_start_char,
                            end_char=current_offset,
                            text=text[section_start_char:current_offset],
                            policy=current_policy,
                            weight_modifier=current_modifier
                        ))
                    
                    current_section_type = s_type
                    current_policy = policy
                    current_modifier = modifier
                    section_start_char = current_offset
                    matched_heading = True
                    break

            current_offset += line_len

        # Close final section
        if current_offset > section_start_char:
            sections.append(DocumentSection(
                section_type=current_section_type,
                start_char=section_start_char,
                end_char=current_offset,
                text=text[section_start_char:current_offset],
                policy=current_policy,
                weight_modifier=current_modifier
            ))

        logger.info(f"Analyzed {len(sections)} document structural zones.")
        return sections

    def get_policy_for_char(self, sections: List[DocumentSection], char_offset: int) -> Tuple[str, float]:
        """Find the processing policy and weight modifier for a given character offset."""
        for sec in sections:
            if sec.start_char <= char_offset < sec.end_char:
                return sec.policy, sec.weight_modifier
        return "primary", 1.0
