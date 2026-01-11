"""
LLM Provider interface for abstracting LLM implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""
    cost_estimate: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def chat(
        self,
        messages: list[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse with content and metadata
        """
        pass
    
    @abstractmethod
    def stream(
        self,
        messages: list[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream a chat completion token by token.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Token strings as they are generated
        """
        pass
    
    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        """
        Estimate cost for a request.
        
        Args:
            tokens_in: Input tokens
            tokens_out: Output tokens
            model: Model identifier
            
        Returns:
            Estimated cost in USD
        """
        # Default implementation returns 0.0
        # Providers should override with actual pricing
        return 0.0
