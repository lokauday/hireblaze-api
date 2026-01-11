"""
OpenAI provider implementation.
"""
import logging
from typing import Optional, Dict, Any
from collections.abc import Iterator
from openai import OpenAI, APIError

from app.core.config import OPENAI_API_KEY
from app.llm.provider import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

# Model pricing per 1M tokens (input/output)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},  # $0.15/$0.60 per 1M tokens
    "gpt-4o": {"input": 2.50, "output": 10.00},  # $2.50/$10.00 per 1M tokens
    "gpt-4": {"input": 30.00, "output": 60.00},  # $30/$60 per 1M tokens
}


class OpenAIProvider(LLMProvider):
    """OpenAI provider using official OpenAI SDK."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI client."""
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        self.client = OpenAI(api_key=self.api_key)
        logger.info("OpenAI provider initialized")
    
    def chat(
        self,
        messages: list[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a chat completion."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 2000,
                **kwargs
            )
            
            content = response.choices[0].message.content or ""
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens
            cost = self.estimate_cost(tokens_in, tokens_out, model)
            
            return LLMResponse(
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=model,
                cost_estimate=cost,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                }
            )
        except APIError as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"OpenAI error: {e}", exc_info=True)
            raise
    
    def stream(
        self,
        messages: list[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """Stream a chat completion token by token."""
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 2000,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except APIError as e:
            logger.error(f"OpenAI streaming API error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}", exc_info=True)
            raise
    
    def estimate_cost(self, tokens_in: int, tokens_out: int, model: str) -> float:
        """Estimate cost in USD."""
        pricing = MODEL_PRICING.get(model, {"input": 0.15, "output": 0.60})
        cost_input = (tokens_in / 1_000_000) * pricing["input"]
        cost_output = (tokens_out / 1_000_000) * pricing["output"]
        return cost_input + cost_output
