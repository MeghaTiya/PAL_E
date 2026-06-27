import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

class TranscriptAnalyzer:
    """
    Analyzes transcript to find segments suitable for question generation based on linguistic cues.
    Isolated step 1 of the tri_plus_one pipeline.
    """
    
    def __init__(self):
        self.definition_keywords = [
            "is defined as", "means that", "refers to", "is called",
            "definition of", "term for", "describes"
        ]
        self.emphasis_keywords = [
            "important", "note that", "remember", "key point",
            "significant", "crucial", "essential", "critical"
        ]
        self.example_keywords = [
            "for example", "for instance", "such as", "like",
            "consider", "imagine", "suppose"
        ]
        self.transition_keywords = [
            "now let's", "next we", "moving on", "another",
            "furthermore", "additionally", "moreover"
        ]
    
    def _timestamp_to_seconds(self, timestamp: str) -> int:
        try:
            parts = timestamp.split(':')
            parts = [int(float(p)) for p in parts]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:
                return parts[0] * 60 + parts[1]
            return 0
        except Exception:
            return 0

    def _seconds_to_timestamp(self, seconds: int) -> str:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def find_candidates(self, transcript: List[Dict[str, str]], interval_seconds: int = 90) -> List[Dict[str, str]]:
        """
        Find candidate segments at fixed intervals (e.g., 90 seconds).
        Accumulates all spoken text within the window.
        """
        candidates = []
        current_interval = 1
        accumulated_text = ""
        
        for segment in transcript:
            seconds = self._timestamp_to_seconds(segment.get("time", "00:00"))
            
            while seconds >= current_interval * interval_seconds:
                target_seconds = current_interval * interval_seconds
                if accumulated_text.strip():
                    score = self._calculate_segment_score(accumulated_text)
                    candidates.append({
                        "time": self._seconds_to_timestamp(target_seconds),
                        "text": accumulated_text.strip(),
                        "score": score
                    })
                accumulated_text = ""
                current_interval += 1
                
            accumulated_text += " " + segment.get("text", "")
            
        if len(accumulated_text.strip()) > 50:
            score = self._calculate_segment_score(accumulated_text)
            candidates.append({
                "time": self._seconds_to_timestamp(current_interval * interval_seconds),
                "text": accumulated_text.strip(),
                "score": score
            })

        logger.info(f"Selected {len(candidates)} fixed-interval candidates from {len(transcript)} segments")
        return candidates
    
    def _calculate_segment_score(self, text: str) -> int:
        score = 0
        
        for keyword in self.definition_keywords:
            if keyword in text:
                score += 3
                
        for keyword in self.emphasis_keywords:
            if keyword in text:
                score += 2
                
        for keyword in self.example_keywords:
            if keyword in text:
                score += 2
                
        for keyword in self.transition_keywords:
            if keyword in text:
                score += 1
                
        question_words = ["what", "why", "how", "when", "where", "who"]
        for word in question_words:
            if f" {word} " in text:
                score += 1
                
        if len(text) > 100: score += 1
        if len(text) > 200: score += 1
        
        technical_patterns = [
            r'\b[A-Z][a-z]*[A-Z][a-z]*\b',
            r'\b\w+ly\b',
            r'\b\d+\.\d+\b',
        ]
        for pattern in technical_patterns:
            if re.search(pattern, text):
                score += 1
                
        return score
