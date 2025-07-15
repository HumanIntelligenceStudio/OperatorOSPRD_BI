"""
Multi-LLM Provider System for OperatorOS
Unified interface for OpenAI, Anthropic, and Gemini APIs with automatic failover
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass

# API clients
import openai
from openai import OpenAI
import anthropic
from anthropic import Anthropic
from google import genai
from google.genai import types

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"

@dataclass
class LLMResponse:
    content: str
    provider: LLMProvider
    model: str
    usage: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class MultiLLMProvider:
    """
    Unified multi-LLM provider with intelligent model selection
    Automatically chooses the best LLM for each task based on strengths and requirements
    Follows OperatorOS production memory guidelines: precision, clarity, no flattery
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize clients
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_client = None
        
        # Provider availability
        self.available_providers = []
        
        self._initialize_providers()
        
        # Default model mappings following blueprint guidelines
        self.model_mappings = {
            LLMProvider.OPENAI: "gpt-4o",  # Latest model per blueprint
            LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",  # Latest model per blueprint
            LLMProvider.GEMINI: "gemini-2.5-flash"  # Latest model per blueprint
        }
        
        # Provider strengths for intelligent selection
        self.provider_strengths = {
            LLMProvider.OPENAI: {
                "coding": 0.95,
                "analysis": 0.90,
                "creative": 0.85,
                "reasoning": 0.90,
                "business": 0.88,
                "technical": 0.92,
                "financial": 0.87,
                "research": 0.85,
                "concise": 0.88,
                "speed": 0.90
            },
            LLMProvider.ANTHROPIC: {
                "coding": 0.88,
                "analysis": 0.95,
                "creative": 0.90,
                "reasoning": 0.95,
                "business": 0.92,
                "technical": 0.89,
                "financial": 0.91,
                "research": 0.93,
                "concise": 0.95,
                "speed": 0.85
            },
            LLMProvider.GEMINI: {
                "coding": 0.82,
                "analysis": 0.85,
                "creative": 0.88,
                "reasoning": 0.83,
                "business": 0.80,
                "technical": 0.85,
                "financial": 0.78,
                "research": 0.90,
                "concise": 0.80,
                "speed": 0.95
            }
        }
        
        # Task patterns for intelligent selection
        self.task_patterns = {
            "financial": ["money", "budget", "finance", "investment", "revenue", "cost", "profit", "cfo", "accounting"],
            "technical": ["code", "programming", "algorithm", "technical", "cto", "system", "architecture", "api"],
            "business": ["strategy", "market", "business", "cmo", "marketing", "operations", "coo", "growth"],
            "analysis": ["analyze", "analysis", "research", "data", "evaluate", "assess", "review", "compare"],
            "creative": ["creative", "design", "brainstorm", "innovative", "ideate", "generate", "concept"],
            "reasoning": ["why", "how", "explain", "reason", "logic", "understand", "clarify", "because"],
            "research": ["research", "find", "investigate", "explore", "study", "examine", "discover"],
            "concise": ["brief", "short", "quick", "summary", "concise", "bullet", "list"]
        }
    
    def _initialize_providers(self):
        """Initialize available LLM providers based on API keys"""
        
        # OpenAI initialization
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                self.available_providers.append(LLMProvider.OPENAI)
                self.logger.info("OpenAI provider initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI: {e}")
        
        # Anthropic initialization
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                self.anthropic_client = Anthropic(api_key=anthropic_key)
                self.available_providers.append(LLMProvider.ANTHROPIC)
                self.logger.info("Anthropic provider initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Anthropic: {e}")
        
        # Gemini initialization
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if gemini_key:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
                self.available_providers.append(LLMProvider.GEMINI)
                self.logger.info("Gemini provider initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Gemini: {e}")
        
        self.logger.info(f"Initialized {len(self.available_providers)} LLM providers: {[p.value for p in self.available_providers]}")
    
    def select_optimal_provider(
        self, 
        messages: List[Dict[str, str]], 
        agent_type: Optional[str] = None
    ) -> LLMProvider:
        """
        Intelligently select the best provider based on message content and agent type
        
        Args:
            messages: Conversation messages to analyze
            agent_type: Type of agent requesting (e.g., 'CFO', 'CTO', 'researcher')
            
        Returns:
            Optimal LLMProvider for the task
        """
        if not self.available_providers:
            return None
        
        # Combine all message content for analysis
        full_content = " ".join([msg.get("content", "") for msg in messages]).lower()
        
        # Calculate task scores based on content patterns
        task_scores = {}
        for task_type, patterns in self.task_patterns.items():
            score = sum(1 for pattern in patterns if pattern in full_content)
            if score > 0:
                task_scores[task_type] = score / len(patterns)  # Normalize
        
        # Add agent-specific scoring
        if agent_type:
            agent_lower = agent_type.lower()
            if "cfo" in agent_lower or "financial" in agent_lower:
                task_scores["financial"] = task_scores.get("financial", 0) + 0.5
            elif "cto" in agent_lower or "technical" in agent_lower:
                task_scores["technical"] = task_scores.get("technical", 0) + 0.5
            elif "cmo" in agent_lower or "marketing" in agent_lower:
                task_scores["business"] = task_scores.get("business", 0) + 0.5
            elif "analyst" in agent_lower or "researcher" in agent_lower:
                task_scores["analysis"] = task_scores.get("analysis", 0) + 0.5
                task_scores["research"] = task_scores.get("research", 0) + 0.5
        
        # If no specific patterns detected, default to analysis/reasoning
        if not task_scores:
            task_scores = {"analysis": 0.5, "reasoning": 0.5}
        
        # Calculate provider fitness scores
        provider_scores = {}
        for provider in self.available_providers:
            total_score = 0
            for task_type, task_weight in task_scores.items():
                provider_strength = self.provider_strengths[provider].get(task_type, 0.5)
                total_score += task_weight * provider_strength
            
            # Add availability bonus for speed when multiple tasks
            if len(task_scores) > 2:
                speed_bonus = self.provider_strengths[provider]["speed"] * 0.1
                total_score += speed_bonus
            
            provider_scores[provider] = total_score
        
        # Select provider with highest fitness score
        optimal_provider = max(provider_scores.items(), key=lambda x: x[1])[0]
        
        self.logger.info(f"Intelligent selection: {optimal_provider.value} (score: {provider_scores[optimal_provider]:.3f}) for tasks: {list(task_scores.keys())}")
        
        return optimal_provider

    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        provider: Optional[LLMProvider] = None,
        agent_type: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> LLMResponse:
        """
        Generate response using intelligent provider selection or specified provider
        
        Args:
            messages: Conversation messages in OpenAI format
            provider: Specific provider to use (None for intelligent selection)
            agent_type: Type of agent requesting (for intelligent selection)
            max_tokens: Maximum tokens to generate
            temperature: Temperature for response generation
            
        Returns:
            LLMResponse with content and metadata
        """
        
        if not self.available_providers:
            return LLMResponse(
                content="No LLM providers available. Please check API keys.",
                provider=LLMProvider.OPENAI,
                model="none",
                usage={},
                success=False,
                error="No providers initialized"
            )
        
        # Intelligent provider selection or fallback
        if provider and provider in self.available_providers:
            target_provider = provider
        else:
            target_provider = self.select_optimal_provider(messages, agent_type)
            if not target_provider:
                target_provider = self.available_providers[0]
        
        try:
            if target_provider == LLMProvider.OPENAI:
                return self._generate_openai_response(messages, max_tokens, temperature)
            elif target_provider == LLMProvider.ANTHROPIC:
                return self._generate_anthropic_response(messages, max_tokens, temperature)
            elif target_provider == LLMProvider.GEMINI:
                return self._generate_gemini_response(messages, max_tokens, temperature)
        except Exception as e:
            self.logger.error(f"Primary provider {target_provider.value} failed: {e}")
            
            # Attempt failover to next available provider
            return self._attempt_failover(messages, target_provider, max_tokens, temperature)
    
    def _generate_openai_response(self, messages: List[Dict], max_tokens: int, temperature: float) -> LLMResponse:
        """Generate response using OpenAI API"""
        model = self.model_mappings[LLMProvider.OPENAI]
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=LLMProvider.OPENAI,
            model=model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            success=True
        )
    
    def _generate_anthropic_response(self, messages: List[Dict], max_tokens: int, temperature: float) -> LLMResponse:
        """Generate response using Anthropic API"""
        model = self.model_mappings[LLMProvider.ANTHROPIC]
        
        # Convert OpenAI format to Anthropic format
        system_message = ""
        claude_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append(msg)
        
        response = self.anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_message,
            messages=claude_messages
        )
        
        return LLMResponse(
            content=response.content[0].text,
            provider=LLMProvider.ANTHROPIC,
            model=model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            success=True
        )
    
    def _generate_gemini_response(self, messages: List[Dict], max_tokens: int, temperature: float) -> LLMResponse:
        """Generate response using Gemini API"""
        model = self.model_mappings[LLMProvider.GEMINI]
        
        # Convert messages to Gemini format
        system_prompt = ""
        user_content = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg["role"] == "user":
                user_content += msg["content"] + "\n"
            elif msg["role"] == "assistant":
                user_content += f"Previous response: {msg['content']}\n"
        
        # Combine system prompt with user content
        full_prompt = f"{system_prompt}\n\n{user_content}".strip()
        
        response = self.gemini_client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        
        return LLMResponse(
            content=response.text or "No response generated",
            provider=LLMProvider.GEMINI,
            model=model,
            usage={
                "prompt_tokens": 0,  # Gemini doesn't provide detailed token counts
                "completion_tokens": 0,
                "total_tokens": 0
            },
            success=True
        )
    
    def _attempt_failover(self, messages: List[Dict], failed_provider: LLMProvider, max_tokens: int, temperature: float) -> LLMResponse:
        """Attempt failover to alternative providers"""
        
        remaining_providers = [p for p in self.available_providers if p != failed_provider]
        
        for provider in remaining_providers:
            try:
                self.logger.info(f"Attempting failover to {provider.value}")
                return self.generate_response(messages, provider, max_tokens, temperature)
            except Exception as e:
                self.logger.error(f"Failover to {provider.value} failed: {e}")
                continue
        
        # All providers failed
        return LLMResponse(
            content="All LLM providers failed. Please check your API keys and try again.",
            provider=failed_provider,
            model="failed",
            usage={},
            success=False,
            error="All providers failed"
        )
    
    def test_all_providers(self) -> Dict[str, LLMResponse]:
        """Test all available providers with a simple prompt"""
        
        test_messages = [
            {
                "role": "system", 
                "content": "You are an OperatorOS agent. Respond with precision and clarity. No flattery."
            },
            {
                "role": "user", 
                "content": "Test response: Confirm your model and provider are working correctly."
            }
        ]
        
        results = {}
        
        for provider in self.available_providers:
            try:
                response = self.generate_response(test_messages, provider, max_tokens=100, temperature=0.3)
                results[provider.value] = response
                self.logger.info(f"Test successful for {provider.value}: {response.success}")
            except Exception as e:
                results[provider.value] = LLMResponse(
                    content=f"Test failed: {str(e)}",
                    provider=provider,
                    model="test_failed",
                    usage={},
                    success=False,
                    error=str(e)
                )
                self.logger.error(f"Test failed for {provider.value}: {e}")
        
        return results
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        return {
            "available_providers": [p.value for p in self.available_providers],
            "total_providers": len(self.available_providers),
            "model_mappings": {p.value: self.model_mappings[p] for p in self.available_providers},
            "initialization_status": {
                "openai": self.openai_client is not None,
                "anthropic": self.anthropic_client is not None,
                "gemini": self.gemini_client is not None
            }
        }

# Global instance for use throughout the application
multi_llm = MultiLLMProvider()