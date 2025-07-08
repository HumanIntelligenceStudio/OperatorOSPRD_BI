from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import json

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Conversation(db.Model):
    """Model for storing conversation metadata"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID string
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_complete = db.Column(db.Boolean, default=False, nullable=False)
    current_agent_index = db.Column(db.Integer, default=0, nullable=False)
    initial_input = db.Column(db.Text, nullable=False)
    
    # Relationship to conversation entries
    entries = db.relationship('ConversationEntry', backref='conversation', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_complete': self.is_complete,
            'current_agent_index': self.current_agent_index,
            'initial_input': self.initial_input,
            'entries': [entry.to_dict() for entry in self.entries.order_by(ConversationEntry.created_at)]
        }

class ConversationEntry(db.Model):
    """Model for storing individual agent responses in conversations"""
    __tablename__ = 'conversation_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    agent_name = db.Column(db.String(50), nullable=False)
    agent_role = db.Column(db.String(50), nullable=False)
    input_text = db.Column(db.Text, nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    next_question = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'agent': self.agent_name,
            'role': self.agent_role,
            'input': self.input_text,
            'response': self.response_text,
            'next_question': self.next_question,
            'timestamp': self.created_at.isoformat()
        }