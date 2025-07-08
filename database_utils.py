"""
Database utilities for enhanced conversation persistence and management
"""

from models import db, Conversation, ConversationEntry
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc, asc
import logging
from typing import List, Dict, Optional, Tuple


class DatabaseManager:
    """Enhanced database operations for conversation persistence"""
    
    @staticmethod
    def get_conversation_stats(days: int = 30) -> Dict:
        """Get comprehensive conversation statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            # Basic conversation stats
            total_conversations = Conversation.query.filter(
                Conversation.created_at >= cutoff_date
            ).count()
            
            completed_conversations = Conversation.query.filter(
                and_(
                    Conversation.created_at >= cutoff_date,
                    Conversation.is_complete == True
                )
            ).count()
            
            # Average completion time
            avg_completion_time = db.session.query(
                func.avg(
                    func.extract('epoch', Conversation.completion_time - Conversation.created_at)
                )
            ).filter(
                and_(
                    Conversation.created_at >= cutoff_date,
                    Conversation.completion_time.isnot(None)
                )
            ).scalar() or 0
            
            # Token usage stats
            total_tokens = db.session.query(
                func.sum(Conversation.total_tokens_used)
            ).filter(
                Conversation.created_at >= cutoff_date
            ).scalar() or 0
            
            avg_tokens_per_conversation = total_tokens / total_conversations if total_conversations > 0 else 0
            
            # Error statistics
            conversations_with_errors = Conversation.query.filter(
                and_(
                    Conversation.created_at >= cutoff_date,
                    Conversation.error_count > 0
                )
            ).count()
            
            error_rate = (conversations_with_errors / total_conversations * 100) if total_conversations > 0 else 0
            
            return {
                'total_conversations': total_conversations,
                'completed_conversations': completed_conversations,
                'completion_rate': (completed_conversations / total_conversations * 100) if total_conversations > 0 else 0,
                'avg_completion_time_seconds': avg_completion_time,
                'total_tokens_used': total_tokens,
                'avg_tokens_per_conversation': round(avg_tokens_per_conversation),
                'conversations_with_errors': conversations_with_errors,
                'error_rate': round(error_rate, 2),
                'period_days': days
            }
            
        except Exception as e:
            logging.error(f"Error getting conversation stats: {str(e)}")
            return {
                'total_conversations': 0,
                'completed_conversations': 0,
                'completion_rate': 0,
                'avg_completion_time_seconds': 0,
                'total_tokens_used': 0,
                'avg_tokens_per_conversation': 0,
                'conversations_with_errors': 0,
                'error_rate': 0,
                'period_days': days
            }
    
    @staticmethod
    def get_conversation_list(page: int = 1, per_page: int = 10, 
                             search_query: Optional[str] = None,
                             completed_only: bool = False) -> Tuple[List[Dict], int]:
        """Get paginated conversation list with search and filtering"""
        try:
            query = Conversation.query.order_by(desc(Conversation.created_at))
            
            # Apply filters
            if completed_only:
                query = query.filter(Conversation.is_complete == True)
            
            if search_query:
                search_pattern = f"%{search_query}%"
                query = query.filter(
                    or_(
                        Conversation.initial_input.ilike(search_pattern),
                        Conversation.id.ilike(search_pattern)
                    )
                )
            
            # Get paginated results
            paginated = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            conversations = [conv.get_summary() for conv in paginated.items]
            total = paginated.total
            
            return conversations, total
            
        except Exception as e:
            logging.error(f"Error getting conversation list: {str(e)}")
            return [], 0
    
    @staticmethod
    def get_conversation_with_entries(conversation_id: str) -> Optional[Dict]:
        """Get complete conversation with all entries"""
        try:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return None
            
            return conversation.to_dict()
            
        except Exception as e:
            logging.error(f"Error getting conversation {conversation_id}: {str(e)}")
            return None
    
    @staticmethod
    def delete_conversation(conversation_id: str) -> bool:
        """Delete a conversation and all its entries"""
        try:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return False
            
            # Delete all entries first (cascade should handle this, but being explicit)
            ConversationEntry.query.filter_by(conversation_id=conversation_id).delete()
            
            # Delete the conversation
            db.session.delete(conversation)
            db.session.commit()
            
            logging.info(f"Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error deleting conversation {conversation_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_stale_conversations(hours: int = 24) -> List[Dict]:
        """Get conversations that have been inactive for specified hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            stale_conversations = Conversation.query.filter(
                and_(
                    Conversation.updated_at < cutoff_time,
                    Conversation.is_complete == False
                )
            ).all()
            
            return [conv.get_summary() for conv in stale_conversations]
            
        except Exception as e:
            logging.error(f"Error getting stale conversations: {str(e)}")
            return []
    
    @staticmethod
    def cleanup_old_conversations(days: int = 90) -> int:
        """Clean up conversations older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Count conversations to be deleted
            count = Conversation.query.filter(
                Conversation.created_at < cutoff_date
            ).count()
            
            # Delete old conversations (cascade will handle entries)
            Conversation.query.filter(
                Conversation.created_at < cutoff_date
            ).delete()
            
            db.session.commit()
            logging.info(f"Cleaned up {count} old conversations")
            return count
            
        except Exception as e:
            logging.error(f"Error cleaning up old conversations: {str(e)}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def get_session_conversations(session_id: str) -> List[Dict]:
        """Get all conversations for a specific session"""
        try:
            conversations = Conversation.query.filter_by(
                session_id=session_id
            ).order_by(desc(Conversation.created_at)).all()
            
            return [conv.get_summary() for conv in conversations]
            
        except Exception as e:
            logging.error(f"Error getting session conversations: {str(e)}")
            return []
    
    @staticmethod
    def get_agent_response_times(days: int = 30) -> Dict:
        """Get detailed agent response time statistics"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get processing times by agent
            agent_times = db.session.query(
                ConversationEntry.agent_name,
                func.avg(ConversationEntry.processing_time_seconds).label('avg_time'),
                func.min(ConversationEntry.processing_time_seconds).label('min_time'),
                func.max(ConversationEntry.processing_time_seconds).label('max_time'),
                func.count(ConversationEntry.id).label('response_count')
            ).filter(
                and_(
                    ConversationEntry.created_at >= cutoff_date,
                    ConversationEntry.error_occurred == False,
                    ConversationEntry.processing_time_seconds > 0
                )
            ).group_by(ConversationEntry.agent_name).all()
            
            return {
                'agent_times': [
                    {
                        'agent_name': at.agent_name,
                        'avg_time': round(at.avg_time, 2) if at.avg_time else 0,
                        'min_time': round(at.min_time, 2) if at.min_time else 0,
                        'max_time': round(at.max_time, 2) if at.max_time else 0,
                        'response_count': at.response_count
                    }
                    for at in agent_times
                ],
                'period_days': days
            }
            
        except Exception as e:
            logging.error(f"Error getting agent response times: {str(e)}")
            return {'agent_times': [], 'period_days': days}
    
    @staticmethod
    def get_error_analysis(days: int = 30) -> Dict:
        """Get detailed error analysis"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get error entries
            error_entries = ConversationEntry.query.filter(
                and_(
                    ConversationEntry.created_at >= cutoff_date,
                    ConversationEntry.error_occurred == True
                )
            ).order_by(desc(ConversationEntry.created_at)).limit(50).all()
            
            # Group errors by agent
            errors_by_agent = {}
            for entry in error_entries:
                agent = entry.agent_name
                if agent not in errors_by_agent:
                    errors_by_agent[agent] = []
                errors_by_agent[agent].append({
                    'id': entry.id,
                    'conversation_id': entry.conversation_id,
                    'error_message': entry.error_message,
                    'created_at': entry.created_at.isoformat()
                })
            
            return {
                'total_errors': len(error_entries),
                'errors_by_agent': errors_by_agent,
                'recent_errors': [
                    {
                        'id': entry.id,
                        'conversation_id': entry.conversation_id,
                        'agent_name': entry.agent_name,
                        'error_message': entry.error_message,
                        'created_at': entry.created_at.isoformat()
                    }
                    for entry in error_entries[:10]
                ],
                'period_days': days
            }
            
        except Exception as e:
            logging.error(f"Error getting error analysis: {str(e)}")
            return {
                'total_errors': 0,
                'errors_by_agent': {},
                'recent_errors': [],
                'period_days': days
            }
    
    @staticmethod
    def backup_conversation_data(conversation_id: str) -> Optional[Dict]:
        """Create a backup of conversation data"""
        try:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return None
            
            backup_data = {
                'conversation': conversation.to_dict(),
                'backup_timestamp': datetime.utcnow().isoformat(),
                'version': '1.0'
            }
            
            return backup_data
            
        except Exception as e:
            logging.error(f"Error backing up conversation {conversation_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_database_health() -> Dict:
        """Get database health and performance metrics"""
        try:
            # Test basic connectivity
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1')).scalar()
            if result != 1:
                raise Exception("Database connectivity test failed")
            
            # Get table sizes
            conversation_count = Conversation.query.count()
            entry_count = ConversationEntry.query.count()
            
            # Get recent activity
            recent_conversations = Conversation.query.filter(
                Conversation.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            # Check for long-running queries or locks (simplified)
            database_size = db.session.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            ).scalar()
            
            return {
                'healthy': True,
                'conversation_count': conversation_count,
                'entry_count': entry_count,
                'recent_conversations_24h': recent_conversations,
                'database_size': database_size,
                'connection_status': 'connected',
                'last_checked': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Database health check failed: {str(e)}")
            return {
                'healthy': False,
                'error': str(e),
                'last_checked': datetime.utcnow().isoformat()
            }