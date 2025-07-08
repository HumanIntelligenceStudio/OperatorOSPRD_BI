"""
Admin dashboard for monitoring multi-agent AI conversation system performance
"""

import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Any

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy import func, desc, and_
from werkzeug.security import check_password_hash, generate_password_hash

from main import db, Conversation, ConversationEntry, limiter
from utils.validators import SecurityValidator
from config import Config

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin authentication
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123'))

class AdminMetrics:
    """Class for calculating admin dashboard metrics"""
    
    @staticmethod
    def get_conversation_stats(days: int = 30) -> Dict[str, Any]:
        """Get conversation statistics for the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Basic conversation stats
        total_conversations = Conversation.query.count()
        recent_conversations = Conversation.query.filter(
            Conversation.created_at >= cutoff_date
        ).count()
        
        completed_conversations = Conversation.query.filter(
            Conversation.is_complete == True
        ).count()
        
        # Average completion time for completed conversations
        completed_recent = Conversation.query.filter(
            and_(
                Conversation.is_complete == True,
                Conversation.created_at >= cutoff_date
            )
        ).all()
        
        avg_completion_time = None
        if completed_recent:
            completion_times = [
                (conv.updated_at - conv.created_at).total_seconds() / 60
                for conv in completed_recent
            ]
            avg_completion_time = sum(completion_times) / len(completion_times)
        
        return {
            'total_conversations': total_conversations,
            'recent_conversations': recent_conversations,
            'completed_conversations': completed_conversations,
            'completion_rate': (completed_conversations / total_conversations * 100) if total_conversations > 0 else 0,
            'avg_completion_time_minutes': avg_completion_time,
            'period_days': days
        }
    
    @staticmethod
    def get_agent_performance(days: int = 30) -> Dict[str, Any]:
        """Get agent performance metrics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Agent response counts
        agent_stats = db.session.query(
            ConversationEntry.agent_name,
            func.count(ConversationEntry.id).label('response_count'),
            func.avg(func.length(ConversationEntry.response_text)).label('avg_response_length')
        ).filter(
            ConversationEntry.created_at >= cutoff_date
        ).group_by(ConversationEntry.agent_name).all()
        
        # Agent response times (approximate based on creation time gaps)
        agent_response_times = {}
        for agent_name in ['Analyst', 'Researcher', 'Writer']:
            entries = ConversationEntry.query.filter(
                and_(
                    ConversationEntry.agent_name == agent_name,
                    ConversationEntry.created_at >= cutoff_date
                )
            ).order_by(ConversationEntry.created_at.desc()).limit(100).all()
            
            if entries:
                # Calculate average time between entries for this agent
                times = []
                for i in range(1, len(entries)):
                    time_diff = (entries[i-1].created_at - entries[i].created_at).total_seconds()
                    if time_diff > 0 and time_diff < 300:  # Filter out unrealistic times
                        times.append(time_diff)
                
                agent_response_times[agent_name] = sum(times) / len(times) if times else 0
        
        return {
            'agent_stats': [
                {
                    'agent': stat.agent_name,
                    'response_count': stat.response_count,
                    'avg_response_length': round(stat.avg_response_length) if stat.avg_response_length else 0,
                    'avg_response_time': round(agent_response_times.get(stat.agent_name, 0), 2)
                }
                for stat in agent_stats
            ],
            'period_days': days
        }
    
    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            # Database connection test
            db.session.execute('SELECT 1')
            db_healthy = True
            db_error = None
        except Exception as e:
            db_healthy = False
            db_error = str(e)
        
        # Recent error rate (last 24 hours)
        recent_conversations = Conversation.query.filter(
            Conversation.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        # Check for incomplete conversations older than 1 hour
        stale_conversations = Conversation.query.filter(
            and_(
                Conversation.is_complete == False,
                Conversation.updated_at < datetime.utcnow() - timedelta(hours=1)
            )
        ).count()
        
        return {
            'database_healthy': db_healthy,
            'database_error': db_error,
            'recent_activity': recent_conversations,
            'stale_conversations': stale_conversations,
            'openai_api_configured': bool(os.environ.get('OPENAI_API_KEY'))
        }
    
    @staticmethod
    def get_usage_trends(days: int = 7) -> Dict[str, Any]:
        """Get usage trends over time"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily conversation creation
        daily_stats = db.session.query(
            func.date(Conversation.created_at).label('date'),
            func.count(Conversation.id).label('count')
        ).filter(
            Conversation.created_at >= cutoff_date
        ).group_by(
            func.date(Conversation.created_at)
        ).order_by('date').all()
        
        # Hourly distribution (last 24 hours)
        hourly_stats = db.session.query(
            func.extract('hour', Conversation.created_at).label('hour'),
            func.count(Conversation.id).label('count')
        ).filter(
            Conversation.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).group_by(
            func.extract('hour', Conversation.created_at)
        ).order_by('hour').all()
        
        return {
            'daily_trends': [
                {
                    'date': stat.date.strftime('%Y-%m-%d'),
                    'conversations': stat.count
                }
                for stat in daily_stats
            ],
            'hourly_distribution': [
                {
                    'hour': int(stat.hour),
                    'conversations': stat.count
                }
                for stat in hourly_stats
            ]
        }

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_authenticated'] = True
            return redirect(url_for('admin.dashboard'))
        else:
            return render_template('admin/login.html', error='Invalid password')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    return redirect(url_for('admin.login'))

def admin_required(f):
    """Decorator for admin authentication"""
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
@limiter.limit("30 per minute")
def dashboard():
    """Main admin dashboard"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/api/stats')
@admin_required
@limiter.limit("60 per minute")
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        days = int(request.args.get('days', 30))
        days = min(days, 365)  # Max 1 year
        
        stats = {
            'conversation_stats': AdminMetrics.get_conversation_stats(days),
            'agent_performance': AdminMetrics.get_agent_performance(days),
            'system_health': AdminMetrics.get_system_health(),
            'usage_trends': AdminMetrics.get_usage_trends(min(days, 30))
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logging.error(f"Error fetching admin stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch statistics'
        }), 500

@admin_bp.route('/api/conversations')
@admin_required
@limiter.limit("30 per minute")
def api_conversations():
    """API endpoint for conversation management"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status = request.args.get('status', 'all')
        
        query = Conversation.query
        
        if status == 'complete':
            query = query.filter(Conversation.is_complete == True)
        elif status == 'incomplete':
            query = query.filter(Conversation.is_complete == False)
        elif status == 'stale':
            query = query.filter(
                and_(
                    Conversation.is_complete == False,
                    Conversation.updated_at < datetime.utcnow() - timedelta(hours=1)
                )
            )
        
        conversations = query.order_by(
            Conversation.created_at.desc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': {
                'conversations': [
                    {
                        'id': conv.id,
                        'initial_input': conv.initial_input[:100] + '...' if len(conv.initial_input) > 100 else conv.initial_input,
                        'created_at': conv.created_at.isoformat(),
                        'updated_at': conv.updated_at.isoformat(),
                        'is_complete': conv.is_complete,
                        'entry_count': conv.entries.count(),
                        'current_agent_index': conv.current_agent_index
                    }
                    for conv in conversations.items
                ],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': conversations.total,
                    'pages': conversations.pages,
                    'has_next': conversations.has_next,
                    'has_prev': conversations.has_prev
                }
            }
        })
        
    except Exception as e:
        logging.error(f"Error fetching conversations: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch conversations'
        }), 500

@admin_bp.route('/api/conversation/<conversation_id>')
@admin_required
@limiter.limit("30 per minute")
def api_conversation_detail(conversation_id):
    """API endpoint for detailed conversation view"""
    try:
        conversation = Conversation.query.get_or_404(conversation_id)
        entries = ConversationEntry.query.filter_by(
            conversation_id=conversation_id
        ).order_by(ConversationEntry.created_at).all()
        
        return jsonify({
            'success': True,
            'data': {
                'conversation': conversation.to_dict(),
                'entries': [entry.to_dict() for entry in entries]
            }
        })
        
    except Exception as e:
        logging.error(f"Error fetching conversation detail: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch conversation details'
        }), 500

@admin_bp.route('/conversations')
@admin_required
@limiter.limit("20 per minute")
def conversations():
    """Conversation management page"""
    return render_template('admin/conversations.html')

@admin_bp.route('/system')
@admin_required
@limiter.limit("20 per minute")
def system():
    """System monitoring page"""
    return render_template('admin/system.html')