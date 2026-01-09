"""Generic LLM client interface."""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from groq import Groq
except ImportError:
    Groq = None


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Generate a response using function/tool calling.
        
        Args:
            prompt: The prompt to send to the model
            tools: List of tool/function definitions
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with 'content' and 'tool_calls' (if any)
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API client implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from OPENAI_API_KEY env var.
            model: Model name to use (default: gpt-4o-mini)
        """
        if OpenAI is None:
            raise ImportError("OpenAI library is not installed. Install it with: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        logger.info(f"OpenAIClient initialized with model: {model}")
    
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000, **kwargs) -> str:
        """
        Generate a response from OpenAI.
        
        Args:
            prompt: The prompt to send to the model
            temperature: Sampling temperature (0-2), lower = more deterministic
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters for the API call
        
        Returns:
            Generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts and structures information from text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")
    
    def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]], temperature: float = 0.3, max_tokens: int = 2000, **kwargs) -> Dict[str, Any]:
        """
        Generate a response using OpenAI function calling.
        
        Args:
            prompt: The prompt to send to the model
            tools: List of tool/function definitions
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with 'content' (str) and 'tool_calls' (list of parsed function calls)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts and structures information from text. Use the provided tools to extract todos."},
                    {"role": "user", "content": prompt}
                ],
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            message = response.choices[0].message
            result = {
                "content": message.content.strip() if message.content else "",
                "tool_calls": []
            }
            
            # Parse tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.type == "function":
                        result["tool_calls"].append({
                            "id": tool_call.id,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        })
            
            logger.info("OpenAI API call completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error calling OpenAI API with tools: {str(e)}", exc_info=True)
            raise Exception(f"Error calling OpenAI API with tools: {str(e)}")


class GroqClient(LLMClient):
    """Groq API client implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-70b-versatile"):
        """
        Initialize Groq client.
        
        Args:
            api_key: Groq API key. If None, will try to get from GROQ_API_KEY env var.
            model: Model name to use (default: llama-3.1-70b-versatile)
                    Other options: llama-3.1-8b-instant, mixtral-8x7b-32768, etc.
        """
        if Groq is None:
            raise ImportError("Groq library is not installed. Install it with: pip install groq")
        
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key is required. Set GROQ_API_KEY environment variable.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = model
        logger.info(f"GroqClient initialized with model: {model}")
    
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000, **kwargs) -> str:
        """
        Generate a response from Groq.
        
        Args:
            prompt: The prompt to send to the model
            temperature: Sampling temperature (0-2), lower = more deterministic
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters for the API call
        
        Returns:
            Generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts and structures information from text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Error calling Groq API: {str(e)}")
    
    def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]], temperature: float = 0.3, max_tokens: int = 2000, **kwargs) -> Dict[str, Any]:
        """
        Generate a response using Groq function calling.
        
        Args:
            prompt: The prompt to send to the model
            tools: List of tool/function definitions
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with 'content' (str) and 'tool_calls' (list of parsed function calls)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts and structures information from text. Use the provided tools to extract todos."},
                    {"role": "user", "content": prompt}
                ],
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            message = response.choices[0].message
            result = {
                "content": message.content.strip() if message.content else "",
                "tool_calls": []
            }
            
            # Parse tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.type == "function":
                        result["tool_calls"].append({
                            "id": tool_call.id,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        })
            
            logger.info("Groq API call completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error calling Groq API with tools: {str(e)}", exc_info=True)
            raise Exception(f"Error calling Groq API with tools: {str(e)}")


# Factory function to create LLM client
def create_llm_client(provider: str = "openai", **kwargs) -> LLMClient:
    """
    Factory function to create an LLM client.
    
    Args:
        provider: LLM provider name ("openai", "groq", etc.)
        **kwargs: Provider-specific arguments (e.g., model, api_key)
    
    Returns:
        LLMClient instance
    
    Examples:
        >>> # OpenAI client
        >>> client = create_llm_client("openai", model="gpt-4o-mini")
        >>> 
        >>> # Groq client
        >>> client = create_llm_client("groq", model="llama-3.1-70b-versatile")
    """
    provider_lower = provider.lower()
    
    if provider_lower == "openai":
        return OpenAIClient(**kwargs)
    elif provider_lower == "groq":
        return GroqClient(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported providers: 'openai', 'groq'")

