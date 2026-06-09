"""
Advanced Citation, Bibliography, and Template Exclusion Engine
Detects properly cited content, reference lists, common academic boilerplate,
and template structures to classify matches into Turnitin-style severity groups.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Bibliography section headers - expanded to Notes, Sources, Endnotes, etc. and supporting numbering/colons
BIBLIOGRAPHY_HEADERS = re.compile(
    r'^\s*(?:\d+[\.\s]+)?(?:references|bibliography|works\s+cited|literature\s+cited|'
    r'sources|citations|cited\s+works|reference\s+list|notes|endnotes|'
    r'further\s+reading|primary\s+sources|secondary\s+sources)[\s:]*$',
    re.IGNORECASE | re.MULTILINE,
)

# APA in-text citations: (Author, 2020) or (Author & Author, 2020, p. 5)
APA_CITATION = re.compile(
    r'\([A-Z][a-z]+(?:\s+(?:&|and)\s+[A-Z][a-z]+)*'
    r'(?:\s+et\s+al\.?)?,?\s*\d{4}[a-z]?(?:,\s*pp?\.\s*\d+(?:-\d+)?)?\)',
)

# IEEE citations: [1], [2, 3], [1-5]
IEEE_CITATION = re.compile(r'\[(\d+(?:\s*[-–,]\s*\d+)*)\]')

# MLA/Chicago: (Author page) or footnote markers
MLA_CITATION = re.compile(r'\([A-Z][a-z]+\s+\d+(?:-\d+)?\)')

# Narrative citations: Author (Year), Author and Author (Year), Author et al. (Year)
NARRATIVE_CITATION = re.compile(
    r'\b[A-Z][a-zA-Z.]+(?:\s+(?:and|&)\s+[A-Z][a-zA-Z.]+)?(?:\s+et\s+al\.?)?\s*\(\d{4}[a-z]?\)'
)

# Quoted text: "..." or '...'
QUOTED_TEXT = re.compile(r'["\u201c][^"\u201d]{10,}["\u201d]')

# DOI and URL patterns
DOI_PATTERN = re.compile(r'https?://doi\.org/\S+|doi:\s*\S+', re.IGNORECASE)
URL_PATTERN = re.compile(r'https?://\S+')

# New patterns
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
AFFILIATION_PATTERN = re.compile(r'(?:Department|Faculty|School|University|Institute|College)\s+of\s+[A-Z][\w\s,]+')
TEMPLATE_HEADINGS = re.compile(
    r'^\s*(?:Abstract|Introduction|Methodology|Methods|Results|Discussion|Conclusion|'
    r'Acknowledgments|Appendix|References|Table\s+of\s+Contents|List\s+of\s+Figures|'
    r'List\s+of\s+Tables)\s*$',
    re.IGNORECASE | re.MULTILINE
)

# Stop words for length check after filtering
ENGLISH_STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "cant", "cannot", "could",
    "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont", "down", "during", "each", "few", "for", "from",
    "further", "had", "hadnt", "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes", "her", "here",
    "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "im", "ive", "if", "in", "into",
    "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt", "so", "some", "such", "than", "that",
    "thats", "the", "their", "theirs", "them", "themselves", "then", "there", "theres", "these", "they", "theyd",
    "theyll", "theyre", "theyve", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasnt", "we", "wed", "well", "were", "weve", "werent", "what", "whats", "when", "whens", "where", "wheres",
    "which", "while", "who", "whos", "whom", "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd",
    "youll", "youre", "youve", "your", "yours", "yourself", "yourselves"
}

# Common academic phrases that should not be flagged (Expanded to 80+ entries)
WHITELIST_PHRASES = [
    # Openings / Transitions
    "in conclusion", "in this paper", "the purpose of this study", "according to",
    "it is important to note", "on the other hand", "in other words", "as a result",
    "for example", "for instance", "in addition", "furthermore", "moreover",
    "however", "nevertheless", "in contrast", "as mentioned above", "the results show",
    "the findings suggest", "the data indicates", "based on the results", "this study aims",
    "the objective of this research", "methodology", "literature review", "theoretical framework",
    "research methodology", "data collection", "data analysis", "the following section",
    "as shown in figure", "as shown in table", "statistically significant", "standard deviation",
    "null hypothesis", "peer reviewed", "systematic review", "meta analysis",
    # Methodology & Process
    "participants were recruited", "data was collected", "informed consent was obtained",
    "a semi-structured interview", "a random sample of", "the experimental group",
    "the control group", "designed to measure the", "with a mean age of", "divided into two groups",
    "the main objective of", "to investigate the effects of", "conducted in accordance with",
    "the ethical approval for", "were statistical analyzed using", "a significance level of",
    "the results of the analysis", "the reliability and validity", "independent variables",
    "dependent variables", "statistically significant difference", "correlation coefficient",
    "chi-square test", "t-test was performed", "analysis of variance",
    # Results & Arguments
    "the findings of this study", "consistent with previous research", "in line with the literature",
    "p-value less than", "no significant difference was found", "can be explained by the",
    "contrary to our hypothesis", "a positive correlation between", "a negative correlation between",
    "plays a crucial role in", "further research is needed to", "the limitations of this study",
    "should be interpreted with caution", "does not necessarily imply", "can be seen as a",
    # General Academic Boilerplate
    "has received considerable attention", "interest in this field has", "a wide range of",
    "in recent years there has", "plays an important role", "is beyond the scope of",
    "highly dependent on the", "to the best of our knowledge", "has been widely documented",
    "a growing body of literature", "points to the conclusion that", "serves as a basis for",
    "will be discussed in detail", "contributes to our understanding", "further investigation is required"
]


class CitationExcluder:
    """
    Detects and marks bibliography sections, in-text citations,
    quoted text, email/URLs, metadata/affiliations, and boilerplate phrases.
    Classifies matches into Turnitin-style Match Groups.
    """

    def __init__(self):
        self.whitelist_set = set(p.lower().strip() for p in WHITELIST_PHRASES)

    def find_bibliography_boundary(self, text: str) -> int | None:
        """Find the character offset where the bibliography/references section begins using hybrid heuristics."""
        heading_matches = list(BIBLIOGRAPHY_HEADERS.finditer(text))
        doc_len = len(text)
        half_doc = doc_len * 0.5
        
        heading_boundary = None
        for match in heading_matches:
            if match.start() >= half_doc:
                heading_boundary = match.start()
                break
        if heading_boundary is None and heading_matches:
            heading_boundary = heading_matches[-1].start()
            
        # Density-based validation for fallback or reinforcement
        density_boundary = None
        if doc_len > 1000:
            start_search = int(doc_len * 0.5)  # Start from middle of document
            # Find candidate paragraph boundaries
            blocks = []
            prev_idx = start_search
            for m in re.finditer(r'\n+', text[start_search:]):
                curr_idx = start_search + m.start()
                if curr_idx > prev_idx:
                    blocks.append((prev_idx, curr_idx))
                prev_idx = start_search + m.end()
            if prev_idx < doc_len:
                blocks.append((prev_idx, doc_len))
            
            ref_indicators = [
                re.compile(r'pp?\.\s*\d+', re.IGNORECASE),
                re.compile(r'\d{4}'),
                re.compile(r'vol\.\s*\d+', re.IGNORECASE),
                re.compile(r'no\.\s*\d+', re.IGNORECASE),
                re.compile(r'doi:\s*\S+', re.IGNORECASE),
                re.compile(r'https?://', re.IGNORECASE),
                re.compile(r'journal', re.IGNORECASE),
                re.compile(r'university', re.IGNORECASE),
                re.compile(r'press', re.IGNORECASE),
                re.compile(r'cite', re.IGNORECASE)
            ]
            for b_start, b_end in blocks:
                block_text = text[b_start:b_end].strip()
                words = block_text.split()
                if len(words) < 10:
                    continue
                matches_count = 0
                for pattern in ref_indicators:
                    matches_count += len(pattern.findall(block_text))
                
                # Check reference density: at least 1.2 indicators per 10 words
                if matches_count / (len(words) / 10.0) >= 1.2:
                    density_boundary = b_start
                    break
                    
        if heading_boundary is not None and density_boundary is not None:
            if abs(heading_boundary - density_boundary) < 1000:
                return min(heading_boundary, density_boundary)
            return heading_boundary
        return heading_boundary or density_boundary

    def mark_exclusions(self, doc_map, text: str) -> None:
        """Mark tokens in doc_map as is_excluded if they belong to excluded categories before matching."""
        bib_start = self.find_bibliography_boundary(text)
        
        # 1. Identify pre-abstract / title-page region (up to "Abstract" or 3000 chars)
        abstract_match = re.search(r'\babstract\b', text[:3000], re.IGNORECASE)
        pre_abstract_limit = abstract_match.start() if abstract_match else min(1500, len(text))
        
        excluded_ranges = []
        
        # In-text citation markers (APA, IEEE, MLA, Narrative) are excluded ANYWHERE in the document
        for match in APA_CITATION.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
        for match in IEEE_CITATION.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
        for match in MLA_CITATION.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
        for match in NARRATIVE_CITATION.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
            
        # Emails, DOIs, URLs are excluded ANYWHERE in the document
        for match in EMAIL_PATTERN.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
        for match in DOI_PATTERN.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
        for match in URL_PATTERN.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
            
        # Boilerplate academic phrases anywhere in the document
        text_lower = text.lower()
        for phrase in self.whitelist_set:
            phrase_len = len(phrase)
            start_idx = 0
            while True:
                idx = text_lower.find(phrase, start_idx)
                if idx == -1:
                    break
                excluded_ranges.append((idx, idx + phrase_len))
                start_idx = idx + 1

        # Affiliations, metadata, and author names are excluded aggressively in the pre-abstract region
        pre_abstract_text = text[:pre_abstract_limit]
        
        for match in TEMPLATE_HEADINGS.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
            
        # Scan line-by-line in the pre-abstract region
        lines = pre_abstract_text.split('\n')
        curr_offset = 0
        for line in lines:
            line_len = len(line)
            line_stripped = line.strip()
            if line_stripped:
                line_lower = line_stripped.lower()
                is_metadata = False
                
                # Check for email, DOI, or URL
                if EMAIL_PATTERN.search(line_stripped) or DOI_PATTERN.search(line_stripped) or URL_PATTERN.search(line_stripped):
                    is_metadata = True
                # Check for affiliation keywords
                elif AFFILIATION_PATTERN.search(line_stripped) or any(kwd in line_lower for kwd in ['department', 'faculty', 'school', 'university', 'institute', 'college', 'laboratory', 'corp', 'inc.', 'ltd.']):
                    is_metadata = True
                # Check for document metadata keywords
                elif any(kwd in line_lower for kwd in ['proceedings', 'journal of', 'transactions on', 'ieee', 'acm', 'springer', 'elsevier', 'arxiv', 'preprint', 'vol.', 'no.', 'issn', 'isbn', 'copyright', 'all rights reserved', 'published in']):
                    is_metadata = True
                # Check for author names or title line (capitalization heuristics)
                else:
                    words = [w for w in line_stripped.split() if w.isalpha()]
                    if words and len(words) < 12:
                        cap_words = [w for w in words if w[0].isupper() or w in ('and', 'or', 'of', 'for', 'the', 'a', 'an', '&')]
                        if len(cap_words) / len(words) >= 0.8:
                            is_metadata = True
                            
                if is_metadata:
                    excluded_ranges.append((curr_offset, curr_offset + line_len))
            curr_offset += line_len + 1
            
        # Optimize range check: Sort and merge overlapping excluded ranges
        if excluded_ranges:
            excluded_ranges.sort(key=lambda r: r[0])
            merged_ranges = []
            for start, end in excluded_ranges:
                if not merged_ranges:
                    merged_ranges.append((start, end))
                else:
                    last_start, last_end = merged_ranges[-1]
                    if start <= last_end:
                        merged_ranges[-1] = (last_start, max(last_end, end))
                    else:
                        merged_ranges.append((start, end))
            excluded_ranges = merged_ranges
            
        # Single-pass token marking
        range_idx = 0
        num_ranges = len(excluded_ranges)
        for token in doc_map.tokens:
            if bib_start is not None and token.start_char >= bib_start:
                token.is_excluded = True
                continue
                
            token_mid = (token.start_char + token.end_char) // 2
            
            # Advance range_idx while the current range ends before token_mid
            while range_idx < num_ranges and excluded_ranges[range_idx][1] <= token_mid:
                range_idx += 1
                
            if range_idx < num_ranges:
                start, end = excluded_ranges[range_idx]
                if start <= token_mid < end:
                    token.is_excluded = True

    def find_citation_spans(self, text: str) -> list[tuple[int, int, str]]:
        """
        Find all citation and quote spans in the text.
        Returns list of (start_char, end_char, citation_type).
        """
        spans = []

        for match in APA_CITATION.finditer(text):
            spans.append((match.start(), match.end(), "apa"))

        for match in IEEE_CITATION.finditer(text):
            spans.append((match.start(), match.end(), "ieee"))

        for match in MLA_CITATION.finditer(text):
            spans.append((match.start(), match.end(), "mla"))

        for match in NARRATIVE_CITATION.finditer(text):
            spans.append((match.start(), match.end(), "narrative"))

        for match in QUOTED_TEXT.finditer(text):
            spans.append((match.start(), match.end(), "quoted"))

        return sorted(spans, key=lambda x: x[0])

    def is_in_bibliography(self, char_offset: int, bibliography_start: int | None) -> bool:
        """Check if a character offset falls within the bibliography section."""
        if bibliography_start is None:
            return False
        return char_offset >= bibliography_start

    def is_citation_span(self, start: int, end: int, citation_spans: list) -> bool:
        """Check if a text span overlaps with any citation."""
        for cit_start, cit_end, _ in citation_spans:
            if start < cit_end and end > cit_start:
                return True
        return False

    def is_whitelisted(self, text: str) -> bool:
        """Check if text is a common academic phrase that should not be flagged."""
        text_lower = text.lower().strip()
        text_clean = re.sub(r'[^\w\s]', '', text_lower)
        text_clean = " ".join(text_clean.split())
        
        for phrase in self.whitelist_set:
            phrase_clean = re.sub(r'[^\w\s]', '', phrase)
            if phrase_clean in text_clean and len(text_clean) < len(phrase_clean) + 25:
                return True
        return False

    def should_exclude_chunk(
        self,
        chunk_start: int,
        chunk_end: int,
        chunk_text: str,
        bibliography_start: int | None,
        citation_spans: list,
    ) -> tuple[bool, str]:
        """
        Determine if a chunk should be excluded from plagiarism scoring.
        """
        if self.is_in_bibliography(chunk_start, bibliography_start):
            return True, "bibliography"

        if self.is_whitelisted(chunk_text):
            return True, "whitelist"

        url_chars = sum(len(m.group()) for m in URL_PATTERN.finditer(chunk_text))
        doi_chars = sum(len(m.group()) for m in DOI_PATTERN.finditer(chunk_text))
        email_chars = sum(len(m.group()) for m in EMAIL_PATTERN.finditer(chunk_text))
        
        if (url_chars + doi_chars + email_chars) > len(chunk_text) * 0.4:
            return True, "boilerplate_content"

        if chunk_end <= 500:
            if AFFILIATION_PATTERN.search(chunk_text) or EMAIL_PATTERN.search(chunk_text):
                return True, "metadata_affiliation"

        if TEMPLATE_HEADINGS.match(chunk_text.strip()):
            return True, "template_heading"

        return False, ""

    def should_exclude_span(
        self,
        start_char: int,
        end_char: int,
        text: str,
        bibliography_start: int | None,
    ) -> bool:
        """
        Determine if a finalized match span should be excluded.
        """
        if self.is_in_bibliography(start_char, bibliography_start):
            return True

        if self.is_whitelisted(text):
            return True

        if end_char <= 500:
            if AFFILIATION_PATTERN.search(text) or EMAIL_PATTERN.search(text):
                return True

        if TEMPLATE_HEADINGS.match(text.strip()):
            return True

        text_len = len(text.strip()) or 1
        url_len = sum(len(m.group()) for m in URL_PATTERN.finditer(text))
        email_len = sum(len(m.group()) for m in EMAIL_PATTERN.finditer(text))
        if (url_len + email_len) / text_len >= 0.8:
            return True

        words = [w.lower().strip() for w in text.split()]
        meaningful_words = [w for w in words if w not in ENGLISH_STOP_WORDS]
        if len(meaningful_words) < 3:
            return True

        return False

    def classify_match_span(
        self,
        start_char: int,
        end_char: int,
        text: str,
        bibliography_start: int | None,
        citation_spans: list,
        semantic_confidence: float = 1.0,
        is_exact: bool = True
    ) -> tuple[str, bool]:
        """
        Intelligently classify a MatchSpan into Turnitin match severity groups.
        Returns (group_type, is_whitelisted)
        """
        if self.is_in_bibliography(start_char, bibliography_start):
            return "bibliography", True
            
        if self.is_whitelisted(text) or self.should_exclude_span(start_char, end_char, text, bibliography_start):
            return "boilerplate", True
            
        has_citation = False
        has_quote = False
        
        for cit_start, cit_end, cit_type in citation_spans:
            if start_char - 40 < cit_end and end_char + 40 > cit_start:
                if cit_type == "quoted":
                    has_quote = True
                else:
                    has_citation = True
                    
        if has_citation and has_quote:
            return "cited_and_quoted", True
        elif has_quote and not has_citation:
            return "missing_citation", False
        elif has_citation and not has_quote:
            if not is_exact:
                # Semantic match with citation is proper paraphrase attribution (cited and quoted)
                return "cited_and_quoted", True
            return "missing_quotation", False
            
        if not is_exact:
            if semantic_confidence < 0.80:
                return "weak_overlap", False
                
        return "uncited_overlap", False

    def get_exclusion_stats(self, text: str) -> dict:
        """Get statistics about excluded content."""
        bib_start = self.find_bibliography_boundary(text)
        citations = self.find_citation_spans(text)

        bib_chars = len(text) - bib_start if bib_start else 0
        citation_chars = sum(end - start for start, end, _ in citations)

        return {
            "bibliography_start": bib_start,
            "bibliography_chars": bib_chars,
            "citation_count": len(citations),
            "citation_chars": citation_chars,
            "total_excluded_chars": bib_chars + citation_chars,
            "exclusion_percentage": (bib_chars + citation_chars) / max(len(text), 1) * 100,
        }
