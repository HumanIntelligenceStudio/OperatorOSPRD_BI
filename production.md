# Production Deployment Guide

## Environment Variables

### Required Environment Variables
```bash
# Core Application
DATABASE_URL=postgresql://user:password@host:port/dbname
OPENAI_API_KEY=sk-your-openai-api-key-here
SESSION_SECRET=your-secure-random-session-secret

# Application Configuration
FLASK_ENV=production
LOG_LEVEL=INFO
```

### Optional Environment Variables
```bash
# OpenAI Configuration
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=500
OPENAI_TEMPERATURE=0.7

# Rate Limiting
RATELIMIT_DEFAULT=10 per minute
REDIS_URL=redis://localhost:6379/0  # For distributed rate limiting

# Security
SESSION_COOKIE_SECURE=true
LOG_TO_FILE=true

# Application Limits
MAX_CONVERSATION_LENGTH=10
MAX_INPUT_LENGTH=5000
MAX_CONVERSATIONS_PER_SESSION=50
```

## Security Features Implemented

### 1. Input Validation & Sanitization
- **Text Input Validation**: Length limits, harmful content detection, spam prevention
- **HTML Sanitization**: Prevents XSS attacks through user input
- **Conversation ID Validation**: UUID format validation
- **JSON Request Validation**: Required field checking

### 2. Rate Limiting
- **API Endpoints**: Different limits per endpoint type
- **IP-based Limiting**: Prevents abuse from single sources
- **Memory/Redis Storage**: Scalable rate limit storage

### 3. Session Security
- **Secure Cookies**: HTTPOnly, Secure, SameSite attributes
- **Session Validation**: Data integrity checks
- **Session Timeouts**: 24-hour permanent sessions
- **Session Size Limits**: Prevents session overflow attacks

### 4. Security Headers
- **X-Content-Type-Options**: nosniff
- **X-Frame-Options**: DENY  
- **X-XSS-Protection**: 1; mode=block
- **Strict-Transport-Security**: HSTS enabled
- **Referrer-Policy**: strict-origin-when-cross-origin

### 5. Database Security
- **Connection Pooling**: Configurable pool sizes
- **Connection Timeouts**: Prevents hanging connections
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **Transaction Rollback**: Automatic rollback on errors

### 6. Error Handling
- **Generic Error Messages**: No sensitive data exposure
- **Comprehensive Logging**: Structured error logging
- **Database Rollback**: Automatic on transaction failures
- **Request Size Limits**: 16MB maximum request size

## Performance Optimizations

### 1. Database Configuration
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,           # Production pool size
    "pool_recycle": 300,       # Connection recycling
    "pool_pre_ping": True,     # Connection health checks
    "pool_timeout": 20,        # Connection timeout
    "max_overflow": 30         # Additional connections
}
```

### 2. Request Monitoring
- **Slow Request Logging**: Requests >5 seconds logged
- **Request Duration Tracking**: Performance monitoring
- **Health Check Endpoint**: `/health` for monitoring

### 3. Memory Management
- **Conversation Limits**: Per-session limits
- **Input Size Limits**: Maximum text length enforcement
- **Session Data Validation**: Size and content checks

## Deployment Checklist

### Pre-Deployment
- [ ] Set all required environment variables
- [ ] Test database connectivity
- [ ] Verify OpenAI API key access
- [ ] Configure secure session secret
- [ ] Set up SSL/TLS certificates
- [ ] Configure production logging

### Post-Deployment
- [ ] Test health check endpoint (`/health`)
- [ ] Verify rate limiting is working
- [ ] Test conversation creation and history
- [ ] Monitor application logs
- [ ] Verify security headers are present
- [ ] Test error handling

## Monitoring & Maintenance

### Health Checks
- **Endpoint**: `GET /health`
- **Response**: JSON with status, timestamp, database status
- **Monitoring**: Use for load balancer health checks

### Logging
- **Format**: Structured JSON logging recommended
- **Levels**: INFO for production, DEBUG for development
- **Rotation**: Configure log rotation for disk space
- **Monitoring**: Monitor for ERROR and WARNING levels

### Database Maintenance
- **Cleanup**: Consider conversation retention policies
- **Indexing**: Monitor query performance
- **Backups**: Regular database backups essential
- **Migration**: Use Flask-Migrate for schema changes

## Security Recommendations

### 1. Network Security
- Use HTTPS in production (SSL/TLS)
- Configure proper firewall rules
- Consider using a CDN for static assets
- Implement proper DNS security

### 2. Infrastructure Security
- Keep Python and dependencies updated
- Regular security patches for OS
- Monitor for vulnerabilities in dependencies
- Use container security scanning if using Docker

### 3. Application Security
- Regular security audits
- Monitor for unusual traffic patterns
- Implement proper backup and recovery
- Consider implementing WAF (Web Application Firewall)

## Scaling Considerations

### Horizontal Scaling
- Application is stateless (sessions in cookies)
- Database connection pooling configured
- Rate limiting supports Redis for distributed setups
- Health checks support load balancer integration

### Performance Tuning
- Monitor database query performance
- Consider caching for conversation history
- Optimize OpenAI API usage
- Monitor memory usage patterns

## Troubleshooting

### Common Issues
1. **Database Connection Errors**: Check DATABASE_URL and network connectivity
2. **OpenAI API Errors**: Verify API key and rate limits
3. **Session Issues**: Check SESSION_SECRET configuration
4. **Rate Limit Errors**: Monitor traffic patterns and adjust limits

### Debug Mode
Never enable debug mode in production:
```python
# NEVER in production
DEBUG = False
```

### Log Analysis
Monitor these log patterns:
- ERROR: Application errors requiring attention
- WARNING: Slow requests or potential issues
- INFO: Normal operations and conversation tracking