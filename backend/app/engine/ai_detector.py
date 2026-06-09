"""
AI Writing Detection Engine
Implements hybrid AI analysis using perplexity, burstiness, entropy, and stylometry.
"""

import math
import re
import logging
from typing import List, Dict, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class AIDetector:
    """
    Hybrid AI analysis engine.
    Analyzes text for AI-generated patterns using statistical heuristics
    and (optionally) a DeBERTa-v3/RoBERTa classifier.
    """

    def __init__(self):
        self._classifier = None
        # We lazy-load the classifier to save memory during initialization

    def _get_classifier(self):
        if self._classifier is None:
            try:
                from transformers import pipeline
                # The user requested DeBERTa-v3 or an AI detector. 
                # We use roberta-base-openai-detector as it's the standard for AI detection,
                # but we can also use a generic DeBERTa model if preferred.
                logger.info("Loading AI Detection model (this may take a moment)...")
                self._classifier = pipeline("text-classification", model="roberta-base-openai-detector")
            except Exception as e:
                logger.error(f"Failed to load AI detection model: {e}")
                self._classifier = False
        return self._classifier

    def _calculate_perplexity_burstiness(self, text: str) -> Tuple[float, float]:
        """
        Estimate perplexity and burstiness using stylometry and sentence structure.
        AI text typically has low perplexity (highly predictable) and low burstiness (uniform sentence length).
        Human text has high perplexity and high burstiness.
        """
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 5]
        if not sentences:
            return 0.0, 0.0

        lengths = [len(s.split()) for s in sentences]
        
        # Burstiness: variance in sentence length
        if len(lengths) > 1:
            mean_len = sum(lengths) / len(lengths)
            variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            burstiness = math.sqrt(variance)  # Standard deviation of sentence length
        else:
            burstiness = 0.0

        # Heuristic perplexity estimate based on unique vocabulary ratio (Type-Token Ratio)
        words = text.lower().split()
        if not words:
            return 0.0, burstiness
            
        unique_words = set(words)
        ttr = len(unique_words) / len(words)
        
        # Higher TTR roughly correlates with higher perplexity/vocabulary richness
        pseudo_perplexity = ttr * 100 
        
        return pseudo_perplexity, burstiness

    def _calculate_entropy(self, text: str) -> float:
        """Shannon entropy of character distribution."""
        if not text:
            return 0.0
        
        char_counts = {}
        for c in text:
            char_counts[c] = char_counts.get(c, 0) + 1
            
        entropy = 0.0
        total = len(text)
        for count in char_counts.values():
            p = count / total
            entropy -= p * math.log2(p)
            
        return entropy

    def analyze(self, text: str, paragraphs: List[Dict]) -> Dict:
        """
        Run the full hybrid AI analysis on the document.
        Returns the overall AI probability and highlighted suspicious spans.
        """
        if not text or len(text.strip()) < 50:
            return {
                "ai_probability": 0.0,
                "confidence_level": "Likely Human",
                "suspicious_spans": []
            }

        perplexity, burstiness = self._calculate_perplexity_burstiness(text)
        entropy = self._calculate_entropy(text)

        classifier = self._get_classifier()
        
        suspicious_spans = []
        ai_scores = []

        # Analyze paragraph by paragraph
        for para in paragraphs:
            p_text = para["text"]
            if len(p_text.split()) < 15:
                continue

            p_score = 0.0
            
            # Neural Model Score
            if classifier and classifier is not False:
                # Truncate text to avoid model length limits
                trunc_text = p_text[:2000]
                try:
                    result = classifier(trunc_text)[0]
                    # roberta-base-openai-detector labels: "Fake" (AI) and "Real" (Human)
                    if result["label"] == "Fake" or result["label"] == "LABEL_1":
                        p_score = result["score"] * 100
                    else:
                        p_score = (1.0 - result["score"]) * 100
                except Exception:
                    pass

            # Add stylistic heuristics weighting
            p_perp, p_burst = self._calculate_perplexity_burstiness(p_text)
            
            # If AI is highly uniform (low burstiness) and low perplexity, boost AI score
            if p_burst < 3.0:
                p_score += 10.0
            if p_perp < 40.0:
                p_score += 15.0
                
            p_score = min(max(p_score, 0.0), 100.0)
            ai_scores.append(p_score)

            if p_score > 60.0:
                suspicious_spans.append({
                    "start_char": para["start_char"],
                    "end_char": para["end_char"],
                    "ai_score": p_score,
                })

        if ai_scores:
            overall_probability = sum(ai_scores) / len(ai_scores)
        else:
            overall_probability = 0.0

        # Adjust overall probability based on global entropy and burstiness
        if burstiness < 4.0:
            overall_probability = min(100.0, overall_probability + 10)
        if entropy < 4.0:  # Low entropy (highly repetitive)
            overall_probability = min(100.0, overall_probability + 15)

        overall_probability = round(overall_probability, 1)

        if overall_probability < 30:
            confidence = "Likely Human"
        elif overall_probability < 60:
            confidence = "Mixed"
        else:
            confidence = "Likely AI-assisted"

        return {
            "ai_probability": overall_probability,
            "confidence_level": confidence,
            "suspicious_spans": suspicious_spans
        }
