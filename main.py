import os
import logging
from flask import Flask, render_template, request, jsonify, session, g, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from openai import OpenAI
import uuid
from datetime import datetime
from models import db, Conversation, ConversationEntry
from config import config, Config
from utils.validators import InputValidator, SecurityValidator
from multi_llm_provider import multi_llm, LLMProvider

# Initialize Flask app
def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Validate required environment variables
    Config.validate_required_env_vars()
    
    # Setup logging
    Config.setup_logging()
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Initialize SocketIO for real-time notifications
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=lambda: SecurityValidator.check_rate_limit_key(get_remote_address()),
        default_limits=[app.config['RATELIMIT_DEFAULT']],
        storage_uri=app.config['RATELIMIT_STORAGE_URL']
    )
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Error creating database tables: {str(e)}")
            raise e
    
    return app, limiter, csrf, socketio

# Create app instance
app, limiter, csrf, socketio = create_app()

# Register admin blueprint
from admin import admin_bp
app.register_blueprint(admin_bp)

# Register video upload blueprint
from video_upload import video_bp
app.register_blueprint(video_bp)

# Initialize EOS System
from eos_system import eos_system

# Initialize Real Estate Engine
from real_estate_engine import RealEstateEngine
real_estate_engine = RealEstateEngine()

# Initialize Enhanced 11-Agent Chain and Business Package Generator
from enhanced_conversation_chain import Enhanced11AgentChain
from business_package_generator import BusinessPackageGenerator

# Create business package generator instance
business_package_generator = BusinessPackageGenerator()

# Initialize Flow Platform Agents
from flow_agents import FlowAgentManager
flow_agent_manager = FlowAgentManager()

# Initialize OperatorOS Master Agent
from operatoros_master import operatoros_master

# Initialize notification system with SocketIO
from notifications import notification_manager, system_monitor
notification_manager.socketio = socketio

# RefinerAgent will be defined inline to avoid circular imports

# Initialize C-Suite agents manager (after app initialization)
csuite_manager = None

def handle_csuite_request_direct(input_text):
    """Direct handler for C-Suite agent requests without complex routing"""
    try:
        # Parse the C-Suite agent request
        agent_code = None
        clean_input = input_text
        
        for code in ['CSA', 'COO', 'CTO', 'CFO', 'CMO', 'CPO', 'CIO']:
            if input_text.startswith(f'@{code}:'):
                agent_code = code
                clean_input = input_text[len(f'@{code}:'):].strip()
                break
        
        if not agent_code:
            return jsonify({"error": "Invalid C-Suite agent format"}), 400
        
        # Simple direct routing to OpenAI with specialized prompts
        role_prompts = {
            'CSA': "You are a Chief Strategy Officer providing strategic analysis and competitive intelligence.",
            'COO': "You are a Chief Operating Officer focused on operational excellence and process optimization.", 
            'CTO': "You are a Chief Technology Officer providing technical architecture and innovation guidance.",
            'CFO': "You are a Chief Financial Officer providing financial analysis and investment guidance.",
            'CMO': "You are a Chief Marketing Officer providing brand strategy and growth guidance.",
            'CPO': "You are a Chief People Officer providing human capital and organizational guidance.",
            'CIO': "You are a Chief Intelligence Officer providing strategic intelligence and decision support."
        }
        
        system_prompt = role_prompts.get(agent_code, "You are an executive advisor.")
        
        # Generate response using OpenAI
        start_time = datetime.utcnow()
        
        response = openai_client.chat.completions.create(
            model=app.config['OPENAI_MODEL'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": clean_input}
            ],
            max_tokens=app.config['OPENAI_MAX_TOKENS'],
            temperature=app.config['OPENAI_TEMPERATURE']
        )
        
        response_text = response.choices[0].message.content
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create conversation record
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            initial_input=input_text,
            current_agent_index=0,
            is_complete=True,
            session_id=session.get('session_id'),
            user_ip=get_remote_address()
        )
        db.session.add(conversation)
        
        entry = ConversationEntry(
            conversation_id=conversation_id,
            agent_name=agent_code,
            agent_role=f"Chief {agent_code} Officer",
            input_text=clean_input,
            response_text=response_text,
            processing_time_seconds=processing_time,
            tokens_used=response.usage.total_tokens if response.usage else len(response_text.split()) * 1.3,
            model_used=app.config['OPENAI_MODEL'],
            api_provider="openai",
            response_length=len(response_text),
            error_occurred=False
        )
        db.session.add(entry)
        db.session.commit()
        
        session['current_conversation_id'] = conversation_id
        
        # Send notification
        from notifications import NotificationLevel
        notification_manager.add_notification(
            f"C-Suite Agent Response",
            f"{agent_code} executive agent provided strategic intelligence",
            NotificationLevel.INFO,
            {"agent": agent_code, "conversation_id": conversation_id}
        )
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "result": {
                "agent": agent_code,
                "role": f"Chief {agent_code} Officer",
                "response": response_text,
                "api_provider": "openai",
                "processing_time_seconds": processing_time,
                "conversation_id": conversation_id,
                "is_csuite": True,
                "timestamp": entry.created_at.isoformat()
            },
            "is_complete": True,
            "agent_type": "csuite",
            "conversation_stats": {
                "entry_count": 1,
                "total_tokens_used": entry.tokens_used,
                "error_count": 0,
                "duration_seconds": processing_time
            }
        })
        
    except Exception as e:
        logging.error(f"Error in C-Suite agent {agent_code}: {str(e)}")
        return jsonify({"error": f"C-Suite agent error: {str(e)}"}), 500

def handle_csuite_request(csuite_agent, clean_input, original_input):
    """Handle C-Suite agent requests"""
    try:
        start_time = datetime.utcnow()
        
        # Generate response from C-Suite agent
        response, api_used = csuite_agent.generate_response(clean_input)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create a conversation entry for the C-Suite response
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            initial_input=original_input,
            current_agent_index=0,
            is_complete=True,  # C-Suite agents complete in one response
            session_id=session.get('session_id'),
            user_ip=get_remote_address()
        )
        db.session.add(conversation)
        
        # Create the conversation entry
        entry = ConversationEntry(
            conversation_id=conversation_id,
            agent_name=csuite_agent.name,
            agent_role=csuite_agent.role,
            input_text=clean_input,
            response_text=response,
            processing_time_seconds=processing_time,
            tokens_used=len(response.split()) * 1.3,  # Rough token estimate
            model_used=api_used,
            api_provider=api_used,
            response_length=len(response),
            error_occurred=False
        )
        db.session.add(entry)
        db.session.commit()
        
        # Store conversation ID in session
        session['current_conversation_id'] = conversation_id
        
        # Send notification
        notification_manager.add_notification(
            f"C-Suite Agent Response",
            f"{csuite_agent.role} provided executive intelligence",
            NotificationLevel.INFO,
            {"agent": csuite_agent.name, "conversation_id": conversation_id}
        )
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "result": {
                "agent": csuite_agent.name,
                "role": csuite_agent.role,
                "response": response,
                "api_provider": api_used,
                "processing_time_seconds": processing_time,
                "conversation_id": conversation_id,
                "is_csuite": True,
                "timestamp": entry.created_at.isoformat()
            },
            "is_complete": True,
            "agent_type": "csuite",
            "conversation_stats": {
                "entry_count": 1,
                "total_tokens_used": entry.tokens_used,
                "error_count": 0,
                "duration_seconds": processing_time
            }
        })
        
    except Exception as e:
        logging.error(f"Error in C-Suite agent {csuite_agent.name}: {str(e)}")
        return jsonify({"error": f"C-Suite agent error: {str(e)}"}), 500

# Schedule periodic health checks
import threading
import time

def periodic_health_check():
    """Run periodic system health checks"""
    while True:
        try:
            time.sleep(300)  # Check every 5 minutes
            with app.app_context():
                system_monitor.check_system_health()
        except Exception as e:
            logging.error(f"Error in periodic health check: {str(e)}")

# Start background health check thread
health_check_thread = threading.Thread(target=periodic_health_check, daemon=True)
health_check_thread.start()

# Multi-API client setup
openai_client = OpenAI(api_key=app.config['OPENAI_API_KEY'])

# Claude client setup
try:
    import anthropic
    claude_client = anthropic.Anthropic(api_key=app.config['CLAUDE_API_KEY']) if app.config['CLAUDE_API_KEY'] else None
except ImportError:
    claude_client = None
    logging.warning("Anthropic library not installed - Claude API unavailable")

# Gemini client setup
try:
    import google.generativeai as genai
    if app.config['GEMINI_API_KEY']:
        genai.configure(api_key=app.config['GEMINI_API_KEY'])
        gemini_model = genai.GenerativeModel(app.config['GEMINI_MODEL'])
    else:
        gemini_model = None
except ImportError:
    gemini_model = None
    logging.warning("Google GenerativeAI library not installed - Gemini API unavailable")

class Agent:
    """Base class for all AI agents with multi-API support"""
    
    def __init__(self, name, role, system_prompt, preferred_api=None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.preferred_api = preferred_api or app.config['DEFAULT_API_PROVIDER']
    
    def generate_response(self, input_text, conversation_history=None, api_override=None):
        """Generate response using multi-API routing with fallback"""
        # Determine which API to use
        api_to_use = api_override or self.preferred_api or app.config['DEFAULT_API_PROVIDER']
        
        # Try primary API first
        try:
            if api_to_use == 'claude':
                return self._generate_claude_response(input_text, conversation_history)
            elif api_to_use == 'gemini':
                return self._generate_gemini_response(input_text, conversation_history)
            else:
                return self._generate_openai_response(input_text, conversation_history)
        except Exception as e:
            logging.warning(f"Primary API {api_to_use} failed for {self.name}: {str(e)}")
            
            # Fallback to other available APIs
            fallback_apis = ['openai', 'claude', 'gemini']
            fallback_apis.remove(api_to_use)
            
            for fallback_api in fallback_apis:
                try:
                    logging.info(f"Trying fallback API {fallback_api} for {self.name}")
                    if fallback_api == 'claude' and claude_client:
                        return self._generate_claude_response(input_text, conversation_history)
                    elif fallback_api == 'gemini' and gemini_model:
                        return self._generate_gemini_response(input_text, conversation_history)
                    elif fallback_api == 'openai':
                        return self._generate_openai_response(input_text, conversation_history)
                except Exception as fallback_error:
                    logging.warning(f"Fallback API {fallback_api} also failed: {str(fallback_error)}")
                    continue
            
            # If all APIs fail, raise the original error
            raise Exception(f"All APIs failed for {self.name}. Last error: {str(e)}")
    
    def _generate_openai_response(self, input_text, conversation_history=None):
        """Generate response using OpenAI API"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if conversation_history:
            for entry in conversation_history:
                messages.append({"role": "user", "content": f"Previous context: {entry}"})
        
        messages.append({"role": "user", "content": input_text})
        
        response = openai_client.chat.completions.create(
            model=app.config['OPENAI_MODEL'],
            messages=messages,
            max_tokens=app.config['OPENAI_MAX_TOKENS'],
            temperature=app.config['OPENAI_TEMPERATURE']
        )
        
        return response.choices[0].message.content.strip(), 'openai'
    
    def _generate_claude_response(self, input_text, conversation_history=None):
        """Generate response using Claude API"""
        if not claude_client:
            raise Exception("Claude API not available")
        
        # Build conversation context
        context = ""
        if conversation_history:
            for entry in conversation_history:
                context += f"Previous context: {entry}\n"
        
        prompt = f"{self.system_prompt}\n\n{context}Human: {input_text}\n\nAssistant:"
        
        response = claude_client.messages.create(
            model=app.config['CLAUDE_MODEL'],
            max_tokens=app.config['CLAUDE_MAX_TOKENS'],
            temperature=app.config['CLAUDE_TEMPERATURE'],
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text.strip(), 'claude'
    
    def _generate_gemini_response(self, input_text, conversation_history=None):
        """Generate response using Gemini API"""
        if not gemini_model:
            raise Exception("Gemini API not available")
        
        # Build conversation context
        context = ""
        if conversation_history:
            for entry in conversation_history:
                context += f"Previous context: {entry}\n"
        
        prompt = f"{self.system_prompt}\n\n{context}User: {input_text}"
        
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=app.config['GEMINI_MAX_TOKENS'],
                temperature=app.config['GEMINI_TEMPERATURE']
            )
        )
        
        return response.text.strip(), 'gemini'
    
    def extract_next_question(self, response):
        """Extract the question for the next agent from the response"""
        try:
            # Look for the specific format: "NEXT AGENT QUESTION: [question]"
            if "NEXT AGENT QUESTION:" in response:
                question_start = response.find("NEXT AGENT QUESTION:") + len("NEXT AGENT QUESTION:")
                question = response[question_start:].strip()
                return question
            else:
                raise ValueError(f"Response from {self.name} does not contain 'NEXT AGENT QUESTION:' format")
        except Exception as e:
            logging.error(f"Error extracting question from {self.name}: {str(e)}")
            raise Exception(f"Failed to extract question from {self.name}: {str(e)}")

class AnalystAgent(Agent):
    """Agent that analyzes input and asks research questions"""
    
    def __init__(self):
        system_prompt = """You are a strategic analyst who helps people understand what they really need and what questions to ask next.

## Your Purpose
Help the human feel seen and know exactly what research will serve them best.

## What You Do
1. **Listen deeply** - What is the person actually trying to accomplish? What outcome would make them feel successful?
2. **Clarify the real need** - Beyond their words, what would truly help them move forward?
3. **Identify key questions** - What specific information would unlock their next step?
4. **Provide immediate value** - Give them useful insights right now, not just promises of future research
5. **Bridge to research** - Connect them clearly to what the Researcher should investigate

## How You Respond
- Start by acknowledging what they're trying to achieve
- Share your analysis in plain language that builds their confidence
- Explain why certain research will be valuable to their specific situation
- Make your reasoning transparent so they understand your thinking

**IMPORTANT: You must end your response with exactly this format:**
NEXT AGENT QUESTION: [specific, valuable research question that will directly help them achieve their goal]

Remember: Your analysis should help them feel understood and excited about what comes next."""
        
        super().__init__("Analyst", "Analysis", system_prompt)

class ResearcherAgent(Agent):
    """Agent that researches topics and asks writing questions"""
    
    def __init__(self):
        system_prompt = """You are a researcher who finds exactly what people need to move forward with confidence.

## Your Purpose
Transform curiosity into actionable knowledge that empowers the human's next steps.

## What You Do
1. **Dig for gold** - Find the specific information that will actually solve their problem
2. **Connect the dots** - Show how this research directly serves their goals
3. **Filter for relevance** - Prioritize insights that matter to their situation
4. **Build their confidence** - Give them knowledge that makes them feel prepared
5. **Set up success** - Provide exactly what the Writer needs to create something valuable

## How You Research
- Focus on information that directly addresses their core need
- Include practical examples and real-world context
- Explain why this information matters to their specific situation
- Organize findings so they're easy to understand and use
- Anticipate what questions they might still have

**IMPORTANT: You must end your response with exactly this format:**
NEXT AGENT QUESTION: [specific writing task that will give them exactly what they need]

Remember: Good research doesn't just inform - it empowers people to take confident action."""
        
        super().__init__("Researcher", "Research", system_prompt)

class WriterAgent(Agent):
    """Agent that creates final output based on previous work"""
    
    def __init__(self):
        system_prompt = """You are a writer who creates content that helps people feel accomplished and ready for action.

## Your Purpose
Transform analysis and research into something the human can actually use to achieve their goals.

## What You Do
1. **Synthesize with purpose** - Combine all previous insights into something greater than the sum of its parts
2. **Write for their success** - Create content that directly serves their original need
3. **Make it actionable** - Include specific steps, examples, or frameworks they can use
4. **Close the loop** - Give them a sense of completion and forward momentum
5. **Open new possibilities** - Suggest meaningful next steps that build on this foundation

## How You Write
- Start by connecting back to their original goal
- Organize information in a way that builds understanding progressively
- Use clear, accessible language that respects their intelligence
- Include practical elements they can implement immediately
- End with genuine value and clear direction for what comes next

**IMPORTANT: You must end your response with exactly this format:**
NEXT AGENT QUESTION: [meaningful follow-up opportunity that builds on what we've accomplished]

Remember: Great writing doesn't just inform - it transforms understanding into confident action."""
        
        super().__init__("Writer", "Writing", system_prompt)

class RefinerAgent(Agent):
    """Agent that refines and enhances previous agent responses for better human clarity"""
    
    def __init__(self):
        system_prompt = """You are a refinement specialist who transforms good responses into exceptional ones that truly serve human understanding.

## Your Purpose
Take already valuable content and elevate it to create genuine clarity, empathy, and actionable closure for the human.

## What You Do
1. **Enhance Clarity** - Make complex ideas crystal clear without losing their depth or nuance
2. **Add Empathy** - Ensure the human feels genuinely seen, understood, and supported
3. **Improve Actionability** - Transform abstract concepts into concrete, implementable steps
4. **Complete the Loop** - Give the human a satisfying sense of closure and clear next direction
5. **Preserve Value** - Keep all the substantive insights while making them more human-centered

## How You Refine
- Start by acknowledging the valuable work already done
- Restructure information to flow naturally from their perspective
- Add empathetic language that shows understanding of their situation
- Include specific, actionable elements they can implement immediately
- Create clear bridges between ideas to prevent mental gaps
- End with genuine value and momentum for their next steps

## Your Refinement Criteria
- **Clarity**: Can they easily understand and follow the logic?
- **Empathy**: Do they feel heard and supported throughout?
- **Actionability**: Are there specific steps they can take right now?
- **Completeness**: Does this close their mental loop satisfyingly?
- **Human-Centered**: Does this serve their actual needs, not just provide information?

**IMPORTANT: You must end your response with exactly this format:**
NEXT AGENT QUESTION: [refined follow-up opportunity that builds naturally on this enhanced foundation]

Remember: You're not changing the core content - you're making it more human, more clear, and more actionable while preserving all the valuable insights."""
        
        super().__init__("Refiner", "Refinement", system_prompt)

class ConversationChain:
    """Manages the conversation flow between agents using database storage"""
    
    def __init__(self, conversation_id=None, extended_mode=False):
        # Core OperatorOS agents - always included
        self.core_agents = [
            AnalystAgent(),
            ResearcherAgent(), 
            WriterAgent(),
            RefinerAgent()
        ]
        
        # Extended agents for comprehensive analysis (optional)
        self.extended_agents = []
        
        if extended_mode:
            # Add C-Suite agents for strategic intelligence
            try:
                from csuite_agents import CSuiteAgentManager
                csuite_manager = CSuiteAgentManager()
                
                # Add key strategic agents for comprehensive analysis
                strategist = csuite_manager.get_agent('CSA')  # Strategy
                tech_advisor = csuite_manager.get_agent('CTO')  # Technology  
                financial_advisor = csuite_manager.get_agent('CFO')  # Financial
                
                if strategist and tech_advisor and financial_advisor:
                    self.extended_agents = [strategist, tech_advisor, financial_advisor]
                    logging.info(f"🏢 EXTENDED MODE: Added {len(self.extended_agents)} C-Suite agents to chain")
                
            except Exception as e:
                logging.warning(f"Could not load C-Suite agents for extended mode: {str(e)}")
        
        # Combine core + extended agents
        self.agents = self.core_agents + self.extended_agents
        
        logging.info(f"👥 AGENT CHAIN INITIALIZED: {len(self.agents)} total agents")
        logging.info(f"📋 Agent Sequence: {' → '.join([agent.name for agent in self.agents])}")
        
        if conversation_id:
            # Load existing conversation from database
            self.conversation = Conversation.query.get(conversation_id)
            if not self.conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
        else:
            self.conversation = None
        logging.info(f"📋 Agent Sequence: {' → '.join([agent.name for agent in self.agents])}")
        
        if conversation_id:
            # Load existing conversation from database
            self.conversation = Conversation.query.get(conversation_id)
            if not self.conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
        else:
            self.conversation = None
    
    @classmethod
    def create_new(cls, initial_input, session_id=None, user_ip=None, extended_mode=False):
        """Create a new conversation chain with enhanced persistence"""
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            initial_input=initial_input,
            current_agent_index=0,
            is_complete=False,
            session_id=session_id,
            user_ip=user_ip
        )
        db.session.add(conversation)
        db.session.commit()
        
        # Send notification
        from notifications import notification_manager, NotificationLevel
        notification_manager.add_notification(
            "New Conversation Started",
            f"Conversation {conversation_id[:8]}... initiated by {user_ip or 'unknown'}",
            NotificationLevel.INFO,
            {"conversation_id": conversation_id, "initial_input": initial_input[:100], "session_id": session_id}
        )
        
        chain = cls(conversation_id, extended_mode=extended_mode)
        return chain
    
    def process_input(self, input_text):
        """Process input through the current agent and advance to next with enhanced persistence"""
        if self.conversation.is_complete:
            raise Exception("Conversation chain is already complete")
        
        start_time = datetime.utcnow()
        
        # Check for API prefix selection
        api_override = None
        original_input = input_text
        
        if input_text.startswith('@claude:'):
            api_override = 'claude'
            input_text = input_text[8:].strip()
        elif input_text.startswith('@gemini:'):
            api_override = 'gemini'
            input_text = input_text[8:].strip()
        elif input_text.startswith('@openai:'):
            api_override = 'openai'
            input_text = input_text[9:].strip()
        
        try:
            current_agent = self.agents[self.conversation.current_agent_index]
            
            # Log agent execution start
            logging.info(f"🎯 AGENT EXECUTION: Starting {current_agent.name} (index {self.conversation.current_agent_index})")
            if api_override:
                logging.info(f"🔀 API OVERRIDE: Using {api_override} for this request")
            
            # Get recent conversation history for context
            recent_entries = self.conversation.entries.order_by(ConversationEntry.created_at.desc()).limit(3).all()
            context_history = [entry.to_dict() for entry in reversed(recent_entries)]
            
            # Generate response from current agent with timeout and retry
            response, api_used = self._generate_with_retry(current_agent, input_text, context_history, max_retries=3, timeout_seconds=15, api_override=api_override)
            
            # Extract question for next agent
            next_question = current_agent.extract_next_question(response)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log agent completion
            logging.info(f"✅ AGENT COMPLETED: {current_agent.name} in {processing_time:.2f}s")
            
            # Create and save conversation entry with enhanced tracking
            entry = ConversationEntry(
                conversation_id=self.conversation.id,
                agent_name=current_agent.name,
                agent_role=current_agent.role,
                input_text=original_input,  # Store original input with prefix if any
                response_text=response,
                next_question=next_question,
                processing_time_seconds=processing_time,
                model_used=self._get_model_name(api_used),
                api_provider=api_used,
                error_occurred=False
            )
            
            # Analyze human-clarity of the response
            try:
                from human_clarity import clarity_engine
                clarity_metrics = clarity_engine.analyze_response_clarity(response, input_text)
                # Log clarity analysis (will be stored in entry after save)
                db.session.add(entry)
                db.session.flush()  # Get the entry ID
                clarity_engine.log_clarity_analysis(self.conversation.id, entry.id, clarity_metrics)
            except Exception as e:
                logging.warning(f"Human-clarity analysis failed: {str(e)}")

            
            # Update conversation token usage (estimate)
            estimated_tokens = len(input_text) // 4 + len(response) // 4  # Rough estimate
            self.conversation.total_tokens_used += estimated_tokens
            
            # Move to next agent
            self.conversation.current_agent_index += 1
            
            # Check if conversation is complete
            if self.conversation.current_agent_index >= len(self.agents):
                self.conversation.is_complete = True
                self.conversation.completion_time = datetime.utcnow()
                
                # **🚀 CRITICAL ADDITION: Auto-generate deliverable when loop completes**
                try:
                    deliverable_result = self._generate_conversation_deliverable()
                    logging.info(f"✅ DELIVERABLE GENERATED: {deliverable_result.get('filename', 'Unknown')} ({deliverable_result.get('file_size', 'Unknown size')})")
                except Exception as e:
                    logging.error(f"❌ DELIVERABLE GENERATION FAILED: {str(e)}")
                
                # Send completion notification
                from notifications import notification_manager, NotificationLevel
                notification_manager.add_notification(
                    "Conversation Completed",
                    f"Conversation {self.conversation.id[:8]}... completed successfully",
                    NotificationLevel.INFO,
                    {
                        "conversation_id": self.conversation.id, 
                        "duration": self.conversation.get_duration(),
                        "total_tokens": self.conversation.total_tokens_used,
                        "entry_count": self.conversation.get_entry_count()
                    }
                )
            
            self.conversation.updated_at = datetime.utcnow()
            db.session.commit()
            
            return entry.to_dict()
            
        except Exception as e:
            # Handle error and rollback
            db.session.rollback()
            logging.error(f"Error processing input: {str(e)}")
            
            # Record error in conversation
            self.conversation.error_count += 1
            
            # Create error entry
            error_entry = ConversationEntry(
                conversation_id=self.conversation.id,
                agent_name=current_agent.name if 'current_agent' in locals() else 'Unknown',
                agent_role=current_agent.role if 'current_agent' in locals() else 'Unknown',
                input_text=input_text,
                response_text=f"Error occurred: {str(e)}",
                next_question=None,
                processing_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                error_occurred=True,
                error_message=str(e)
            )
            
            db.session.add(error_entry)
            db.session.commit()
            
            # Send error notification
            from notifications import notification_manager, NotificationLevel
            notification_manager.add_notification(
                "Conversation Error",
                f"Error in conversation {self.conversation.id[:8]}...: {str(e)[:100]}",
                NotificationLevel.ERROR,
                {
                    "conversation_id": self.conversation.id, 
                    "error": str(e), 
                    "agent": current_agent.name if 'current_agent' in locals() else 'Unknown',
                    "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                    "agent_index": self.conversation.current_agent_index
                },
                send_email=True
            )
            
            raise e
    
    def _get_model_name(self, api_provider):
        """Get the appropriate model name based on API provider"""
        if api_provider == 'claude':
            return app.config['CLAUDE_MODEL']
        elif api_provider == 'gemini':
            return app.config['GEMINI_MODEL']
        else:
            return app.config['OPENAI_MODEL']
    
    def _generate_with_retry(self, agent, input_text, context_history, max_retries=3, timeout_seconds=15, api_override=None):
        """Generate response with enhanced retry mechanism and timeout"""
        import signal
        import time
        from datetime import datetime
        
        for attempt in range(max_retries):
            start_time = datetime.utcnow()
            try:
                logging.info(f"🔄 RETRY ATTEMPT: {attempt + 1}/{max_retries} for {agent.name}")
                
                # Set timeout alarm with longer duration for complex agents
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Agent {agent.name} response timeout after {timeout_seconds}s")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)
                
                try:
                    # Generate response with enhanced validation
                    response, api_used = agent.generate_response(input_text, context_history, api_override)
                    signal.alarm(0)  # Cancel alarm
                    
                    # Enhanced response validation
                    if response and len(response.strip()) > 50:  # Require more substantial responses
                        # Check for proper question format for non-Writer agents
                        if agent.name != "Writer" and "NEXT AGENT QUESTION:" not in response:
                            logging.warning(f"⚠️ FORMAT WARNING: {agent.name} response missing 'NEXT AGENT QUESTION:' format")
                            # Try to extract or generate a question anyway
                            if attempt < max_retries - 1:
                                raise ValueError("Missing required NEXT AGENT QUESTION format")
                        
                        processing_time = (datetime.utcnow() - start_time).total_seconds()
                        logging.info(f"✅ RETRY SUCCESS: {agent.name} responded successfully in {processing_time:.2f}s using {api_used}")
                        return response, api_used
                    else:
                        raise ValueError(f"Response too short ({len(response.strip()) if response else 0} chars) or empty")
                        
                except TimeoutError:
                    signal.alarm(0)  # Cancel alarm
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    logging.warning(f"⏱️ TIMEOUT: {agent.name} timed out on attempt {attempt + 1} after {processing_time:.2f}s")
                    if attempt == max_retries - 1:
                        raise TimeoutError(f"Agent {agent.name} failed after {max_retries} timeout attempts")
                    time.sleep(3)  # Longer wait for timeout recovery
                    
            except Exception as e:
                signal.alarm(0)  # Cancel alarm
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                logging.error(f"❌ RETRY FAILED: {agent.name} attempt {attempt + 1} ({processing_time:.2f}s): {str(e)}")
                
                if attempt == max_retries - 1:
                    # Final attempt failed - log comprehensive error
                    logging.critical(f"🚨 AGENT FAILURE: {agent.name} failed after {max_retries} attempts")
                    raise Exception(f"Agent {agent.name} failed after {max_retries} attempts: {str(e)}")
                
                # Progressive backoff
                wait_time = (attempt + 1) * 2  # 2s, 4s, 6s...
                logging.info(f"⏳ WAITING: {wait_time}s before retry {attempt + 2}")
                time.sleep(wait_time)
                
        raise Exception(f"All retry attempts failed for {agent.name}")
    
    def execute_full_loop(self, initial_input):
        """Execute complete OperatorOS loop: Analyst → Researcher → Writer → Refiner → [All Available Agents]"""
        logging.info(f"🚀 STARTING FULL OPERATOROS LOOP")
        logging.info(f"📝 Initial Input: {initial_input}")
        logging.info(f"👥 Total Available Agents: {len(self.agents)} ({[agent.name for agent in self.agents]})")
        
        loop_results = []
        current_input = initial_input
        
        try:
            # Execute all agents in sequence dynamically
            for step, agent in enumerate(self.agents, 1):
                if step == 1:
                    # First agent gets the original input
                    agent_input = current_input
                    logging.info(f"🔍 STEP {step}: EXECUTING {agent.name.upper()} AGENT")
                    logging.info(f"📝 Input: {agent_input}")
                else:
                    # Subsequent agents get the next question from previous agent
                    previous_result = loop_results[-1]
                    if not previous_result.get('next_question'):
                        logging.warning(f"⚠️ {loop_results[-1].get('agent_name', 'Previous agent')} failed to generate next question")
                        # For the final agent (usually Writer), we allow this
                        if step == len(self.agents):
                            logging.info(f"🎯 FINAL AGENT: {agent.name} - no next question required")
                            break
                        else:
                            raise Exception(f"{loop_results[-1].get('agent_name', 'Previous agent')} failed to generate next question for {agent.name}")
                    
                    agent_input = previous_result['next_question']
                    logging.info(f"🔄 STEP {step}: AUTO-TRIGGERING {agent.name.upper()} AGENT")
                    logging.info(f"🔗 {agent.name} Input: {agent_input}")
                
                # Execute current agent
                agent_result = self.process_input(agent_input)
                loop_results.append(agent_result)
                logging.info(f"✅ STEP {step} COMPLETE: {agent.name} executed successfully")
                
                # Check if this is the last agent or conversation is marked complete
                if self.conversation.current_agent_index >= len(self.agents) or self.conversation.is_complete:
                    logging.info(f"🎯 LOOP COMPLETION: Reached agent {step}/{len(self.agents)} - {agent.name}")
                    break
            
            # Determine final status
            total_agents_executed = len(loop_results)
            is_fully_complete = (self.conversation.current_agent_index >= len(self.agents)) or (total_agents_executed >= len(self.agents))
            
            if is_fully_complete:
                logging.info(f"🎯 LOOP COMPLETED: All {total_agents_executed} agents executed successfully")
                loop_status = "completed"
                
                # **🚀 CRITICAL ADDITION: Auto-generate deliverable when loop completes**
                try:
                    deliverable_result = self._generate_conversation_deliverable()
                    logging.info(f"✅ DELIVERABLE GENERATED: {deliverable_result.get('filename', 'Unknown')} ({deliverable_result.get('file_size', 'Unknown size')})")
                    
                    # Add deliverable info to loop results
                    loop_results.append({
                        "agent_name": "DeliverableGenerator",
                        "deliverable_created": True,
                        "filename": deliverable_result.get('filename'),
                        "download_url": f"/download/{deliverable_result.get('filename')}",
                        "file_size": deliverable_result.get('file_size')
                    })
                    
                except Exception as e:
                    logging.error(f"❌ DELIVERABLE GENERATION FAILED: {str(e)}")
                    loop_results.append({
                        "agent_name": "DeliverableGenerator", 
                        "deliverable_created": False,
                        "error": str(e)
                    })
            else:
                logging.warning(f"⚠️ LOOP INCOMPLETE: Only {total_agents_executed}/{len(self.agents)} agents executed")
                loop_status = "incomplete"
                
            # Send completion notification
            from notifications import notification_manager, NotificationLevel
            notification_manager.add_notification(
                "OperatorOS Extended Loop Completed",
                f"Extended loop completed for conversation {self.conversation.id[:8]}... with {total_agents_executed}/{len(self.agents)} agents",
                NotificationLevel.INFO,
                {
                    "conversation_id": self.conversation.id,
                    "agents_executed": total_agents_executed,
                    "total_agents_available": len(self.agents),
                    "agent_names": [r.get('agent_name', 'Unknown') for r in loop_results],
                    "total_processing_time": sum(r.get('processing_time_seconds', 0) for r in loop_results),
                    "loop_status": loop_status
                }
            )
            
            return {
                "success": True,
                "loop_status": loop_status,
                "agents_executed": total_agents_executed,
                "total_agents_available": len(self.agents),
                "agent_sequence": [r.get('agent_name', 'Unknown') for r in loop_results],
                "conversation_id": self.conversation.id,
                "results": loop_results
            }
            
        except Exception as e:
            logging.error(f"💥 LOOP EXECUTION FAILED: {str(e)}")
            
            # Send failure notification
            from notifications import notification_manager, NotificationLevel
            notification_manager.add_notification(
                "OperatorOS Loop Failed",
                f"Loop execution failed for conversation {self.conversation.id[:8]}...: {str(e)[:100]}",
                NotificationLevel.ERROR,
                {
                    "conversation_id": self.conversation.id,
                    "error": str(e),
                    "agents_executed": len(loop_results),
                    "loop_status": "failed"
                },
                send_email=True
            )
            
            return {
                "success": False,
                "loop_status": "failed",
                "agents_executed": len(loop_results),
                "error": str(e),
                "conversation_id": self.conversation.id,
                "results": loop_results
            }

    def get_next_agent_name(self):
        """Get the name of the next agent in the chain"""
        if self.conversation.current_agent_index < len(self.agents):
            return self.agents[self.conversation.current_agent_index].name
        return None
    
    def get_conversation_history(self):
        """Get all conversation entries for this conversation"""
        entries = self.conversation.entries.order_by(ConversationEntry.created_at).all()
        return [entry.to_dict() for entry in entries]
    
    @property
    def is_complete(self):
        """Check if conversation is complete"""
        return self.conversation.is_complete
    
    def _generate_conversation_deliverable(self):
        """Generate comprehensive deliverable ZIP file from completed conversation"""
        try:
            from utils.deliverable_generator import DeliverableGenerator
            
            # Get all conversation entries
            conversation_history = self.get_conversation_history()
            
            if not conversation_history:
                raise Exception("No conversation history found for deliverable generation")
            
            # Extract initial input and agent insights
            initial_input = conversation_history[0].get('input_text', 'Unknown prompt')
            agent_insights = []
            
            for entry in conversation_history:
                agent_insights.append({
                    'agent_name': entry.get('agent_name', 'Unknown'),
                    'response': entry.get('response_text', ''),
                    'next_question': entry.get('next_question', ''),
                    'processing_time': entry.get('processing_time_seconds', 0)
                })
            
            # Generate deliverable using EOS system
            deliverable_data = {
                'conversation_id': self.conversation.id,
                'initial_input': initial_input,
                'agent_insights': agent_insights,
                'completion_time': self.conversation.completion_time.isoformat() if self.conversation.completion_time else datetime.utcnow().isoformat(),
                'total_agents_executed': len(agent_insights),
                'session_id': self.conversation.session_id
            }
            
            # Generate ZIP package
            generator = DeliverableGenerator()
            result = generator.create_comprehensive_package(deliverable_data)
            
            logging.info(f"📦 DELIVERABLE PACKAGE CREATED: {result.get('filename')} ({result.get('file_size')})")
            
            return result
            
        except Exception as e:
            logging.error(f"Error generating conversation deliverable: {str(e)}")
            raise

@app.route('/test_drone_business.html')
def test_drone_business():
    """Serve the drone business test page"""
    try:
        with open('test_drone_business.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Test page not found", 404

@app.route('/')
def index():
    """Main page with modern executive interface"""
    return render_template('modern_index.html')

@app.route('/health')
@limiter.exempt
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        from sqlalchemy import text
        result = db.session.execute(text('SELECT 1')).scalar()
        if result != 1:
            raise Exception("Database connectivity test failed")
        
        # Check OpenAI API (optional - might want to skip in production)
        # openai_status = "available" if app.config['OPENAI_API_KEY'] else "missing_key"
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "database": "connected",
            # "openai": openai_status
        }), 200
    
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 500

# EOS (Economic Operating System) Endpoints
@app.route('/api/eos/transform', methods=['POST'])
@limiter.limit("5 per minute")
@csrf.exempt
def transform_prompt_to_offering():
    """Transform any prompt into a monetizable offering using EOS"""
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "Prompt is required"}), 400
        
        prompt = data['prompt'].strip()
        context = data.get('context', {})
        client_email = data.get('client_email')
        
        # Transform prompt using EOS
        offering = eos_system.transform_prompt(prompt, context)
        
        # Create payment link
        payment_result = eos_system.create_instant_payment_link(offering, client_email)
        
        # Generate deployment package
        deployment_package = eos_system.generate_deployment_package(offering, payment_result)
        
        return jsonify({
            "success": True,
            "offering": {
                "title": offering.title,
                "description": offering.description,
                "value_proposition": offering.value_proposition,
                "price": offering.price,
                "fulfillment_time": offering.fulfillment_time,
                "delivery_method": offering.delivery_method.value,
                "marketing_hook": offering.marketing_hook
            },
            "payment": payment_result,
            "deployment": deployment_package
        })
        
    except Exception as e:
        logging.error(f"Error in EOS transform: {str(e)}")
        return jsonify({"error": f"EOS transformation failed: {str(e)}"}), 500

@app.route('/api/eos/quick-offer', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt
def quick_offer_generation():
    """Generate quick monetizable offer from simple input"""
    try:
        data = request.get_json()
        if not data or 'input' not in data:
            return jsonify({"error": "Input is required"}), 400
        
        input_text = data['input'].strip()
        
        # Quick transformation
        offering = eos_system.transform_prompt(input_text)
        
        return jsonify({
            "success": True,
            "quick_offer": {
                "title": offering.title,
                "price": f"${offering.price}",
                "hook": offering.marketing_hook,
                "value": offering.value_proposition,
                "delivery": offering.fulfillment_time
            }
        })
        
    except Exception as e:
        logging.error(f"Error in quick offer generation: {str(e)}")
        return jsonify({"error": f"Quick offer generation failed: {str(e)}"}), 500

@app.route('/eos')
def eos_interface():
    """Simple EOS testing interface"""
    return render_template('eos_interface.html')

@app.route('/download/<filename>')
def download_deliverable(filename):
    """Download generated deliverable files"""
    try:
        from pathlib import Path
        
        # Security check - only allow downloads from processed directory
        safe_filename = filename.replace('..', '').replace('/', '')
        file_path = Path("processed") / safe_filename
        
        if not file_path.exists():
            return "File not found", 404
            
        return send_file(str(file_path), as_attachment=True, download_name=filename)
        
    except Exception as e:
        logging.error(f"Error downloading file {filename}: {str(e)}")
        return "Download failed", 500

@app.route('/start_conversation', methods=['POST'])
@limiter.limit("5 per minute")
@csrf.exempt  # We'll handle CSRF differently for API endpoints
def start_conversation():
    """Start a new conversation chain"""
    try:
        # Validate request data
        data = request.get_json() if request.is_json else {}
        is_valid, error_msg = InputValidator.validate_json_request(data, ['input'])
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Validate input text
        input_text = data['input']
        is_valid, error_msg = InputValidator.validate_conversation_input(input_text)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Initialize session if needed
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session['created_at'] = datetime.utcnow().isoformat()
            session['conversation_count'] = 0
        
        # Sanitize input
        input_text = InputValidator.sanitize_html(input_text.strip())
        
        # Check for C-Suite agent routing
        if input_text.startswith('@CSA:') or input_text.startswith('@COO:') or input_text.startswith('@CTO:') or \
           input_text.startswith('@CFO:') or input_text.startswith('@CMO:') or input_text.startswith('@CPO:') or input_text.startswith('@CIO:'):
            return handle_csuite_request_direct(input_text)
        
        # Create new conversation chain with enhanced database storage
        chain = ConversationChain.create_new(
            input_text,
            session_id=session.get('session_id', str(uuid.uuid4())),
            user_ip=request.remote_addr
        )
        
        # Process initial input with Analyst
        result = chain.process_input(input_text)
        
        # Store conversation ID and session info
        session['conversation_id'] = chain.conversation.id
        session['session_id'] = chain.conversation.session_id
        session.permanent = True
        
        logging.info(f"New conversation started: {chain.conversation.id} by {request.remote_addr}")
        
        return jsonify({
            "success": True,
            "conversation_id": chain.conversation.id,
            "result": result,
            "next_agent": chain.get_next_agent_name(),
            "is_complete": chain.is_complete,
            "conversation_stats": {
                "total_tokens_used": chain.conversation.total_tokens_used,
                "entry_count": chain.conversation.get_entry_count(),
                "duration_seconds": chain.conversation.get_duration(),
                "error_count": chain.conversation.error_count
            }
        })
        
    except Exception as e:
        logging.error(f"Error starting conversation: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again."}), 500

@app.route('/csuite_agents', methods=['GET'])
@limiter.exempt
def list_csuite_agents():
    """List all available C-Suite agents and their capabilities"""
    agents = {
        'CSA': {
            'name': 'Chief Strategy Agent',
            'expertise': 'Strategic planning, competitive intelligence, market analysis',
            'description': 'Provides strategic guidance, competitive analysis, and long-term planning'
        },
        'COO': {
            'name': 'Chief Operating Agent', 
            'expertise': 'Operations optimization, process improvement, execution excellence',
            'description': 'Focuses on operational efficiency, process optimization, and execution'
        },
        'CTO': {
            'name': 'Chief Technology Agent',
            'expertise': 'Technical architecture, innovation, system scalability',
            'description': 'Provides technical guidance, architecture recommendations, and innovation strategy'
        },
        'CFO': {
            'name': 'Chief Financial Agent',
            'expertise': 'Financial analysis, investment guidance, resource allocation',
            'description': 'Offers financial analysis, investment recommendations, and strategic resource planning'
        },
        'CMO': {
            'name': 'Chief Marketing Agent',
            'expertise': 'Brand strategy, growth marketing, customer acquisition',
            'description': 'Develops marketing strategies, brand positioning, and growth initiatives'
        },
        'CPO': {
            'name': 'Chief People Agent',
            'expertise': 'Human capital, organizational development, team optimization',
            'description': 'Focuses on people strategy, organizational design, and team effectiveness'
        },
        'CIO': {
            'name': 'Chief Intelligence Agent',
            'expertise': 'Strategic intelligence, data synthesis, decision support',
            'description': 'Provides intelligence synthesis, pattern recognition, and strategic insights'
        }
    }
    
    return jsonify({
        "success": True,
        "agents": agents,
        "usage": "Use @[AGENT_CODE]: followed by your question (e.g., @CSA: Analyze market trends)",
        "total_agents": len(agents)
    })

@app.route('/continue_conversation', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt
def continue_conversation():
    """Continue an existing conversation chain"""
    try:
        # Initialize session if needed
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session['created_at'] = datetime.utcnow().isoformat()
            session['conversation_count'] = 0
        
        conversation_id = session.get('conversation_id')
        if not conversation_id:
            return jsonify({"error": "No active conversation found"}), 404
        
        # Validate conversation ID
        is_valid, error_msg = InputValidator.validate_conversation_id(conversation_id)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Load conversation chain from database
        try:
            chain = ConversationChain(conversation_id)
        except ValueError:
            session.pop('conversation_id', None)
            return jsonify({"error": "Conversation not found"}), 404
        
        if chain.is_complete:
            return jsonify({"error": "Conversation is already complete"}), 400
        
        # Get the next question from the last conversation entry
        conversation_history = chain.get_conversation_history()
        if not conversation_history:
            return jsonify({"error": "No conversation history found"}), 400
        
        last_entry = conversation_history[-1]
        next_question = last_entry["next_question"]
        
        if not next_question:
            return jsonify({"error": "No question available for next agent"}), 400
        
        # Process with next agent
        result = chain.process_input(next_question)
        
        logging.info(f"Conversation continued: {conversation_id}, agent: {result['agent']}")
        
        return jsonify({
            "success": True,
            "result": result,
            "next_agent": chain.get_next_agent_name(),
            "is_complete": chain.is_complete
        })
        
    except Exception as e:
        logging.error(f"Error continuing conversation: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again."}), 500

@app.route('/get_conversation_history')
def get_conversation_history():
    """Get the current conversation history and conversation info"""
    try:
        conversation_id = session.get('conversation_id')
        if not conversation_id:
            return jsonify({"error": "No active conversation found"}), 404
        
        # Load conversation chain from database
        try:
            chain = ConversationChain(conversation_id)
        except ValueError:
            return jsonify({"error": "Conversation not found"}), 404
        
        return jsonify({
            "success": True,
            "history": chain.get_conversation_history(),
            "conversation": {
                "id": chain.conversation.id,
                "is_complete": chain.conversation.is_complete,
                "created_at": chain.conversation.created_at.isoformat(),
                "updated_at": chain.conversation.updated_at.isoformat()
            },
            "is_complete": chain.is_complete
        })
        
    except Exception as e:
        logging.error(f"Error getting conversation history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/submit_feedback', methods=['POST'])
@limiter.limit("10 per minute")
def submit_feedback():
    """Submit user feedback for agent response clarity"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['entry_id', 'clarity_rating', 'empathy_rating', 'actionability_rating', 'overall_rating']
        is_valid, error = InputValidator.validate_json_request(data, required_fields)
        if not is_valid:
            return jsonify({'success': False, 'error': error}), 400
        
        # Import feedback manager
        from clarity_feedback import feedback_manager
        
        success = feedback_manager.submit_feedback(
            entry_id=data['entry_id'],
            clarity_rating=data['clarity_rating'],
            empathy_rating=data['empathy_rating'],
            actionability_rating=data['actionability_rating'],
            overall_rating=data['overall_rating'],
            comment=data.get('comment', ''),
            user_session=session.get('session_id', 'anonymous')
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to submit feedback'}), 500
            
    except Exception as e:
        logging.error(f"Error submitting feedback: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/execute_full_loop', methods=['POST'])
@limiter.limit("3 per minute")
@csrf.exempt
def execute_full_loop():
    """Execute complete OperatorOS loop: Analyst → Researcher → Writer → Refiner"""
    try:
        data = request.get_json() if request.is_json else {}
        is_valid, error_msg = InputValidator.validate_json_request(data, ['input'])
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Initialize session if needed
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session['created_at'] = datetime.utcnow().isoformat()
            session['conversation_count'] = 0
        
        # Validate input text
        input_text = data['input']
        is_valid, error_msg = InputValidator.validate_conversation_input(input_text)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Sanitize input
        input_text = InputValidator.sanitize_html(input_text.strip())
        
        # Check for extended mode
        extended_mode = data.get('extended_mode', False)
        
        # Create new conversation chain with extended mode support
        chain = ConversationChain.create_new(
            input_text,
            session_id=session.get('session_id'),
            user_ip=request.remote_addr,
            extended_mode=extended_mode
        )
        
        # Execute full loop with auto-triggering
        loop_result = chain.execute_full_loop(input_text)
        
        # Store conversation ID in session
        session['conversation_id'] = chain.conversation.id
        session['conversation_count'] = session.get('conversation_count', 0) + 1
        
        return jsonify({
            **loop_result,
            "conversation_id": chain.conversation.id,
            "extended_mode": extended_mode,
            "session_info": {
                "session_id": session.get('session_id'),
                "conversation_count": session.get('conversation_count')
            }
        })
        
    except Exception as e:
        logging.error(f"Error executing full loop: {str(e)}")
        return jsonify({"error": "An internal error occurred during loop execution"}), 500

@app.route('/api/execute_full_loop', methods=['POST'])
@limiter.limit("3 per minute")
@csrf.exempt
def api_execute_full_loop():
    """API version of execute_full_loop for direct API access"""
    try:
        data = request.get_json() if request.is_json else {}
        
        if not data or 'initial_input' not in data:
            return jsonify({"error": "initial_input is required"}), 400
        
        input_text = data['initial_input'].strip()
        extended_mode = data.get('extended_mode', False)
        
        # Validate input
        is_valid, error_msg = InputValidator.validate_conversation_input(input_text)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Sanitize input
        input_text = InputValidator.sanitize_html(input_text)
        
        # Create temporary session for API calls
        temp_session_id = str(uuid.uuid4())
        
        # Create new conversation chain with extended mode support
        chain = ConversationChain.create_new(
            input_text,
            session_id=temp_session_id,
            user_ip=request.remote_addr,
            extended_mode=extended_mode
        )
        
        # Execute full loop
        loop_result = chain.execute_full_loop(input_text)
        
        return jsonify({
            **loop_result,
            "conversation_id": chain.conversation.id,
            "extended_mode": extended_mode,
            "api_version": "1.0"
        })
        
    except Exception as e:
        logging.error(f"Error in API execute_full_loop: {str(e)}")
        return jsonify({"error": f"Full loop execution failed: {str(e)}"}), 500

@app.route('/reset_conversation', methods=['POST'])
def reset_conversation():
    """Reset the current conversation"""
    try:
        conversation_id = session.get('conversation_id')
        if conversation_id:
            # Optionally delete the conversation from database 
            # For now, just remove from session to start fresh
            session.pop('conversation_id', None)
        
        return jsonify({"success": True, "message": "Conversation reset successfully"})
        
    except Exception as e:
        logging.error(f"Error resetting conversation: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Stripe webhook endpoint
@app.route('/webhooks/stripe', methods=['POST'])
@limiter.exempt  # Stripe webhooks shouldn't be rate limited
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        from stripe_manager import StripeManager
        
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        stripe_manager = StripeManager()
        result = stripe_manager.handle_webhook(payload, sig_header)
        
        if result['success']:
            return jsonify({'status': 'success'}), 200
        else:
            logging.error(f"Webhook processing failed: {result.get('error')}")
            return jsonify({'status': 'error', 'message': result.get('error')}), 400
            
    except Exception as e:
        logging.error(f"Error processing Stripe webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/list_conversations')
@limiter.limit("20 per minute")
def list_conversations():
    """Get a list of all conversations with optional search"""
    try:
        # Validate session
        if not SecurityValidator.validate_session_data(session):
            session.clear()
            return jsonify({"error": "Session data invalid, please refresh"}), 400
        
        # Get search query if provided
        search_query = request.args.get('search', '').strip()
        
        # Build query
        query = Conversation.query
        
        if search_query:
            # Search in initial_input field
            search_pattern = f"%{search_query}%"
            query = query.filter(Conversation.initial_input.ilike(search_pattern))
        
        conversations = query.order_by(Conversation.created_at.desc()).limit(50).all()
        
        conversation_list = []
        for conv in conversations:
            # Safely truncate and sanitize initial input
            initial_input = InputValidator.sanitize_html(conv.initial_input)
            if len(initial_input) > 100:
                initial_input = initial_input[:100] + "..."
            
            conversation_list.append({
                "id": conv.id,
                "initial_input": initial_input,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "is_complete": conv.is_complete,
                "entry_count": conv.entries.count()
            })
        
        return jsonify({
            "success": True,
            "conversations": conversation_list,
            "search_query": search_query
        })
        
    except Exception as e:
        logging.error(f"Error listing conversations: {str(e)}")
        return jsonify({"error": "Failed to load conversations"}), 500

@app.route('/load_conversation/<conversation_id>')
@limiter.limit("15 per minute")
def load_conversation(conversation_id):
    """Load a specific conversation"""
    try:
        # Validate conversation ID
        is_valid, error_msg = InputValidator.validate_conversation_id(conversation_id)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Validate session
        if not SecurityValidator.validate_session_data(session):
            session.clear()
            return jsonify({"error": "Session data invalid, please refresh"}), 400
        
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Set the conversation in session
        session['conversation_id'] = conversation_id
        session.permanent = True
        
        # Get conversation history
        chain = ConversationChain(conversation_id)
        history = chain.get_conversation_history()
        
        logging.info(f"Conversation loaded: {conversation_id}")
        
        return jsonify({
            "success": True,
            "conversation": conversation.to_dict(),
            "history": history,
            "is_complete": chain.is_complete
        })
        
    except Exception as e:
        logging.error(f"Error loading conversation: {str(e)}")
        return jsonify({"error": "Failed to load conversation"}), 500

@app.route('/export_conversation/<conversation_id>')
@limiter.limit("10 per minute")
def export_conversation(conversation_id):
    """Export a conversation as a text file"""
    try:
        # Validate conversation ID
        is_valid, error_msg = InputValidator.validate_conversation_id(conversation_id)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Validate session
        if not SecurityValidator.validate_session_data(session):
            session.clear()
            return jsonify({"error": "Session data invalid, please refresh"}), 400
        
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Get conversation history
        chain = ConversationChain(conversation_id)
        history = chain.get_conversation_history()
        
        # Generate export content
        export_content = f"""Multi-Agent AI Conversation Export
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Conversation ID: {conversation_id}
Created: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Status: {'Complete' if conversation.is_complete else 'In Progress'}

Initial Input:
{conversation.initial_input}

{'='*80}

"""
        
        for i, entry in enumerate(history, 1):
            export_content += f"""Step {i}: {entry['agent']} ({entry['role']})
Time: {entry['timestamp']}

Input:
{entry['input']}

Response:
{entry['response']}

Next Question: {entry.get('next_question', 'N/A')}

{'-'*60}

"""
        
        # Create response with text file
        from flask import Response
        
        response = Response(
            export_content,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename=conversation_{conversation_id[:8]}.txt',
                'Content-Type': 'text/plain; charset=utf-8'
            }
        )
        
        logging.info(f"Conversation exported: {conversation_id}")
        
        return response
        
    except Exception as e:
        logging.error(f"Error exporting conversation: {str(e)}")
        return jsonify({"error": "Failed to export conversation"}), 500

# Security and error handling middleware
@app.before_request
def security_headers():
    """Add security headers to all responses"""
    g.start_time = datetime.utcnow()

@app.after_request
def after_request(response):
    """Add security headers and logging"""
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Log request duration
    if hasattr(g, 'start_time'):
        duration = (datetime.utcnow() - g.start_time).total_seconds()
        if duration > 5:  # Log slow requests
            logging.warning(f"Slow request: {request.endpoint} took {duration:.2f}s")
    
    return response

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({"error": "Resource not found"}), 404
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    logging.error(f"Internal server error: {str(error)}")
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({"error": "An internal error occurred"}), 500
    return render_template('index.html'), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors"""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": f"Too many requests. Please try again in {e.retry_after} seconds."
    }), 429

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle request too large errors"""
    return jsonify({"error": "Request too large"}), 413

# Flow Platform Routes
@app.route('/flow')
def flow_platform():
    """Replit Flow Platform - Dual-purpose personal flow and project builder"""
    return render_template('flow_platform.html')

# OperatorOS Master Agent Routes
@app.route('/api/operatoros/activate', methods=['GET'])
@limiter.limit("5 per minute")
def activate_operatoros():
    """Activate OperatorOS Master Agent system"""
    try:
        activation_message = operatoros_master.activate_operatoros()
        
        return jsonify({
            "success": True,
            "message": activation_message,
            "system_status": "activated",
            "available_agents": list(operatoros_master.agents.keys()),
            "metrics": operatoros_master.get_autonomy_metrics()
        })
        
    except Exception as e:
        logging.error(f"Error activating OperatorOS: {str(e)}")
        return jsonify({"error": f"OperatorOS activation failed: {str(e)}"}), 500

@app.route('/api/operatoros/daily-briefing', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt
def daily_autonomy_briefing():
    """Generate comprehensive daily autonomy briefing"""
    try:
        data = request.get_json() or {}
        user_input = data.get('input', '')
        
        # Generate daily briefing
        result = operatoros_master.daily_autonomy_briefing(user_input)
        
        if result['success']:
            # Create conversation record
            conversation_id = str(uuid.uuid4())
            conversation = Conversation(
                id=conversation_id,
                initial_input=user_input or "Daily autonomy briefing",
                current_agent_index=0,
                is_complete=True,
                session_id=session.get('session_id'),
                user_ip=get_remote_address()
            )
            db.session.add(conversation)
            
            entry = ConversationEntry(
                conversation_id=conversation_id,
                agent_name="OperatorOS Master",
                agent_role="Master Life Operating System Agent",
                input_text=user_input or "Daily briefing request",
                response_text=result['response'],
                processing_time_seconds=0.5,
                tokens_used=result.get('tokens_used', 0),
                model_used="gpt-3.5-turbo",
                api_provider="openai",
                response_length=len(result['response']),
                error_occurred=False
            )
            db.session.add(entry)
            db.session.commit()
            
            session['current_conversation_id'] = conversation_id
            
            return jsonify({
                "success": True,
                "conversation_id": conversation_id,
                "briefing": result['response'],
                "tokens_used": result.get('tokens_used', 0),
                "type": "daily_briefing",
                "metrics": operatoros_master.get_autonomy_metrics()
            })
        else:
            return jsonify({"error": result.get('error', 'Briefing generation failed')}), 500
        
    except Exception as e:
        logging.error(f"Error generating daily briefing: {str(e)}")
        return jsonify({"error": f"Daily briefing failed: {str(e)}"}), 500

@app.route('/api/dashboard', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt
def dashboard_endpoint():
    """Generate executive dashboard for all C-Suite agents"""
    try:
        data = request.get_json()
        input_text = data.get('input', '').strip() if data else ''
        
        # Check if this is a dashboard command
        if '@all dashboard' in input_text.lower() or input_text.lower() == '@all dashboard':
            # Import dashboard generator
            from dashboard_automation import ExecutiveDashboardGenerator
            
            # Generate dashboard
            generator = ExecutiveDashboardGenerator()
            dashboard_content = generator.generate_executive_dashboard()
            
            return jsonify({
                "success": True,
                "response": dashboard_content,
                "timestamp": datetime.utcnow().isoformat(),
                "agent_type": "dashboard",
                "conversation_stats": {
                    "dashboard_type": "executive_summary",
                    "agents_synthesized": 8,
                    "sections_generated": 6
                }
            })
        else:
            return jsonify({"error": "Use '@all dashboard' command to generate executive dashboard"}), 400
        
    except Exception as e:
        logging.error(f"Error generating dashboard: {str(e)}")
        return jsonify({"error": f"Dashboard generation error: {str(e)}"}), 500

@app.route('/api/operatoros/agent', methods=['POST'])
@limiter.limit("15 per minute")
@csrf.exempt
def operatoros_agent_consultation():
    """Route request to specific OperatorOS C-Suite agent or dynamic agent"""
    try:
        data = request.get_json()
        if not data or 'input' not in data:
            return jsonify({"error": "Input is required"}), 400
        
        input_text = data['input'].strip()
        
        # Get user session for dynamic agents
        user_session = session.get('session_id')
        if not user_session:
            session['session_id'] = str(uuid.uuid4())
            user_session = session['session_id']
        
        # Route to appropriate agent (now supports dynamic agents)
        result = operatoros_master.route_to_agent(input_text, user_session)
        
        if result['success']:
            # Create conversation record
            conversation_id = str(uuid.uuid4())
            conversation = Conversation(
                id=conversation_id,
                initial_input=input_text,
                current_agent_index=0,
                is_complete=True,
                session_id=session.get('session_id'),
                user_ip=get_remote_address()
            )
            db.session.add(conversation)
            
            agent_name = result.get('agent', 'OperatorOS Agent')
            entry = ConversationEntry(
                conversation_id=conversation_id,
                agent_name=agent_name,
                agent_role=f"OperatorOS {agent_name}",
                input_text=input_text,
                response_text=result['response'],
                processing_time_seconds=0.5,
                tokens_used=result.get('tokens_used', 0),
                model_used="gpt-3.5-turbo",
                api_provider="openai",
                response_length=len(result['response']),
                error_occurred=False
            )
            db.session.add(entry)
            db.session.commit()
            
            session['current_conversation_id'] = conversation_id
            
            return jsonify({
                "success": True,
                "conversation_id": conversation_id,
                "agent": result.get('agent'),
                "response": result['response'],
                "tokens_used": result.get('tokens_used', 0),
                "type": result.get('type', 'agent_response'),
                "metrics": operatoros_master.get_autonomy_metrics(),
                "agent_data": result.get('agent_data', {})  # For dynamic agent creation
            })
        else:
            return jsonify({"error": result.get('error', 'Agent consultation failed')}), 500
        
    except Exception as e:
        logging.error(f"Error in agent consultation: {str(e)}")
        return jsonify({"error": f"Agent consultation failed: {str(e)}"}), 500

@app.route('/api/operatoros/multi-agent', methods=['POST'])
@limiter.limit("5 per minute")
@csrf.exempt
def operatoros_multi_agent_analysis():
    """Generate multi-agent collaborative analysis"""
    try:
        data = request.get_json()
        if not data or 'input' not in data:
            return jsonify({"error": "Input is required"}), 400
        
        input_text = data['input'].strip()
        
        # Generate cross-agent analysis
        result = operatoros_master.cross_agent_analysis(input_text)
        
        if result['success']:
            # Create conversation record
            conversation_id = str(uuid.uuid4())
            conversation = Conversation(
                id=conversation_id,
                initial_input=input_text,
                current_agent_index=0,
                is_complete=True,
                session_id=session.get('session_id'),
                user_ip=get_remote_address()
            )
            db.session.add(conversation)
            
            entry = ConversationEntry(
                conversation_id=conversation_id,
                agent_name="OperatorOS Multi-Agent",
                agent_role="Collaborative C-Suite Analysis",
                input_text=input_text,
                response_text=result['response'],
                processing_time_seconds=1.0,
                tokens_used=result.get('tokens_used', 0),
                model_used="gpt-3.5-turbo",
                api_provider="openai",
                response_length=len(result['response']),
                error_occurred=False
            )
            db.session.add(entry)
            db.session.commit()
            
            session['current_conversation_id'] = conversation_id
            
            return jsonify({
                "success": True,
                "conversation_id": conversation_id,
                "analysis": result['response'],
                "tokens_used": result.get('tokens_used', 0),
                "type": "multi_agent_analysis",
                "metrics": operatoros_master.get_autonomy_metrics()
            })
        else:
            return jsonify({"error": result.get('error', 'Multi-agent analysis failed')}), 500
        
    except Exception as e:
        logging.error(f"Error in multi-agent analysis: {str(e)}")
        return jsonify({"error": f"Multi-agent analysis failed: {str(e)}"}), 500

@app.route('/api/operatoros/metrics', methods=['GET'])
@limiter.limit("20 per minute")
def operatoros_metrics():
    """Get current OperatorOS autonomy metrics"""
    try:
        metrics = operatoros_master.get_autonomy_metrics()
        return jsonify({
            "success": True,
            "metrics": metrics
        })
        
    except Exception as e:
        logging.error(f"Error getting OperatorOS metrics: {str(e)}")
        return jsonify({"error": f"Metrics retrieval failed: {str(e)}"}), 500

# Dynamic Agent Creation API Endpoints
@app.route('/api/agents/create', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt
def create_dynamic_agent():
    """Create a new dynamic agent with natural language command"""
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({"error": "Agent creation command is required"}), 400
        
        command = data['command'].strip()
        
        # Get user session
        user_session = session.get('session_id')
        if not user_session:
            session['session_id'] = str(uuid.uuid4())
            user_session = session['session_id']
        
        # Create dynamic agent
        result = operatoros_master.create_dynamic_agent(command, user_session)
        
        # Create conversation record if successful
        if result['success']:
            conversation_id = str(uuid.uuid4())
            conversation = Conversation(
                id=conversation_id,
                initial_input=command,
                current_agent_index=0,
                is_complete=True,
                session_id=user_session,
                user_ip=get_remote_address()
            )
            db.session.add(conversation)
            
            entry = ConversationEntry(
                conversation_id=conversation_id,
                agent_name="Dynamic Agent Creator",
                agent_role="Agent Creation System",
                input_text=command,
                response_text=result['response'],
                processing_time_seconds=0.3,
                tokens_used=0,
                model_used="system",
                api_provider="internal",
                response_length=len(result['response']),
                error_occurred=False
            )
            db.session.add(entry)
            db.session.commit()
            
            session['current_conversation_id'] = conversation_id
        
        return jsonify({
            "success": result['success'],
            "response": result['response'],
            "type": result['type'],
            "agent_data": result.get('agent_data', {}),
            "conversation_id": conversation_id if result['success'] else None
        })
        
    except Exception as e:
        logging.error(f"Error creating dynamic agent: {str(e)}")
        return jsonify({"error": f"Agent creation failed: {str(e)}"}), 500

@app.route('/api/agents/list', methods=['GET'])
@limiter.limit("20 per minute")
def list_user_agents():
    """List all dynamic agents for the current user"""
    try:
        user_session = session.get('session_id')
        if not user_session:
            return jsonify({
                "success": True,
                "agents": [],
                "built_in_agents": [
                    {"code": "CFO", "name": "Chief Financial Officer", "icon": "💰"},
                    {"code": "COO", "name": "Chief Operating Officer", "icon": "⚙️"},
                    {"code": "CSA", "name": "Chief Strategy Agent", "icon": "🎯"},
                    {"code": "CMO", "name": "Chief Marketing Officer", "icon": "🎨"},
                    {"code": "CTO", "name": "Chief Technology Officer", "icon": "💻"},
                    {"code": "CPO", "name": "Chief People Officer", "icon": "🌱"},
                    {"code": "CIO", "name": "Chief Intelligence Officer", "icon": "🧠"}
                ]
            })
        
        # Get user's dynamic agents
        from models import DynamicAgent
        agents = DynamicAgent.query.filter_by(
            user_session=user_session, 
            is_active=True
        ).order_by(DynamicAgent.created_at.desc()).all()
        
        agent_list = [agent.to_dict() for agent in agents]
        
        return jsonify({
            "success": True,
            "agents": agent_list,
            "built_in_agents": [
                {"code": "CFO", "name": "Chief Financial Officer", "icon": "💰"},
                {"code": "COO", "name": "Chief Operating Officer", "icon": "⚙️"},
                {"code": "CSA", "name": "Chief Strategy Agent", "icon": "🎯"},
                {"code": "CMO", "name": "Chief Marketing Officer", "icon": "🎨"},
                {"code": "CTO", "name": "Chief Technology Officer", "icon": "💻"},
                {"code": "CPO", "name": "Chief People Officer", "icon": "🌱"},
                {"code": "CIO", "name": "Chief Intelligence Officer", "icon": "🧠"}
            ]
        })
        
    except Exception as e:
        logging.error(f"Error listing agents: {str(e)}")
        return jsonify({"error": f"Failed to list agents: {str(e)}"}), 500

@app.route('/api/agents/retire/<agent_code>', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt
def retire_dynamic_agent(agent_code):
    """Retire (deactivate) a dynamic agent"""
    try:
        user_session = session.get('session_id')
        if not user_session:
            return jsonify({"error": "User session not found"}), 400
        
        # Retire the agent
        from dynamic_agent_creator import DynamicAgentCreator
        creator = DynamicAgentCreator()
        result = creator.retire_agent(user_session, agent_code)
        
        return jsonify({
            "success": result['success'],
            "message": result['message'] if result['success'] else result['error']
        })
        
    except Exception as e:
        logging.error(f"Error retiring agent: {str(e)}")
        return jsonify({"error": f"Agent retirement failed: {str(e)}"}), 500

@app.route('/api/agents/modify/<agent_code>', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt
def modify_dynamic_agent(agent_code):
    """Modify a dynamic agent's function"""
    try:
        data = request.get_json()
        if not data or 'new_function' not in data:
            return jsonify({"error": "New function is required"}), 400
        
        user_session = session.get('session_id')
        if not user_session:
            return jsonify({"error": "User session not found"}), 400
        
        new_function = data['new_function'].strip()
        
        # Modify the agent
        from dynamic_agent_creator import DynamicAgentCreator
        creator = DynamicAgentCreator()
        result = creator.modify_agent(user_session, agent_code, new_function)
        
        return jsonify({
            "success": result['success'],
            "message": result['message'] if result['success'] else result['error']
        })
        
    except Exception as e:
        logging.error(f"Error modifying agent: {str(e)}")
        return jsonify({"error": f"Agent modification failed: {str(e)}"}), 500

@app.route('/operatoros')
def operatoros_interface():
    """OperatorOS Master Agent interface"""
    return render_template('operatoros_interface.html')

@app.route('/api/flow/generate', methods=['POST'])
@limiter.limit("10 per minute")
def generate_personal_flow():
    """Generate personalized daily flow plan"""
    try:
        data = request.get_json()
        
        # Validate input
        energy = data.get('energy')
        priority = data.get('priority', '').strip()
        open_loops = data.get('open_loops', '').strip()
        
        if not energy or not priority:
            return jsonify({"success": False, "error": "Energy level and priority are required"}), 400
        
        # Generate user ID if not in session
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        
        user_id = session['user_id']
        start_time = datetime.utcnow()
        
        # Generate flow plan using Flow Agent
        result = flow_agent_manager.generate_personal_flow(energy, priority, open_loops)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Save session to database
        from models import FlowSession
        flow_session = FlowSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            mode='personal',
            input_data={
                'energy': energy,
                'priority': priority,
                'open_loops': open_loops
            },
            output_data={
                'response': result.get('response'),
                'tokens_used': result.get('tokens_used', 0)
            },
            tokens_used=result.get('tokens_used', 0),
            processing_time=processing_time,
            success=result.get('success', True)
        )
        
        db.session.add(flow_session)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "response": result.get('response'),
            "processing_time": processing_time,
            "tokens_used": result.get('tokens_used', 0),
            "session_id": flow_session.id
        })
        
    except Exception as e:
        logging.error(f"Error generating personal flow: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/flow/project/build', methods=['POST'])
@limiter.limit("5 per minute")
def build_project_strategy():
    """Build comprehensive project strategy using 4-agent pipeline"""
    try:
        data = request.get_json()
        
        # Validate input
        vision = data.get('vision', '').strip()
        project_type = data.get('type', '').strip()
        
        if not vision or not project_type:
            return jsonify({"success": False, "error": "Project vision and type are required"}), 400
        
        # Generate user ID if not in session
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        
        user_id = session['user_id']
        start_time = datetime.utcnow()
        
        # Build project strategy using Project Agent pipeline
        result = flow_agent_manager.build_project_strategy(vision, project_type)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Save session to database
        from models import FlowSession, Project
        flow_session = FlowSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            mode='project',
            input_data={
                'vision': vision,
                'project_type': project_type
            },
            output_data={
                'strategy': result.get('strategy'),
                'analysis': result.get('analysis'),
                'research': result.get('research'),
                'tokens_used': result.get('tokens_used', 0)
            },
            tokens_used=result.get('tokens_used', 0),
            processing_time=processing_time,
            success=result.get('success', True)
        )
        
        db.session.add(flow_session)
        
        # Save as project record
        project = Project(
            user_id=user_id,
            project_name=vision[:100] + '...' if len(vision) > 100 else vision,
            project_type=project_type,
            vision_text=vision,
            strategy_output=result
        )
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "strategy": result.get('strategy'),
            "processing_time": processing_time,
            "tokens_used": result.get('tokens_used', 0),
            "session_id": flow_session.id,
            "project_id": project.id
        })
        
    except Exception as e:
        logging.error(f"Error building project strategy: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Real Estate Engine API Endpoint
@app.route('/api/real_estate_engine', methods=['POST'])
@limiter.limit("5 per minute")
@csrf.exempt
def api_real_estate_engine():
    """Process real estate agent prompts through OperatorOS loop"""
    try:
        data = request.get_json() if request.is_json else {}
        
        if not data or 'prompt' not in data:
            return jsonify({"error": "prompt is required"}), 400
        
        prompt = data['prompt'].strip()
        
        # Validate input
        is_valid, error_msg = InputValidator.validate_conversation_input(prompt)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Sanitize input
        prompt = InputValidator.sanitize_html(prompt)
        
        # Create temporary session for API calls
        temp_session_id = str(uuid.uuid4())
        
        # Process through real estate engine
        result = real_estate_engine.process_real_estate_prompt(prompt, temp_session_id)
        
        if result["success"]:
            logging.info(f"Real Estate package generated: {result['package_id']}")
            return jsonify({
                "success": True,
                "package_id": result["package_id"],
                "download_url": result["download_url"],
                "property_type": result["property_type"],
                "location": result["location"],
                "file_count": result["file_count"],
                "processing_time": result["processing_time"],
                "files": ["listing.md", "market.md", "actions.md", "pricing.md"]
            })
        else:
            return jsonify({"success": False, "error": result["error"]}), 500
        
    except Exception as e:
        logging.error(f"Error in real estate engine API: {str(e)}")
        return jsonify({"error": f"Real estate processing failed: {str(e)}"}), 500

# Universal Business Intelligence API Endpoints
@app.route('/api/business_intelligence', methods=['POST'])
@limiter.limit("5 per minute")
@csrf.exempt
def api_business_intelligence():
    """
    Universal Business Intelligence API - Generates comprehensive business packages
    Transforms any business prompt into professional 10-file .md package
    """
    try:
        data = request.get_json() if request.is_json else {}
        
        if not data or 'prompt' not in data:
            return jsonify({"error": "Business prompt is required"}), 400
        
        prompt = data['prompt'].strip()
        
        # Validate input
        is_valid, error_msg = InputValidator.validate_conversation_input(prompt)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Sanitize input
        prompt = InputValidator.sanitize_html(prompt)
        
        # Create temporary session for API calls
        temp_session_id = str(uuid.uuid4())
        
        # Execute Enhanced 11-Agent Pipeline
        chain = Enhanced11AgentChain.create_new(
            prompt, 
            session_id=temp_session_id,
            user_ip=request.remote_addr
        )
        
        # Execute complete C-Suite pipeline
        result = chain.execute_complete_pipeline(prompt)
        
        if result["success"]:
            business_package = result["business_package"]
            logging.info(f"Business Intelligence package generated: {business_package.get('package_id', 'Unknown')}")
            
            return jsonify({
                "success": True,
                "package_id": business_package.get("package_id"),
                "download_url": business_package.get("download_url"),
                "file_count": business_package.get("file_count", 10),
                "files": business_package.get("files_generated", []),
                "processing_time": result.get("processing_time", 0),
                "agents_completed": result.get("agents_completed", 11),
                "conversation_id": result.get("conversation_id"),
                "business_context": business_package.get("business_context", {}),
                "package_size": business_package.get("package_size_bytes", 0)
            })
        else:
            return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500
        
    except Exception as e:
        logging.error(f"Error in business intelligence API: {str(e)}")
        return jsonify({"error": f"Business intelligence processing failed: {str(e)}"}), 500

@app.route('/api/executive_advisory', methods=['POST'])
@limiter.limit("3 per minute")
@csrf.exempt
def api_executive_advisory():
    """
    Executive Advisory API - Premium C-Suite intelligence for enterprise clients
    Generates executive-grade strategic intelligence packages
    """
    try:
        data = request.get_json() if request.is_json else {}
        
        if not data or 'business_challenge' not in data:
            return jsonify({"error": "Business challenge description is required"}), 400
        
        business_challenge = data['business_challenge'].strip()
        priority_level = data.get('priority_level', 'standard')  # standard, urgent, strategic
        
        # Validate input
        is_valid, error_msg = InputValidator.validate_conversation_input(business_challenge)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Sanitize input
        business_challenge = InputValidator.sanitize_html(business_challenge)
        
        # Create session for tracking
        session_id = str(uuid.uuid4())
        
        # Execute Enhanced 11-Agent Pipeline with executive focus
        chain = Enhanced11AgentChain.create_new(
            business_challenge, 
            session_id=session_id,
            user_ip=request.remote_addr
        )
        
        # Execute complete C-Suite pipeline
        result = chain.execute_complete_pipeline(business_challenge)
        
        if result["success"]:
            business_package = result["business_package"]
            
            # Add executive-specific metadata
            executive_metadata = {
                "executive_grade": True,
                "c_suite_analysis": True,
                "strategic_intelligence": True,
                "priority_level": priority_level,
                "enterprise_ready": True
            }
            
            logging.info(f"Executive Advisory package generated: {business_package.get('package_id', 'Unknown')}")
            
            return jsonify({
                "success": True,
                "package_id": business_package.get("package_id"),
                "download_url": business_package.get("download_url"),
                "executive_grade": True,
                "c_suite_agents": 7,
                "strategic_files": business_package.get("file_count", 10),
                "processing_time": result.get("processing_time", 0),
                "intelligence_level": "Executive C-Suite",
                "business_value": "Strategic Intelligence Package",
                "metadata": executive_metadata,
                "conversation_id": result.get("conversation_id")
            })
        else:
            return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500
        
    except Exception as e:
        logging.error(f"Error in executive advisory API: {str(e)}")
        return jsonify({"error": f"Executive advisory processing failed: {str(e)}"}), 500

# Multi-LLM Testing Routes
@app.route('/llm-test')
def llm_test_dashboard():
    """Multi-LLM testing dashboard"""
    return render_template('llm_test_dashboard.html')

@app.route('/api/llm/status')
@limiter.limit("30 per minute")
@csrf.exempt  # API endpoint
def llm_status():
    """Get status of all LLM providers"""
    try:
        status = multi_llm.get_provider_status()
        return jsonify(status)
    except Exception as e:
        logging.error(f"Error getting LLM status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/llm/test-all', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt  # API endpoint
def test_all_llm_providers():
    """Test all available LLM providers"""
    try:
        results = multi_llm.test_all_providers()
        
        # Convert results to JSON-serializable format
        json_results = {}
        for provider, response in results.items():
            json_results[provider] = {
                "content": response.content,
                "provider": response.provider.value,
                "model": response.model,
                "usage": response.usage,
                "success": response.success,
                "error": response.error
            }
        
        return jsonify(json_results)
        
    except Exception as e:
        logging.error(f"Error testing LLM providers: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/llm/custom-test', methods=['POST'])
@limiter.limit("15 per minute")
@csrf.exempt  # API endpoint
def custom_llm_test():
    """Run a custom test on specified provider(s)"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        provider_name = data.get('provider')
        
        if not prompt.strip():
            return jsonify({"error": "Prompt cannot be empty"}), 400
        
        # Convert provider name to enum
        provider = None
        if provider_name:
            try:
                provider = LLMProvider(provider_name)
            except ValueError:
                return jsonify({"error": f"Invalid provider: {provider_name}"}), 400
        
        # Create messages from prompt
        messages = [
            {
                "role": "system",
                "content": "You are an OperatorOS agent following production memory guidelines. Respond with precision and clarity - no flattery, no soothing, no inflation."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Generate response
        response = multi_llm.generate_response(
            messages=messages,
            provider=provider,
            max_tokens=500,
            temperature=0.7
        )
        
        return jsonify({
            "content": response.content,
            "provider": response.provider.value,
            "model": response.model,
            "usage": response.usage,
            "success": response.success,
            "error": response.error
        })
        
    except Exception as e:
        logging.error(f"Error in custom LLM test: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/llm/chat', methods=['POST'])
@limiter.limit("30 per minute")
@csrf.exempt  # API endpoint
def llm_chat():
    """General LLM chat endpoint with provider selection"""
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        provider_name = data.get('provider')
        max_tokens = data.get('max_tokens', 1000)
        temperature = data.get('temperature', 0.7)
        
        if not messages:
            return jsonify({"error": "Messages cannot be empty"}), 400
        
        # Convert provider name to enum if specified
        provider = None
        if provider_name:
            try:
                provider = LLMProvider(provider_name)
            except ValueError:
                return jsonify({"error": f"Invalid provider: {provider_name}"}), 400
        
        # Generate response
        response = multi_llm.generate_response(
            messages=messages,
            provider=provider,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return jsonify({
            "content": response.content,
            "provider": response.provider.value,
            "model": response.model,
            "usage": response.usage,
            "success": response.success,
            "error": response.error
        })
        
    except Exception as e:
        logging.error(f"Error in LLM chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
