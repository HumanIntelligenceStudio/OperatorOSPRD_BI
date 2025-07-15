"""
Intelligent Agent Router for OperatorOS
Routes agent requests to optimal LLM providers based on agent type and task requirements
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
import logging
from multi_llm_provider import multi_llm, LLMProvider

class AgentType(Enum):
    CSA = "CSA"  # Chief Strategic Advisor
    CFO = "CFO"  # Chief Financial Officer
    COO = "COO"  # Chief Operating Officer
    CTO = "CTO"  # Chief Technology Officer
    CMO = "CMO"  # Chief Marketing Officer
    CPO = "CPO"  # Chief Product Officer
    CIO = "CIO"  # Chief Information Officer
    ANALYST = "Analyst"
    RESEARCHER = "Researcher"
    WRITER = "Writer"
    REFINER = "Refiner"
    GENERAL = "General"

@dataclass
class AgentRequest:
    agent_type: AgentType
    messages: List[Dict[str, str]]
    user_input: str
    context: Dict[str, Any]
    priority: str = "normal"  # high, normal, low
    require_precision: bool = True

class IntelligentAgentRouter:
    """
    Routes OperatorOS agent requests to optimal LLM providers
    Follows production memory guidelines while maximizing response quality
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Agent-specific LLM preferences based on strengths
        self.agent_preferences = {
            AgentType.CFO: {
                "primary": LLMProvider.ANTHROPIC,  # Best for financial analysis
                "secondary": LLMProvider.OPENAI,
                "strengths": ["financial", "analysis", "reasoning", "concise"]
            },
            AgentType.CTO: {
                "primary": LLMProvider.OPENAI,  # Best for technical tasks
                "secondary": LLMProvider.ANTHROPIC,
                "strengths": ["technical", "coding", "reasoning", "analysis"]
            },
            AgentType.CMO: {
                "primary": LLMProvider.ANTHROPIC,  # Best for business strategy
                "secondary": LLMProvider.OPENAI,
                "strengths": ["business", "creative", "analysis", "reasoning"]
            },
            AgentType.COO: {
                "primary": LLMProvider.ANTHROPIC,  # Best for operations analysis
                "secondary": LLMProvider.OPENAI,
                "strengths": ["business", "analysis", "reasoning", "concise"]
            },
            AgentType.CSA: {
                "primary": LLMProvider.ANTHROPIC,  # Best for strategic thinking
                "secondary": LLMProvider.OPENAI,
                "strengths": ["reasoning", "analysis", "business", "concise"]
            },
            AgentType.CPO: {
                "primary": LLMProvider.OPENAI,  # Best for product development
                "secondary": LLMProvider.ANTHROPIC,
                "strengths": ["creative", "technical", "business", "analysis"]
            },
            AgentType.CIO: {
                "primary": LLMProvider.OPENAI,  # Best for information systems
                "secondary": LLMProvider.ANTHROPIC,
                "strengths": ["technical", "analysis", "business", "reasoning"]
            },
            AgentType.ANALYST: {
                "primary": LLMProvider.ANTHROPIC,  # Best for deep analysis
                "secondary": LLMProvider.OPENAI,
                "strengths": ["analysis", "reasoning", "research", "concise"]
            },
            AgentType.RESEARCHER: {
                "primary": LLMProvider.GEMINI,  # Best for research tasks
                "secondary": LLMProvider.ANTHROPIC,
                "strengths": ["research", "analysis", "speed", "reasoning"]
            },
            AgentType.WRITER: {
                "primary": LLMProvider.ANTHROPIC,  # Best for precise writing
                "secondary": LLMProvider.OPENAI,
                "strengths": ["creative", "concise", "reasoning", "analysis"]
            },
            AgentType.REFINER: {
                "primary": LLMProvider.ANTHROPIC,  # Best for refinement
                "secondary": LLMProvider.OPENAI,
                "strengths": ["reasoning", "concise", "analysis", "creative"]
            },
            AgentType.GENERAL: {
                "primary": LLMProvider.OPENAI,  # Good all-around
                "secondary": LLMProvider.ANTHROPIC,
                "strengths": ["reasoning", "analysis", "speed", "business"]
            }
        }
    
    def route_agent_request(self, request: AgentRequest) -> Dict[str, Any]:
        """
        Route agent request to optimal LLM provider
        
        Args:
            request: AgentRequest with agent type, messages, and context
            
        Returns:
            Dict with response, provider used, and metadata
        """
        
        # Get agent preferences
        preferences = self.agent_preferences.get(request.agent_type, self.agent_preferences[AgentType.GENERAL])
        
        # Enhance messages with OperatorOS production memory guidelines
        enhanced_messages = self._enhance_messages_with_guidelines(request.messages, request.agent_type)
        
        # Determine optimal provider
        optimal_provider = self._select_provider_for_agent(request, preferences)
        
        # Set parameters based on agent type and priority
        max_tokens, temperature = self._get_agent_parameters(request.agent_type, request.priority)
        
        try:
            # Generate response using intelligent selection
            response = multi_llm.generate_response(
                messages=enhanced_messages,
                provider=optimal_provider,
                agent_type=request.agent_type.value,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Log routing decision
            self.logger.info(f"Routed {request.agent_type.value} to {response.provider.value} (success: {response.success})")
            
            return {
                "success": response.success,
                "content": response.content,
                "provider_used": response.provider.value,
                "model_used": response.model,
                "agent_type": request.agent_type.value,
                "routing_reason": f"Optimal for {request.agent_type.value} strengths: {preferences['strengths']}",
                "usage": response.usage,
                "error": response.error
            }
            
        except Exception as e:
            self.logger.error(f"Error routing {request.agent_type.value} request: {str(e)}")
            return {
                "success": False,
                "content": f"Agent routing failed: {str(e)}",
                "provider_used": "none",
                "model_used": "none",
                "agent_type": request.agent_type.value,
                "routing_reason": "Error occurred",
                "usage": {},
                "error": str(e)
            }
    
    def _enhance_messages_with_guidelines(self, messages: List[Dict], agent_type: AgentType) -> List[Dict]:
        """Enhance messages with OperatorOS production memory guidelines"""
        
        # Base production memory guidelines
        base_guidelines = """You are an OperatorOS agent following production memory guidelines:
- No flattery, no soothing, no inflation
- Respond with precision and clarity
- Challenge with precision, not friction
- Mirror, don't mentor
- Dignity structured, labor remembered, clarity delivered"""
        
        # Agent-specific enhancements
        agent_enhancements = {
            AgentType.CFO: "Focus on financial precision, data-driven insights, and clear monetary impact.",
            AgentType.CTO: "Provide technical accuracy, system thinking, and implementation clarity.",
            AgentType.CMO: "Deliver strategic market insights with measurable business impact.",
            AgentType.COO: "Focus on operational efficiency, process optimization, and execution clarity.",
            AgentType.CSA: "Provide strategic oversight with long-term perspective and decision frameworks.",
            AgentType.CPO: "Balance user needs with technical feasibility and business objectives.",
            AgentType.CIO: "Focus on information systems, data management, and technology alignment.",
            AgentType.ANALYST: "Provide deep analysis with supporting evidence and clear conclusions.",
            AgentType.RESEARCHER: "Deliver comprehensive research with verified sources and insights.",
            AgentType.WRITER: "Create precise, clear content that serves the user's specific needs.",
            AgentType.REFINER: "Improve clarity, remove unnecessary elements, enhance precision."
        }
        
        enhancement = agent_enhancements.get(agent_type, "Provide clear, actionable guidance.")
        full_guidelines = f"{base_guidelines}\n\nAgent Role: {enhancement}"
        
        enhanced_messages = []
        for i, message in enumerate(messages):
            if i == 0 and message.get("role") == "system":
                # Enhance existing system message
                enhanced_content = f"{full_guidelines}\n\n{message['content']}"
                enhanced_messages.append({"role": "system", "content": enhanced_content})
            elif i == 0:
                # Add system message if none exists
                enhanced_messages.append({"role": "system", "content": full_guidelines})
                enhanced_messages.append(message)
            else:
                enhanced_messages.append(message)
        
        return enhanced_messages
    
    def _select_provider_for_agent(self, request: AgentRequest, preferences: Dict) -> Optional[LLMProvider]:
        """Select optimal provider based on agent preferences and availability"""
        
        # Check if primary provider is available
        primary = preferences["primary"]
        if primary in multi_llm.available_providers:
            return primary
        
        # Fall back to secondary
        secondary = preferences["secondary"]
        if secondary in multi_llm.available_providers:
            self.logger.info(f"Primary provider {primary.value} unavailable, using secondary {secondary.value}")
            return secondary
        
        # Use intelligent selection as final fallback
        return multi_llm.select_optimal_provider(request.messages, request.agent_type.value)
    
    def _get_agent_parameters(self, agent_type: AgentType, priority: str) -> tuple:
        """Get max_tokens and temperature based on agent type and priority"""
        
        # Base parameters by agent type
        agent_params = {
            AgentType.CFO: (800, 0.3),      # Precise, conservative
            AgentType.CTO: (1000, 0.4),     # Technical detail
            AgentType.CMO: (900, 0.6),      # Creative but strategic
            AgentType.COO: (800, 0.4),      # Operational clarity
            AgentType.CSA: (1200, 0.5),     # Strategic depth
            AgentType.CPO: (900, 0.5),      # Balanced approach
            AgentType.CIO: (800, 0.4),      # Information focused
            AgentType.ANALYST: (1000, 0.3), # Detailed analysis
            AgentType.RESEARCHER: (1200, 0.4), # Comprehensive research
            AgentType.WRITER: (1000, 0.5),  # Creative precision
            AgentType.REFINER: (600, 0.3),  # Concise refinement
            AgentType.GENERAL: (800, 0.5)   # Balanced general use
        }
        
        base_tokens, base_temp = agent_params.get(agent_type, (800, 0.5))
        
        # Adjust for priority
        if priority == "high":
            return (min(base_tokens + 200, 1500), base_temp - 0.1)
        elif priority == "low":
            return (max(base_tokens - 200, 400), base_temp + 0.1)
        
        return (base_tokens, base_temp)
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about agent routing decisions"""
        return {
            "available_providers": [p.value for p in multi_llm.available_providers],
            "agent_preferences": {
                agent.value: {
                    "primary": prefs["primary"].value,
                    "secondary": prefs["secondary"].value,
                    "strengths": prefs["strengths"]
                }
                for agent, prefs in self.agent_preferences.items()
            },
            "routing_strategy": "Intelligent agent-specific provider selection with production memory guidelines"
        }

# Global router instance
intelligent_router = IntelligentAgentRouter()