"""
Automated Fulfillment System for AI Form Check Pro Report
Handles instant delivery after Stripe payment with video upload, processing, and PDF generation
"""

import os
import logging
import smtplib
import requests
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
from pathlib import Path

# Try different email imports for compatibility
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    from email.mime.application import MimeApplication
except ImportError:
    from email.mime.text import MIMEText as MimeText
    from email.mime.multipart import MIMEMultipart as MimeMultipart
    from email.mime.application import MIMEApplication as MimeApplication

from models import db, Payment, PaymentStatus
from notifications import NotificationManager

class FulfillmentSystem:
    """Automated fulfillment system for AI Form Check Pro Report"""
    
    def __init__(self):
        self.notification_manager = NotificationManager()
        self.upload_folder = Path("uploads/form_check_videos")
        self.processed_folder = Path("processed/form_check_reports")
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self.processed_folder.mkdir(parents=True, exist_ok=True)
        
    def trigger_fulfillment(self, payment_id: int) -> Dict[str, Any]:
        """Trigger automated fulfillment for AI Form Check Pro Report"""
        try:
            # Get payment details
            payment = Payment.query.get(payment_id)
            if not payment or payment.status != PaymentStatus.PAID:
                return {"success": False, "error": "Payment not found or not paid"}
            
            # Check if this is for AI Form Check Pro Report
            if "ai form check" not in payment.project_name.lower():
                return {"success": False, "error": "Not an AI Form Check Pro Report order"}
            
            # Generate unique upload token
            upload_token = str(uuid.uuid4())
            upload_expiry = datetime.utcnow() + timedelta(hours=48)  # 48-hour upload window
            
            # Store upload token in payment metadata
            payment.description = json.dumps({
                "original_description": payment.description or "",
                "upload_token": upload_token,
                "upload_expiry": upload_expiry.isoformat(),
                "fulfillment_started": datetime.utcnow().isoformat()
            })
            db.session.commit()
            
            # Send upload instructions email
            email_result = self.send_upload_instructions_email(
                payment.client_name,
                payment.client_email,
                upload_token,
                upload_expiry
            )
            
            if email_result["success"]:
                # Log fulfillment initiation
                self.notification_manager.add_notification(
                    "Fulfillment Started",
                    f"AI Form Check Pro Report fulfillment initiated for {payment.client_name}",
                    "info",
                    {"payment_id": payment_id, "upload_token": upload_token}
                )
                
                logging.info(f"Fulfillment started for payment {payment_id}, upload token: {upload_token}")
                
                return {
                    "success": True,
                    "upload_token": upload_token,
                    "upload_expiry": upload_expiry.isoformat(),
                    "message": "Upload instructions sent to customer"
                }
            else:
                return email_result
                
        except Exception as e:
            logging.error(f"Error triggering fulfillment: {str(e)}")
            return {"success": False, "error": f"Fulfillment error: {str(e)}"}
    
    def send_upload_instructions_email(self, client_name: str, client_email: str, 
                                     upload_token: str, upload_expiry: datetime) -> Dict[str, Any]:
        """Send email with video upload instructions"""
        try:
            # Create upload URL
            upload_url = f"{os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')}/upload-video/{upload_token}"
            
            subject = "🎯 Your AI Form Check Pro Report - Video Upload Instructions"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    .upload-button {{ display: inline-block; background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
                    .steps {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .step {{ margin: 15px 0; }}
                    .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; }}
                    .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎯 AI Form Check Pro Report</h1>
                        <p>Your personalized form analysis is ready to begin!</p>
                    </div>
                    
                    <div class="content">
                        <h2>Hi {client_name},</h2>
                        
                        <p>Thank you for your purchase! Your AI Form Check Pro Report will be delivered within <strong>5 minutes</strong> of uploading your video.</p>
                        
                        <div class="warning">
                            <strong>⏰ Upload Window:</strong> You have 48 hours to upload your video (expires {upload_expiry.strftime('%B %d, %Y at %I:%M %p UTC')})
                        </div>
                        
                        <a href="{upload_url}" class="upload-button">📹 UPLOAD YOUR VIDEO NOW</a>
                        
                        <div class="steps">
                            <h3>📋 What to Include in Your Video:</h3>
                            <div class="step">✅ <strong>Full Exercise Demonstration</strong> - Show your complete form from start to finish</div>
                            <div class="step">✅ <strong>Multiple Angles</strong> - Side view is most important, front view if possible</div>
                            <div class="step">✅ <strong>Clear Lighting</strong> - Ensure your body is clearly visible</div>
                            <div class="step">✅ <strong>2-3 Repetitions</strong> - Show consistent form patterns</div>
                            <div class="step">✅ <strong>Normal Speed</strong> - Don't slow down or speed up</div>
                        </div>
                        
                        <h3>📱 Technical Requirements:</h3>
                        <ul>
                            <li>Video format: MP4, MOV, or AVI</li>
                            <li>Maximum file size: 500MB</li>
                            <li>Minimum resolution: 720p</li>
                            <li>Duration: 30 seconds to 3 minutes</li>
                        </ul>
                        
                        <h3>🚀 What Happens Next:</h3>
                        <ol>
                            <li>Upload your video using the button above</li>
                            <li>Our AI analyzes your form in real-time</li>
                            <li>You receive your detailed PDF report within 5 minutes</li>
                            <li>Get personalized recommendations and corrections</li>
                        </ol>
                        
                        <p>Questions? Reply to this email and we'll help you get the perfect analysis!</p>
                    </div>
                    
                    <div class="footer">
                        <p>Powered by OperatorOS AI Form Analysis</p>
                        <p>This link is unique to your order and expires in 48 hours</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self.send_email(client_email, subject, html_body)
            
        except Exception as e:
            logging.error(f"Error sending upload instructions: {str(e)}")
            return {"success": False, "error": f"Email error: {str(e)}"}
    
    def process_uploaded_video(self, upload_token: str, video_file_path: str) -> Dict[str, Any]:
        """Process uploaded video and generate AI Form Check Pro Report"""
        try:
            # Find payment by upload token
            payments = Payment.query.all()
            payment = None
            
            for p in payments:
                try:
                    metadata = json.loads(p.description or "{}")
                    if metadata.get("upload_token") == upload_token:
                        payment = p
                        break
                except:
                    continue
            
            if not payment:
                return {"success": False, "error": "Invalid upload token"}
            
            # Check upload expiry
            metadata = json.loads(payment.description)
            upload_expiry = datetime.fromisoformat(metadata["upload_expiry"])
            if datetime.utcnow() > upload_expiry:
                return {"success": False, "error": "Upload window expired"}
            
            # Move video to processing folder
            video_filename = f"{upload_token}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            processed_video_path = self.processed_folder / video_filename
            
            # Copy video file
            import shutil
            shutil.move(video_file_path, processed_video_path)
            
            # Generate AI analysis (simulate for now)
            analysis_result = self.generate_form_analysis(processed_video_path, payment.client_name)
            
            if analysis_result["success"]:
                # Generate PDF report
                pdf_result = self.generate_pdf_report(analysis_result["analysis"], payment.client_name)
                
                if pdf_result["success"]:
                    # Send delivery email
                    delivery_result = self.send_delivery_email(
                        payment.client_name,
                        payment.client_email,
                        pdf_result["pdf_path"],
                        analysis_result["analysis"]
                    )
                    
                    if delivery_result["success"]:
                        # Update payment metadata
                        metadata["fulfillment_completed"] = datetime.utcnow().isoformat()
                        metadata["video_processed"] = str(processed_video_path)
                        metadata["report_delivered"] = True
                        payment.description = json.dumps(metadata)
                        db.session.commit()
                        
                        # Send notification
                        self.notification_manager.add_notification(
                            "Report Delivered",
                            f"AI Form Check Pro Report delivered to {payment.client_name}",
                            "success",
                            {"payment_id": payment.id, "processing_time": "< 5 minutes"}
                        )
                        
                        logging.info(f"Form check report delivered for payment {payment.id}")
                        
                        return {
                            "success": True,
                            "message": "Report generated and delivered successfully",
                            "delivery_time": "< 5 minutes"
                        }
                    else:
                        return delivery_result
                else:
                    return pdf_result
            else:
                return analysis_result
                
        except Exception as e:
            logging.error(f"Error processing video: {str(e)}")
            return {"success": False, "error": f"Processing error: {str(e)}"}
    
    def generate_form_analysis(self, video_path: Path, client_name: str) -> Dict[str, Any]:
        """Generate AI form analysis from video"""
        try:
            # Simulate AI analysis - in production, integrate with actual AI model
            analysis = {
                "exercise_detected": "Squat",
                "overall_score": 78,
                "key_findings": [
                    {
                        "category": "Knee Alignment",
                        "score": 85,
                        "status": "Good",
                        "feedback": "Knees track well over toes throughout the movement",
                        "improvement": "Focus on maintaining this alignment under heavier loads"
                    },
                    {
                        "category": "Hip Depth",
                        "score": 65,
                        "status": "Needs Improvement",
                        "feedback": "Not reaching full depth consistently",
                        "improvement": "Work on ankle and hip mobility to achieve deeper squat position"
                    },
                    {
                        "category": "Spine Neutrality",
                        "score": 82,
                        "status": "Good",
                        "feedback": "Maintains neutral spine position well",
                        "improvement": "Continue focusing on core engagement"
                    },
                    {
                        "category": "Tempo Control",
                        "score": 72,
                        "status": "Fair",
                        "feedback": "Descent speed is appropriate, but could control ascent better",
                        "improvement": "Focus on deliberate, controlled upward movement"
                    }
                ],
                "personalized_recommendations": [
                    "Perform goblet squats with pause at bottom to improve depth",
                    "Add ankle mobility work to your warm-up routine",
                    "Practice tempo squats: 3 seconds down, 2 seconds up",
                    "Focus on driving through heels during ascent"
                ],
                "corrective_exercises": [
                    "90/90 Hip Stretch - 2x30 seconds each side",
                    "Ankle Wall Slides - 3x10 reps",
                    "Goblet Squat Hold - 3x20 seconds",
                    "Single-leg Glute Bridges - 2x12 each side"
                ],
                "progression_plan": {
                    "week_1_2": "Focus on mobility and depth with bodyweight squats",
                    "week_3_4": "Add light weight while maintaining full range of motion", 
                    "week_5_6": "Gradually increase load while monitoring form",
                    "ongoing": "Regular form checks and progressive overload"
                },
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "video_duration": "45 seconds",
                "reps_analyzed": 3
            }
            
            return {"success": True, "analysis": analysis}
            
        except Exception as e:
            logging.error(f"Error generating analysis: {str(e)}")
            return {"success": False, "error": f"Analysis error: {str(e)}"}
    
    def generate_pdf_report(self, analysis: Dict, client_name: str) -> Dict[str, Any]:
        """Generate PDF report using Canva template integration"""
        try:
            # Create report content
            report_content = self.create_report_content(analysis, client_name)
            
            # In production, integrate with Canva API or PDF generation library
            # For now, create a simple HTML-to-PDF conversion
            
            report_filename = f"AI_Form_Check_Report_{client_name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = self.processed_folder / report_filename
            
            # Generate HTML report (simulate PDF generation)
            html_report = self.create_html_report(analysis, client_name)
            
            # Save as HTML for now (in production, convert to PDF)
            with open(pdf_path.with_suffix('.html'), 'w') as f:
                f.write(html_report)
            
            # Create a mock PDF file
            with open(pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4\nMock PDF for AI Form Check Pro Report')
            
            return {"success": True, "pdf_path": pdf_path}
            
        except Exception as e:
            logging.error(f"Error generating PDF: {str(e)}")
            return {"success": False, "error": f"PDF generation error: {str(e)}"}
    
    def create_html_report(self, analysis: Dict, client_name: str) -> str:
        """Create HTML report with professional styling"""
        score_color = "#28a745" if analysis["overall_score"] >= 80 else "#ffc107" if analysis["overall_score"] >= 60 else "#dc3545"
        
        findings_html = ""
        for finding in analysis["key_findings"]:
            status_color = "#28a745" if finding["status"] == "Good" else "#ffc107" if finding["status"] == "Fair" else "#dc3545"
            findings_html += f"""
            <div class="finding-card">
                <div class="finding-header">
                    <h3>{finding["category"]}</h3>
                    <div class="score-badge" style="background-color: {status_color};">{finding["score"]}/100</div>
                </div>
                <p><strong>Status:</strong> <span style="color: {status_color};">{finding["status"]}</span></p>
                <p><strong>Feedback:</strong> {finding["feedback"]}</p>
                <p><strong>Improvement:</strong> {finding["improvement"]}</p>
            </div>
            """
        
        recommendations_html = "".join([f"<li>{rec}</li>" for rec in analysis["personalized_recommendations"]])
        exercises_html = "".join([f"<li>{ex}</li>" for ex in analysis["corrective_exercises"]])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .report-container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
                .content {{ padding: 40px; }}
                .overall-score {{ text-align: center; margin: 30px 0; }}
                .score-circle {{ display: inline-block; width: 120px; height: 120px; border-radius: 50%; background: {score_color}; color: white; line-height: 120px; font-size: 24px; font-weight: bold; }}
                .finding-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #667eea; }}
                .finding-header {{ display: flex; justify-content: between; align-items: center; margin-bottom: 15px; }}
                .score-badge {{ padding: 5px 10px; border-radius: 20px; color: white; font-weight: bold; }}
                .section {{ margin: 30px 0; }}
                .recommendations {{ background: #e8f5e8; padding: 20px; border-radius: 8px; }}
                .exercises {{ background: #fff3cd; padding: 20px; border-radius: 8px; }}
                .progression {{ background: #f0f0f0; padding: 20px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="report-container">
                <div class="header">
                    <h1>🎯 AI Form Check Pro Report</h1>
                    <h2>{client_name}</h2>
                    <p>Personalized Movement Analysis & Recommendations</p>
                </div>
                
                <div class="content">
                    <div class="overall-score">
                        <h2>Overall Form Score</h2>
                        <div class="score-circle">{analysis["overall_score"]}/100</div>
                        <p><strong>Exercise Analyzed:</strong> {analysis["exercise_detected"]}</p>
                        <p><strong>Repetitions:</strong> {analysis["reps_analyzed"]} | <strong>Duration:</strong> {analysis["video_duration"]}</p>
                    </div>
                    
                    <div class="section">
                        <h2>📊 Detailed Analysis</h2>
                        {findings_html}
                    </div>
                    
                    <div class="section recommendations">
                        <h2>💡 Personalized Recommendations</h2>
                        <ul>{recommendations_html}</ul>
                    </div>
                    
                    <div class="section exercises">
                        <h2>🏋️ Corrective Exercises</h2>
                        <ul>{exercises_html}</ul>
                    </div>
                    
                    <div class="section progression">
                        <h2>📈 4-Week Progression Plan</h2>
                        <p><strong>Weeks 1-2:</strong> {analysis["progression_plan"]["week_1_2"]}</p>
                        <p><strong>Weeks 3-4:</strong> {analysis["progression_plan"]["week_3_4"]}</p>
                        <p><strong>Weeks 5-6:</strong> {analysis["progression_plan"]["week_5_6"]}</p>
                        <p><strong>Ongoing:</strong> {analysis["progression_plan"]["ongoing"]}</p>
                    </div>
                    
                    <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p><em>Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</em></p>
                        <p>Powered by OperatorOS AI Form Analysis</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def create_report_content(self, analysis: Dict, client_name: str) -> Dict[str, Any]:
        """Create structured report content for PDF generation"""
        return {
            "client_name": client_name,
            "exercise": analysis["exercise_detected"],
            "overall_score": analysis["overall_score"],
            "analysis_date": datetime.now().strftime('%B %d, %Y'),
            "findings": analysis["key_findings"],
            "recommendations": analysis["personalized_recommendations"],
            "corrective_exercises": analysis["corrective_exercises"],
            "progression_plan": analysis["progression_plan"]
        }
    
    def send_delivery_email(self, client_name: str, client_email: str, 
                          pdf_path: Path, analysis: Dict) -> Dict[str, Any]:
        """Send delivery email with PDF report attached"""
        try:
            subject = f"🎯 Your AI Form Check Pro Report is Ready! ({analysis['overall_score']}/100)"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    .score-highlight {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0; }}
                    .score-number {{ font-size: 48px; font-weight: bold; color: #28a745; }}
                    .key-findings {{ background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎯 Your AI Form Check Pro Report</h1>
                        <p>Personalized analysis complete!</p>
                    </div>
                    
                    <div class="content">
                        <h2>Hi {client_name},</h2>
                        
                        <p>Your AI Form Check Pro Report has been generated and is attached to this email!</p>
                        
                        <div class="score-highlight">
                            <div class="score-number">{analysis['overall_score']}/100</div>
                            <p><strong>Overall Form Score</strong></p>
                            <p>Exercise Analyzed: <strong>{analysis['exercise_detected']}</strong></p>
                        </div>
                        
                        <div class="key-findings">
                            <h3>🔍 Quick Summary:</h3>
                            <ul>
                                <li><strong>Best Aspect:</strong> {max(analysis['key_findings'], key=lambda x: x['score'])['category']} ({max(analysis['key_findings'], key=lambda x: x['score'])['score']}/100)</li>
                                <li><strong>Focus Area:</strong> {min(analysis['key_findings'], key=lambda x: x['score'])['category']} ({min(analysis['key_findings'], key=lambda x: x['score'])['score']}/100)</li>
                                <li><strong>Top Recommendation:</strong> {analysis['personalized_recommendations'][0]}</li>
                            </ul>
                        </div>
                        
                        <h3>📋 What's in Your Report:</h3>
                        <ul>
                            <li>Detailed breakdown of {len(analysis['key_findings'])} key movement areas</li>
                            <li>{len(analysis['personalized_recommendations'])} personalized recommendations</li>
                            <li>{len(analysis['corrective_exercises'])} corrective exercises</li>
                            <li>4-week progression plan</li>
                            <li>Professional analysis with scoring</li>
                        </ul>
                        
                        <p><strong>Need another analysis?</strong> Feel free to purchase another report for different exercises or to track your progress!</p>
                        
                        <p>Questions about your report? Simply reply to this email and we'll help you implement the recommendations effectively.</p>
                    </div>
                    
                    <div class="footer">
                        <p>Thank you for choosing OperatorOS AI Form Analysis!</p>
                        <p>Report delivered in under 5 minutes as promised ⚡</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return self.send_email_with_attachment(client_email, subject, html_body, pdf_path)
            
        except Exception as e:
            logging.error(f"Error sending delivery email: {str(e)}")
            return {"success": False, "error": f"Delivery email error: {str(e)}"}
    
    def send_email(self, to_email: str, subject: str, html_body: str) -> Dict[str, Any]:
        """Send HTML email (mock implementation for development)"""
        try:
            # For development, simulate email sending and log the content
            logging.info(f"📧 SIMULATED EMAIL SENT")
            logging.info(f"To: {to_email}")
            logging.info(f"Subject: {subject}")
            logging.info(f"Body preview: {html_body[:200]}...")
            
            # In production, integrate with actual email service (SendGrid, Mailgun, etc.)
            # For now, create a local copy of the email for reference
            email_folder = Path("emails/sent")
            email_folder.mkdir(parents=True, exist_ok=True)
            
            email_filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{to_email.replace('@', '_at_')}.html"
            email_path = email_folder / email_filename
            
            with open(email_path, 'w') as f:
                f.write(f"<!-- Email sent to {to_email} -->\n")
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(html_body)
            
            return {"success": True, "message": "Email simulated successfully", "email_file": str(email_path)}
            
        except Exception as e:
            logging.error(f"Error simulating email: {str(e)}")
            return {"success": False, "error": f"Email simulation failed: {str(e)}"}
    
    def send_email_with_attachment(self, to_email: str, subject: str, html_body: str, 
                                 attachment_path: Path) -> Dict[str, Any]:
        """Send HTML email with PDF attachment (mock implementation for development)"""
        try:
            # For development, simulate email sending with attachment
            logging.info(f"📧 SIMULATED EMAIL WITH ATTACHMENT SENT")
            logging.info(f"To: {to_email}")
            logging.info(f"Subject: {subject}")
            logging.info(f"Attachment: {attachment_path}")
            logging.info(f"Body preview: {html_body[:200]}...")
            
            # Create a local copy of the email for reference
            email_folder = Path("emails/sent")
            email_folder.mkdir(parents=True, exist_ok=True)
            
            email_filename = f"email_with_attachment_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{to_email.replace('@', '_at_')}.html"
            email_path = email_folder / email_filename
            
            with open(email_path, 'w') as f:
                f.write(f"<!-- Email with attachment sent to {to_email} -->\n")
                f.write(f"<!-- Subject: {subject} -->\n")
                f.write(f"<!-- Attachment: {attachment_path} -->\n")
                f.write(html_body)
            
            return {"success": True, "message": "Email with attachment simulated successfully", "email_file": str(email_path)}
            
        except Exception as e:
            logging.error(f"Error simulating email with attachment: {str(e)}")
            return {"success": False, "error": f"Email simulation failed: {str(e)}"}

# Global fulfillment system instance
fulfillment_system = FulfillmentSystem()