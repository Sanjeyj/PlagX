import sys
import logging
logging.basicConfig(level=logging.INFO)

try:
    from app.engine.ai_detector import AIDetector
    
    print("Initializing AIDetector...")
    detector = AIDetector()
    
    print("Running analysis...")
    text = "This is a test document. It contains some words. I am extending the length of this string so that it goes well above fifty characters and triggers the actual AI detection logic rather than just returning immediately. This should be long enough."
    para = [{"text": text, "start_char": 0, "end_char": len(text)}]
    
    result = detector.analyze(text, para)
    print("Result:", result)
    print("Success!")
except Exception as e:
    print(f"CRASH: {e}")
    sys.exit(1)
