import re
import validators
from flask import current_app
from typing import Optional, Tuple, Union

class InputValidator:
    """Utility class for validating user inputs"""
    
    @staticmethod
    def validate_conversation_input(input_text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate conversation input text
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not input_text:
            return False, "Input text is required"
        
        input_text = input_text.strip()
        
        if not input_text:
            return False, "Input text cannot be empty"
        
        if len(input_text) < 3:
            return False, "Input text must be at least 3 characters long"
        
        max_length = current_app.config.get('MAX_INPUT_LENGTH', 5000)
        if len(input_text) > max_length:
            return False, f"Input text cannot exceed {max_length} characters"
        
        # Check for potentially harmful content
        harmful_patterns = [
            r'<script[^>]*>',  # Script tags
            r'javascript:',     # JavaScript URLs
            r'data:text/html',  # Data URLs
            r'vbscript:',      # VBScript URLs
        ]
        
        for pattern in harmful_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                return False, "Input contains potentially harmful content"
        
        # Check for excessive repetition (potential spam)
        words = input_text.split()
        if len(words) > 10:
            unique_words = set(word.lower() for word in words)
            if len(unique_words) / len(words) < 0.3:  # Less than 30% unique words
                return False, "Input appears to be spam or excessive repetition"
        
        return True, None
    
    @staticmethod
    def validate_conversation_id(conversation_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate conversation ID format
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not conversation_id:
            return False, "Conversation ID is required"
        
        # UUID v4 format validation
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, conversation_id, re.IGNORECASE):
            return False, "Invalid conversation ID format"
        
        return True, None
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Basic HTML sanitization for display purposes
        
        Args:
            text: Input text to sanitize
            
        Returns:
            str: Sanitized text
        """
        if not text:
            return ""
        
        # Replace HTML entities
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        
        return text
    
    @staticmethod
    def validate_json_request(data: dict, required_fields: list) -> Tuple[bool, Optional[str]]:
        """
        Validate JSON request data
        
        Args:
            data: Request data dictionary
            required_fields: List of required field names
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not data:
            return False, "Request data is required"
        
        if not isinstance(data, dict):
            return False, "Request data must be a valid JSON object"
        
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        return True, None

class SecurityValidator:
    """Security-focused validation utilities"""
    
    @staticmethod
    def check_rate_limit_key(key: str) -> str:
        """
        Generate a safe rate limit key
        
        Args:
            key: Raw key (e.g., IP address)
            
        Returns:
            str: Sanitized key for rate limiting
        """
        # Remove any non-alphanumeric characters except dots, colons, and dashes
        safe_key = re.sub(r'[^a-zA-Z0-9.:_-]', '', key)
        return safe_key[:64]  # Limit length
    
    @staticmethod
    def validate_session_data(session_data: dict) -> bool:
        """
        Validate session data for security issues
        
        Args:
            session_data: Flask session data
            
        Returns:
            bool: True if session data is valid
        """
        if not isinstance(session_data, dict):
            return False
        
        # Check for session size (prevent session overflow attacks)
        try:
            import pickle
            session_size = len(pickle.dumps(session_data))
            if session_size > 4096:  # 4KB limit
                return False
        except Exception:
            return False
        
        # Validate conversation_id if present
        if 'conversation_id' in session_data:
            is_valid, _ = InputValidator.validate_conversation_id(session_data['conversation_id'])
            if not is_valid:
                return False
        
        return True