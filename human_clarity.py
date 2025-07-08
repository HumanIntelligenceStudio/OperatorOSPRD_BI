"""
Human-Clarity Prompt Engine Integration
Measures and improves how well AI agents serve human understanding
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from main import db
from models import ConversationEntry, Conversation


class ClarityLevel(Enum):
    EXCELLENT = "excellent"  # Human feels seen, understood, and empowered
    GOOD = "good"           # Clear direction but could be more human-centered
    FAIR = "fair"           # Functional but lacks empathy or clarity
    POOR = "poor"           # Confusing or doesn't serve human needs


@dataclass
class ClarityMetrics:
    """Metrics for measuring human-clarity in agent responses"""
    clarity_score: float  # 0-100 scale
    empathy_detected: bool
    actionability: float  # How clear the next steps are
    understanding_shown: bool  # Does response show understanding of human need
    dignity_preserved: bool
    loop_completion: float  # How well it closes the mental loop


class HumanClarityEngine:
    """Engine for measuring and improving human-clarity in AI responses"""
    
    def __init__(self):
        self.clarity_patterns = {
            # Positive patterns that show human understanding
            "empathy_indicators": [
                "I understand you're trying to",
                "What you're looking for",
                "This will help you",
                "You're working toward",
                "I can see that",
                "This matters because"
            ],
            "action_clarity": [
                "Here's what to do next",
                "Your next step",
                "You can now",
                "This enables you to",
                "You'll be able to"
            ],
            "loop_closure": [
                "This completes",
                "You now have what you need",
                "This gives you",
                "You're ready to",
                "This solves"
            ],
            # Negative patterns that reduce human clarity
            "clarity_reducers": [
                "As an AI",
                "I cannot",
                "I don't have access",
                "You should probably",
                "It depends",
                "There are many factors"
            ]
        }
    
    def analyze_response_clarity(self, response_text: str, original_input: str) -> ClarityMetrics:
        """Analyze how well a response serves human understanding"""
        
        # Calculate empathy score
        empathy_score = self._calculate_empathy_score(response_text)
        
        # Calculate actionability 
        actionability = self._calculate_actionability(response_text)
        
        # Check if understanding is shown
        understanding_shown = self._shows_understanding(response_text, original_input)
        
        # Check dignity preservation
        dignity_preserved = self._preserves_dignity(response_text)
        
        # Calculate loop completion
        loop_completion = self._calculate_loop_completion(response_text)
        
        # Overall clarity score
        clarity_score = (
            empathy_score * 0.2 +
            actionability * 0.3 +
            (100 if understanding_shown else 0) * 0.2 +
            (100 if dignity_preserved else 0) * 0.1 +
            loop_completion * 0.2
        )
        
        return ClarityMetrics(
            clarity_score=clarity_score,
            empathy_detected=empathy_score > 30,
            actionability=actionability,
            understanding_shown=understanding_shown,
            dignity_preserved=dignity_preserved,
            loop_completion=loop_completion
        )
    
    def _calculate_empathy_score(self, text: str) -> float:
        """Calculate empathy indicators in response"""
        empathy_count = 0
        for indicator in self.clarity_patterns["empathy_indicators"]:
            if indicator.lower() in text.lower():
                empathy_count += 1
        
        # Penalty for AI-centric language
        for reducer in self.clarity_patterns["clarity_reducers"]:
            if reducer.lower() in text.lower():
                empathy_count -= 0.5
        
        return min(100, max(0, empathy_count * 20))
    
    def _calculate_actionability(self, text: str) -> float:
        """Calculate how actionable the response is"""
        action_score = 0
        for indicator in self.clarity_patterns["action_clarity"]:
            if indicator.lower() in text.lower():
                action_score += 1
        
        # Check for specific steps or instructions
        if "step" in text.lower() or ":" in text:
            action_score += 0.5
        
        return min(100, action_score * 25)
    
    def _shows_understanding(self, response: str, original_input: str) -> bool:
        """Check if response demonstrates understanding of human need"""
        # Look for reflection of user's intent
        key_words = original_input.lower().split()[:5]  # First 5 words often contain intent
        
        understanding_indicators = 0
        for word in key_words:
            if len(word) > 3 and word in response.lower():
                understanding_indicators += 1
        
        # Also check for empathy patterns
        empathy_found = any(
            indicator.lower() in response.lower() 
            for indicator in self.clarity_patterns["empathy_indicators"]
        )
        
        return understanding_indicators >= 2 or empathy_found
    
    def _preserves_dignity(self, text: str) -> bool:
        """Check if response preserves human dignity"""
        # Avoid condescending or overly limiting language
        dignity_reducers = [
            "you should probably",
            "you might want to consider",
            "it's complicated",
            "you may not understand",
            "this is beyond"
        ]
        
        for reducer in dignity_reducers:
            if reducer.lower() in text.lower():
                return False
        
        return True
    
    def _calculate_loop_completion(self, text: str) -> float:
        """Calculate how well the response closes the mental loop"""
        completion_score = 0
        
        for indicator in self.clarity_patterns["loop_closure"]:
            if indicator.lower() in text.lower():
                completion_score += 1
        
        # Check for forward momentum
        if "next" in text.lower() or "now" in text.lower():
            completion_score += 0.5
        
        return min(100, completion_score * 30)
    
    def suggest_clarity_improvements(self, metrics: ClarityMetrics, response_text: str) -> List[str]:
        """Suggest specific improvements to increase human clarity"""
        suggestions = []
        
        if metrics.clarity_score < 60:
            suggestions.append("Add more acknowledgment of the human's specific goal")
        
        if not metrics.empathy_detected:
            suggestions.append("Start with understanding: 'I can see you're trying to...'")
        
        if metrics.actionability < 50:
            suggestions.append("Include clearer next steps or specific actions")
        
        if not metrics.understanding_shown:
            suggestions.append("Reflect back their core need in your own words")
        
        if not metrics.dignity_preserved:
            suggestions.append("Remove limiting language and trust their capability")
        
        if metrics.loop_completion < 50:
            suggestions.append("End with clear closure or forward momentum")
        
        return suggestions
    
    def log_clarity_analysis(self, conversation_id: str, entry_id: int, metrics: ClarityMetrics):
        """Log clarity analysis for monitoring and improvement"""
        try:
            # Store in conversation entry as JSON metadata
            entry = ConversationEntry.query.get(entry_id)
            if entry:
                clarity_data = {
                    "clarity_score": metrics.clarity_score,
                    "empathy_detected": metrics.empathy_detected,
                    "actionability": metrics.actionability,
                    "understanding_shown": metrics.understanding_shown,
                    "dignity_preserved": metrics.dignity_preserved,
                    "loop_completion": metrics.loop_completion,
                    "analyzed_at": datetime.utcnow().isoformat()
                }
                
                # Add to error_message field as JSON (repurposing for clarity data)
                if not entry.error_message:
                    entry.error_message = json.dumps({"clarity_analysis": clarity_data})
                else:
                    try:
                        existing_data = json.loads(entry.error_message)
                        existing_data["clarity_analysis"] = clarity_data
                        entry.error_message = json.dumps(existing_data)
                    except:
                        # If not valid JSON, replace with new data
                        entry.error_message = json.dumps({"clarity_analysis": clarity_data})
                
                db.session.commit()
                
                logging.info(f"Clarity analysis logged for entry {entry_id}: score={metrics.clarity_score:.1f}")
        
        except Exception as e:
            logging.error(f"Failed to log clarity analysis: {str(e)}")
    
    def get_clarity_trends(self, days: int = 7) -> Dict:
        """Get clarity trends over time"""
        try:
            # Query recent entries with clarity data
            from datetime import timedelta
            since_date = datetime.utcnow() - timedelta(days=days)
            
            entries = ConversationEntry.query.filter(
                ConversationEntry.created_at >= since_date,
                ConversationEntry.error_message.isnot(None)
            ).all()
            
            clarity_scores = []
            empathy_count = 0
            total_analyzed = 0
            
            for entry in entries:
                try:
                    if entry.error_message:
                        data = json.loads(entry.error_message)
                        if "clarity_analysis" in data:
                            analysis = data["clarity_analysis"]
                            clarity_scores.append(analysis["clarity_score"])
                            if analysis["empathy_detected"]:
                                empathy_count += 1
                            total_analyzed += 1
                except:
                    continue
            
            avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0
            empathy_rate = empathy_count / total_analyzed if total_analyzed > 0 else 0
            
            return {
                "average_clarity_score": round(avg_clarity, 1),
                "empathy_rate": round(empathy_rate * 100, 1),
                "total_analyzed": total_analyzed,
                "trend": "improving" if avg_clarity > 70 else "needs_attention"
            }
            
        except Exception as e:
            logging.error(f"Failed to get clarity trends: {str(e)}")
            return {"error": str(e)}


# Global instance
clarity_engine = HumanClarityEngine()