import logging
import random
from typing import Dict, Any, Tuple

from .state import LearnerState
from .statistics_irt import IRTPriors
from .q_learning_head import QLearningHead

logger = logging.getLogger(__name__)

class HybridMixtureLogic:
    """
    Confidence-scaled mixture logic.
    Blends the symbolic (IRT) and neural (RL) engines cleanly.
    Fully isolated and testable.
    """
    
    def __init__(self, initial_rl_weight: float = 0.3, max_rl_weight: float = 0.8):
        self.irt_engine = IRTPriors()
        self.rl_engine = QLearningHead()
        
        self.initial_rl_weight = initial_rl_weight
        self.max_rl_weight = max_rl_weight
        self.current_rl_weight = initial_rl_weight
        
    def _calculate_weights(self, state: LearnerState) -> Tuple[float, float]:
        """
        Dynamically calculates the blending weights based on system state.
        RL weight increases with decision count and system confidence.
        Returns: (irt_weight, rl_weight)
        """
        if state.decision_count < 10:
            # Cold start: rely purely on statistical IRT
            return 1.0, 0.0
            
        # Gradually increase RL weight based on experience
        rl_weight = min(
            self.max_rl_weight,
            self.initial_rl_weight + (state.decision_count - 10) * 0.02
        )
        
        # Scale by confidence: High confidence allows RL to take over more
        if state.confidence_level > 0.6:
            rl_weight = min(self.max_rl_weight, rl_weight * 1.2)
            
        # Extreme learning velocity also boosts RL
        if abs(state.learning_velocity) > 0.3:
            rl_weight = min(self.max_rl_weight, rl_weight * 1.1)
            
        self.current_rl_weight = rl_weight
        return 1.0 - rl_weight, rl_weight

    def get_next_difficulty(self, state: LearnerState) -> str:
        """
        Main decision function. Blends IRT and RL predictions.
        """
        irt_weight, rl_weight = self._calculate_weights(state)
        
        irt_pred = self.irt_engine.recommend_difficulty(state)
        rl_pred = self.rl_engine.recommend_difficulty(state)
        
        # If they agree, return it immediately
        if irt_pred == rl_pred:
            final_pred = irt_pred
        else:
            # Stochastic blending based on weights
            if random.random() < irt_weight:
                final_pred = irt_pred
            else:
                final_pred = rl_pred
                
        logger.info(
            f"Mixture Logic: IRT={irt_pred} ({irt_weight*100:.1f}%), "
            f"RL={rl_pred} ({rl_weight*100:.1f}%) -> Final: {final_pred}"
        )
        return final_pred

    def update_feedback(self, old_state: LearnerState, action: str, correct: bool, new_state: LearnerState) -> None:
        """
        Calculates reward and updates the RL head.
        """
        # Simple reward formulation: 
        # Correct answer -> positive reward.
        # However, too many correct on 'easy' should have diminishing returns compared to 'hard'.
        reward = 0.0
        if correct:
            reward = 1.0 if action == "easy" else (2.0 if action == "medium" else 3.0)
        else:
            reward = -1.0 if action == "hard" else (-2.0 if action == "medium" else -3.0)
            
        self.rl_engine.update(old_state, action, reward, new_state)
