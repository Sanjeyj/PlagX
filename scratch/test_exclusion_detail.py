import sys
import os
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Mock settings/env before imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///d:/PlagX/backend/plagx.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.engine.offset_mapper import OffsetMapper, ParagraphMapping
from app.engine.citation_excluder import CitationExcluder

sample_text = """Title: Deep Learning Models for Visual Recognition
Authors: John Smith, Jane Doe
Affiliations: Department of Computer Science, University of California, Berkeley
Emails: j.smith@berkeley.edu, j.doe@berkeley.edu

Abstract
Visual recognition has seen significant progress in recent years due to deep convolutional neural networks. This paper presents a novel model that achieves state-of-the-art performance on ImageNet.

Introduction
Deep learning models have revolutionized computer vision (Smith et al., 2021). According to Doe & Smith (2020), in recent years there has been a growing body of literature pointing to the conclusion that neural networks excel at extracting visual features. However, "the exact mechanisms of feature representation remain a mystery" (Smith, 2019, p. 45). On the other hand, standard methods still struggle with out-of-distribution generalization. For example, as shown in figure 1, the model fails when lighting conditions change.

Methodology
We conduct our experiments using the ImageNet dataset. The participants were recruited from a pool of volunteers. Data was collected over a period of three months. A random sample of images was selected for training.

References
1. Smith, J., & Doe, J. (2021). Deep Learning in Vision. Journal of Computer Vision, vol. 12, no. 3, pp. 100-112. doi:10.1002/jcv.123
2. Doe, J. (2020). Neural Networks and Vision. University Press.
3. Smith, J. (2019). Representation Learning. Journal of Machine Learning, 5(2), 34-46.
"""

def test_exclusions():
    mapper = OffsetMapper()
    excluder = CitationExcluder()
    
    # Split text into rough paragraph objects for the mapper
    paragraphs = []
    lines = sample_text.split("\n\n")
    start = 0
    for idx, p_text in enumerate(lines):
        p_text_stripped = p_text.strip()
        if not p_text_stripped:
            continue
        p_start = sample_text.find(p_text_stripped, start)
        p_end = p_start + len(p_text_stripped)
        
        class ParaObj:
            def __init__(self, index, start_char, end_char, text):
                self.paragraph_index = index
                self.start_char = start_char
                self.end_char = end_char
                self.text = text
                self.page_number = 1
                
        paragraphs.append(ParaObj(idx, p_start, p_end, p_text_stripped))
        start = p_end
        
    doc_map = mapper.build_document_map(sample_text, paragraphs, "academic_sample.txt")
    
    print(f"Total tokens generated: {len(doc_map.tokens)}")
    
    # Mark exclusions
    excluder.mark_exclusions(doc_map, sample_text)
    
    print("\n--- EXCLUDED TOKENS ANALYSIS ---")
    excluded_tokens = [t for t in doc_map.tokens if t.is_excluded]
    print(f"Excluded tokens: {len(excluded_tokens)} / {len(doc_map.tokens)}")
    
    # Let's inspect some tokens from each section
    print("\nTitle page / Metadata tokens:")
    meta_tokens = [t for t in doc_map.tokens if t.end_char <= 300]
    for t in meta_tokens:
        print(f"  '{t.text}' ({t.start_char}-{t.end_char}): excluded={t.is_excluded}")
        
    print("\nAbstract tokens:")
    abstract_start = sample_text.find("Abstract")
    abstract_end = sample_text.find("Introduction")
    abs_tokens = [t for t in doc_map.tokens if abstract_start <= t.start_char < abstract_end]
    for t in abs_tokens[:15]:
        print(f"  '{t.text}' ({t.start_char}-{t.end_char}): excluded={t.is_excluded}")
        
    print("\nCitations and Boilerplate tokens in Introduction:")
    intro_start = sample_text.find("Introduction")
    intro_end = sample_text.find("Methodology")
    intro_tokens = [t for t in doc_map.tokens if intro_start <= t.start_char < intro_end]
    # Find specific citation tokens
    for t in intro_tokens:
        if "smith" in t.text or "doe" in t.text or "al" in t.text or "mystery" in t.text or "recent" in t.text or "figure" in t.text:
            print(f"  '{t.text}' ({t.start_char}-{t.end_char}): excluded={t.is_excluded}")
            
    print("\nReferences tokens:")
    ref_start = sample_text.find("References")
    ref_tokens = [t for t in doc_map.tokens if t.start_char >= ref_start]
    for t in ref_tokens[:15]:
        print(f"  '{t.text}' ({t.start_char}-{t.end_char}): excluded={t.is_excluded}")

if __name__ == "__main__":
    test_exclusions()
