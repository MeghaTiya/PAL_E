from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    """
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        Generate text from the given prompt.
        
        Args:
            prompt: The input prompt for the LLM.
            system_prompt: Optional system prompt to guide the model.
            kwargs: Additional parameters for generation (temperature, max_tokens, etc.)
            
        Returns:
            The generated text response.
        """
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, schema: Any, system_prompt: Optional[str] = None, **kwargs) -> Dict:
        """
        Generate JSON output matching a specific schema.
        
        Args:
            prompt: The input prompt for the LLM.
            schema: The expected Pydantic schema or JSON schema dict.
            system_prompt: Optional system prompt to guide the model.
            kwargs: Additional parameters.
            
        Returns:
            A dictionary matching the schema.
        """
        pass
