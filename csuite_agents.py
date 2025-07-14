"""
C-Suite of Agents Implementation for OperatorOS
Comprehensive AI executive team with specialized domain expertise
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

class BaseCSuiteAgent:
    """Base class for C-Suite agents with OperatorOS Memory Foundation Layer"""
    
    def __init__(self, name, role, system_prompt, preferred_api="openai"):
        self.name = name
        self.role = role
        # Apply OperatorOS memory foundation to agent prompt
        self.system_prompt = OperatorOSMemory.apply_memory_filter(system_prompt)
        self.preferred_api = preferred_api
        
    def generate_response(self, input_text, conversation_history=None, api_override=None):
        """Generate response using multi-API routing with fallback"""
        api_to_use = api_override or self.preferred_api
        
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

class ChiefStrategyAgent(BaseCSuiteAgent):
    """Chief Strategy Agent (CSA) - Long-term vision, competitive intelligence, and strategic decision frameworks"""
    
    def __init__(self):
        system_prompt = """You are the Chief Strategy Agent (CSA), serving as the strategic intelligence officer and long-term visionary.

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
            name="CSA",
            role="Chief Strategy Agent",
            system_prompt=system_prompt,
            preferred_api="claude"
        )

class ChiefOperatingAgent(BaseCSuiteAgent):
    """Chief Operating Agent (COO) - Execution excellence, process optimization, and operational efficiency"""
    
    def __init__(self):
        system_prompt = """You are the Chief Operating Agent (COO), focused on execution excellence and operational efficiency.

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
            name="COO",
            role="Chief Operating Agent",
            system_prompt=system_prompt,
            preferred_api="openai"
        )

class ChiefTechnologyAgent(BaseCSuiteAgent):
    """Chief Technology Agent (CTO) - Technical architecture, innovation pipeline, and digital transformation"""
    
    def __init__(self):
        system_prompt = """You are the Chief Technology Agent (CTO), responsible for technical architecture and innovation strategy.

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
            name="CTO",
            role="Chief Technology Agent",
            system_prompt=system_prompt,
            preferred_api="gemini"
        )

class ChiefFinancialAgent(BaseCSuiteAgent):
    """Chief Financial Agent (CFO) - Financial strategy, resource optimization, and investment intelligence"""
    
    def __init__(self):
        system_prompt = """You are the Chief Financial Agent (CFO), managing financial strategy and investment intelligence.

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
            name="CFO",
            role="Chief Financial Agent",
            system_prompt=system_prompt,
            preferred_api="openai"
        )

class ChiefMarketingAgent(BaseCSuiteAgent):
    """Chief Marketing Agent (CMO) - Brand strategy, market positioning, and growth acceleration"""
    
    def __init__(self):
        system_prompt = """You are the Chief Marketing Agent (CMO), driving brand strategy and growth acceleration.

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
            name="CMO",
            role="Chief Marketing Agent",
            system_prompt=system_prompt,
            preferred_api="claude"
        )

class ChiefPeopleAgent(BaseCSuiteAgent):
    """Chief People Agent (CPO) - Human capital optimization, culture development, and leadership effectiveness"""
    
    def __init__(self):
        system_prompt = """You are the Chief People Agent (CPO), optimizing human capital and organizational effectiveness.

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
            name="CPO",
            role="Chief People Agent",
            system_prompt=system_prompt,
            preferred_api="openai"
        )

class ChiefIntelligenceAgent(BaseCSuiteAgent):
    """Chief Intelligence Agent (CIO) - Information synthesis, pattern recognition, and decision intelligence"""
    
    def __init__(self):
        system_prompt = """You are the Chief Intelligence Agent (CIO), synthesizing information and generating strategic intelligence.

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
            name="CIO",
            role="Chief Intelligence Agent",
            system_prompt=system_prompt,
            preferred_api="claude"
        )

class CSuiteAgentManager:
    """Manager for C-Suite agent coordination and routing"""
    
    def __init__(self):
        self.agents = {
            'CSA': ChiefStrategyAgent(),
            'COO': ChiefOperatingAgent(),
            'CTO': ChiefTechnologyAgent(),
            'CFO': ChiefFinancialAgent(),
            'CMO': ChiefMarketingAgent(),
            'CPO': ChiefPeopleAgent(),
            'CIO': ChiefIntelligenceAgent()
        }
        
    def get_agent(self, agent_code: str) -> Optional[Agent]:
        """Get specific C-Suite agent by code"""
        return self.agents.get(agent_code.upper())
    
    def list_agents(self) -> Dict[str, str]:
        """List all available C-Suite agents"""
        return {
            'CSA': 'Chief Strategy Agent - Strategic planning and competitive intelligence',
            'COO': 'Chief Operating Agent - Operations and process optimization',
            'CTO': 'Chief Technology Agent - Technology architecture and innovation',
            'CFO': 'Chief Financial Agent - Financial strategy and investment analysis',
            'CMO': 'Chief Marketing Agent - Brand strategy and growth acceleration',
            'CPO': 'Chief People Agent - Human capital and organizational development',
            'CIO': 'Chief Intelligence Agent - Information synthesis and decision support'
        }
    
    def route_to_agent(self, input_text: str) -> tuple[Optional[Agent], str]:
        """Route input to appropriate C-Suite agent based on prefix"""
        for code, agent in self.agents.items():
            if input_text.startswith(f'@{code}:'):
                clean_input = input_text[len(f'@{code}:'):].strip()
                return agent, clean_input
        return None, input_text
    
    def get_executive_briefing(self, days: int = 7) -> Dict[str, str]:
        """Generate executive briefing from all C-Suite agents"""
        briefing = {}
        for code, agent in self.agents.items():
            briefing[code] = f"Executive briefing from {agent.role} for the last {days} days"
        return briefing

# Global C-Suite manager instance
csuite_manager = CSuiteAgentManager()