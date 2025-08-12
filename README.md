# FastAPI Chatbot Template

A production-ready FastAPI template for building chatbot applications with task and conversation management using MongoDB.

## 🚀 Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **MongoDB Integration**: Async MongoDB operations with Motor
- **JWT Authentication**: Secure user authentication and authorization
- **Task Management**: Create and manage chatbot tasks with messages
- **Conversation Management**: Group related tasks into conversations
- **Structured Logging**: JSON logging with structured context
- **Auto Documentation**: Interactive API docs with Swagger UI
- **Production Ready**: Follows FastAPI best practices and security guidelines

## 📋 Requirements

- Python 3.9+
- MongoDB 4.4+
- Virtual environment support (python3-venv)

## 🛠️ Installation

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd fastapi-chatbot-template
```

2. **Start with Docker Compose**
```bash
docker-compose up --build
```

This will start:
- FastAPI app on http://localhost:8000
- MongoDB on port 27017
- Mongo Express (DB admin) on http://localhost:8081

### Option 2: Manual Setup

1. **Install system dependencies** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3.12-venv python3-pip mongodb
```

2. **Clone and setup**
```bash
git clone <repository-url>
cd fastapi-chatbot-template
```

3. **Run setup script**
```bash
chmod +x setup.sh
./setup.sh
```

4. **Create environment file**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Start MongoDB**
```bash
sudo systemctl start mongodb
```

6. **Run the application**
```bash
source venv/bin/activate
uvicorn main:app --reload
```

## 🔧 Configuration

Create a `.env` file with your settings:

```env
# Application
APP_NAME=chatbot-api
ENV=dev
DEBUG=true

# Database
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=chatbot_db

# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# API Keys
API_KEY=your-internal-api-key-change-this

# CORS
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Logging
LOG_LEVEL=INFO
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

## 🏗️ Architecture

The project follows a clean architecture pattern:

```
app/
├── core/           # Configuration, security, logging
├── models/         # Pydantic models for MongoDB documents
├── repositories/   # Database operations (CRUD)
├── services/       # Business logic (framework-agnostic)
├── api/            # FastAPI routes and dependencies
│   └── v1/
│       ├── routers/    # API endpoints
│       └── schemas.py  # Request/response models
└── utils/          # Utility functions
```

## 🎯 Usage Examples

### 1. User Registration and Authentication

```python
import httpx

# Register a new user
response = httpx.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "user@example.com",
    "username": "johndoe",
    "password": "securepassword123",
    "full_name": "John Doe"
})

# Login to get access token
response = httpx.post("http://localhost:8000/api/v1/auth/login", json={
    "username": "johndoe",
    "password": "securepassword123"
})
token = response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}
```

### 2. Chat Interactions

```python
# Send a message (creates conversation and task automatically)
response = httpx.post("http://localhost:8000/api/v1/chat/", 
    headers=headers,
    json={
        "message": "Help me plan a project timeline",
        "metadata": {"priority": "high"}
    }
)

chat_response = response.json()
task_id = chat_response["task_id"]
conversation_id = chat_response["conversation_id"]

# Add assistant response to the task
response = httpx.post(f"http://localhost:8000/api/v1/tasks/{task_id}/messages",
    headers=headers,
    json={
        "role": "assistant",
        "content": "I'd be happy to help you plan your project timeline! Let's start by breaking down the main phases of your project.",
        "metadata": {"generated_by": "chatbot"}
    }
)
```

### 3. Managing Conversations

```python
# List user's conversations
response = httpx.get("http://localhost:8000/api/v1/conversations/", headers=headers)

# Get specific conversation
response = httpx.get(f"http://localhost:8000/api/v1/conversations/{conversation_id}", headers=headers)

# Update conversation
response = httpx.put(f"http://localhost:8000/api/v1/conversations/{conversation_id}",
    headers=headers,
    json={
        "title": "Project Planning Session",
        "description": "Detailed planning for Q1 project"
    }
)
```

### 4. Task Management

```python
# List tasks with filtering
response = httpx.get("http://localhost:8000/api/v1/tasks/",
    headers=headers,
    params={
        "status": "pending",
        "priority": "high",
        "limit": 10
    }
)

# Update task status
response = httpx.put(f"http://localhost:8000/api/v1/tasks/{task_id}",
    headers=headers,
    json={
        "status": "completed",
        "completion_percentage": 100
    }
)
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt for secure password storage
- **CORS Protection**: Configurable CORS origins
- **Input Validation**: Pydantic models for request validation
- **Rate Limiting**: Ready for rate limiting middleware

## 📊 Data Models

### User
- Email, username, password (hashed)
- Profile information
- Active status and permissions

### Conversation
- Groups related tasks together
- User ownership
- Metadata for categorization

### Task
- Contains user message and chatbot responses
- Status tracking (pending, in_progress, completed, failed)
- Priority levels and categorization
- Completion percentage tracking

### ChatMessage
- Individual messages within tasks
- Role-based (user, assistant, system)
- Metadata for additional context

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py -v
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
# Build and run
docker-compose up --build

# Production deployment
docker build -t chatbot-api .
docker run -p 8000:8000 --env-file .env chatbot-api
```

### Environment-Specific Settings

- **Development**: Debug mode, detailed logs
- **Staging**: Production-like with debug info
- **Production**: Optimized, secure, monitoring enabled

## 📈 Monitoring and Observability

- **Health Checks**: `/api/v1/health/` and `/api/v1/health/ready`
- **Structured Logging**: JSON logs with request context
- **Metrics**: Ready for Prometheus integration
- **Tracing**: OpenTelemetry compatible

## 🤝 Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development instructions.

## 🆘 Troubleshooting

### Common Issues

1. **Virtual Environment Error**: Install `python3-venv`
   ```bash
   sudo apt install python3.12-venv
   ```

2. **MongoDB Connection**: Ensure MongoDB is running
   ```bash
   sudo systemctl start mongodb
   ```

3. **Permission Errors**: Use proper virtual environment
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Import Errors**: Ensure PYTHONPATH includes project root
   ```bash
   export PYTHONPATH=/path/to/project:$PYTHONPATH
   ```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔄 Changelog

### v1.0.0
- Initial release with core functionality
- User authentication and management
- Task and conversation management
- Chat interaction endpoints
- MongoDB integration
- Comprehensive API documentation
- Docker support
- Production-ready configuration 