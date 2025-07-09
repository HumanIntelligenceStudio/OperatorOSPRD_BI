"""
Video Upload Handler for AI Form Check Pro Report
Handles secure video uploads with validation and automatic processing
"""

import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, render_template, jsonify, abort
from werkzeug.utils import secure_filename
import json

from main import limiter
from fulfillment_system import fulfillment_system
from models import Payment

# Create video upload blueprint
video_bp = Blueprint('video', __name__)

# Configuration
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
UPLOAD_FOLDER = Path("uploads/form_check_videos")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_upload_token(upload_token: str) -> dict:
    """Validate upload token and return payment info"""
    try:
        # Find payment by upload token
        payments = Payment.query.all()
        
        for payment in payments:
            try:
                metadata = json.loads(payment.description or "{}")
                if metadata.get("upload_token") == upload_token:
                    # Check if token is still valid
                    upload_expiry = datetime.fromisoformat(metadata["upload_expiry"])
                    if datetime.utcnow() <= upload_expiry:
                        return {
                            "valid": True,
                            "payment": payment,
                            "metadata": metadata,
                            "expiry": upload_expiry
                        }
                    else:
                        return {"valid": False, "reason": "Upload window expired"}
            except:
                continue
        
        return {"valid": False, "reason": "Invalid upload token"}
        
    except Exception as e:
        logging.error(f"Error validating upload token: {str(e)}")
        return {"valid": False, "reason": "Validation error"}

@video_bp.route('/upload-video/<upload_token>')
@limiter.limit("10 per minute")
def upload_page(upload_token):
    """Video upload page"""
    try:
        # Validate token
        validation = validate_upload_token(upload_token)
        
        if not validation["valid"]:
            return render_template('video_upload_error.html', 
                                 error=validation["reason"]), 400
        
        payment = validation["payment"]
        expiry = validation["expiry"]
        
        return render_template('video_upload.html',
                             upload_token=upload_token,
                             client_name=payment.client_name,
                             project_name=payment.project_name,
                             expiry=expiry.strftime('%B %d, %Y at %I:%M %p UTC'))
        
    except Exception as e:
        logging.error(f"Error loading upload page: {str(e)}")
        return render_template('video_upload_error.html', 
                             error="Page loading error"), 500

@video_bp.route('/api/upload-video/<upload_token>', methods=['POST'])
@limiter.limit("3 per minute")
def upload_video(upload_token):
    """Handle video file upload"""
    try:
        # Validate token
        validation = validate_upload_token(upload_token)
        
        if not validation["valid"]:
            return jsonify({
                "success": False,
                "error": validation["reason"]
            }), 400
        
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({
                "success": False,
                "error": "No video file uploaded"
            }), 400
        
        file = request.files['video']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # Check file size
        if request.content_length > MAX_FILE_SIZE:
            return jsonify({
                "success": False,
                "error": f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            }), 400
        
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{upload_token}_{timestamp}_{original_filename}"
        file_path = UPLOAD_FOLDER / filename
        
        # Save file
        file.save(file_path)
        
        # Verify file was saved and has content
        if not file_path.exists() or file_path.stat().st_size == 0:
            return jsonify({
                "success": False,
                "error": "File upload failed"
            }), 500
        
        logging.info(f"Video uploaded successfully: {filename} ({file_path.stat().st_size} bytes)")
        
        # Process video asynchronously
        processing_result = fulfillment_system.process_uploaded_video(upload_token, str(file_path))
        
        if processing_result["success"]:
            return jsonify({
                "success": True,
                "message": "Video uploaded and processed successfully! Check your email for the report.",
                "processing_time": processing_result.get("delivery_time", "< 5 minutes")
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Processing failed: {processing_result['error']}"
            }), 500
        
    except Exception as e:
        logging.error(f"Error uploading video: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Upload processing error"
        }), 500

@video_bp.route('/api/upload-progress/<upload_token>')
@limiter.limit("30 per minute")
def upload_progress(upload_token):
    """Get upload progress status"""
    try:
        # Validate token
        validation = validate_upload_token(upload_token)
        
        if not validation["valid"]:
            return jsonify({
                "valid": False,
                "reason": validation["reason"]
            })
        
        payment = validation["payment"]
        metadata = validation["metadata"]
        
        # Check processing status
        processing_status = {
            "upload_token_valid": True,
            "client_name": payment.client_name,
            "project_name": payment.project_name,
            "upload_expiry": metadata["upload_expiry"],
            "fulfillment_started": metadata.get("fulfillment_started"),
            "fulfillment_completed": metadata.get("fulfillment_completed"),
            "report_delivered": metadata.get("report_delivered", False)
        }
        
        return jsonify(processing_status)
        
    except Exception as e:
        logging.error(f"Error checking upload progress: {str(e)}")
        return jsonify({
            "valid": False,
            "reason": "Progress check error"
        }), 500