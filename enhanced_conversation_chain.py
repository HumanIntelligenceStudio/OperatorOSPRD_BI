"""
Enhanced 11-Agent Conversation Chain for Complete C-Suite Advisory Board
Implements: Analyst → Researcher → Writer → CSA → COO → CTO → CFO → CMO → CPO → CIO → Refiner
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from models import db, Conversation, ConversationEntry
from business_package_generator import business_package_generator

class Enhanced11AgentChain:
    """
    Enhanced conversation chain with complete 11-agent C-Suite pipeline
    Guarantees universal business package generation from every input
    """
    
    def __init__(self, conversation_id: str = None):
        if conversation_id:
            self.conversation = Conversation.query.get(conversation_id)
            if not self.conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
        else:
            self.conversation = None
        
        # Complete 11-agent pipeline
        self.agent_pipeline = [
            "Analyst",
            "Researcher", 
            "Writer",
            "CSA",  # Chief Strategy Agent
            "COO",  # Chief Operating Agent
            "CTO",  # Chief Technology Agent
            "CFO",  # Chief Financial Agent
            "CMO",  # Chief Marketing Agent
            "CPO",  # Chief People Agent
            "CIO",  # Chief Intelligence Agent
            "Refiner"
        ]
        
        self.agent_results = {}
        self.processing_start_time = None
        self.business_package = None
    
    @classmethod
    def create_new(cls, initial_input: str, session_id: str = None, user_ip: str = None) -> 'Enhanced11AgentChain':
        """Create new conversation chain with guaranteed business package generation"""
        conversation_id = str(uuid.uuid4())
        
        conversation = Conversation(
            id=conversation_id,
            session_id=session_id or str(uuid.uuid4()),
            initial_input=initial_input,
            user_ip=user_ip or "127.0.0.1",
            is_complete=False,
            current_agent_index=0
        )
        
        db.session.add(conversation)
        db.session.commit()
        
        chain = cls(conversation_id)
        logging.info(f"Created new Enhanced 11-Agent chain: {conversation_id}")
        return chain
    
    def execute_complete_pipeline(self, input_text: str) -> Dict[str, Any]:
        """
        Execute complete 11-agent pipeline with guaranteed business package generation
        
        Returns:
            Dict with complete results including downloadable business package
        """
        try:
            self.processing_start_time = time.time()
            logging.info(f"Starting Enhanced 11-Agent pipeline for: {self.conversation.id}")
            
            # Execute all 11 agents in sequence
            current_input = input_text
            
            for i, agent_name in enumerate(self.agent_pipeline):
                try:
                    logging.info(f"Executing agent {i+1}/11: {agent_name}")
                    
                    # Generate agent response
                    agent_result = self._execute_agent(agent_name, current_input)
                    
                    # Store result
                    self.agent_results[agent_name.lower()] = agent_result["response"]
                    
                    # Create conversation entry
                    self._create_conversation_entry(
                        agent_name=agent_name,
                        input_text=current_input,
                        response=agent_result["response"],
                        processing_time=agent_result.get("processing_time", 0)
                    )
                    
                    # Update current input for next agent
                    current_input = agent_result.get("next_question", current_input)
                    
                    # Update conversation progress
                    self.conversation.current_agent_index = i + 1
                    db.session.commit()
                    
                except Exception as e:
                    logging.error(f"Error in agent {agent_name}: {str(e)}")
                    # Continue with next agent to ensure pipeline completion
                    self.agent_results[agent_name.lower()] = f"Agent processing error: {str(e)}"
            
            # Mark conversation as complete
            self.conversation.is_complete = True
            self.conversation.completion_time = datetime.utcnow()
            db.session.commit()
            
            # Generate universal business package
            self.business_package = business_package_generator.generate_universal_package(
                input_text, 
                self.agent_results
            )
            
            processing_time = time.time() - self.processing_start_time
            
            logging.info(f"Enhanced 11-Agent pipeline completed in {processing_time:.2f}s")
            
            return {
                "success": True,
                "conversation_id": self.conversation.id,
                "agents_completed": len(self.agent_pipeline),
                "processing_time": processing_time,
                "business_package": self.business_package,
                "agent_results": self.agent_results,
                "pipeline_complete": True
            }
            
        except Exception as e:
            logging.error(f"Error in Enhanced 11-Agent pipeline: {str(e)}")
            return {
                "success": False,
                "error": f"Pipeline execution failed: {str(e)}",
                "conversation_id": self.conversation.id if self.conversation else None
            }
    
    def _execute_agent(self, agent_name: str, input_text: str) -> Dict[str, Any]:
        """Execute individual agent with specialized prompts"""
        try:
            from openai import OpenAI
            import os
            
            client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            
            # Get agent-specific system prompt
            system_prompt = self._get_agent_system_prompt(agent_name)
            
            # Generate response
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_text}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            processing_time = time.time() - start_time
            response_text = response.choices[0].message.content
            
            # Generate next question for pipeline continuation
            next_question = self._generate_next_question(agent_name, response_text, input_text)
            
            return {
                "response": response_text,
                "next_question": next_question,
                "processing_time": processing_time,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0
            }
            
        except Exception as e:
            logging.error(f"Error executing agent {agent_name}: {str(e)}")
            return {
                "response": f"Agent {agent_name} encountered an error: {str(e)}",
                "next_question": input_text,
                "processing_time": 0,
                "tokens_used": 0
            }
    
    def _get_agent_system_prompt(self, agent_name: str) -> str:
        """Get specialized system prompt for each agent"""
        prompts = {
            "Analyst": """You are a Senior Business Analyst providing strategic analysis and market intelligence. 
            Focus on business analysis, competitive positioning, and strategic recommendations.
            Provide detailed analysis with actionable insights for executive decision-making.""",
            
            "Researcher": """You are a Strategic Researcher providing comprehensive market research and data analysis.
            Focus on market trends, customer insights, and competitive intelligence.
            Provide data-driven insights with specific examples and industry context.""",
            
            "Writer": """You are a Strategic Communications Writer creating professional business content.
            Focus on clear, executive-level communication with compelling messaging.
            Provide well-structured content suitable for C-suite audiences.""",
            
            "CSA": """You are a Chief Strategy Agent providing strategic direction and competitive intelligence.
            Focus on long-term strategic planning, market positioning, and competitive advantages.
            Provide strategic recommendations with clear rationale and implementation guidance.""",
            
            "COO": """You are a Chief Operating Agent focused on operational excellence and execution.
            Focus on process optimization, resource allocation, and operational efficiency.
            Provide operational recommendations with clear implementation steps.""",
            
            "CTO": """You are a Chief Technology Agent providing technical strategy and innovation guidance.
            Focus on technology architecture, digital transformation, and innovation opportunities.
            Provide technical recommendations with scalability and security considerations.""",
            
            "CFO": """You are a Chief Financial Agent providing financial strategy and analysis.
            Focus on financial planning, investment analysis, and resource optimization.
            Provide financial recommendations with clear ROI and risk assessment.""",
            
            "CMO": """You are a Chief Marketing Agent providing marketing strategy and growth planning.
            Focus on brand strategy, customer acquisition, and market expansion.
            Provide marketing recommendations with clear growth tactics and metrics.""",
            
            "CPO": """You are a Chief People Agent focused on human capital and organizational development.
            Focus on team optimization, culture development, and leadership effectiveness.
            Provide people strategy recommendations with clear implementation approaches.""",
            
            "CIO": """You are a Chief Intelligence Agent providing strategic intelligence and insights synthesis.
            Focus on information synthesis, pattern recognition, and strategic decision support.
            Provide intelligence recommendations with cross-functional insights.""",
            
            "Refiner": """You are a Strategic Refiner providing final synthesis and recommendations.
            Focus on consolidating insights, refining strategies, and providing final recommendations.
            Provide refined strategic guidance with clear action priorities."""
        }
        
        return prompts.get(agent_name, "You are a strategic business advisor providing professional guidance.")
    
    def _generate_next_question(self, current_agent: str, response: str, original_input: str) -> str:
        """Generate next question for pipeline continuation"""
        # Simple question generation based on agent type
        if current_agent in ["Analyst", "Researcher"]:
            return f"Based on this analysis: {response[:200]}..., what strategic recommendations would you provide?"
        elif current_agent in ["CSA", "COO", "CTO", "CFO", "CMO", "CPO", "CIO"]:
            return f"Considering this C-suite perspective: {response[:200]}..., what implementation approach would you recommend?"
        else:
            return f"How would you refine and synthesize these insights: {response[:200]}...?"
    
    def _create_conversation_entry(self, agent_name: str, input_text: str, response: str, processing_time: float):
        """Create conversation entry with enhanced tracking"""
        entry = ConversationEntry(
            conversation_id=self.conversation.id,
            agent_name=agent_name,
            agent_role=f"C-Suite {agent_name}",
            input_text=input_text,
            response_text=response,
            processing_time_seconds=processing_time,
            tokens_used=0,  # Will be updated if available
            model_used="gpt-3.5-turbo",
            api_provider="openai",
            response_length=len(response)
        )
        
        db.session.add(entry)
        db.session.commit()
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get comprehensive conversation summary"""
        return {
            "conversation_id": self.conversation.id,
            "is_complete": self.conversation.is_complete,
            "agents_completed": self.conversation.current_agent_index,
            "total_agents": len(self.agent_pipeline),
            "processing_time": self.conversation.get_duration(),
            "business_package": self.business_package,
            "created_at": self.conversation.created_at.isoformat(),
            "completion_time": self.conversation.completion_time.isoformat() if self.conversation.completion_time else None
        }