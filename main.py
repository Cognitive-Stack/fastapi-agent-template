from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
import structlog

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.routers import health, auth, conversations, tasks, chat
from app.repositories.user import UserRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.task import TaskRepository
from app.services.socketio_service import SocketIOService

# Configure structured logging
configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting up application", app_name=settings.app_name, env=settings.env)
    
    # Initialize MongoDB connection
    app.state.mongo = AsyncIOMotorClient(str(settings.mongo_uri))
    app.state.settings = settings
    
    # Test database connection
    try:
        await app.state.mongo.admin.command('ping')
        logger.info("Connected to MongoDB", db_name=settings.mongo_db_name)
    except Exception as e:
        logger.error("Failed to connect to MongoDB", error=str(e))
        raise
    
    # Create database indexes
    db = app.state.mongo[settings.mongo_db_name]
    try:
        user_repo = UserRepository(db)
        conversation_repo = ConversationRepository(db)
        task_repo = TaskRepository(db)
        
        await user_repo.create_indexes()
        await conversation_repo.create_indexes()
        await task_repo.create_indexes()
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning("Failed to create some database indexes", error=str(e))
    
    # Initialize Socket.IO service
    app.state.socketio_service = SocketIOService(db)
    logger.info("Socket.IO service initialized")
    
    # Mount Socket.IO application
    socketio_asgi = app.state.socketio_service.get_asgi_app()
    app.mount("/socket.io", socketio_asgi)
    logger.info("Socket.IO mounted at /socket.io")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    
    # Cleanup Socket.IO connections
    if hasattr(app.state, 'socketio_service'):
        await app.state.socketio_service.sio.shutdown()
        logger.info("Socket.IO connections closed")
    
    app.state.mongo.close()


# Create FastAPI application
app = FastAPI(
    title="Chatbot API",
    description="A FastAPI template for managing chatbot tasks and conversations with MongoDB and real-time Socket.IO chat",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/docs" if settings.env != "prod" else None,
    redoc_url="/redoc" if settings.env != "prod" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    logger.info(
        "Request received",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None
    )
    
    response = await call_next(request)
    
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code
    )
    
    return response


# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")

# Mount static files for the test client
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Chatbot API with Real-time Chat",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "socketio": "/socket.io",
        "test_client": "/static/socketio_test.html"
    }


# Add Socket.IO info endpoint
@app.get("/socket-info", tags=["socketio"])
async def socket_info():
    """Get Socket.IO connection information."""
    return {
        "socket_url": "/socket.io",
        "test_client": "/static/socketio_test.html",
        "events": {
            "client_to_server": {
                "chat": "Send a chat message",
                "join_conversation": "Join a specific conversation room",
                "leave_conversation": "Leave a conversation room"
            },
            "server_to_client": {
                "connected": "Connection established successfully",
                "conversation": "Chat response received",
                "error": "Error occurred",
                "joined_conversation": "Successfully joined conversation",
                "left_conversation": "Successfully left conversation"
            }
        },
        "authentication": "Include JWT token in auth object during connection",
        "example_connection": {
            "auth": {"token": "your_jwt_token_here"},
            "events": {
                "chat": {"message": "Hello!", "conversation_id": "optional"},
                "join_conversation": {"conversation_id": "conversation_id_here"}
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 