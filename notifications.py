"""
Real-time notification system for admin monitoring
"""

import os
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json

from flask_socketio import SocketIO, emit
from sqlalchemy import func, and_
from main import db, Conversation, ConversationEntry


class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Notification:
    id: str
    title: str
    message: str
    level: NotificationLevel
    timestamp: datetime
    data: Optional[Dict] = None
    acknowledged: bool = False


class NotificationManager:
    """Manages real-time notifications and alerts"""
    
    def __init__(self, socketio: SocketIO = None):
        self.socketio = socketio
        self.notifications: List[Notification] = []
        self.max_notifications = 100
        self.email_enabled = bool(os.environ.get('SMTP_SERVER'))
        self.setup_email()
    
    def setup_email(self):
        """Setup email configuration"""
        if self.email_enabled:
            self.smtp_server = os.environ.get('SMTP_SERVER')
            self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
            self.smtp_username = os.environ.get('SMTP_USERNAME')
            self.smtp_password = os.environ.get('SMTP_PASSWORD')
            self.from_email = os.environ.get('FROM_EMAIL', self.smtp_username)
            self.admin_emails = os.environ.get('ADMIN_EMAILS', '').split(',')
            self.admin_emails = [email.strip() for email in self.admin_emails if email.strip()]
    
    def add_notification(self, title: str, message: str, level: NotificationLevel, 
                        data: Optional[Dict] = None, send_email: bool = False):
        """Add a new notification"""
        notification = Notification(
            id=f"notif_{datetime.utcnow().timestamp()}",
            title=title,
            message=message,
            level=level,
            timestamp=datetime.utcnow(),
            data=data or {}
        )
        
        self.notifications.insert(0, notification)
        
        # Keep only latest notifications
        if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[:self.max_notifications]
        
        # Send real-time notification via WebSocket
        if self.socketio:
            self.socketio.emit('admin_notification', {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'level': notification.level.value,
                'timestamp': notification.timestamp.isoformat(),
                'data': notification.data
            }, namespace='/admin')
        
        # Send email for critical/error notifications
        if send_email and level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]:
            self.send_email_alert(notification)
        
        # Log notification
        log_level = {
            NotificationLevel.INFO: logging.info,
            NotificationLevel.WARNING: logging.warning,
            NotificationLevel.ERROR: logging.error,
            NotificationLevel.CRITICAL: logging.critical
        }[level]
        
        log_level(f"Admin notification: {title} - {message}")
        
        return notification
    
    def send_email_alert(self, notification: Notification):
        """Send email alert for critical notifications"""
        if not self.email_enabled or not self.admin_emails:
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.admin_emails)
            msg['Subject'] = f"[{notification.level.value.upper()}] Multi-Agent AI System Alert: {notification.title}"
            
            body = f"""
System Alert - Multi-Agent AI Conversation System

Level: {notification.level.value.upper()}
Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
Title: {notification.title}

Message:
{notification.message}

Additional Data:
{json.dumps(notification.data, indent=2) if notification.data else 'None'}

Please check the admin dashboard for more details: /admin/dashboard

This is an automated message from the Multi-Agent AI System monitoring.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logging.info(f"Email alert sent for notification: {notification.title}")
            
        except Exception as e:
            logging.error(f"Failed to send email alert: {str(e)}")
    
    def get_notifications(self, limit: int = 50, level: Optional[NotificationLevel] = None) -> List[Dict]:
        """Get recent notifications"""
        notifications = self.notifications[:limit]
        
        if level:
            notifications = [n for n in notifications if n.level == level]
        
        return [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'level': n.level.value,
                'timestamp': n.timestamp.isoformat(),
                'data': n.data,
                'acknowledged': n.acknowledged
            }
            for n in notifications
        ]
    
    def acknowledge_notification(self, notification_id: str) -> bool:
        """Mark notification as acknowledged"""
        for notification in self.notifications:
            if notification.id == notification_id:
                notification.acknowledged = True
                return True
        return False
    
    def clear_notifications(self, level: Optional[NotificationLevel] = None):
        """Clear notifications"""
        if level:
            self.notifications = [n for n in self.notifications if n.level != level]
        else:
            self.notifications = []


class SystemMonitor:
    """Monitors system health and performance"""
    
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager
        self.last_check = datetime.utcnow()
        self.thresholds = {
            'max_stale_conversations': int(os.environ.get('MAX_STALE_CONVERSATIONS', '10')),
            'max_error_rate': float(os.environ.get('MAX_ERROR_RATE', '0.1')),  # 10%
            'min_completion_rate': float(os.environ.get('MIN_COMPLETION_RATE', '0.8')),  # 80%
            'max_avg_response_time': int(os.environ.get('MAX_AVG_RESPONSE_TIME', '300')),  # 5 minutes
        }
    
    def check_system_health(self):
        """Perform comprehensive system health check"""
        try:
            current_time = datetime.utcnow()
            
            # Check for stale conversations
            self.check_stale_conversations()
            
            # Check completion rates
            self.check_completion_rates()
            
            # Check response times
            self.check_response_times()
            
            # Check database connectivity
            self.check_database_health()
            
            # Check recent errors
            self.check_error_patterns()
            
            self.last_check = current_time
            
        except Exception as e:
            self.notification_manager.add_notification(
                "System Health Check Failed",
                f"Failed to perform system health check: {str(e)}",
                NotificationLevel.ERROR,
                {"error": str(e)},
                send_email=True
            )
    
    def check_stale_conversations(self):
        """Check for conversations that have been stuck"""
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        
        stale_count = Conversation.query.filter(
            and_(
                Conversation.is_complete == False,
                Conversation.updated_at < cutoff_time
            )
        ).count()
        
        if stale_count > self.thresholds['max_stale_conversations']:
            self.notification_manager.add_notification(
                "High Number of Stale Conversations",
                f"Found {stale_count} conversations that haven't been updated in over 2 hours",
                NotificationLevel.WARNING,
                {"stale_count": stale_count, "threshold": self.thresholds['max_stale_conversations']},
                send_email=True
            )
    
    def check_completion_rates(self):
        """Check conversation completion rates"""
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        
        total_recent = Conversation.query.filter(
            Conversation.created_at >= recent_cutoff
        ).count()
        
        if total_recent > 5:  # Only check if we have sufficient data
            completed_recent = Conversation.query.filter(
                and_(
                    Conversation.created_at >= recent_cutoff,
                    Conversation.is_complete == True
                )
            ).count()
            
            completion_rate = completed_recent / total_recent if total_recent > 0 else 0
            
            if completion_rate < self.thresholds['min_completion_rate']:
                self.notification_manager.add_notification(
                    "Low Completion Rate Detected",
                    f"Completion rate in last 24h: {completion_rate:.1%} (threshold: {self.thresholds['min_completion_rate']:.1%})",
                    NotificationLevel.WARNING,
                    {
                        "completion_rate": completion_rate,
                        "completed": completed_recent,
                        "total": total_recent,
                        "threshold": self.thresholds['min_completion_rate']
                    },
                    send_email=True
                )
    
    def check_response_times(self):
        """Check average response times"""
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        
        # Get recent completed conversations
        recent_conversations = Conversation.query.filter(
            and_(
                Conversation.updated_at >= recent_cutoff,
                Conversation.is_complete == True
            )
        ).all()
        
        if len(recent_conversations) > 3:  # Only check if we have sufficient data
            total_time = 0
            for conv in recent_conversations:
                completion_time = (conv.updated_at - conv.created_at).total_seconds()
                total_time += completion_time
            
            avg_response_time = total_time / len(recent_conversations)
            
            if avg_response_time > self.thresholds['max_avg_response_time']:
                self.notification_manager.add_notification(
                    "High Average Response Time",
                    f"Average completion time in last hour: {avg_response_time:.1f}s (threshold: {self.thresholds['max_avg_response_time']}s)",
                    NotificationLevel.WARNING,
                    {
                        "avg_response_time": avg_response_time,
                        "threshold": self.thresholds['max_avg_response_time'],
                        "sample_size": len(recent_conversations)
                    }
                )
    
    def check_database_health(self):
        """Check database connectivity and performance"""
        try:
            # Test basic query
            db.session.execute('SELECT 1')
            
            # Check for connection pool issues
            pool_size = db.engine.pool.size()
            checked_out = db.engine.pool.checkedout()
            
            if checked_out > pool_size * 0.8:  # 80% of pool used
                self.notification_manager.add_notification(
                    "Database Connection Pool Warning",
                    f"High database connection usage: {checked_out}/{pool_size} connections in use",
                    NotificationLevel.WARNING,
                    {"checked_out": checked_out, "pool_size": pool_size}
                )
                
        except Exception as e:
            self.notification_manager.add_notification(
                "Database Health Check Failed",
                f"Database connectivity issue: {str(e)}",
                NotificationLevel.CRITICAL,
                {"error": str(e)},
                send_email=True
            )
    
    def check_error_patterns(self):
        """Check for error patterns in recent activity"""
        # This would typically analyze application logs
        # For now, we'll check for recent failed conversations
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        
        # Find conversations that started recently but haven't progressed
        stuck_conversations = Conversation.query.filter(
            and_(
                Conversation.created_at >= recent_cutoff,
                Conversation.current_agent_index == 0,
                Conversation.is_complete == False
            )
        ).count()
        
        total_recent = Conversation.query.filter(
            Conversation.created_at >= recent_cutoff
        ).count()
        
        if total_recent > 5 and stuck_conversations > total_recent * 0.2:  # 20% stuck
            self.notification_manager.add_notification(
                "High Number of Stuck Conversations",
                f"{stuck_conversations} of {total_recent} recent conversations appear stuck at the first agent",
                NotificationLevel.WARNING,
                {"stuck_count": stuck_conversations, "total_recent": total_recent}
            )


# Global notification manager instance
notification_manager = NotificationManager()
system_monitor = SystemMonitor(notification_manager)