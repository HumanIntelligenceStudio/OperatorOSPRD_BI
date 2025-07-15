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
    Unified multi-LLM provider with automatic failover and load balancing
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
    
    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        provider: Optional[LLMProvider] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> LLMResponse:
        """
        Generate response using specified provider or automatic failover
        
        Args:
            messages: Conversation messages in OpenAI format
            provider: Specific provider to use (None for automatic selection)
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
        
        # Select provider
        target_provider = provider if provider in self.available_providers else self.available_providers[0]
        
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