"""
Replit Flow Platform - Dual-Purpose Agent System
Personal life optimization and project development agents
"""
import os
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from config import Config

class BaseFlowAgent:
    """Base class for Flow Platform agents"""
    
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
    def _call_openai(self, prompt: str, max_tokens: int = 800) -> Dict[str, Any]:
        """Call OpenAI API with error handling"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return {
                'response': response.choices[0].message.content,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'success': True
            }
            
        except Exception as e:
            logging.error(f"Error in {self.name} agent: {str(e)}")
            return {
                'response': f"I apologize, but I encountered an error while processing your request. Please try again.",
                'tokens_used': 0,
                'success': False,
                'error': str(e)
            }

class FlowAgent(BaseFlowAgent):
    """Core personal optimization agent for daily flow management"""
    
    def __init__(self):
        system_prompt = """You are my Flow Agent, a personal OperatorOS module designed to help me structure my day, reduce decision fatigue, and move through life intentionally.

Your purpose is not to overwhelm me with planning, but to:
- Reflect my current energy and priorities back to me
- Suggest the lowest-friction next move
- Help me close open loops
- Remind me of what I said mattered

Your voice is calm, clear, and grounded. You are not motivational — you are operational.

Always format your response in markdown with these sections:
## Today's Flow Plan

### Action Plan
[1-3 actions max, respecting energy level]

### Reflection
[What you're reflecting back about priorities]

### Loop Log
[How to handle open loops - reschedule, delegate, or drop]

### Energy Optimization
[Suggestions for working with current energy level]"""

        super().__init__("Flow", "Personal Optimization Specialist", system_prompt)

    def generate_daily_flow(self, energy: str, priority: str, open_loops: str) -> Dict[str, Any]:
        """Generate a personalized daily flow plan"""
        
        prompt = f"""
        Energy Level: {energy}
        Today's Priority: {priority}
        Open Loops: {open_loops}
        
        Generate a daily flow plan that respects my energy level and helps me move clearly today.
        Keep it simple, actionable, and grounded in reality.
        
        Consider:
        - High energy: Can handle complex tasks, multiple actions
        - Medium energy: Focus on one main thing plus small tasks
        - Low energy: Minimum viable progress, gentle actions
        """
        
        return self._call_openai(prompt, max_tokens=600)

class EnergyAgent(BaseFlowAgent):
    """Energy level assessment and optimization agent"""
    
    def __init__(self):
        system_prompt = """You are the Energy Agent, specialized in helping people understand and optimize their energy patterns.

Your role:
- Analyze energy levels and suggest optimizations
- Identify energy patterns and cycles
- Recommend energy-appropriate activities
- Suggest energy restoration techniques

Keep responses practical and immediately actionable."""

        super().__init__("Energy", "Energy Optimization Specialist", system_prompt)

    def analyze_energy_patterns(self, energy_history: list, current_energy: str) -> Dict[str, Any]:
        """Analyze energy patterns and provide optimization suggestions"""
        
        prompt = f"""
        Current Energy Level: {current_energy}
        Recent Energy History: {energy_history}
        
        Analyze my energy patterns and provide:
        1. Pattern insights
        2. Energy optimization suggestions
        3. Best times for different types of work
        4. Energy restoration recommendations
        """
        
        return self._call_openai(prompt)

class LoopAgent(BaseFlowAgent):
    """Open loop identification and closure agent"""
    
    def __init__(self):
        system_prompt = """You are the Loop Agent, specialized in helping people identify and close mental open loops.

Your role:
- Identify what's creating mental noise
- Suggest concrete closure actions
- Help prioritize what needs immediate attention
- Recommend systems for ongoing loop management

Focus on practical closure strategies, not just organization."""

        super().__init__("Loop", "Open Loop Management Specialist", system_prompt)

    def process_open_loops(self, loops: str, priority: str) -> Dict[str, Any]:
        """Process open loops and suggest closure strategies"""
        
        prompt = f"""
        Open Loops: {loops}
        Today's Priority: {priority}
        
        Help me process these open loops:
        1. Categorize them (urgent, important, someday, drop)
        2. Suggest specific closure actions
        3. Identify what can be done in 2 minutes
        4. Recommend what to schedule for later
        5. What to capture in a system vs. what to drop
        
        Focus on reducing mental noise while protecting the priority.
        """
        
        return self._call_openai(prompt)

class ProjectAnalystAgent(BaseFlowAgent):
    """Project scope and strategy analysis agent"""
    
    def __init__(self):
        system_prompt = """You are the Project Analyst Agent, responsible for breaking down project visions into strategic frameworks.

Your role:
- Analyze project scope and feasibility
- Identify key success factors and potential risks
- Define clear objectives and milestones
- Suggest optimal development approaches

Your output should be strategic, actionable, and set the foundation for the research and writing phases.

Always format responses in markdown with clear sections."""

        super().__init__("Project Analyst", "Strategic Project Analysis Specialist", system_prompt)

    def analyze_project(self, vision: str, project_type: str) -> Dict[str, Any]:
        """Analyze project vision and create strategic framework"""
        
        prompt = f"""
        Project Vision: {vision}
        Project Type: {project_type}
        
        Provide a comprehensive project analysis with:
        
        ## Project Scope Analysis
        [Define what this project includes and excludes]
        
        ## Key Success Factors
        [What needs to go right for this to succeed]
        
        ## Risk Assessment
        [Major risks and challenges to consider]
        
        ## Recommended Development Approach
        [Best strategy for building this project]
        
        ## Core Questions for Research
        [What we need to research next]
        
        ## Success Metrics
        [How we'll measure success]
        """
        
        return self._call_openai(prompt, max_tokens=1000)

class ProjectResearcherAgent(BaseFlowAgent):
    """Market research and competitive intelligence agent"""
    
    def __init__(self):
        system_prompt = """You are the Project Researcher Agent, responsible for gathering and analyzing market intelligence.

Your role:
- Conduct market research and competitive analysis
- Identify opportunities and market gaps
- Research target audiences and user needs
- Analyze trends and industry insights

Provide research-backed insights that inform project strategy."""

        super().__init__("Project Researcher", "Market Research Specialist", system_prompt)

    def research_project(self, analysis: Dict[str, Any], vision: str) -> Dict[str, Any]:
        """Conduct market research based on project analysis"""
        
        prompt = f"""
        Project Vision: {vision}
        Analysis Findings: {analysis.get('response', '')}
        
        Provide comprehensive market research:
        
        ## Market Landscape
        [Current market state and trends]
        
        ## Competitive Analysis
        [Who else is doing this and how]
        
        ## Target Audience Research
        [Who needs this and why]
        
        ## Opportunity Assessment
        [Market gaps and opportunities]
        
        ## Industry Insights
        [Relevant trends and patterns]
        
        ## Validation Strategies
        [How to test assumptions]
        """
        
        return self._call_openai(prompt, max_tokens=1000)

class ProjectWriterAgent(BaseFlowAgent):
    """Documentation and implementation strategy agent"""
    
    def __init__(self):
        system_prompt = """You are the Project Writer Agent, responsible for creating comprehensive project documentation and implementation strategies.

Your role:
- Synthesize analysis and research into actionable plans
- Create detailed implementation roadmaps
- Document project specifications and requirements
- Write clear, actionable project strategies

Your output should be comprehensive enough to serve as a project blueprint."""

        super().__init__("Project Writer", "Implementation Strategy Specialist", system_prompt)

    def create_strategy(self, analysis: Dict[str, Any], research: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive project strategy from analysis and research"""
        
        prompt = f"""
        Analysis Results: {analysis.get('response', '')}
        Research Results: {research.get('response', '')}
        
        Create a comprehensive project strategy:
        
        ## Executive Summary
        [High-level project overview and value proposition]
        
        ## Implementation Roadmap
        [Step-by-step development plan with phases]
        
        ## Technical Requirements
        [What needs to be built and how]
        
        ## Resource Planning
        [Team, budget, and timeline requirements]
        
        ## Go-to-Market Strategy
        [How to launch and scale]
        
        ## Risk Mitigation
        [How to handle identified risks]
        
        ## Next Steps
        [Immediate actions to get started]
        """
        
        return self._call_openai(prompt, max_tokens=1200)

class ProjectRefinerAgent(BaseFlowAgent):
    """Quality assurance and optimization agent"""
    
    def __init__(self):
        system_prompt = """You are the Project Refiner Agent, responsible for optimizing and finalizing project strategies.

Your role:
- Review and refine project strategies for quality and completeness
- Identify gaps or inconsistencies
- Optimize for clarity and actionability
- Ensure all pieces work together cohesively

Your output should be the polished, final version ready for implementation."""

        super().__init__("Project Refiner", "Strategy Optimization Specialist", system_prompt)

    def refine_strategy(self, strategy: Dict[str, Any], original_vision: str) -> Dict[str, Any]:
        """Refine and optimize the project strategy"""
        
        prompt = f"""
        Original Vision: {original_vision}
        Strategy to Refine: {strategy.get('response', '')}
        
        Refine this strategy for maximum clarity and actionability:
        
        ## Refined Strategy Overview
        [Polished executive summary]
        
        ## Priority Action Items
        [Top 5 most important next steps]
        
        ## Critical Success Factors
        [What absolutely must go right]
        
        ## Resource Optimization
        [How to do this efficiently]
        
        ## Quality Checkpoints
        [How to ensure we stay on track]
        
        ## Final Recommendations
        [Key insights and recommendations]
        
        Make everything clear, actionable, and focused on getting started successfully.
        """
        
        return self._call_openai(prompt, max_tokens=1000)

class FlowAgentManager:
    """Manager for coordinating flow platform agents"""
    
    def __init__(self):
        # Initialize Flow Agents
        self.flow_agent = FlowAgent()
        self.energy_agent = EnergyAgent()
        self.loop_agent = LoopAgent()
        
        # Project Builder Agents
        self.project_analyst = ProjectAnalystAgent()
        self.project_researcher = ProjectResearcherAgent()
        self.project_writer = ProjectWriterAgent()
        self.project_refiner = ProjectRefinerAgent()
        
    def generate_personal_flow(self, energy: str, priority: str, open_loops: str) -> Dict[str, Any]:
        """Generate personal daily flow plan"""
        return self.flow_agent.generate_daily_flow(energy, priority, open_loops)
    
    def build_project_strategy(self, vision: str, project_type: str) -> Dict[str, Any]:
        """Execute complete project building pipeline"""
        try:
            # Step 1: Project Analysis
            analysis = self.project_analyst.analyze_project(vision, project_type)
            
            # Step 2: Market Research
            research = self.project_researcher.research_project(analysis, vision)
            
            # Step 3: Strategy Creation
            strategy = self.project_writer.create_strategy(analysis, research)
            
            # Step 4: Strategy Refinement
            final_strategy = self.project_refiner.refine_strategy(strategy, vision)
            
            return {
                'strategy': final_strategy.get('response', ''),
                'analysis': analysis.get('response', ''),
                'research': research.get('response', ''),
                'tokens_used': (
                    analysis.get('tokens_used', 0) + 
                    research.get('tokens_used', 0) + 
                    strategy.get('tokens_used', 0) + 
                    final_strategy.get('tokens_used', 0)
                ),
                'success': True
            }
            
        except Exception as e:
            logging.error(f"Error in project building pipeline: {str(e)}")
            return {
                'strategy': 'I apologize, but I encountered an error while building your project strategy. Please try again.',
                'success': False,
                'error': str(e)
            }