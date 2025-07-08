# Multi-Agent AI Conversation System

## Overview

This is a Flask-based web application that implements a multi-agent AI conversation system. The application allows users to interact with different AI agents, each with specialized roles and capabilities. The system uses OpenAI's GPT-3.5-turbo model to power the AI agents and maintains conversation history in memory.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a simple Flask web application architecture with the following key characteristics:

### Frontend Architecture
- **Framework**: Vanilla HTML/CSS/JavaScript with Bootstrap for styling
- **UI Components**: Single-page application with dynamic content updates
- **Styling**: Bootstrap Agent Dark Theme with custom CSS animations
- **Icons**: Font Awesome for visual elements

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **API Structure**: RESTful endpoints for agent interactions
- **Session Management**: Flask sessions for user state management
- **Logging**: Python logging module for debugging and monitoring

### Data Storage
- **Primary Storage**: In-memory dictionary for conversation history
- **Session Storage**: Flask session cookies for user identification
- **No Persistent Database**: All data is stored in memory and lost on restart

## Key Components

### Agent System
- **Base Agent Class**: Extensible class structure for different AI agent types
- **Agent Specialization**: Each agent has a unique name, role, and system prompt
- **OpenAI Integration**: Uses OpenAI's chat completions API for response generation
- **Conversation Context**: Maintains conversation history for context-aware responses

### Core Functionality
- **Multi-Agent Support**: Framework supports multiple specialized AI agents
- **Conversation Management**: Tracks and maintains conversation history per session
- **Real-time Interaction**: AJAX-based communication for seamless user experience
- **Error Handling**: Comprehensive error handling for API failures and edge cases

## Data Flow

1. **User Input**: User submits input through the web interface
2. **Session Management**: Flask creates or retrieves existing session
3. **Agent Selection**: System determines which agent(s) should respond
4. **Context Preparation**: Conversation history is prepared for the AI model
5. **OpenAI API Call**: Request sent to OpenAI with system prompt and context
6. **Response Processing**: AI response is processed and formatted
7. **Storage Update**: Conversation history is updated in memory
8. **UI Update**: Frontend is updated with the new response

## External Dependencies

### Core Dependencies
- **Flask**: Web framework for Python
- **OpenAI Python Client**: Official OpenAI API client library
- **Bootstrap**: CSS framework for responsive design
- **Font Awesome**: Icon library for UI elements

### API Dependencies
- **OpenAI API**: GPT-3.5-turbo model for AI agent responses
- **Model Configuration**: 500 max tokens, 0.7 temperature for balanced creativity

## Deployment Strategy

### Environment Configuration
- **Environment Variables**: 
  - `OPENAI_API_KEY`: Required for OpenAI API access
  - `SESSION_SECRET`: Flask session encryption key (defaults to dev key)

### Runtime Requirements
- **Python Environment**: Requires Python with Flask and OpenAI packages
- **Memory Usage**: Conversation data stored in memory (not persistent)
- **API Limits**: Subject to OpenAI API rate limits and usage quotas

### Scalability Considerations
- **Current Limitations**: In-memory storage limits scalability
- **Session Dependency**: Uses Flask sessions for user identification
- **Stateless Design**: Each request is independent except for conversation history

### Security Considerations
- **API Key Management**: OpenAI API key stored as environment variable
- **Session Security**: Flask session cookies for user state
- **Input Validation**: Basic input handling (may need enhancement)

## Development Notes

- The application is designed for development/demo purposes with in-memory storage
- Production deployment would require persistent storage for conversation history
- The agent system is designed to be extensible for adding new specialized agents
- Error handling includes logging for debugging and monitoring
- The UI uses animations and loading indicators for better user experience