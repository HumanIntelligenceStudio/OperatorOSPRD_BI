import os
import logging
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import uuid
from datetime import datetime

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-dev")

# OpenAI API setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY environment variable is not set")
    
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# In-memory storage for conversations
conversations = {}

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
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
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
    """Manages the conversation flow between agents"""
    
    def __init__(self):
        self.agents = [
            AnalystAgent(),
            ResearcherAgent(),
            WriterAgent()
        ]
        self.current_agent_index = 0
        self.conversation_history = []
        self.is_complete = False
    
    def process_input(self, input_text):
        """Process input through the current agent and advance to next"""
        if self.is_complete:
            raise Exception("Conversation chain is already complete")
        
        try:
            current_agent = self.agents[self.current_agent_index]
            
            # Generate response from current agent
            response = current_agent.generate_response(input_text, self.conversation_history[-3:])  # Use last 3 entries for context
            
            # Extract question for next agent
            next_question = current_agent.extract_next_question(response)
            
            # Store conversation entry
            conversation_entry = {
                "agent": current_agent.name,
                "role": current_agent.role,
                "input": input_text,
                "response": response,
                "next_question": next_question,
                "timestamp": datetime.now().isoformat()
            }
            
            self.conversation_history.append(conversation_entry)
            
            # Move to next agent
            self.current_agent_index += 1
            
            # Check if conversation is complete
            if self.current_agent_index >= len(self.agents):
                self.is_complete = True
            
            return conversation_entry
            
        except Exception as e:
            logging.error(f"Error processing input: {str(e)}")
            raise e
    
    def get_next_agent_name(self):
        """Get the name of the next agent in the chain"""
        if self.current_agent_index < len(self.agents):
            return self.agents[self.current_agent_index].name
        return None

@app.route('/')
def index():
    """Main page with conversation interface"""
    return render_template('index.html')

@app.route('/start_conversation', methods=['POST'])
def start_conversation():
    """Start a new conversation chain"""
    try:
        data = request.get_json()
        if not data or 'input' not in data:
            return jsonify({"error": "Input text is required"}), 400
        
        input_text = data['input'].strip()
        if not input_text:
            return jsonify({"error": "Input text cannot be empty"}), 400
        
        # Create new conversation chain
        conversation_id = str(uuid.uuid4())
        chain = ConversationChain()
        
        # Process initial input with Analyst
        result = chain.process_input(input_text)
        
        # Store conversation in memory
        conversations[conversation_id] = {
            "chain": chain,
            "created_at": datetime.now().isoformat()
        }
        
        # Store conversation ID in session
        session['conversation_id'] = conversation_id
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "result": result,
            "next_agent": chain.get_next_agent_name(),
            "is_complete": chain.is_complete
        })
        
    except Exception as e:
        logging.error(f"Error starting conversation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/continue_conversation', methods=['POST'])
def continue_conversation():
    """Continue an existing conversation chain"""
    try:
        conversation_id = session.get('conversation_id')
        if not conversation_id or conversation_id not in conversations:
            return jsonify({"error": "No active conversation found"}), 404
        
        chain = conversations[conversation_id]["chain"]
        
        if chain.is_complete:
            return jsonify({"error": "Conversation is already complete"}), 400
        
        # Get the next question from the last conversation entry
        if not chain.conversation_history:
            return jsonify({"error": "No conversation history found"}), 400
        
        last_entry = chain.conversation_history[-1]
        next_question = last_entry["next_question"]
        
        # Process with next agent
        result = chain.process_input(next_question)
        
        return jsonify({
            "success": True,
            "result": result,
            "next_agent": chain.get_next_agent_name(),
            "is_complete": chain.is_complete
        })
        
    except Exception as e:
        logging.error(f"Error continuing conversation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_conversation_history')
def get_conversation_history():
    """Get the current conversation history"""
    try:
        conversation_id = session.get('conversation_id')
        if not conversation_id or conversation_id not in conversations:
            return jsonify({"error": "No active conversation found"}), 404
        
        chain = conversations[conversation_id]["chain"]
        
        return jsonify({
            "success": True,
            "history": chain.conversation_history,
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
        if conversation_id and conversation_id in conversations:
            del conversations[conversation_id]
        
        session.pop('conversation_id', None)
        
        return jsonify({"success": True, "message": "Conversation reset successfully"})
        
    except Exception as e:
        logging.error(f"Error resetting conversation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Internal server error: {str(error)}")
    return render_template('index.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
