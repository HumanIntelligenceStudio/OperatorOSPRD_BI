"""
Real-time Human-Clarity Feedback System
Allows users to provide feedback on agent response clarity for continuous improvement
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from main import db
from models import ConversationEntry


class FeedbackType(Enum):
    CLARITY = "clarity"
    EMPATHY = "empathy"
    ACTIONABILITY = "actionability"
    OVERALL = "overall"


@dataclass
class UserFeedback:
    """User feedback on agent response clarity"""
    entry_id: int
    feedback_type: FeedbackType
    rating: int  # 1-5 scale
    comment: Optional[str] = None
    timestamp: datetime = None
    user_session: Optional[str] = None


class ClarityFeedbackManager:
    """Manages user feedback on response clarity for continuous improvement"""
    
    def __init__(self):
        self.feedback_storage = []
        
    def submit_feedback(self, entry_id: int, clarity_rating: int, 
                       empathy_rating: int, actionability_rating: int,
                       overall_rating: int, comment: str = None,
                       user_session: str = None) -> bool:
        """Submit user feedback for an agent response"""
        try:
            # Validate ratings
            for rating in [clarity_rating, empathy_rating, actionability_rating, overall_rating]:
                if not 1 <= rating <= 5:
                    raise ValueError("Ratings must be between 1 and 5")
            
            # Get the conversation entry
            entry = ConversationEntry.query.get(entry_id)
            if not entry:
                raise ValueError(f"Entry {entry_id} not found")
            
            # Create feedback data
            feedback_data = {
                "user_feedback": {
                    "clarity_rating": clarity_rating,
                    "empathy_rating": empathy_rating,
                    "actionability_rating": actionability_rating,
                    "overall_rating": overall_rating,
                    "comment": comment,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_session": user_session
                }
            }
            
            # Store in the entry's error_message field (as JSON metadata)
            if entry.error_message:
                try:
                    existing_data = json.loads(entry.error_message)
                    existing_data.update(feedback_data)
                    entry.error_message = json.dumps(existing_data)
                except:
                    entry.error_message = json.dumps(feedback_data)
            else:
                entry.error_message = json.dumps(feedback_data)
            
            db.session.commit()
            
            # Analyze feedback for improvement suggestions
            self._analyze_feedback_for_improvements(entry_id, feedback_data["user_feedback"])
            
            logging.info(f"User feedback submitted for entry {entry_id}: overall={overall_rating}/5")
            return True
            
        except Exception as e:
            logging.error(f"Failed to submit feedback: {str(e)}")
            return False
    
    def _analyze_feedback_for_improvements(self, entry_id: int, feedback: Dict):
        """Analyze feedback to generate improvement suggestions"""
        try:
            suggestions = []
            
            # Low clarity rating
            if feedback["clarity_rating"] <= 2:
                suggestions.append("Response clarity needs improvement - consider simpler language")
            
            # Low empathy rating
            if feedback["empathy_rating"] <= 2:
                suggestions.append("Response lacks empathy - add acknowledgment of user's situation")
            
            # Low actionability rating
            if feedback["actionability_rating"] <= 2:
                suggestions.append("Response needs clearer action items - add specific next steps")
            
            # Overall low rating
            if feedback["overall_rating"] <= 2:
                suggestions.append("Overall response quality is poor - review all aspects")
            
            # Log suggestions for agent improvement
            if suggestions:
                logging.warning(f"Improvement needed for entry {entry_id}: {'; '.join(suggestions)}")
                
                # Store suggestions in notification system
                from notifications import notification_manager
                notification_manager.add_notification(
                    title="Response Quality Alert",
                    message=f"Entry {entry_id} received low user ratings. Suggestions: {'; '.join(suggestions)}",
                    level="warning"
                )
                
        except Exception as e:
            logging.error(f"Failed to analyze feedback: {str(e)}")
    
    def get_feedback_stats(self, days: int = 7) -> Dict:
        """Get feedback statistics for the last N days"""
        try:
            from datetime import timedelta
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Query entries with feedback
            entries = ConversationEntry.query.filter(
                ConversationEntry.created_at >= since_date,
                ConversationEntry.error_message.isnot(None)
            ).all()
            
            feedback_data = []
            for entry in entries:
                try:
                    if entry.error_message:
                        data = json.loads(entry.error_message)
                        if "user_feedback" in data:
                            feedback_data.append({
                                "entry_id": entry.id,
                                "agent": entry.agent_name,
                                **data["user_feedback"]
                            })
                except:
                    continue
            
            if not feedback_data:
                return {"error": "No feedback data available"}
            
            # Calculate averages
            total_feedback = len(feedback_data)
            avg_clarity = sum(f["clarity_rating"] for f in feedback_data) / total_feedback
            avg_empathy = sum(f["empathy_rating"] for f in feedback_data) / total_feedback
            avg_actionability = sum(f["actionability_rating"] for f in feedback_data) / total_feedback
            avg_overall = sum(f["overall_rating"] for f in feedback_data) / total_feedback
            
            # Agent-specific stats
            agent_stats = {}
            for feedback in feedback_data:
                agent = feedback["agent"]
                if agent not in agent_stats:
                    agent_stats[agent] = []
                agent_stats[agent].append(feedback["overall_rating"])
            
            agent_averages = {
                agent: round(sum(ratings) / len(ratings), 1)
                for agent, ratings in agent_stats.items()
            }
            
            return {
                "total_feedback_count": total_feedback,
                "average_clarity": round(avg_clarity, 1),
                "average_empathy": round(avg_empathy, 1),
                "average_actionability": round(avg_actionability, 1),
                "average_overall": round(avg_overall, 1),
                "agent_ratings": agent_averages,
                "feedback_trend": "improving" if avg_overall > 3.5 else "needs_attention",
                "period_days": days
            }
            
        except Exception as e:
            logging.error(f"Failed to get feedback stats: {str(e)}")
            return {"error": str(e)}
    
    def get_low_rated_responses(self, threshold: int = 2) -> List[Dict]:
        """Get responses with low user ratings for improvement analysis"""
        try:
            entries = ConversationEntry.query.filter(
                ConversationEntry.error_message.isnot(None)
            ).all()
            
            low_rated = []
            for entry in entries:
                try:
                    if entry.error_message:
                        data = json.loads(entry.error_message)
                        if "user_feedback" in data:
                            feedback = data["user_feedback"]
                            if feedback.get("overall_rating", 5) <= threshold:
                                low_rated.append({
                                    "entry_id": entry.id,
                                    "agent": entry.agent_name,
                                    "input_text": entry.input_text[:100] + "...",
                                    "response_text": entry.response_text[:200] + "...",
                                    "feedback": feedback,
                                    "created_at": entry.created_at.isoformat()
                                })
                except:
                    continue
            
            return sorted(low_rated, key=lambda x: x["feedback"]["overall_rating"])
            
        except Exception as e:
            logging.error(f"Failed to get low rated responses: {str(e)}")
            return []
    
    def generate_improvement_report(self) -> Dict:
        """Generate a comprehensive improvement report based on user feedback"""
        try:
            stats = self.get_feedback_stats(days=30)
            low_rated = self.get_low_rated_responses(threshold=2)
            
            # Identify patterns in low-rated responses
            common_issues = {}
            for response in low_rated:
                feedback = response["feedback"]
                if feedback["clarity_rating"] <= 2:
                    common_issues["clarity"] = common_issues.get("clarity", 0) + 1
                if feedback["empathy_rating"] <= 2:
                    common_issues["empathy"] = common_issues.get("empathy", 0) + 1
                if feedback["actionability_rating"] <= 2:
                    common_issues["actionability"] = common_issues.get("actionability", 0) + 1
            
            # Generate recommendations
            recommendations = []
            if common_issues.get("clarity", 0) > 3:
                recommendations.append("Focus on simpler, clearer language in responses")
            if common_issues.get("empathy", 0) > 3:
                recommendations.append("Increase empathy and acknowledgment in agent prompts")
            if common_issues.get("actionability", 0) > 3:
                recommendations.append("Ensure all responses include specific, actionable next steps")
            
            return {
                "overview": stats,
                "low_rated_count": len(low_rated),
                "common_issues": common_issues,
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Failed to generate improvement report: {str(e)}")
            return {"error": str(e)}


# Global instance
feedback_manager = ClarityFeedbackManager()