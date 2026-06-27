import os
import sys
import logging
from pprint import pprint

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipelines.tri_plus_one.pipeline import TriPlusOnePipeline
from engine_rl.mixture_logic import HybridMixtureLogic
from engine_rl.state import LearnerState

def main():
    print("="*50)
    print(" PAL SYSTEM DEMO: End-to-End Architecture Run ")
    print("="*50)

    # 1. Setup Mock Data
    video_path = "question_generator/test.mp4" # Ensure this file exists
    mock_transcript = [
        {"time": "00:00:10", "text": "Welcome to the lecture. Today we discuss NeuroSymbolic AI."},
        {"time": "00:01:20", "text": "NeuroSymbolic AI is defined as the integration of neural networks with symbolic reasoning. For example, using deep learning for perception and symbolic logic for reasoning."},
        {"time": "00:02:30", "text": "This is important because it allows models to not only recognize patterns, but also explain their reasoning step-by-step."}
    ]

    print("\n[PHASE 1] Tri+1 Pipeline: Video-to-Question")
    print("-" * 50)
    try:
        # Note: use_vlm=False to speed up demo and rely on OCR/Transcript fallback
        pipeline = TriPlusOnePipeline(use_vlm=False) 
        questions = pipeline.run(video_path, mock_transcript)
        
        print("\nGenerated Questions (Structured):")
        for q in questions:
            print(f"- Time: {q['timestamp']}")
            pprint(q['question_data'])
    except Exception as e:
        print(f"Phase 1 Failed: {e}")

    print("\n[PHASE 2] Hybrid RL Engine: Adaptive Difficulty")
    print("-" * 50)
    try:
        rl_engine = HybridMixtureLogic()
        state = LearnerState(initial_skill=45.0)
        
        recommended_diff = rl_engine.get_next_difficulty(state)
        print(f"Current Learner Skill: {state.skill_score}")
        print(f"Recommended Next Difficulty: {recommended_diff}")
        
        # Simulate user answering the question correctly
        print(f"Simulating user answering a '{recommended_diff}' question correctly...")
        rl_engine.update_feedback(state, recommended_diff, correct=True, new_state=state)
        
        print(f"Updated Learner Skill: {state.skill_score}")
        print(f"New Recommended Difficulty: {rl_engine.get_next_difficulty(state)}")
    except Exception as e:
        print(f"Phase 2 Failed: {e}")


if __name__ == "__main__":
    main()
