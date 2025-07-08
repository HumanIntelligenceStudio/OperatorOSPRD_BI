import os
import logging
from flask import Flask, render_template, request, jsonify, session, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from openai import OpenAI
import uuid
from datetime import datetime
from models import db, Conversation, ConversationEntry
from config import config, Config
from utils.validators import InputValidator, SecurityValidator

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
    
    return app, limiter, csrf

# Create app instance
app, limiter, csrf = create_app()

# OpenAI client setup
openai_client = OpenAI(api_key=app.config['OPENAI_API_KEY'])

class Agent:
    """Base class for all AI agents"""
    
    def __init__(self, name, role, system_prompt):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
    
    def generate_response(self, input_text, conversation_history=None):
        """Generate response using OpenAI API"""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add conversation history if provided
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
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error generating response for {self.name}: {str(e)}")
            raise Exception(f"Failed to generate response from {self.name}: {str(e)}")
    
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
        system_prompt = """You are an expert Analyst. Your role is to analyze the given input thoroughly and provide insights, 
        patterns, and key observations. After your analysis, you must end your response with a specific research question 
        for the Researcher to investigate further. 
        
        IMPORTANT: You must end your response with exactly this format:
        NEXT AGENT QUESTION: [your specific research question here]
        
        Focus on breaking down the topic, identifying key components, and formulating a targeted research question."""
        
        super().__init__("Analyst", "Analysis", system_prompt)

class ResearcherAgent(Agent):
    """Agent that researches topics and asks writing questions"""
    
    def __init__(self):
        system_prompt = """You are an expert Researcher. Your role is to research and provide comprehensive information 
        about the topic or question given to you. Provide facts, context, and detailed insights based on your knowledge.
        After your research, you must end your response with a specific question for the Writer to create content.
        
        IMPORTANT: You must end your response with exactly this format:
        NEXT AGENT QUESTION: [your specific writing question here]
        
        Focus on gathering comprehensive information and formulating a clear writing directive."""
        
        super().__init__("Researcher", "Research", system_prompt)

class WriterAgent(Agent):
    """Agent that creates final output based on previous work"""
    
    def __init__(self):
        system_prompt = """You are an expert Writer. Your role is to create well-structured, engaging, and comprehensive 
        content based on the analysis and research provided by previous agents. Synthesize the information into a 
        coherent final output.
        
        IMPORTANT: You must end your response with exactly this format:
        NEXT AGENT QUESTION: [a question for potential follow-up or next steps]
        
        Focus on creating high-quality, well-organized content that incorporates all previous insights."""
        
        super().__init__("Writer", "Writing", system_prompt)

class ConversationChain:
    """Manages the conversation flow between agents using database storage"""
    
    def __init__(self, conversation_id=None):
        self.agents = [
            AnalystAgent(),
            ResearcherAgent(),
            WriterAgent()
        ]
        
        if conversation_id:
            # Load existing conversation from database
            self.conversation = Conversation.query.get(conversation_id)
            if not self.conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
        else:
            self.conversation = None
    
    @classmethod
    def create_new(cls, initial_input):
        """Create a new conversation chain"""
        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            initial_input=initial_input,
            current_agent_index=0,
            is_complete=False
        )
        db.session.add(conversation)
        db.session.commit()
        
        chain = cls(conversation_id)
        return chain
    
    def process_input(self, input_text):
        """Process input through the current agent and advance to next"""
        if self.conversation.is_complete:
            raise Exception("Conversation chain is already complete")
        
        try:
            current_agent = self.agents[self.conversation.current_agent_index]
            
            # Get recent conversation history for context
            recent_entries = self.conversation.entries.order_by(ConversationEntry.created_at.desc()).limit(3).all()
            context_history = [entry.to_dict() for entry in reversed(recent_entries)]
            
            # Generate response from current agent
            response = current_agent.generate_response(input_text, context_history)
            
            # Extract question for next agent
            next_question = current_agent.extract_next_question(response)
            
            # Create and save conversation entry
            entry = ConversationEntry(
                conversation_id=self.conversation.id,
                agent_name=current_agent.name,
                agent_role=current_agent.role,
                input_text=input_text,
                response_text=response,
                next_question=next_question
            )
            
            db.session.add(entry)
            
            # Move to next agent
            self.conversation.current_agent_index += 1
            
            # Check if conversation is complete
            if self.conversation.current_agent_index >= len(self.agents):
                self.conversation.is_complete = True
            
            self.conversation.updated_at = datetime.utcnow()
            db.session.commit()
            
            return entry.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error processing input: {str(e)}")
            raise e
    
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

@app.route('/')
def index():
    """Main page with conversation interface"""
    return render_template('index.html')

@app.route('/health')
@limiter.exempt
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
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
        
        # Check session limits
        if not SecurityValidator.validate_session_data(session):
            session.clear()
            return jsonify({"error": "Session data invalid, please refresh"}), 400
        
        # Sanitize input
        input_text = InputValidator.sanitize_html(input_text.strip())
        
        # Create new conversation chain with database storage
        chain = ConversationChain.create_new(input_text)
        
        # Process initial input with Analyst
        result = chain.process_input(input_text)
        
        # Store conversation ID in session
        session['conversation_id'] = chain.conversation.id
        session.permanent = True
        
        logging.info(f"New conversation started: {chain.conversation.id}")
        
        return jsonify({
            "success": True,
            "conversation_id": chain.conversation.id,
            "result": result,
            "next_agent": chain.get_next_agent_name(),
            "is_complete": chain.is_complete
        })
        
    except Exception as e:
        logging.error(f"Error starting conversation: {str(e)}")
        return jsonify({"error": "An internal error occurred. Please try again."}), 500

@app.route('/continue_conversation', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt
def continue_conversation():
    """Continue an existing conversation chain"""
    try:
        # Validate session
        if not SecurityValidator.validate_session_data(session):
            session.clear()
            return jsonify({"error": "Session data invalid, please refresh"}), 400
        
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
    """Get the current conversation history"""
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
            "is_complete": chain.is_complete
        })
        
    except Exception as e:
        logging.error(f"Error getting conversation history: {str(e)}")
        return jsonify({"error": str(e)}), 500

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
