from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, Index
from datetime import datetime
import json

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Conversation(db.Model):
    """Model for storing conversation metadata with enhanced persistence features"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID string
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    is_complete = db.Column(db.Boolean, default=False, nullable=False, index=True)
    current_agent_index = db.Column(db.Integer, default=0, nullable=False)
    initial_input = db.Column(db.Text, nullable=False)
    
    # Enhanced fields for better conversation tracking
    session_id = db.Column(db.String(128), nullable=True, index=True)  # Track user sessions
    user_ip = db.Column(db.String(45), nullable=True)  # Store IP for analytics
    completion_time = db.Column(db.DateTime, nullable=True)  # Track when conversation completed
    total_tokens_used = db.Column(db.Integer, default=0)  # Track token usage
    error_count = db.Column(db.Integer, default=0)  # Track errors during conversation
    
    # Relationship to conversation entries
    entries = db.relationship('ConversationEntry', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_conversation_status_time', 'is_complete', 'created_at'),
        Index('idx_conversation_session', 'session_id', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_complete': self.is_complete,
            'current_agent_index': self.current_agent_index,
            'initial_input': self.initial_input,
            'session_id': self.session_id,
            'completion_time': self.completion_time.isoformat() if self.completion_time else None,
            'total_tokens_used': self.total_tokens_used,
            'error_count': self.error_count,
            'entries': [entry.to_dict() for entry in self.entries.order_by(ConversationEntry.created_at)]
        }
    
    def get_duration(self):
        """Get conversation duration in seconds"""
        if self.completion_time:
            return (self.completion_time - self.created_at).total_seconds()
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def get_entry_count(self):
        """Get total number of entries in this conversation"""
        return self.entries.count()
    
    def get_summary(self):
        """Get a summary of the conversation for display"""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'is_complete': self.is_complete,
            'initial_input': self.initial_input[:100] + '...' if len(self.initial_input) > 100 else self.initial_input,
            'entry_count': self.get_entry_count(),
            'duration_seconds': self.get_duration(),
            'current_agent_index': self.current_agent_index,
            'total_tokens_used': self.total_tokens_used,
            'error_count': self.error_count
        }

class ConversationEntry(db.Model):
    """Model for storing individual agent responses in conversations with enhanced persistence"""
    __tablename__ = 'conversation_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False, index=True)
    agent_name = db.Column(db.String(50), nullable=False, index=True)
    agent_role = db.Column(db.String(50), nullable=False)
    input_text = db.Column(db.Text, nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    next_question = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Enhanced fields for better tracking and analysis
    processing_time_seconds = db.Column(db.Float, default=0.0)  # Time taken to generate response
    tokens_used = db.Column(db.Integer, default=0)  # Tokens used for this response
    model_used = db.Column(db.String(50), default='gpt-3.5-turbo')  # Model used for response
    api_provider = db.Column(db.String(20), default='openai')  # API provider used (openai, claude, gemini)
    response_length = db.Column(db.Integer, default=0)  # Length of response in characters
    error_occurred = db.Column(db.Boolean, default=False)  # Whether an error occurred
    error_message = db.Column(db.Text, nullable=True)  # Error message if any
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_entry_conversation_time', 'conversation_id', 'created_at'),
        Index('idx_entry_agent_time', 'agent_name', 'created_at'),
        Index('idx_entry_search', 'conversation_id', 'agent_name', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'agent': self.agent_name,
            'role': self.agent_role,
            'input': self.input_text,
            'response': self.response_text,
            'next_question': self.next_question,
            'timestamp': self.created_at.isoformat(),
            'processing_time_seconds': self.processing_time_seconds,
            'tokens_used': self.tokens_used,
            'model_used': self.model_used,
            'api_provider': self.api_provider,
            'response_length': self.response_length,
            'error_occurred': self.error_occurred,
            'error_message': self.error_message
        }
    
    def get_response_stats(self):
        """Get statistics about this response"""
        return {
            'response_length': len(self.response_text),
            'has_next_question': bool(self.next_question and self.next_question.strip()),
            'processing_time': self.processing_time_seconds,
            'tokens_used': self.tokens_used,
            'model_used': self.model_used
        }

# Database event listeners for automatic field updates
@event.listens_for(ConversationEntry, 'before_insert')
def set_response_length(mapper, connection, target):
    """Automatically set response length before insert"""
    if target.response_text:
        target.response_length = len(target.response_text)

@event.listens_for(ConversationEntry, 'before_update')
def update_response_length(mapper, connection, target):
    """Automatically update response length before update"""
    if target.response_text:
        target.response_length = len(target.response_text)