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
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'agent_name': self.agent_name,
            'agent_role': self.agent_role,
            'input_text': self.input_text,
            'response_text': self.response_text,
            'next_question': self.next_question,
            'created_at': self.created_at.isoformat(),
            'processing_time_seconds': self.processing_time_seconds,
            'tokens_used': self.tokens_used,
            'model_used': self.model_used,
            'api_provider': self.api_provider,
            'response_length': self.response_length,
            'error_occurred': self.error_occurred,
            'error_message': self.error_message
        }

# Flow Platform Models
class FlowSession(db.Model):
    """Model for storing Flow Platform sessions"""
    __tablename__ = 'flow_sessions'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID string
    user_id = db.Column(db.String(128), nullable=False, index=True)
    mode = db.Column(db.String(20), nullable=False, index=True)  # 'personal' or 'project'
    input_data = db.Column(db.JSON)
    output_data = db.Column(db.JSON)
    tokens_used = db.Column(db.Integer, default=0)
    processing_time = db.Column(db.Float, default=0.0)
    success = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_flow_user_mode_time', 'user_id', 'mode', 'created_at'),
        Index('idx_flow_mode_time', 'mode', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'mode': self.mode,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'tokens_used': self.tokens_used,
            'processing_time': self.processing_time,
            'success': self.success,
            'created_at': self.created_at.isoformat()
        }

class UserPreferences(db.Model):
    """Model for storing user preferences and patterns"""
    __tablename__ = 'user_preferences'
    
    user_id = db.Column(db.String(128), primary_key=True)
    preferred_mode = db.Column(db.String(20), default='personal')
    energy_patterns = db.Column(db.JSON, default=dict)
    project_history = db.Column(db.JSON, default=list)
    notification_settings = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'preferred_mode': self.preferred_mode,
            'energy_patterns': self.energy_patterns,
            'project_history': self.project_history,
            'notification_settings': self.notification_settings,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class DailyPattern(db.Model):
    """Model for tracking daily patterns for personal optimization"""
    __tablename__ = 'daily_patterns'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    energy_level = db.Column(db.String(20))  # 'high', 'medium', 'low'
    completed_priority = db.Column(db.Text)
    open_loops_count = db.Column(db.Integer, default=0)
    satisfaction_score = db.Column(db.Integer)  # 1-5 scale
    flow_quality = db.Column(db.Integer)  # 1-5 scale
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_daily_user_date', 'user_id', 'date'),
        Index('idx_daily_user_energy', 'user_id', 'energy_level'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat(),
            'energy_level': self.energy_level,
            'completed_priority': self.completed_priority,
            'open_loops_count': self.open_loops_count,
            'satisfaction_score': self.satisfaction_score,
            'flow_quality': self.flow_quality,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }

class Project(db.Model):
    """Model for tracking projects in the project builder mode"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), nullable=False, index=True)
    project_name = db.Column(db.String(255))
    project_type = db.Column(db.String(50))  # 'business', 'creative', etc.
    status = db.Column(db.String(50), default='active', index=True)
    vision_text = db.Column(db.Text)
    strategy_output = db.Column(db.JSON)
    download_count = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_project_user_status', 'user_id', 'status'),
        Index('idx_project_user_time', 'user_id', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'project_name': self.project_name,
            'project_type': self.project_type,
            'status': self.status,
            'vision_text': self.vision_text,
            'strategy_output': self.strategy_output,
            'download_count': self.download_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
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

class UserFeedback(db.Model):
    """Model for storing user feedback on agent responses"""
    __tablename__ = 'user_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_entry_id = db.Column(db.Integer, db.ForeignKey('conversation_entries.id'), nullable=False)
    feedback_type = db.Column(db.String(20), nullable=False)  # clarity, empathy, actionability, overall
    rating = db.Column(db.Integer, nullable=False)  # 1-5 scale
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_session = db.Column(db.String(128), nullable=True)
    
    # Relationship to conversation entry
    entry = db.relationship('ConversationEntry', backref='feedback')
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_entry_id': self.conversation_entry_id,
            'feedback_type': self.feedback_type,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat(),
            'user_session': self.user_session
        }

class PaymentStatus:
    """Enum for payment status"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Payment(db.Model):
    """Model for storing Stripe payment records"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    stripe_payment_id = db.Column(db.String(100), nullable=True, unique=True)  # Stripe payment ID
    stripe_invoice_id = db.Column(db.String(100), nullable=True, unique=True)  # Stripe invoice ID
    project_name = db.Column(db.String(200), nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Amount in dollars
    currency = db.Column(db.String(3), default='usd', nullable=False)
    description = db.Column(db.Text, nullable=True)
    payment_type = db.Column(db.String(20), nullable=False)  # 'link' or 'invoice'
    status = db.Column(db.String(20), default=PaymentStatus.PENDING, nullable=False)
    payment_url = db.Column(db.String(500), nullable=True)  # Stripe payment/invoice URL
    due_date = db.Column(db.DateTime, nullable=True)  # For invoices
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)  # When payment was completed
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_payment_status', 'status'),
        Index('idx_payment_client', 'client_email'),
        Index('idx_payment_created', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'stripe_payment_id': self.stripe_payment_id,
            'stripe_invoice_id': self.stripe_invoice_id,
            'project_name': self.project_name,
            'client_name': self.client_name,
            'client_email': self.client_email,
            'amount': self.amount,
            'currency': self.currency,
            'description': self.description,
            'payment_type': self.payment_type,
            'status': self.status,
            'payment_url': self.payment_url,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }
    
    def get_status_badge(self):
        """Get Bootstrap badge class for status display"""
        status_classes = {
            PaymentStatus.PENDING: 'warning',
            PaymentStatus.PAID: 'success',
            PaymentStatus.FAILED: 'danger',
            PaymentStatus.CANCELLED: 'secondary'
        }
        return status_classes.get(self.status, 'secondary')