from typing import List, Optional, Union, Dict
from dataclasses import dataclass, field, asdict

@dataclass
class QuestionSchema:
    """
    Schema for the structured JSON output of the Question Generator.
    Fields are named shortly (q, a, d, t, c) as per the specification.
    """
    q: str
    a: str
    d: str
    t: str
    c: Optional[str] = None
    options: Optional[Union[List[str], Dict[str, str]]] = None
    
    def model_dump(self):
        return asdict(self)

@dataclass
class QuestionOutput:
    """
    Output model wrapping a list of questions.
    """
    questions: List[QuestionSchema] = field(default_factory=list)
    
    def model_dump(self):
        return asdict(self)
