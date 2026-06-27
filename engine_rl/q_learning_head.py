import json
import os
import random
import logging
from typing import Dict, Any

from .state import LearnerState

logger = logging.getLogger(__name__)

class QLearningHead:
    """
    Neural/RL Engine: Deep Learning / Tabular Q-learning head.
    Learns optimal difficulty selection policy based on learner feedback.
    """
    
    def __init__(self, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.2):
        self.alpha = alpha      # Learning rate
        self.gamma = gamma      # Discount factor
        self.epsilon = epsilon  # Exploration rate
        self.actions = ["easy", "medium", "hard"]
        
        # State space discretization (simplistic for tabular approach)
        # e.g., Skill ranges: 0-33, 34-66, 67-100
        self.q_table: Dict[str, Dict[str, float]] = {}
        
    def _discretize_state(self, state: LearnerState) -> str:
        """
        Converts the continuous LearnerState into a discrete string representation for the Q-table.
        """
        skill = state.skill_score
        if skill < 33.3:
            skill_bin = "low"
        elif skill < 66.6:
            skill_bin = "med"
        else:
            skill_bin = "high"
            
        vel = "pos" if state.learning_velocity > 0 else "neg"
        
        return f"{skill_bin}_{vel}"
        
    def _get_q_values(self, state_key: str) -> Dict[str, float]:
        if state_key not in self.q_table:
            self.q_table[state_key] = {a: 0.0 for a in self.actions}
        return self.q_table[state_key]
        
    def recommend_difficulty(self, state: LearnerState) -> str:
        """
        Selects an action using epsilon-greedy policy based on Q-values.
        """
        state_key = self._discretize_state(state)
        q_values = self._get_q_values(state_key)
        
        # Exploration
        if random.random() < self.epsilon:
            action = random.choice(self.actions)
            logger.debug(f"RL Exploration: selected {action}")
            return action
            
        # Exploitation
        max_q = max(q_values.values())
        best_actions = [a for a, q in q_values.items() if q == max_q]
        action = random.choice(best_actions)
        
        logger.debug(f"RL Exploitation: selected {action} for state {state_key} (Q-values: {q_values})")
        return action
        
    def update(self, old_state: LearnerState, action: str, reward: float, new_state: LearnerState) -> None:
        """
        Updates the Q-table based on the observed reward and transition.
        """
        old_state_key = self._discretize_state(old_state)
        new_state_key = self._discretize_state(new_state)
        
        old_q = self._get_q_values(old_state_key)[action]
        max_next_q = max(self._get_q_values(new_state_key).values())
        
        # Q-learning formula
        new_q = old_q + self.alpha * (reward + self.gamma * max_next_q - old_q)
        self.q_table[old_state_key][action] = new_q
        
        logger.debug(f"RL Update: Q({old_state_key}, {action}) updated to {new_q:.3f} (Reward: {reward:.2f})")
