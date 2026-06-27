import logging
from typing import List, Dict, Any, Optional

from .transcript_analyzer import TranscriptAnalyzer
from .context_validator import ContextValidator
from .question_generator import QuestionGenerator
from .difficulty_rater import DifficultyRater
from core.schemas.question import QuestionSchema, QuestionOutput

logger = logging.getLogger(__name__)

class TriPlusOnePipeline:
    """
    Main orchestrator for the Tri+1 Video-to-Question pipeline.
    Connects: TranscriptAnalyzer -> ContextValidator -> QuestionGenerator -> DifficultyRater
    """
    
    def __init__(self, use_vlm: bool = True):
        logger.info("Initializing Tri+1 Educational Question Generation Pipeline")
        self.transcript_analyzer = TranscriptAnalyzer()
        self.context_validator = ContextValidator(use_vlm=use_vlm)
        self.question_generator = QuestionGenerator()
        self.difficulty_rater = DifficultyRater()

    def run(self, video_path: str, transcript: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Execute the complete pipeline.
        Returns a list of structured dictionaries matching the required outputs.
        """
        logger.info(f"=== TRI+1 PIPELINE START ===")
        logger.info(f"Processing video: {video_path}")
        
        # Step 1: Analyze Transcript
        candidates = self.transcript_analyzer.find_candidates(transcript)
        logger.info(f"Step 1: Found {len(candidates)} candidate segments")
        
        final_questions = []
        
        for i, segment in enumerate(candidates):
            logger.info(f"--- Processing segment {i+1}/{len(candidates)} ---")
            
            # Step 2: Context Validation
            context = self.context_validator.validate(video_path, segment)
            if not context:
                logger.warning(f"Step 2: Context validation failed for segment at {segment.get('time')}")
                continue
                
            # Step 3: Question Generation
            question_output: Optional[QuestionOutput] = self.question_generator.generate_questions(
                context=context, 
                timestamp=segment.get('time')
            )
            
            if not question_output or not question_output.questions:
                logger.warning(f"Step 3: Question generation failed for segment at {segment.get('time')}")
                continue
                
            # Step 4: Difficulty Rating (Neuro-symbolic adjustment)
            for q in question_output.questions:
                # Get true difficulty rating
                actual_difficulty = self.difficulty_rater.rate_difficulty(q, context)
                # Ensure the Pydantic schema is updated
                q.d = actual_difficulty
                
                # Append to final results in expected format
                final_questions.append({
                    "timestamp": segment.get('time'),
                    "question_data": q.model_dump(),  # Serializes the Pydantic schema
                    "context_metadata": context
                })
                
        logger.info(f"=== TRI+1 PIPELINE END ===")
        logger.info(f"Generated {len(final_questions)} final Q-A pairs")
        return final_questions
