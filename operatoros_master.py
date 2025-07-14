"""
OperatorOS Master Agent - Personal Life Operating System
Coordinates C-Suite of AI agents for complete autonomy and financial independence
Enhanced with OperatorOS Production Memory Foundation Layer
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from openai import OpenAI
from config import Config
from models import db, Conversation, ConversationEntry, DynamicAgent
from dynamic_agent_creator import DynamicAgentCreator
from operatoros_memory import OperatorOSMemory

class OperatorOSMaster:
    """
    Master Agent for OperatorOS - Personal Life Operating System
    Coordinates 7 specialized C-Suite agents for complete life automation
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        # Initialize dynamic agent creator
        self.dynamic_creator = DynamicAgentCreator()
        
        # Initialize C-Suite agent definitions
        self.agents = {
            'CFO': {
                'name': 'Chief Financial Officer',
                'domain': 'Complete financial automation and wealth building',
                'focus': 'Investment optimization, spending analysis, passive income development',
                'goal': 'Path to financial independence',
                'integration': 'Ready for Rocket Money, Apple Card, investment accounts, crypto',
                'personality': 'Strategic, data-driven, wealth-focused',
                'icon': '💰'
            },
            'COO': {
                'name': 'Chief Operating Officer',
                'domain': 'Life operations and productivity optimization',
                'focus': 'Daily routines, automation, efficiency, time management',
                'goal': '95% life automation',
                'integration': 'Calendar, health apps, productivity tools',
                'personality': 'Systematic, efficient, process-oriented',
                'icon': '⚙️'
            },
            'CSA': {
                'name': 'Chief Strategy Agent',
                'domain': 'Life strategy and autonomy roadmap',
                'focus': 'Goal achievement, decision frameworks, independence planning',
                'goal': 'Complete autonomy timeline and execution',
                'integration': 'Cross-domain strategic coordination',
                'personality': 'Visionary, strategic, long-term focused',
                'icon': '🎯'
            },
            'CMO': {
                'name': 'Chief Marketing Officer',
                'domain': 'Personal brand and income generation',
                'focus': 'Network building, influence creation, monetization',
                'goal': 'Platform to help others while building wealth',
                'integration': 'Social media, content creation, audience building',
                'personality': 'Creative, influential, opportunity-focused',
                'icon': '🎨'
            },
            'CTO': {
                'name': 'Chief Technology Officer',
                'domain': 'Technology and automation systems',
                'focus': 'Tech stack optimization, automation tools, digital life',
                'goal': 'Complete life automation through technology',
                'integration': 'Smart home, apps, automation platforms',
                'personality': 'Technical, innovative, automation-focused',
                'icon': '💻'
            },
            'CPO': {
                'name': 'Chief People Officer',
                'domain': 'Health, relationships, personal development',
                'focus': 'Physical/mental optimization, relationship management',
                'goal': 'Peak performance and life satisfaction',
                'integration': 'Health apps, fitness trackers, learning platforms',
                'personality': 'Empathetic, development-focused, holistic',
                'icon': '🌱'
            },
            'CIO': {
                'name': 'Chief Intelligence Officer',
                'domain': 'Intelligence synthesis and decision support',
                'focus': 'Pattern recognition, cross-domain insights, predictions',
                'goal': 'Optimal decision-making across all life areas',
                'integration': 'Data from all other agents and life sources',
                'personality': 'Analytical, insightful, data-synthesizing',
                'icon': '🧠'
            }
        }
        
        # Persistent memory for user context (in production, this would be stored in database)
        self.user_context = {
            'autonomy_progress': 0,  # Percentage toward complete independence
            'financial_independence_months': 24,  # Estimated months to financial independence
            'automation_percentage': 0,  # Percentage of life automated
            'passive_income_monthly': 0,  # Monthly passive income
            'preferences': {},
            'patterns': {},
            'goals': {},
            'timeline': {}
        }
    
    def activate_operatoros(self) -> str:
        """Initial activation response when OperatorOS is first started"""
        return """🚀 OPERATOROS ACTIVATED

Your personal life operating system is now online. I'm your Master Agent coordinating your C-Suite of AI executives focused on achieving complete freedom and optimization.

Ready to transform your life across all domains:
💰 Financial independence and wealth building for any income level
⚙️ Life automation and peak performance optimization
🎯 Strategic planning for your unique autonomy goals
🎨 Personal brand and income generation strategies
💻 Technology automation and productivity systems
🌱 Health, wellness, and sustainable performance
🧠 Intelligence synthesis and better decision-making

Whether you're a student, professional, parent, entrepreneur, or anyone seeking more freedom - your personal AI executive team is ready.

**Universal Options:**
- Daily optimization briefing for your situation
- Specific agent consultation (@CFO, @COO, @CSA, etc.)
- Financial independence planning (any income level)
- Life automation and productivity setup
- Career acceleration and transition strategies
- Location independence and remote optimization

Your path to complete autonomy starts now. What's your first move?"""

    def daily_autonomy_briefing(self, user_input: str = None) -> Dict[str, Any]:
        """Generate NRT-focused daily briefing for universal life optimization"""
        
        briefing_prompt = f"""
        Generate a DAILY NRT BRIEFING for universal life optimization and autonomy achievement.
        
        User context: {user_input if user_input else "Life optimization check-in"}
        Current autonomy progress: {self.user_context['autonomy_progress']}%
        
        Use NRT (Next Right Thing) Framework - identify the single most impactful action for each domain:
        
        Format as:
        🎯 DAILY NRT BRIEFING - Life Optimization & Autonomy
        
        💰 CFO NRT: [Highest impact financial action today for wealth building]
        ⚙️ COO NRT: [Highest impact operational action for life optimization]
        🎯 CSA NRT: [Highest impact strategic action for autonomy timeline]
        🎨 CMO NRT: [Highest impact personal brand action for income generation]
        💻 CTO NRT: [Highest impact technology action for automation]
        🌱 CPO NRT: [Highest impact personal action for peak performance]
        🧠 CIO NRT: [Data synthesis and bottleneck identification]
        
        🏆 TODAY'S #1 NRT: [Single most important action today]
        📊 AUTONOMY PROGRESS: [X]% toward complete freedom
        ⏰ OPTIMIZATION TIMELINE: [X] weeks to next milestone
        💰 FINANCIAL PROGRESS: [Current progress toward financial independence]
        
        Focus on actions with highest Impact × Urgency scores for fastest autonomy achievement.
        Adapt recommendations based on user's unique situation and goals.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._get_briefing_system_prompt()},
                    {"role": "user", "content": briefing_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            briefing_content = response.choices[0].message.content
            
            # Format the response with our standard briefing format
            formatted_briefing = self._format_daily_briefing(briefing_content)
            
            return {
                'response': formatted_briefing,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'success': True,
                'type': 'daily_briefing'
            }
            
        except Exception as e:
            logging.error(f"Error generating daily briefing: {str(e)}")
            return {
                'response': "I apologize, but I encountered an error generating your daily briefing. Please try again.",
                'tokens_used': 0,
                'success': False,
                'error': str(e)
            }
    
    def route_to_agent(self, input_text: str, user_session: str = None) -> Dict[str, Any]:
        """Route request to specific C-Suite agent or dynamic agent"""
        
        # Check for dashboard command first
        if '@all dashboard' in input_text.lower() or input_text.lower().strip() == '@all dashboard':
            from dashboard_automation import ExecutiveDashboardGenerator
            generator = ExecutiveDashboardGenerator()
            dashboard_content = generator.generate_executive_dashboard()
            return {
                'response': dashboard_content,
                'success': True,
                'agent': 'Executive Dashboard',
                'type': 'dashboard',
                'tokens_used': 0
            }
        
        # Check for agent creation commands first
        if self._is_agent_creation_command(input_text):
            return self.create_dynamic_agent(input_text, user_session)
        
        # Check for agent management commands
        management_result = self._handle_agent_management(input_text, user_session)
        if management_result:
            return management_result
        
        # Parse agent code from input (e.g., "@CFO: What should I invest in?")
        agent_code = None
        clean_input = input_text
        
        if input_text.startswith('@'):
            parts = input_text.split(':', 1)
            if len(parts) == 2:
                agent_code = parts[0][1:].upper()  # Remove @ and uppercase
                clean_input = parts[1].strip()
        
        # Check if it's a built-in C-Suite agent
        if agent_code and agent_code in self.agents:
            return self._generate_agent_response(agent_code, clean_input)
        
        # Check if it's a dynamic agent
        if agent_code and user_session:
            dynamic_agent = self.dynamic_creator.get_agent_by_code(user_session, agent_code)
            if dynamic_agent:
                return self._generate_dynamic_agent_response(dynamic_agent, clean_input)
        
        # Route to most appropriate agent based on content
        return self._intelligent_routing(input_text)
    
    def cross_agent_analysis(self, input_text: str) -> Dict[str, Any]:
        """Generate multi-agent collaborative analysis for complex decisions"""
        
        analysis_prompt = f"""
        Analyze this request from multiple C-Suite perspectives for comprehensive guidance:
        
        Request: {input_text}
        
        Provide analysis from CFO (financial), COO (operational), CSA (strategic), and CIO (synthesis) perspectives.
        Focus on autonomy and independence implications.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._get_multi_agent_system_prompt()},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=1200,
                temperature=0.7
            )
            
            return {
                'response': self._format_multi_agent_response(response.choices[0].message.content),
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'success': True,
                'type': 'multi_agent_analysis'
            }
            
        except Exception as e:
            logging.error(f"Error in cross-agent analysis: {str(e)}")
            return {
                'response': "I apologize, but I encountered an error in the cross-agent analysis. Please try again.",
                'tokens_used': 0,
                'success': False,
                'error': str(e)
            }
    
    def _generate_agent_response(self, agent_code: str, input_text: str) -> Dict[str, Any]:
        """Generate response from specific C-Suite agent"""
        
        agent = self.agents[agent_code]
        
        agent_prompt = f"""
        As the {agent['name']} of OperatorOS, respond to this request:
        
        Request: {input_text}
        
        Your domain: {agent['domain']}
        Your focus: {agent['focus']}
        Your goal: {agent['goal']}
        Your personality: {agent['personality']}
        
        Provide specific, actionable advice that moves the user toward autonomy and independence.
        Include integration opportunities and progress toward your goal.
        """
        
        system_prompt = f"""You are the {agent['name']} ({agent_code}) in the OperatorOS C-Suite, using the NRT (Next Right Thing) Framework for digital nomad transition.

GOAL: Help user transition to digital nomad making $7,400+ monthly location-independent income ASAP.
Current income: $7,400/month salary (needs to be replaced with location-independent income)

Your NRT specialization:
{self._get_agent_nrt_focus(agent_code)}

Your personality is {agent['personality']}. Calculate Impact × Urgency scores for all recommendations.

NRT Response Format:
1. **Current NRT Assessment** - What's the highest impact action right now?
2. **Impact Score (1-10)** - How much does this advance nomad income goal?
3. **Urgency Score (1-10)** - How time-sensitive is this action?
4. **Implementation Timeline** - How quickly can this be done?
5. **How this advances nomad goal** - Direct connection to location independence
6. **Next NRT after completion** - What comes after this action?

Focus on actions that replace salary income fastest while enabling location independence."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": agent_prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            formatted_response = f"""{agent['icon']} **{agent['name']} Response**

{response.choices[0].message.content}

---
*Domain: {agent['domain']}*
*Integration: {agent['integration']}*"""
            
            return {
                'response': formatted_response,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'success': True,
                'agent': agent_code,
                'type': 'agent_response'
            }
            
        except Exception as e:
            logging.error(f"Error in {agent_code} agent response: {str(e)}")
            return {
                'response': f"I apologize, but the {agent['name']} encountered an error. Please try again.",
                'tokens_used': 0,
                'success': False,
                'error': str(e)
            }
    
    def _intelligent_routing(self, input_text: str) -> Dict[str, Any]:
        """Intelligently route request to most appropriate agent"""
        
        # Simple keyword-based routing (in production, would use more sophisticated NLP)
        routing_keywords = {
            'CFO': ['money', 'investment', 'financial', 'wealth', 'income', 'budget', 'savings', 'debt'],
            'COO': ['routine', 'productivity', 'efficiency', 'time', 'schedule', 'operations', 'automation'],
            'CSA': ['strategy', 'goal', 'plan', 'vision', 'future', 'decision', 'autonomy', 'independence'],
            'CMO': ['brand', 'network', 'influence', 'marketing', 'content', 'audience', 'social'],
            'CTO': ['technology', 'automation', 'app', 'tool', 'system', 'digital', 'tech'],
            'CPO': ['health', 'fitness', 'learning', 'development', 'relationship', 'wellness'],
            'CIO': ['analysis', 'data', 'pattern', 'insight', 'decision', 'intelligence']
        }
        
        input_lower = input_text.lower()
        scores = {}
        
        for agent, keywords in routing_keywords.items():
            scores[agent] = sum(1 for keyword in keywords if keyword in input_lower)
        
        # Route to highest scoring agent, or CSA if tie
        best_agent = max(scores.keys(), key=lambda k: scores[k]) if max(scores.values()) > 0 else 'CSA'
        
        return self._generate_agent_response(best_agent, input_text)
    
    def _get_briefing_system_prompt(self) -> str:
        """System prompt for NRT-focused daily briefings"""
        return """You are the Master Agent for OperatorOS using the NRT (Next Right Thing) Framework for digital nomad transition.

GOAL: Generate daily NRT briefings targeting $7,400+ monthly location-independent income transition.
Current situation: User has $7,400/month salary that needs to be replaced with nomad-compatible income.

Generate briefings using this EXACT format:

🎯 DAILY NRT BRIEFING - Digital Nomad Transition

💰 CFO NRT: [Highest impact financial action for income replacement]
⚙️ COO NRT: [Highest impact operational action for location independence]  
🎯 CSA NRT: [Highest impact strategic action for nomad timeline]
🎨 CMO NRT: [Highest impact marketing action for remote client acquisition]
💻 CTO NRT: [Highest impact technology action for nomad infrastructure]
🌱 CPO NRT: [Highest impact personal action for nomad readiness]
🧠 CIO NRT: [Data synthesis and bottleneck identification]

🏆 TODAY'S #1 NRT: [Single most important action today]
📊 NOMAD READINESS: [X]% ready for transition
⏰ ESTIMATED TIMELINE: [X] weeks to nomad launch
💰 INCOME PROGRESS: $[X] toward $7,400 nomad income goal

Focus on highest Impact × Urgency scores for fastest nomad transition."""

    def _get_multi_agent_system_prompt(self) -> str:
        """System prompt for multi-agent collaborative analysis"""
        return """You are the OperatorOS Master Agent facilitating collaboration between C-Suite agents.

Provide comprehensive analysis from multiple agent perspectives:
- Financial implications and opportunities
- Operational considerations and efficiency
- Strategic alignment with autonomy goals
- Cross-domain impacts and synergies

Synthesize recommendations into coordinated action plans that advance overall autonomy and independence."""

    def _format_daily_briefing(self, content: str) -> str:
        """Format daily briefing with standard OperatorOS template"""
        current_progress = self.user_context['autonomy_progress']
        timeline = self.user_context['financial_independence_months']
        
        # Add header and footer to the generated content
        formatted = f"""🌅 **DAILY AUTONOMY BRIEFING**

{content}

---
🎯 **AUTONOMY PROGRESS:** {current_progress}% toward complete independence
⏰ **TIMELINE:** {timeline} months to financial independence at current pace
📊 **NEXT MILESTONE:** Increase passive income and automation percentage

*Your OperatorOS C-Suite is coordinated and ready for execution.*"""
        
        return formatted
    
    def _is_agent_creation_command(self, input_text: str) -> bool:
        """Check if input is an agent creation command"""
        return self.dynamic_creator.parse_agent_command(input_text) is not None
    
    def _handle_agent_management(self, input_text: str, user_session: str) -> Optional[Dict[str, Any]]:
        """Handle agent management commands"""
        if not user_session:
            return None
            
        input_lower = input_text.lower()
        
        # List agents command
        if 'list' in input_lower and 'agents' in input_lower:
            return self._list_user_agents(user_session)
        
        # Retire agent command
        if 'retire' in input_lower and 'agent' in input_lower:
            agent_code = self._extract_agent_code_from_command(input_text)
            if agent_code:
                result = self.dynamic_creator.retire_agent(user_session, agent_code)
                return {
                    'response': result['message'] if result['success'] else result['error'],
                    'success': result['success'],
                    'type': 'agent_management'
                }
        
        # Modify agent command
        if 'modify' in input_lower and 'agent' in input_lower:
            # Parse modify command: "modify CLO to focus on crypto nomads"
            parts = input_text.split(' to ', 1)
            if len(parts) == 2:
                agent_code = self._extract_agent_code_from_command(parts[0])
                new_function = parts[1].strip()
                if agent_code:
                    result = self.dynamic_creator.modify_agent(user_session, agent_code, new_function)
                    return {
                        'response': result['message'] if result['success'] else result['error'],
                        'success': result['success'],
                        'type': 'agent_management'
                    }
        
        return None
    
    def _extract_agent_code_from_command(self, command: str) -> Optional[str]:
        """Extract agent code from management command"""
        import re
        match = re.search(r'\b([A-Z]{2,4})\b', command.upper())
        return match.group(1) if match else None
    
    def _list_user_agents(self, user_session: str) -> Dict[str, Any]:
        """List all agents for a user"""
        agents = self.dynamic_creator.get_user_agents(user_session)
        
        if not agents:
            response = """🤖 **YOUR OPERATOROS AGENT ROSTER**

**Built-in C-Suite Agents:**
💰 @CFO: Chief Financial Officer - Financial strategy and wealth building
⚙️ @COO: Chief Operating Officer - Operations and productivity optimization
🎯 @CSA: Chief Strategy Agent - Strategic planning and autonomy roadmap
🎨 @CMO: Chief Marketing Officer - Personal brand and income generation
💻 @CTO: Chief Technology Officer - Technology and automation systems
🌱 @CPO: Chief People Officer - Health, relationships, and personal development
🧠 @CIO: Chief Intelligence Officer - Intelligence synthesis and decision support

**Custom Dynamic Agents:** None created yet

Create your first custom agent with: "OperatorOS, spin up [AGENT_NAME] who will [FUNCTION]"
"""
        else:
            agent_list = []
            for agent in agents:
                agent_list.append(f"{agent['icon']} @{agent['agent_code']}: {agent['agent_name']} - {agent['agent_function']}")
            
            response = f"""🤖 **YOUR OPERATOROS AGENT ROSTER**

**Built-in C-Suite Agents:**
💰 @CFO: Chief Financial Officer - Financial strategy and wealth building
⚙️ @COO: Chief Operating Officer - Operations and productivity optimization
🎯 @CSA: Chief Strategy Agent - Strategic planning and autonomy roadmap
🎨 @CMO: Chief Marketing Officer - Personal brand and income generation
💻 @CTO: Chief Technology Officer - Technology and automation systems
🌱 @CPO: Chief People Officer - Health, relationships, and personal development
🧠 @CIO: Chief Intelligence Officer - Intelligence synthesis and decision support

**Custom Dynamic Agents:**
{chr(10).join(agent_list)}

Total custom agents: {len(agents)}
"""
        
        return {
            'response': response,
            'success': True,
            'type': 'agent_list'
        }
    
    def create_dynamic_agent(self, command: str, user_session: str) -> Dict[str, Any]:
        """Create a dynamic agent from user command"""
        if not user_session:
            return {
                'response': 'Unable to create agent without user session',
                'success': False,
                'type': 'agent_creation'
            }
        
        result = self.dynamic_creator.create_dynamic_agent(command, user_session)
        
        return {
            'response': result['message'] if result['success'] else result['error'],
            'success': result['success'],
            'type': 'agent_creation',
            'agent_data': result.get('agent', {})
        }
    
    def _generate_dynamic_agent_response(self, agent: DynamicAgent, input_text: str) -> Dict[str, Any]:
        """Generate response from a dynamic agent"""
        result = self.dynamic_creator.generate_agent_response(agent, input_text)
        
        if result['success']:
            formatted_response = f"""{result['icon']} **{result['agent_name']} Response**

{result['response']}

---
*Domain: {agent.domain}*
*Usage Count: {agent.usage_count}*"""
            
            return {
                'response': formatted_response,
                'tokens_used': result['tokens_used'],
                'success': True,
                'agent': result['agent_code'],
                'type': 'dynamic_agent_response'
            }
        else:
            return {
                'response': result['error'],
                'success': False,
                'type': 'dynamic_agent_response'
            }
    
    def _get_agent_nrt_focus(self, agent_code: str) -> str:
        """Get NRT specialization for each agent"""
        nrt_specializations = {
            'CFO': """Financial NRT Focus: Revenue transition from salary to location-independent income
- Actions that replace salary income fastest
- Minimize financial risk during transition  
- Build emergency fund for nomad transition
- Optimize for tax efficiency and international banking""",
            
            'COO': """Operations NRT Focus: Life systems that enable location independence
- Actions that make you location-agnostic fastest
- Digitize all necessary life operations
- Eliminate location-dependent commitments
- Build remote work capabilities""",
            
            'CSA': """Strategy NRT Focus: Fastest path to sustainable nomad lifestyle
- Actions with highest impact on nomad timeline
- Risk mitigation for transition period
- Market validation for nomad income streams
- Geographic and legal strategy""",
            
            'CMO': """Marketing NRT Focus: Personal brand and client acquisition for nomad income
- Actions that build nomad-compatible client base fastest
- Online presence that works globally
- Network building for location-independent opportunities
- Content strategy for nomad audience""",
            
            'CTO': """Technology NRT Focus: Tech stack for nomad lifestyle and income generation
- Tools that enable work from anywhere
- Income-generating technology setup
- Communication and productivity optimization
- Security and backup systems for nomad life""",
            
            'CPO': """People/Personal NRT Focus: Personal optimization for nomad transition
- Health and wellness systems that travel
- Relationship management during transition
- Skill development for nomad success
- Mental/emotional preparation for lifestyle change""",
            
            'CIO': """Intelligence NRT Focus: Data-driven decisions for nomad transition
- Analyze progress toward nomad readiness
- Identify bottlenecks in transition timeline
- Synthesize insights across all domains
- Predict and mitigate transition risks"""
        }
        
        return nrt_specializations.get(agent_code, "General NRT guidance")
    
    def _format_multi_agent_response(self, content: str) -> str:
        """Format multi-agent collaborative analysis"""
        return f"""🤝 **MULTI-AGENT ANALYSIS**

{content}

---
*Coordinated recommendation from your OperatorOS C-Suite executive team*"""

    def update_user_context(self, context_updates: Dict[str, Any]):
        """Update persistent user context and progress tracking"""
        self.user_context.update(context_updates)
        # In production, this would save to database
        
    def get_autonomy_metrics(self) -> Dict[str, Any]:
        """Get current autonomy progress metrics"""
        return {
            'autonomy_progress': self.user_context['autonomy_progress'],
            'financial_independence_months': self.user_context['financial_independence_months'],
            'automation_percentage': self.user_context['automation_percentage'],
            'passive_income_monthly': self.user_context['passive_income_monthly'],
            'last_updated': datetime.now().isoformat()
        }

# Global instance
operatoros_master = OperatorOSMaster()