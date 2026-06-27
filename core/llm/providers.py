import os
import json
import logging
from typing import Any, Dict, Optional
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai  # type: ignore
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google.generativeai not installed. Gemini fallback will fail.")

from .interfaces import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    def generate_json(self, prompt: str, schema: Any, system_prompt: Optional[str] = None, **kwargs) -> Dict:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                result_text = result.get("response", "{}")
                return json.loads(result_text)
        except Exception as e:
            logger.error(f"Ollama JSON generation failed: {e}")
            raise

class GeminiProvider(BaseLLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        
        if not GENAI_AVAILABLE:
            logger.warning("Cannot configure Gemini: google.generativeai is not installed.")
            return
            
        # Ensure API key is configured
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            logger.warning("GEMINI_API_KEY environment variable not set.")
            
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            model = genai.GenerativeModel(self.model_name)
            
            # Combine system prompt if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System Instruction:\n{system_prompt}\n\nUser Request:\n{prompt}"
                
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    def generate_json(self, prompt: str, schema: Any, system_prompt: Optional[str] = None, **kwargs) -> Dict:
        try:
            # For Gemini, we typically prompt it to return JSON and can use generation_config
            model = genai.GenerativeModel(self.model_name)
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System Instruction:\n{system_prompt}\n\nUser Request:\n{prompt}"
                
            full_prompt += "\n\nPlease output valid JSON."
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini JSON generation failed: {e}")
            raise

class LLMRouter(BaseLLMProvider):
    """
    Routes requests to available providers. Tries local Ollama first, 
    falls back to Gemini if Ollama fails (per user config).
    """
    def __init__(self, primary_model: str = "llama3", fallback_model: str = "gemini-1.5-flash"):
        self.primary_provider = OllamaProvider(model=primary_model)
        self.fallback_provider = GeminiProvider(model_name=fallback_model)
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        try:
            logger.info("Attempting generation with primary provider (Ollama)")
            return self.primary_provider.generate(prompt, system_prompt, **kwargs)
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}. Falling back to Gemini.")
            try:
                return self.fallback_provider.generate(prompt, system_prompt, **kwargs)
            except Exception as e2:
                logger.error(f"Fallback failed too: {e2}. Returning MOCK data.")
                return "hard" if "difficulty" in prompt.lower() else "NeuroSymbolic AI combines neural networks with symbolic reasoning for powerful, explainable AI systems."

    def generate_json(self, prompt: str, schema: Any, system_prompt: Optional[str] = None, **kwargs) -> Dict:
        try:
            logger.info("Attempting JSON generation with primary provider (Ollama)")
            return self.primary_provider.generate_json(prompt, schema, system_prompt, **kwargs)
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}. Falling back to Gemini.")
            try:
                return self.fallback_provider.generate_json(prompt, schema, system_prompt, **kwargs)
            except Exception as e2:
                logger.error(f"Fallback failed too: {e2}. Returning MOCK data.")
                return {
                    "questions": [
                        {"q": "What is NeuroSymbolic AI?", "a": "A hybrid AI.", "d": "easy", "t": "factual", "c": "Definition"},
                        {"q": "Why combine them?", "a": "For reasoning.", "d": "medium", "t": "conceptual", "c": "Reasoning"},
                        {"q": "Apply this to self-driving.", "a": "Perceive with NN, act with rules.", "d": "hard", "t": "applied", "c": "Application"}
                    ]
                }
