import math
import logging
from typing import Dict, Any

from .state import LearnerState

logger = logging.getLogger(__name__)

class IRTPriors:
    """
    Symbolic Engine: Calculates 2PL IRT (Item Response Theory) statistical priors.
    Separates the statistical calculation from the deep learning RL head.
    """
    
    def __init__(self):
        # Default difficulty (b) and discrimination (a) parameters for each level
        self.item_params = {
            "easy": {"a": 1.0, "b": 30.0},
            "medium": {"a": 1.2, "b": 50.0},
            "hard": {"a": 1.5, "b": 75.0}
        }
        
    def calculate_success_probability(self, learner_skill: float, difficulty: str) -> float:
        """
        Calculates the probability of a correct response using the 2PL IRT model.
        
        Formula: P(theta) = 1 / (1 + exp(-a * (theta - b)))
        Where:
        - theta: learner's skill
        - a: item discrimination
        - b: item difficulty
        """
        params = self.item_params.get(difficulty, self.item_params["medium"])
        a = params["a"]
        b = params["b"]
        
        # Scaling skill to avoid overflow, assuming skill is 0-100
        try:
            # Scale down the difference to make exponentiation stable
            logit = -a * ((learner_skill - b) / 10.0)
            prob = 1.0 / (1.0 + math.exp(logit))
            return prob
        except OverflowError:
            return 0.0 if logit > 0 else 1.0

    def recommend_difficulty(self, state: LearnerState) -> str:
        """
        Recommends a difficulty level based strictly on IRT targeting.
        Targets a difficulty where the success probability is around 0.5 - 0.7 for optimal learning.
        """
        skill = state.skill_score
        
        probs = {
            diff: self.calculate_success_probability(skill, diff)
            for diff in ["easy", "medium", "hard"]
        }
        
        # Find the difficulty where probability is closest to the ideal learning zone (0.6)
        target_prob = 0.6
        best_diff = "medium"
        min_diff_gap = float('inf')
        
        for diff, prob in probs.items():
            gap = abs(prob - target_prob)
            if gap < min_diff_gap:
                min_diff_gap = gap
                best_diff = diff
                
        logger.debug(f"IRT Recommendation: {best_diff} (Skill: {skill:.1f}, Probs: {probs})")
        return best_diff
