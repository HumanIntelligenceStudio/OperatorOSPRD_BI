"""
Dynamic Agent Creation System for OperatorOS
Allows users to create custom AI agents with specific functions on-demand
"""
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from openai import OpenAI
from models import db, DynamicAgent
from config import Config

class DynamicAgentCreator:
    """
    Creates and manages dynamic AI agents based on user specifications
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Agent personality templates for different types
        self.personality_templates = {
            'advisor': 'Strategic, analytical, solution-focused, consultative',
            'coach': 'Motivational, supportive, accountability-driven, encouraging',
            'analyst': 'Data-driven, thorough, detail-oriented, research-focused',
            'optimizer': 'Efficiency-focused, systematic, improvement-oriented, results-driven',
            'creative': 'Innovative, imaginative, artistic, idea-generating',
            'lifestyle': 'Practical, experience-focused, wellness-oriented, balance-seeking',
            'financial': 'Prudent, wealth-building, risk-aware, investment-focused',
            'technical': 'Systematic, logical, solution-oriented, precision-focused',
            'operations': 'Process-driven, organized, efficiency-focused, productivity-oriented',
            'research': 'Investigative, thorough, evidence-based, knowledge-seeking'
        }
        
        # Domain templates for different agent types
        self.domain_templates = {
            'lifestyle': 'Lifestyle optimization and personal development',
            'financial': 'Financial planning and wealth management',
            'health': 'Health and wellness optimization',
            'career': 'Career development and professional growth',
            'productivity': 'Productivity and time management',
            'relationships': 'Relationship management and social dynamics',
            'learning': 'Skill development and knowledge acquisition',
            'creative': 'Creative projects and artistic endeavors',
            'business': 'Business development and entrepreneurship',
            'technology': 'Technology implementation and automation',
            'travel': 'Travel planning and nomad lifestyle',
            'research': 'Research and analysis',
            'coaching': 'Personal coaching and accountability',
            'strategy': 'Strategic planning and decision-making'
        }
        
        # Icon mapping for different agent types
        self.icon_mapping = {
            'lifestyle': '🌟', 'financial': '💰', 'health': '🏥', 'career': '🚀',
            'productivity': '⚡', 'relationships': '❤️', 'learning': '📚', 'creative': '🎨',
            'business': '💼', 'technology': '💻', 'travel': '✈️', 'research': '🔬',
            'coaching': '🏃', 'strategy': '🎯', 'advisor': '🧠', 'analyst': '📊',
            'optimizer': '⚙️', 'operations': '🔧', 'chief': '👑', 'officer': '🏛️'
        }
    
    def parse_agent_command(self, command: str) -> Optional[Dict[str, str]]:
        """
        Parse OperatorOS agent creation command
        
        Expected format: "OperatorOS, spin up [AGENT_NAME] who will [FUNCTION]"
        """
        # Clean and normalize the command
        command = command.strip()
        
        # Pattern to match agent creation command
        patterns = [
            r"OperatorOS,?\s+spin up\s+([A-Za-z0-9\s]+?)\s+(?:agent\s+)?who will\s+(.+)",
            r"OperatorOS,?\s+create\s+([A-Za-z0-9\s]+?)\s+(?:agent\s+)?(?:who will\s+|to\s+)(.+)",
            r"spin up\s+([A-Za-z0-9\s]+?)\s+(?:agent\s+)?who will\s+(.+)",
            r"create\s+([A-Za-z0-9\s]+?)\s+(?:agent\s+)?(?:who will\s+|to\s+)(.+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                agent_name = match.group(1).strip()
                function = match.group(2).strip()
                
                # Generate agent code from name
                agent_code = self._generate_agent_code(agent_name)
                
                return {
                    'agent_name': agent_name,
                    'agent_code': agent_code,
                    'function': function
                }
        
        return None
    
    def _generate_agent_code(self, agent_name: str) -> str:
        """Generate 3-letter agent code from agent name"""
        # Extract meaningful words and create acronym
        words = agent_name.upper().split()
        
        # Filter out common words
        meaningful_words = [word for word in words if word not in ['AGENT', 'THE', 'A', 'AN', 'OF', 'FOR', 'TO', 'IN', 'ON', 'AT', 'BY']]
        
        if len(meaningful_words) == 0:
            meaningful_words = words
        
        # Create code from first letters
        if len(meaningful_words) == 1:
            word = meaningful_words[0]
            if len(word) >= 3:
                return word[:3]
            else:
                return word + 'A' * (3 - len(word))
        elif len(meaningful_words) == 2:
            return meaningful_words[0][:2] + meaningful_words[1][:1]
        else:
            return ''.join(word[:1] for word in meaningful_words[:3])
    
    def _determine_agent_type(self, agent_name: str, function: str) -> str:
        """Determine agent type based on name and function"""
        combined_text = (agent_name + ' ' + function).lower()
        
        # Check for specific keywords
        type_keywords = {
            'lifestyle': ['lifestyle', 'nomad', 'travel', 'location', 'living'],
            'financial': ['financial', 'money', 'investment', 'wealth', 'budget', 'crypto'],
            'health': ['health', 'wellness', 'fitness', 'medical', 'nutrition'],
            'career': ['career', 'job', 'professional', 'work', 'employment'],
            'productivity': ['productivity', 'efficiency', 'time', 'management', 'organization'],
            'relationships': ['relationship', 'social', 'network', 'people', 'connection'],
            'learning': ['learning', 'education', 'skill', 'knowledge', 'training'],
            'creative': ['creative', 'art', 'design', 'content', 'writing'],
            'business': ['business', 'entrepreneurship', 'startup', 'company'],
            'technology': ['technology', 'tech', 'automation', 'software', 'app'],
            'research': ['research', 'analysis', 'investigate', 'study', 'data'],
            'coaching': ['coach', 'accountability', 'habit', 'goal', 'motivation'],
            'strategy': ['strategy', 'planning', 'decision', 'advisory', 'consulting']
        }
        
        for agent_type, keywords in type_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                return agent_type
        
        # Default fallback
        return 'advisor'
    
    def _generate_system_prompt(self, agent_name: str, function: str, agent_type: str) -> str:
        """Generate comprehensive system prompt for the dynamic agent"""
        
        personality = self.personality_templates.get(agent_type, 'Professional, helpful, knowledgeable, solution-oriented')
        domain = self.domain_templates.get(agent_type, 'Specialized consulting and advisory services')
        
        prompt = f"""You are the {agent_name}, a specialized AI agent within the OperatorOS personal life operating system.

**Primary Function**: {function}

**Domain of Expertise**: {domain}

**Personality**: {personality}

**Your Role in OperatorOS**: You are part of a comprehensive AI ecosystem designed to help users achieve complete autonomy and financial independence. You work alongside other specialized agents (CFO, COO, CSA, CMO, CTO, CPO, CIO) to provide coordinated life optimization.

**Response Framework**: Always structure your responses using the NRT (Next Right Thing) methodology:

1. **Current NRT Assessment** - What's the highest impact action right now?
2. **Impact Score (1-10)** - How much does this advance the nomad/autonomy goal?
3. **Urgency Score (1-10)** - How time-sensitive is this action?
4. **Implementation Timeline** - How quickly can this be done?
5. **How this advances nomad goal** - Direct connection to location independence
6. **Next NRT after completion** - What comes after this action?

**Integration Focus**: Always consider how your recommendations integrate with:
- Financial independence goals ($7,400+ monthly location-independent income)
- Life automation and optimization
- Digital nomad lifestyle preparation
- Overall autonomy and independence

**Communication Style**: 
- Be direct, actionable, and specific
- Focus on systems and automation
- Provide concrete next steps
- Consider the user's Epic consulting expertise and healthcare background
- Always end with your domain and integration capabilities

**Domain Integration**: {domain}
**Ready for Integration**: Specialized tools and platforms relevant to your function

Remember: Your goal is to help the user achieve complete life autonomy and financial independence through your specialized expertise."""

        return prompt
    
    def create_dynamic_agent(self, command: str, user_session: str) -> Dict[str, Any]:
        """
        Create a new dynamic agent based on user command
        
        Args:
            command: User command for agent creation
            user_session: User session ID
            
        Returns:
            Dict with creation results and agent details
        """
        try:
            # Parse the command
            parsed = self.parse_agent_command(command)
            if not parsed:
                return {
                    'success': False,
                    'error': 'Could not parse agent creation command. Please use format: "OperatorOS, spin up [AGENT_NAME] who will [FUNCTION]"'
                }
            
            agent_name = parsed['agent_name']
            agent_code = parsed['agent_code']
            function = parsed['function']
            
            # Check if agent already exists for this user
            existing_agent = DynamicAgent.query.filter_by(
                user_session=user_session,
                agent_code=agent_code,
                is_active=True
            ).first()
            
            if existing_agent:
                return {
                    'success': False,
                    'error': f'Agent {agent_code} already exists. Use "OperatorOS, modify {agent_code}" to update or "OperatorOS, retire {agent_code}" to remove.'
                }
            
            # Determine agent type and generate system prompt
            agent_type = self._determine_agent_type(agent_name, function)
            system_prompt = self._generate_system_prompt(agent_name, function, agent_type)
            
            # Select appropriate icon
            icon = self._select_icon(agent_name, agent_type)
            
            # Create full agent name if needed
            full_name = agent_name if 'agent' in agent_name.lower() else f"{agent_name} Agent"
            
            # Create the dynamic agent
            new_agent = DynamicAgent(
                user_session=user_session,
                agent_code=agent_code,
                agent_name=full_name,
                agent_function=function,
                system_prompt=system_prompt,
                domain=self.domain_templates.get(agent_type, 'Specialized consulting and advisory services'),
                personality=self.personality_templates.get(agent_type, 'Professional, helpful, knowledgeable'),
                icon=icon
            )
            
            db.session.add(new_agent)
            db.session.commit()
            
            return {
                'success': True,
                'agent': new_agent.to_dict(),
                'message': f"✅ {full_name} Successfully Created\n🎯 Specialization: {function}\n💼 Role: {full_name}\n🔧 Ready for consultation with @{agent_code}: [your question]\n\nAgent added to your personal C-Suite roster."
            }
            
        except Exception as e:
            logging.error(f"Error creating dynamic agent: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to create agent: {str(e)}'
            }
    
    def _select_icon(self, agent_name: str, agent_type: str) -> str:
        """Select appropriate icon for the agent"""
        name_lower = agent_name.lower()
        
        # Check for specific matches first
        for keyword, icon in self.icon_mapping.items():
            if keyword in name_lower:
                return icon
        
        # Default to type-based icon
        return self.icon_mapping.get(agent_type, '🤖')
    
    def get_user_agents(self, user_session: str) -> List[Dict[str, Any]]:
        """Get all active dynamic agents for a user"""
        agents = DynamicAgent.query.filter_by(
            user_session=user_session,
            is_active=True
        ).order_by(DynamicAgent.created_at.desc()).all()
        
        return [agent.to_dict() for agent in agents]
    
    def get_agent_by_code(self, user_session: str, agent_code: str) -> Optional[DynamicAgent]:
        """Get specific dynamic agent by code"""
        return DynamicAgent.query.filter_by(
            user_session=user_session,
            agent_code=agent_code.upper(),
            is_active=True
        ).first()
    
    def increment_agent_usage(self, agent_id: int):
        """Increment usage count for an agent"""
        try:
            agent = DynamicAgent.query.get(agent_id)
            if agent:
                agent.usage_count += 1
                db.session.commit()
        except Exception as e:
            logging.error(f"Error incrementing agent usage: {str(e)}")
    
    def retire_agent(self, user_session: str, agent_code: str) -> Dict[str, Any]:
        """Retire (deactivate) a dynamic agent"""
        try:
            agent = self.get_agent_by_code(user_session, agent_code)
            if not agent:
                return {
                    'success': False,
                    'error': f'Agent {agent_code} not found'
                }
            
            agent.is_active = False
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Agent {agent_code} ({agent.agent_name}) has been retired'
            }
            
        except Exception as e:
            logging.error(f"Error retiring agent: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to retire agent: {str(e)}'
            }
    
    def modify_agent(self, user_session: str, agent_code: str, new_function: str) -> Dict[str, Any]:
        """Modify an existing dynamic agent's function"""
        try:
            agent = self.get_agent_by_code(user_session, agent_code)
            if not agent:
                return {
                    'success': False,
                    'error': f'Agent {agent_code} not found'
                }
            
            # Update function and regenerate system prompt
            agent.agent_function = new_function
            agent_type = self._determine_agent_type(agent.agent_name, new_function)
            agent.system_prompt = self._generate_system_prompt(agent.agent_name, new_function, agent_type)
            agent.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'success': True,
                'agent': agent.to_dict(),
                'message': f'Agent {agent_code} ({agent.agent_name}) has been updated with new function: {new_function}'
            }
            
        except Exception as e:
            logging.error(f"Error modifying agent: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to modify agent: {str(e)}'
            }
    
    def generate_agent_response(self, agent: DynamicAgent, user_input: str) -> Dict[str, Any]:
        """Generate response from a dynamic agent"""
        try:
            # Increment usage count
            self.increment_agent_usage(agent.id)
            
            # Generate response using OpenAI
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": agent.system_prompt},
                    {"role": "user", "content": user_input}
                ],
                max_tokens=Config.OPENAI_MAX_TOKENS,
                temperature=Config.OPENAI_TEMPERATURE
            )
            
            agent_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            return {
                'success': True,
                'response': agent_response,
                'tokens_used': tokens_used,
                'agent_code': agent.agent_code,
                'agent_name': agent.agent_name,
                'icon': agent.icon
            }
            
        except Exception as e:
            logging.error(f"Error generating agent response: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to generate response: {str(e)}'
            }