import logging
from typing import Dict, Any

from core.llm.providers import LLMRouter
from core.schemas.question import QuestionSchema

logger = logging.getLogger(__name__)

class DifficultyRater:
    """
    Rates the difficulty of generated questions using a Neuro-Symbolic approach.
    Symbolic: Heuristic rule-engine (fast, deterministic).
    Neural: LLM fallback (when heuristics fail or yield low confidence).
    """
    
    def __init__(self):
        self.llm = LLMRouter()
        
    def rate_difficulty(self, question: QuestionSchema, context: Dict[str, Any]) -> str:
        """
        Determine the difficulty level ('easy', 'medium', 'hard') of a question.
        First tries the heuristic engine, falls back to LLM if needed.
        """
        # Try symbolic/heuristic approach first
        difficulty, confidence = self._heuristic_rating(question, context)
        
        if confidence > 0.7:
            logger.debug(f"Heuristic rating succeeded for question '{question.q[:20]}...' with confidence {confidence}")
            return difficulty
            
        # Fallback to neural/LLM approach
        logger.debug(f"Heuristic rating confidence too low ({confidence}). Falling back to LLM.")
        return self._llm_rating(question, context)
        
    def _heuristic_rating(self, question: QuestionSchema, context: Dict[str, Any]) -> tuple[str, float]:
        """
        Rule-based engine for rating difficulty.
        Returns a tuple of (difficulty_level, confidence).
        """
        # Force to string just in case bad data made its way through
        q_text = str(question.q).lower()
        a_text = str(question.a).lower()
        
        # Word counts
        q_len = len(q_text.split())
        a_len = len(a_text.split())
        
        score = 0
        
        # Heuristics based on question type words
        if any(w in q_text for w in ['what', 'who', 'where', 'when', 'define']):
            score -= 1  # Often factual/easy
        if any(w in q_text for w in ['why', 'how', 'explain', 'compare']):
            score += 1  # Often conceptual/medium
        if any(w in q_text for w in ['apply', 'evaluate', 'synthesize', 'scenario']):
            score += 2  # Often applied/hard
            
        # Length heuristics
        if a_len > 30: score += 1
        if q_len > 25: score += 1
        
        # Determine mapping based on heuristic score
        if score <= 0:
            return "easy", 0.8
        elif score == 1 or score == 2:
            return "medium", 0.75
        else:
            return "hard", 0.85

    def _llm_rating(self, question: QuestionSchema, context: Dict[str, Any]) -> str:
        """
        Neural engine for rating difficulty using LLM.
        """
        prompt = (
            f"Question: {question.q}\n"
            f"Answer: {question.a}\n\n"
            f"Evaluate the difficulty of this question on a scale of: easy, medium, hard. "
            f"Return ONLY the word 'easy', 'medium', or 'hard'."
        )
        
        try:
            response = self.llm.generate(prompt=prompt, system_prompt="You are an expert educational assessor.")
            response = response.strip().lower()
            
            if "hard" in response: return "hard"
            if "medium" in response: return "medium"
            return "easy"
        except Exception as e:
            logger.error(f"LLM rating failed: {e}. Defaulting to medium.")
            return "medium"
