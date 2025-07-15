import os
import logging
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET') or os.urandom(32)
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 20,
        "max_overflow": 20
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Multi-API Configuration
    DEFAULT_API_PROVIDER = os.environ.get('DEFAULT_API_PROVIDER', 'openai')
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', '500'))
    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', '0.7'))
    
    # Claude (Anthropic) Configuration
    CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')
    CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
    CLAUDE_MAX_TOKENS = int(os.environ.get('CLAUDE_MAX_TOKENS', '500'))
    CLAUDE_TEMPERATURE = float(os.environ.get('CLAUDE_TEMPERATURE', '0.7'))
    
    # Gemini (Google) Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-pro')
    GEMINI_MAX_TOKENS = int(os.environ.get('GEMINI_MAX_TOKENS', '500'))
    GEMINI_TEMPERATURE = float(os.environ.get('GEMINI_TEMPERATURE', '0.7'))
    
    # Rate Limiting Configuration
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '10 per minute')
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Security Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Application Limits
    MAX_CONVERSATION_LENGTH = int(os.environ.get('MAX_CONVERSATION_LENGTH', '10'))
    MAX_INPUT_LENGTH = int(os.environ.get('MAX_INPUT_LENGTH', '5000'))
    MAX_CONVERSATIONS_PER_SESSION = int(os.environ.get('MAX_CONVERSATIONS_PER_SESSION', '50'))
    
    # Admin configuration
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    ADMIN_SESSION_TIMEOUT = int(os.environ.get('ADMIN_SESSION_TIMEOUT', '3600'))  # 1 hour
    
    @staticmethod
    def validate_required_env_vars():
        """Validate that all required environment variables are set"""
        required_vars = [
            'DATABASE_URL',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
    
    @staticmethod
    def setup_logging():
        """Setup application logging"""
        log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format=Config.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('app.log') if os.environ.get('LOG_TO_FILE') else logging.NullHandler()
            ]
        )
        
        # Suppress noisy third-party logs
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # Production-specific overrides
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        "pool_size": 20,
        "max_overflow": 30
    }

# Configuration selector
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}