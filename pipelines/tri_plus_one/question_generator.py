import logging
from typing import Dict, Any, Optional

from core.llm.providers import LLMRouter
from core.schemas.question import QuestionOutput, QuestionSchema

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """
    Generates structured Q-A pairs based on the context validated in step 2.
    Uses LLMRouter and strictly enforces the QuestionOutput Pydantic schema.
    """
    
    def __init__(self):
        self.llm = LLMRouter()
        
    def generate_questions(self, context: Dict[str, Any], timestamp: str) -> Optional[QuestionOutput]:
        """
        Generate factual, conceptual, and applied questions for the given context.
        """
        try:
            slide_content = context.get('slide_content', '')
            transcript_text = context.get('transcript_text', '')
            concepts = ", ".join(context.get('educational_concepts', []))
            
            system_prompt = (
                "You are an expert instructional designer. "
                "Generate exactly 3 educational questions (1 factual, 1 conceptual, 1 applied) "
                "based on the provided lecture context.\n"
                "You MUST return the result as a valid JSON object matching this exact schema:\n"
                "{\n"
                "  \"questions\": [\n"
                "    {\"q\": \"Question text\", \"a\": \"Correct answer text\", \"options\": {\"a\": \"Correct answer text\", \"b\": \"Plausible distractor 1\", \"c\": \"Plausible distractor 2\", \"d\": \"Plausible distractor 3\"}, \"d\": \"easy\", \"t\": \"factual\", \"c\": \"Concept name\"}\n"
                "  ]\n"
                "}\n"
                "Do not include any explanations or markdown formatting outside the JSON."
            )
            
            prompt = (
                f"Slide text: {slide_content}\n"
                f"Transcript: {transcript_text}\n"
                f"Identified concepts: {concepts}\n\n"
                f"Output exactly 3 questions in the required JSON format."
            )
            
            json_data = self.llm.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                schema=None
            )
            
            # Map the raw dicts back to QuestionSchema objects
            questions_list = []
            
            def extract_questions(data):
                found = []
                if isinstance(data, list):
                    for item in data:
                        found.extend(extract_questions(item))
                elif isinstance(data, dict):
                    if "q" in data or "question" in data:
                        found.append(data)
                    else:
                        for val in data.values():
                            found.extend(extract_questions(val))
                return found

            raw_items = extract_questions(json_data)
                    
            def to_string(val):
                if not val:
                    return ""
                if isinstance(val, str):
                    return val
                if isinstance(val, list):
                    return " ".join(to_string(v) for v in val if v).strip()
                if isinstance(val, dict):
                    # If it's a dict, try to extract common text fields, or just dump values
                    for k in ["q", "question", "a", "answer", "text", "content", "value"]:
                        if k in val:
                            return to_string(val[k])
                    return " ".join(to_string(v) for v in val.values() if v).strip()
                return str(val)

            for item in raw_items:
                q_raw = item.get("q") or item.get("question") or ""
                a_raw = item.get("a") or item.get("answer") or ""
                options_raw = item.get("options") or item.get("o") or []
                d_raw = item.get("d") or item.get("difficulty") or "medium"
                t_raw = item.get("t") or item.get("type") or "factual"
                c_raw = item.get("c") or item.get("concept") or item.get("context") or ""
                
                q = to_string(q_raw)
                a = to_string(a_raw)
                d = to_string(d_raw)
                t = to_string(t_raw)
                c = to_string(c_raw)
                
                options = {}
                if isinstance(options_raw, dict):
                    options = {str(k).lower(): to_string(v) for k, v in options_raw.items()}
                elif isinstance(options_raw, list):
                    options = {"a": "", "b": "", "c": "", "d": ""}
                    keys = ["a", "b", "c", "d"]
                    for idx, val in enumerate(options_raw):
                        if idx < 4:
                            options[keys[idx]] = to_string(val)

                if q:
                    questions_list.append(QuestionSchema(q=q, a=a, d=d, t=t, c=c, options=options))
                
            validated_output = QuestionOutput(questions=questions_list)
            logger.info(f"Successfully generated {len(validated_output.questions)} questions for timestamp {timestamp}")
            
            return validated_output
            
        except Exception as e:
            logger.error(f"Failed to generate questions for timestamp {timestamp}: {e}")
            return None
