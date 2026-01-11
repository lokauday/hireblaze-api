"""
LLM Runner for orchestration: builds messages, calls tools, logs output, returns structured JSON.
"""
import logging
import json
import hashlib
from typing import Optional, Dict, Any, List
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime

from app.llm.provider import LLMProvider, LLMResponse
from app.llm.openai_provider import OpenAIProvider
from app.llm.router import get_model_for_feature
from app.db.models.ai_run import AiRun
from app.db.models.ai_memory import AiMemory
from app.llm.tools.context_tools import (
    get_user_profile,
    get_job,
    list_documents,
    get_document_content,
    get_resume_versions,
    compute_keyword_match,
)

logger = logging.getLogger(__name__)

# Standardized output format
STANDARD_OUTPUT_SCHEMA = {
    "title": str,
    "summary": str,
    "content": str,
    "bullets": list,
    "warnings": list,
    "keywords_added": list,
    "next_actions": list,
}


class LLMRunner:
    """Orchestrates LLM calls with context, tools, and logging."""
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        """Initialize runner with provider."""
        self.provider = provider
        if not self.provider:
            try:
                self.provider = OpenAIProvider()
            except ValueError:
                logger.warning("OpenAI provider not available - LLM features disabled")
                self.provider = None
    
    def _load_prompt_template(self, feature: str, version: str = "v1") -> str:
        """Load prompt template from file."""
        prompt_path = Path(__file__).parent / "prompts" / f"{feature}_{version}.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        logger.warning(f"Prompt template not found: {prompt_path}")
        return f"You are an expert assistant. {feature} analysis requested."
    
    def _build_messages(self, prompt_template: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build messages for LLM from template and context."""
        # Simple template substitution
        prompt = prompt_template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if isinstance(value, dict):
                value = json.dumps(value, indent=2)
            prompt = prompt.replace(placeholder, str(value) if value else "")
        
        return [
            {"role": "system", "content": "You are a helpful AI assistant for job applications."},
            {"role": "user", "content": prompt}
        ]
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with fallback."""
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback: return text as content
        return {
            "title": "AI Response",
            "summary": text[:200] + "..." if len(text) > 200 else text,
            "content": text,
            "bullets": [],
            "warnings": [],
            "keywords_added": [],
            "next_actions": [],
        }
    
    def _compute_input_hash(self, feature: str, context: Dict[str, Any]) -> str:
        """Compute hash of input for deduplication."""
        input_str = f"{feature}:{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(input_str.encode()).hexdigest()
    
    def run(
        self,
        feature: str,
        user_id: int,
        db: Session,
        context: Dict[str, Any],
        job_id: Optional[int] = None,
        prompt_version: str = "v1",
        plan: str = "free",
    ) -> Dict[str, Any]:
        """
        Run LLM analysis with context and tools.
        
        Args:
            feature: Feature name (e.g., "job_match", "recruiter_lens")
            user_id: User ID
            db: Database session
            context: Context dict with input data
            job_id: Optional job ID for context
            prompt_version: Prompt version (default "v1")
            plan: User plan ("free" | "premium")
            
        Returns:
            Standardized response dict
        """
        if not self.provider:
            raise ValueError("LLM provider not available")
        
        # Get model for feature
        model = get_model_for_feature(feature, plan)
        
        # Load prompt template
        prompt_template = self._load_prompt_template(feature, prompt_version)
        
        # Enrich context with tools
        enriched_context = context.copy()
        enriched_context["user_profile"] = get_user_profile(user_id, db)
        if job_id:
            enriched_context["job"] = get_job(job_id, db)
        
        # Build messages
        messages = self._build_messages(prompt_template, enriched_context)
        
        # Create AI run record
        input_hash = self._compute_input_hash(feature, context)
        ai_run = AiRun(
            user_id=user_id,
            feature=feature,
            input_hash=input_hash,
            prompt_version=prompt_version,
            model=model,
            status="pending",
        )
        db.add(ai_run)
        db.commit()
        db.refresh(ai_run)
        
        try:
            # Call LLM
            response = self.provider.chat(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Parse response
            result = self._parse_json_response(response.content)
            
            # Update AI run
            ai_run.status = "completed"
            ai_run.tokens_in = response.tokens_in
            ai_run.tokens_out = response.tokens_out
            ai_run.cost_estimate = response.cost_estimate
            ai_run.completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"LLM run completed: feature={feature}, user_id={user_id}, tokens={response.tokens_in + response.tokens_out}")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM run failed: {e}", exc_info=True)
            
            # Update AI run with error
            ai_run.status = "failed"
            ai_run.error_message = str(e)
            ai_run.completed_at = datetime.utcnow()
            db.commit()
            
            raise
