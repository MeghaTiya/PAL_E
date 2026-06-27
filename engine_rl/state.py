import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LearnerState:
    """
    Isolates learner state tracking from decision logic.
    Tracks skill score, decision count, learning velocity, and confidence.
    """
    def __init__(self, initial_skill: float = 50.0):
        self.skill_score: float = initial_skill
        self.decision_count: int = 0
        self.history = []
        
        # Derived metrics
        self.learning_velocity: float = 0.0
        self.confidence_level: float = 0.5

    def update(self, correct: bool, difficulty: str, response_time: float) -> None:
        """
        Updates the state after an answer is provided.
        """
        self.decision_count += 1
        
        # Simple adjustment logic for skill score based on difficulty and correctness
        adjustment = 0.0
        if difficulty == "easy":
            adjustment = 2.0 if correct else -5.0
        elif difficulty == "medium":
            adjustment = 5.0 if correct else -3.0
        elif difficulty == "hard":
            adjustment = 8.0 if correct else -1.0
            
        # Time penalty for very slow answers
        if response_time > 30.0:
            adjustment -= 1.0
            
        previous_score = self.skill_score
        self.skill_score = max(0.0, min(100.0, self.skill_score + adjustment))
        
        # Update history
        self.history.append({
            "correct": correct,
            "difficulty": difficulty,
            "response_time": response_time,
            "score_change": self.skill_score - previous_score
        })
        
        # Re-calculate derived metrics
        self._recalculate_metrics()
        
    def _recalculate_metrics(self) -> None:
        """
        Calculate learning velocity and system confidence in the user's skill level.
        """
        # Velocity: Average score change over last 5 interactions
        recent = self.history[-5:]
        if recent:
            self.learning_velocity = sum(r["score_change"] for r in recent) / len(recent)
        
        # Confidence: Increases with more data, decreases with erratic performance
        base_confidence = min(0.9, self.decision_count * 0.05)
        # Erratic is high variance in score changes
        if len(recent) > 2:
            avg_change = self.learning_velocity
            variance = sum((r["score_change"] - avg_change)**2 for r in recent) / len(recent)
            penalty = min(0.3, variance * 0.01)
            self.confidence_level = max(0.1, base_confidence - penalty)
        else:
            self.confidence_level = base_confidence

    def get_state_dict(self) -> Dict[str, Any]:
        """Returns the state as a dictionary for external consumption."""
        return {
            "skill_score": self.skill_score,
            "decision_count": self.decision_count,
            "learning_velocity": self.learning_velocity,
            "confidence_level": self.confidence_level
        }
