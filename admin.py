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
from notifications import notification_manager, system_monitor, NotificationLevel

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
        """Get comprehensive agent performance metrics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Enhanced agent statistics
        agent_stats = db.session.query(
            ConversationEntry.agent_name,
            ConversationEntry.agent_role,
            func.count(ConversationEntry.id).label('response_count'),
            func.avg(func.length(ConversationEntry.response_text)).label('avg_response_length'),
            func.count(func.distinct(ConversationEntry.conversation_id)).label('conversations_handled'),
            func.min(ConversationEntry.created_at).label('first_response'),
            func.max(ConversationEntry.created_at).label('last_response'),
            func.avg(func.length(ConversationEntry.next_question)).label('avg_question_length')
        ).filter(
            ConversationEntry.created_at >= cutoff_date
        ).group_by(ConversationEntry.agent_name, ConversationEntry.agent_role).all()
        
        # Calculate agent success rates and handoff efficiency
        agent_success_rates = []
        handoff_efficiency = []
        
        for agent_name in ['Analyst', 'Researcher', 'Writer']:
            # Count conversations that reached this agent
            conversations_reached = db.session.query(
                func.count(func.distinct(ConversationEntry.conversation_id))
            ).filter(
                and_(
                    ConversationEntry.agent_name == agent_name,
                    ConversationEntry.created_at >= cutoff_date
                )
            ).scalar() or 0
            
            if agent_name == 'Writer':
                # For writer, check completion rate
                conversations_completed = db.session.query(
                    func.count(func.distinct(Conversation.id))
                ).join(ConversationEntry).filter(
                    and_(
                        ConversationEntry.agent_name == agent_name,
                        ConversationEntry.created_at >= cutoff_date,
                        Conversation.is_complete == True
                    )
                ).scalar() or 0
            else:
                # For other agents, check handoff success
                next_agent = {'Analyst': 'Researcher', 'Researcher': 'Writer'}[agent_name]
                conversations_completed = db.session.query(
                    func.count(func.distinct(ConversationEntry.conversation_id))
                ).filter(
                    and_(
                        ConversationEntry.agent_name == next_agent,
                        ConversationEntry.conversation_id.in_(
                            db.session.query(ConversationEntry.conversation_id).filter(
                                and_(
                                    ConversationEntry.agent_name == agent_name,
                                    ConversationEntry.created_at >= cutoff_date
                                )
                            )
                        )
                    )
                ).scalar() or 0
            
            success_rate = (conversations_completed / conversations_reached * 100) if conversations_reached > 0 else 0
            agent_success_rates.append({
                'agent_name': agent_name,
                'conversations_reached': conversations_reached,
                'conversations_completed': conversations_completed,
                'success_rate': round(success_rate, 2)
            })
        
        # Daily performance trends
        daily_performance = db.session.query(
            ConversationEntry.agent_name,
            func.date(ConversationEntry.created_at).label('date'),
            func.count(ConversationEntry.id).label('responses'),
            func.avg(func.length(ConversationEntry.response_text)).label('avg_length'),
            func.count(func.distinct(ConversationEntry.conversation_id)).label('unique_conversations')
        ).filter(
            ConversationEntry.created_at >= cutoff_date
        ).group_by(
            ConversationEntry.agent_name,
            func.date(ConversationEntry.created_at)
        ).order_by('date').all()
        
        # Agent response time analysis
        agent_response_times = {}
        conversation_durations = {}
        
        for agent_name in ['Analyst', 'Researcher', 'Writer']:
            # Get recent entries for this agent
            entries = ConversationEntry.query.filter(
                and_(
                    ConversationEntry.agent_name == agent_name,
                    ConversationEntry.created_at >= cutoff_date
                )
            ).order_by(ConversationEntry.created_at.desc()).limit(200).all()
            
            if entries:
                # Calculate processing times within conversations
                times = []
                for entry in entries:
                    # Get conversation start time
                    conv_start = db.session.query(Conversation.created_at).filter(
                        Conversation.id == entry.conversation_id
                    ).scalar()
                    
                    if conv_start:
                        processing_time = (entry.created_at - conv_start).total_seconds()
                        if processing_time > 0 and processing_time < 1800:  # Filter unrealistic times (30 min max)
                            times.append(processing_time)
                
                agent_response_times[agent_name] = {
                    'avg_processing_time': round(sum(times) / len(times), 2) if times else 0,
                    'min_processing_time': round(min(times), 2) if times else 0,
                    'max_processing_time': round(max(times), 2) if times else 0
                }
        
        # Agent quality metrics (based on response characteristics)
        quality_metrics = []
        for agent_name in ['Analyst', 'Researcher', 'Writer']:
            entries = ConversationEntry.query.filter(
                and_(
                    ConversationEntry.agent_name == agent_name,
                    ConversationEntry.created_at >= cutoff_date
                )
            ).all()
            
            if entries:
                # Calculate quality indicators
                total_responses = len(entries)
                responses_with_questions = sum(1 for e in entries if e.next_question and len(e.next_question.strip()) > 10)
                avg_response_length = sum(len(e.response_text) for e in entries) / total_responses
                
                quality_metrics.append({
                    'agent_name': agent_name,
                    'question_generation_rate': round((responses_with_questions / total_responses * 100), 2),
                    'avg_response_length': round(avg_response_length),
                    'response_consistency': round(min(100, (avg_response_length / 500) * 100), 2),  # Normalized score
                    'total_responses': total_responses
                })
        
        # Performance rankings
        if agent_stats:
            most_active = max(agent_stats, key=lambda x: x.response_count)
            most_efficient = min(agent_stats, key=lambda x: x.avg_response_length or float('inf'))
            
            performance_summary = {
                'total_agents': len(agent_stats),
                'most_active_agent': most_active.agent_name,
                'most_efficient_agent': most_efficient.agent_name,
                'best_success_rate': max(agent_success_rates, key=lambda x: x['success_rate'])['agent_name'] if agent_success_rates else None,
                'total_responses': sum(stat.response_count for stat in agent_stats),
                'avg_response_length_all': round(sum(stat.avg_response_length or 0 for stat in agent_stats) / len(agent_stats)),
                'period_days': days
            }
        else:
            performance_summary = {
                'total_agents': 0,
                'most_active_agent': None,
                'most_efficient_agent': None,
                'best_success_rate': None,
                'total_responses': 0,
                'avg_response_length_all': 0,
                'period_days': days
            }
        
        return {
            'agent_stats': [
                {
                    'agent': stat.agent_name,
                    'role': stat.agent_role,
                    'response_count': stat.response_count,
                    'avg_response_length': round(stat.avg_response_length) if stat.avg_response_length else 0,
                    'conversations_handled': stat.conversations_handled,
                    'first_response': stat.first_response.isoformat() if stat.first_response else None,
                    'last_response': stat.last_response.isoformat() if stat.last_response else None,
                    'avg_question_length': round(stat.avg_question_length) if stat.avg_question_length else 0,
                    'processing_times': agent_response_times.get(stat.agent_name, {})
                }
                for stat in agent_stats
            ],
            'success_rates': agent_success_rates,
            'daily_performance': [
                {
                    'agent_name': perf.agent_name,
                    'date': perf.date.strftime('%Y-%m-%d'),
                    'responses': perf.responses,
                    'avg_length': round(perf.avg_length) if perf.avg_length else 0,
                    'unique_conversations': perf.unique_conversations
                }
                for perf in daily_performance
            ],
            'quality_metrics': quality_metrics,
            'performance_summary': performance_summary,
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

@admin_bp.route('/agent-performance')
@admin_required
@limiter.limit("20 per minute")
def agent_performance():
    """Agent performance analytics page"""
    return render_template('admin/agent_performance.html')


# Real-time notification API endpoints
@admin_bp.route('/api/notifications')
@admin_required
@limiter.limit("60 per minute")
def api_notifications():
    """API endpoint for getting admin notifications"""
    try:
        limit = request.args.get('limit', 50, type=int)
        level = request.args.get('level')
        
        # Convert level string to enum if provided
        notification_level = None
        if level:
            notification_level = NotificationLevel(level)
        
        notifications = notification_manager.get_notifications(limit, notification_level)
        
        return jsonify({
            'success': True,
            'data': {
                'notifications': notifications,
                'total': len(notifications)
            }
        })
    
    except Exception as e:
        logging.error(f"Error fetching notifications: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch notifications'
        }), 500


@admin_bp.route('/api/notifications/<notification_id>/acknowledge', methods=['POST'])
@admin_required
@limiter.limit("30 per minute")
def api_acknowledge_notification(notification_id):
    """API endpoint for acknowledging a notification"""
    try:
        success = notification_manager.acknowledge_notification(notification_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Notification acknowledged'})
        else:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
    
    except Exception as e:
        logging.error(f"Error acknowledging notification: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to acknowledge notification'}), 500


@admin_bp.route('/api/notifications/clear', methods=['POST'])
@admin_required
@limiter.limit("10 per minute")
def api_clear_notifications():
    """API endpoint for clearing notifications"""
    try:
        level = request.json.get('level') if request.json else None
        
        # Convert level string to enum if provided
        notification_level = None
        if level:
            notification_level = NotificationLevel(level)
        
        notification_manager.clear_notifications(notification_level)
        
        return jsonify({'success': True, 'message': 'Notifications cleared'})
    
    except Exception as e:
        logging.error(f"Error clearing notifications: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to clear notifications'}), 500


@admin_bp.route('/api/system/check-health', methods=['POST'])
@admin_required
@limiter.limit("5 per minute")
def api_check_system_health():
    """API endpoint for triggering system health check"""
    try:
        system_monitor.check_system_health()
        
        return jsonify({
            'success': True, 
            'message': 'System health check completed',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logging.error(f"Error running system health check: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to run system health check'}), 500