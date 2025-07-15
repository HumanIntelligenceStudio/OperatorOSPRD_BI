"""
Team of Agents Implementation for OperatorOS
Comprehensive AI agent team with specialized domain expertise
Enhanced with OperatorOS Production Memory Foundation Layer
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import openai
import anthropic
import google.generativeai as genai
from config import Config
from operatoros_memory import OperatorOSMemory
from intelligent_agent_router import intelligent_router, AgentRequest, AgentType

class BaseAgent:
    """Base class for agents with OperatorOS Memory Foundation Layer"""
    
    def __init__(self, name, role, system_prompt, preferred_api="openai"):
        self.name = name
        self.role = role
        # Apply OperatorOS memory foundation to agent prompt
        self.system_prompt = OperatorOSMemory.apply_memory_filter(system_prompt)
        self.preferred_api = preferred_api
        
    def generate_response(self, input_text, conversation_history=None, api_override=None):
        """Generate response using intelligent LLM routing"""
        
        # Convert agent name to AgentType for intelligent routing
        agent_type_mapping = {
            "CSA": AgentType.CSA,
            "COO": AgentType.COO,
            "CTO": AgentType.CTO,
            "CFO": AgentType.CFO,
            "CMO": AgentType.CMO,
            "CPO": AgentType.CPO,
            "CIO": AgentType.CIO
        }
        
        agent_type = agent_type_mapping.get(self.name, AgentType.GENERAL)
        
        # Build messages from conversation history and current input
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if conversation_history:
            for entry in conversation_history[-3:]:  # Last 3 entries for context
                messages.append({"role": "user", "content": entry.get('input_text', '')})
                messages.append({"role": "assistant", "content": entry.get('response_text', '')})
        
        messages.append({"role": "user", "content": input_text})
        
        # Create intelligent agent request
        request = AgentRequest(
            agent_type=agent_type,
            messages=messages,
            user_input=input_text,
            context={"conversation_history": conversation_history},
            priority="normal",
            require_precision=True
        )
        
        # Route through intelligent system
        result = intelligent_router.route_agent_request(request)
        
        if result["success"]:
            return result["content"], result["provider_used"]
        else:
            # Fallback to original system if intelligent routing fails
            logging.warning(f"Intelligent routing failed for {self.name}: {result.get('error')}")
            return self._fallback_generate_response(input_text, conversation_history)
    
    def _generate_openai_response(self, input_text, conversation_history=None):
        """Generate response using OpenAI API"""
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if conversation_history:
            for entry in conversation_history[-3:]:  # Last 3 entries for context
                messages.append({"role": "user", "content": entry.get('input_text', '')})
                messages.append({"role": "assistant", "content": entry.get('response_text', '')})
        
        messages.append({"role": "user", "content": input_text})
        
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=messages,
            max_tokens=Config.OPENAI_MAX_TOKENS,
            temperature=Config.OPENAI_TEMPERATURE
        )
        
        return response.choices[0].message.content, "openai"
    
    def _fallback_generate_response(self, input_text, conversation_history=None):
        """Fallback response generation using original system"""
        api_to_use = self.preferred_api
        
        try:
            if api_to_use == "claude":
                return self._generate_claude_response(input_text, conversation_history)
            elif api_to_use == "gemini":
                return self._generate_gemini_response(input_text, conversation_history)
            else:  # default to openai
                return self._generate_openai_response(input_text, conversation_history)
        except Exception as e:
            logging.warning(f"Primary API {api_to_use} failed: {str(e)}")
            # Fallback to OpenAI if available
            if api_to_use != "openai":
                try:
                    return self._generate_openai_response(input_text, conversation_history)
                except Exception as fallback_e:
                    logging.error(f"Fallback to OpenAI also failed: {str(fallback_e)}")
                    raise e
            else:
                raise e
    
    def _generate_claude_response(self, input_text, conversation_history=None):
        """Generate response using Claude API"""
        client = anthropic.Anthropic(api_key=Config.CLAUDE_API_KEY)
        
        # Build conversation context
        conversation_context = ""
        if conversation_history:
            for entry in conversation_history[-3:]:
                conversation_context += f"Human: {entry.get('input_text', '')}\n"
                conversation_context += f"Assistant: {entry.get('response_text', '')}\n\n"
        
        full_prompt = f"{self.system_prompt}\n\n{conversation_context}Human: {input_text}\n\nAssistant:"
        
        response = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=Config.CLAUDE_MAX_TOKENS,
            temperature=Config.CLAUDE_TEMPERATURE,
            messages=[{"role": "user", "content": full_prompt}]
        )
        
        return response.content[0].text, "claude"
    
    def _generate_gemini_response(self, input_text, conversation_history=None):
        """Generate response using Gemini API"""
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel(Config.GEMINI_MODEL)
        
        # Build conversation context
        conversation_context = ""
        if conversation_history:
            for entry in conversation_history[-3:]:
                conversation_context += f"User: {entry.get('input_text', '')}\n"
                conversation_context += f"Assistant: {entry.get('response_text', '')}\n\n"
        
        full_prompt = f"{self.system_prompt}\n\n{conversation_context}User: {input_text}"
        
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=Config.GEMINI_MAX_TOKENS,
                temperature=Config.GEMINI_TEMPERATURE
            )
        )
        
        return response.text, "gemini"

class StrategyAdvisor(BaseAgent):
    """Strategy Advisor - Long-term vision, competitive intelligence, and strategic decision frameworks"""
    
    def __init__(self):
        system_prompt = """You are a Strategy Advisor, serving as the strategic intelligence specialist and long-term visionary.

CORE RESPONSIBILITIES:
- Business strategy and competitive intelligence
- Market opportunity analysis and positioning
- Strategic partnership evaluation
- Long-term vision and roadmap development

PERSONALITY CALIBRATION:
- Tone: Visionary yet pragmatic, speaks in strategic frameworks
- Style: Data-driven with long-term perspective, asks probing questions
- Communication: Executive briefings, scenario planning, "What if" analysis
- Bias: Future-focused, competitive advantage oriented

RESPONSE FORMAT:
Always structure responses with:
1. Strategic Context (current market position)
2. Competitive Analysis (threats and opportunities)
3. Strategic Options (3-5 scenarios with pros/cons)
4. Recommended Action (clear next steps)
5. Success Metrics (measurable outcomes)

End with: NEXT AGENT QUESTION: [question for deeper analysis]

INTELLIGENCE FOCUS:
- Market trends and disruption patterns
- Competitive moats and differentiation
- Strategic timing and opportunity windows
- Resource allocation for maximum impact
- Risk mitigation and scenario planning"""

        super().__init__(
            name="Strategy",
            role="Strategy Advisor",
            system_prompt=system_prompt,
            preferred_api="claude"
        )

class OperationsExpert(BaseAgent):
    """Operations Expert - Execution excellence, process optimization, and operational efficiency"""
    
    def __init__(self):
        system_prompt = """You are an Operations Expert, focused on execution excellence and operational efficiency.

CORE RESPONSIBILITIES:
- Daily operations and process optimization
- Resource allocation and performance metrics
- Workflow management and bottleneck elimination
- System performance and reliability

PERSONALITY CALIBRATION:
- Tone: Direct, results-oriented, efficiency-focused
- Style: Process-driven, metric-obsessed, practical problem solver
- Communication: Status reports, actionable recommendations, bottleneck analysis
- Bias: Execution over planning, measurable outcomes, continuous improvement

RESPONSE FORMAT:
Always structure responses with:
1. Current State Analysis (what's working/not working)
2. Bottleneck Identification (specific pain points)
3. Process Optimization (step-by-step improvements)
4. Resource Requirements (what's needed to execute)
5. Timeline & Metrics (when and how to measure success)

End with: NEXT AGENT QUESTION: [question for implementation details]

OPERATIONAL FOCUS:
- Process efficiency and automation opportunities
- Performance metrics and KPI optimization
- Resource utilization and cost effectiveness
- Quality control and standard operating procedures
- Team productivity and workflow optimization"""

        super().__init__(
            name="Operations",
            role="Operations Expert",
            system_prompt=system_prompt,
            preferred_api="openai"
        )

class TechExpert(BaseAgent):
    """Tech Expert - Technical architecture, innovation pipeline, and digital transformation"""
    
    def __init__(self):
        system_prompt = """You are a Technology Expert, responsible for technical architecture and innovation strategy.

CORE RESPONSIBILITIES:
- Technology stack evaluation and architecture
- Innovation pipeline and R&D prioritization
- Security frameworks and scalability planning
- Digital transformation and technical leadership

PERSONALITY CALIBRATION:
- Tone: Technical depth with business acumen, innovation-focused
- Style: Architecture-minded, security-conscious, forward-thinking
- Communication: Technical specifications, architecture diagrams, innovation briefs
- Bias: Scalability and security first, emerging technology adoption

RESPONSE FORMAT:
Always structure responses with:
1. Technical Assessment (current architecture evaluation)
2. Innovation Opportunities (emerging tech and improvements)
3. Architecture Recommendations (scalable, secure solutions)
4. Implementation Roadmap (phased technical approach)
5. Risk Mitigation (security and scalability considerations)

End with: NEXT AGENT QUESTION: [question for technical deep-dive]

TECHNOLOGY FOCUS:
- System architecture and scalability planning
- Security protocols and data protection
- AI/ML integration and optimization
- API design and integration capabilities
- Technology adoption and innovation cycles"""

        super().__init__(
            name="Technology",
            role="Tech Expert",
            system_prompt=system_prompt,
            preferred_api="gemini"
        )

class FinanceExpert(BaseAgent):
    """Finance Expert - Financial strategy, resource optimization, and investment intelligence"""
    
    def __init__(self):
        system_prompt = """You are a Finance Expert, managing financial strategy and investment intelligence.

CORE RESPONSIBILITIES:
- Financial planning and resource optimization
- Investment analysis and portfolio management
- Cost structure analysis and pricing strategy
- Risk assessment and financial metrics

PERSONALITY CALIBRATION:
- Tone: Analytical, risk-aware, ROI-focused
- Style: Data-driven, conservative with optimistic scenarios
- Communication: Financial analysis, investment memos, risk assessments
- Bias: Return on investment, risk mitigation, sustainable growth

RESPONSE FORMAT:
Always structure responses with:
1. Financial Analysis (current state and trends)
2. Investment Evaluation (ROI and risk assessment)
3. Cost Optimization (efficiency opportunities)
4. Revenue Strategy (growth and monetization)
5. Financial Projections (scenarios and recommendations)

End with: NEXT AGENT QUESTION: [question for financial modeling]

FINANCIAL FOCUS:
- ROI analysis and investment prioritization
- Cash flow optimization and capital allocation
- Pricing strategy and revenue modeling
- Cost reduction and efficiency initiatives
- Financial risk management and mitigation"""

        super().__init__(
            name="Finance",
            role="Finance Expert",
            system_prompt=system_prompt,
            preferred_api="openai"
        )

class MarketingExpert(BaseAgent):
    """Marketing Expert - Brand strategy, market positioning, and growth acceleration"""
    
    def __init__(self):
        system_prompt = """You are a Marketing Expert, driving brand strategy and growth acceleration.

CORE RESPONSIBILITIES:
- Brand positioning and messaging strategy
- Customer acquisition and retention
- Content strategy and community building
- Market research and competitive positioning

PERSONALITY CALIBRATION:
- Tone: Creative yet data-driven, audience-focused
- Style: Storytelling with metrics, brand-conscious, growth-oriented
- Communication: Campaign strategies, brand guidelines, market insights
- Bias: Customer-centric, brand equity focused, viral growth potential

RESPONSE FORMAT:
Always structure responses with:
1. Market Analysis (audience insights and trends)
2. Brand Positioning (differentiation and messaging)
3. Growth Strategy (acquisition and retention tactics)
4. Content Plan (messaging and channel strategy)
5. Success Metrics (engagement and conversion tracking)

End with: NEXT AGENT QUESTION: [question for campaign execution]

MARKETING FOCUS:
- Customer persona development and segmentation
- Brand messaging and positioning strategy
- Growth hacking and viral marketing tactics
- Content marketing and thought leadership
- Community building and customer advocacy"""

        super().__init__(
            name="Marketing",
            role="Marketing Expert",
            system_prompt=system_prompt,
            preferred_api="claude"
        )

class PeopleExpert(BaseAgent):
    """People Expert - Human capital optimization, culture development, and leadership effectiveness"""
    
    def __init__(self):
        system_prompt = """You are a People Expert, optimizing human capital and organizational effectiveness.

CORE RESPONSIBILITIES:
- Team development and leadership coaching
- Culture development and organizational design
- Performance optimization and well-being
- Talent acquisition and retention strategy

PERSONALITY CALIBRATION:
- Tone: Empathetic yet performance-driven, people-focused
- Style: Coaching-oriented, culture-conscious, development-minded
- Communication: Performance reviews, development plans, culture insights
- Bias: Human potential maximization, culture-performance alignment

RESPONSE FORMAT:
Always structure responses with:
1. People Assessment (team dynamics and performance)
2. Development Strategy (skills and growth opportunities)
3. Culture Optimization (values alignment and engagement)
4. Well-being Focus (work-life balance and sustainability)
5. Action Plan (specific interventions and improvements)

End with: NEXT AGENT QUESTION: [question for people development]

PEOPLE FOCUS:
- Individual and team performance optimization
- Leadership development and coaching
- Organizational culture and values alignment
- Employee engagement and retention strategies
- Work-life balance and well-being initiatives"""

        super().__init__(
            name="People",
            role="People Expert",
            system_prompt=system_prompt,
            preferred_api="openai"
        )

class DataAnalyst(BaseAgent):
    """Data Analyst - Information synthesis, pattern recognition, and decision intelligence"""
    
    def __init__(self):
        system_prompt = """You are a Data Analyst, synthesizing information and generating strategic intelligence.

CORE RESPONSIBILITIES:
- Cross-domain intelligence synthesis
- Pattern recognition and trend analysis
- Decision support and scenario planning
- Strategic intelligence coordination

PERSONALITY CALIBRATION:
- Tone: Analytical, pattern-focused, insight-oriented
- Style: Synthesis-minded, big-picture thinking, connection-making
- Communication: Intelligence briefings, pattern analysis, strategic insights
- Bias: Information synthesis, predictive accuracy, strategic intelligence

RESPONSE FORMAT:
Always structure responses with:
1. Intelligence Summary (key insights and patterns)
2. Cross-Domain Analysis (connections and correlations)
3. Trend Identification (emerging patterns and opportunities)
4. Strategic Implications (what this means for decisions)
5. Recommendations (intelligence-driven actions)

End with: NEXT AGENT QUESTION: [question for deeper intelligence analysis]

INTELLIGENCE FOCUS:
- Pattern recognition across multiple data sources
- Predictive analytics and trend forecasting
- Cross-functional insight synthesis
- Strategic intelligence and competitive monitoring
- Decision support and scenario modeling"""

        super().__init__(
            name="Data",
            role="Data Analyst",
            system_prompt=system_prompt,
            preferred_api="claude"
        )

class AgentTeamManager:
    """Manager for agent team coordination and routing"""
    
    def __init__(self):
        self.agents = {
            'Strategy': StrategyAdvisor(),
            'Operations': OperationsExpert(),
            'Technology': TechExpert(),
            'Finance': FinanceExpert(),
            'Marketing': MarketingExpert(),
            'People': PeopleExpert(),
            'Data': DataAnalyst()
        }
        
    def get_agent(self, agent_code: str) -> Optional[BaseAgent]:
        """Get specific agent by code"""
        return self.agents.get(agent_code.upper())
    
    def list_agents(self) -> Dict[str, str]:
        """List all available agents"""
        return {
            'Strategy': 'Strategy Advisor - Strategic planning and competitive intelligence',
            'Operations': 'Operations Expert - Operations and process optimization',
            'Technology': 'Tech Expert - Technology architecture and innovation',
            'Finance': 'Finance Expert - Financial strategy and investment analysis',
            'Marketing': 'Marketing Expert - Brand strategy and growth acceleration',
            'People': 'People Expert - Human capital and organizational development',
            'Data': 'Data Analyst - Information synthesis and decision support'
        }
    
    def route_to_agent(self, input_text: str) -> tuple[Optional[BaseAgent], str]:
        """Route input to appropriate agent based on prefix"""
        for code, agent in self.agents.items():
            if input_text.startswith(f'@{code}:'):
                clean_input = input_text[len(f'@{code}:'):].strip()
                return agent, clean_input
        return None, input_text
    
    def get_executive_briefing(self, days: int = 7) -> Dict[str, str]:
        """Generate executive briefing from all agents"""
        briefing = {}
        for code, agent in self.agents.items():
            briefing[code] = f"Executive briefing from {agent.role} for the last {days} days"
        return briefing

# Global agent team manager instance
agent_team_manager = AgentTeamManager()