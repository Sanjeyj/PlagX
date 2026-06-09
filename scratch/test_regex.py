import re

BIBLIOGRAPHY_HEADERS = re.compile(
    r'^\s*(?:\d+[\.\s]+)?(?:references|bibliography|works\s+cited|literature\s+cited|'
    r'sources|citations|cited\s+works|reference\s+list|notes|endnotes|'
    r'further\s+reading|primary\s+sources|secondary\s+sources)[\s:]*$',
    re.IGNORECASE | re.MULTILINE,
)

NARRATIVE_CITATION = re.compile(
    r'\b[A-Z][a-zA-Z.]+(?:\s+(?:and|&)\s+[A-Z][a-zA-Z.]+)?(?:\s+et\s+al\.?)?\s*\(\d{4}[a-z]?\)'
)

def test():
    test_headers = [
        "References",
        "10. References",
        "  Bibliography: ",
        "Works Cited",
        "References and Bibliography" # shouldn't match unless we support it
    ]
    for h in test_headers:
        m = BIBLIOGRAPHY_HEADERS.match(h)
        print(f"Header '{h}': {'MATCH' if m else 'NO MATCH'}")
        
    test_citations = [
        "Doe & Smith (2020)",
        "According to Smith (2020), vision is...",
        "Johnson et al. (2018) showed that",
        "This is (Smith et al., 2021) in parentheses", # should not match NARRATIVE_CITATION, but will be matched by parenthetical citation regex
        "A. Smith (2019) is a narrative cite"
    ]
    for c in test_citations:
        m = NARRATIVE_CITATION.search(c)
        print(f"Citation in '{c}': MATCH = '{m.group()}'" if m else f"Citation in '{c}': NO MATCH")

if __name__ == "__main__":
    test()
