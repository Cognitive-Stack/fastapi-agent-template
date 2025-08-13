from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.v1.schemas import ChatRequest, ChatResponse, TaskCreate, ChatMessageResponse
from app.services.task import TaskService
from app.services.conversation import ConversationService


class ChatService:
    """Service for handling chat interactions."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.task_service = TaskService(db)
        self.conversation_service = ConversationService(db)
    
    async def process_message(self, user_id: str, chat_request: ChatRequest) -> ChatResponse:
        """Process a chat message and create appropriate task/conversation."""
        task_data = TaskCreate(
            conversation_id=chat_request.conversation_id,
            user_message=chat_request.message,
            metadata=chat_request.metadata,
            priority="medium",
            tags=["chat"]
        )
        
        task = await self.task_service.create_task(
            user_id=user_id,
            task_data=task_data
        )
        user_message = task.messages[0] if task.messages else None
        user_message_json = user_message.model_dump()
        user_message_json['id'] = str(user_message_json['id'])
        user_message_json['timestamp'] = user_message_json['created_at'].timestamp() if user_message_json['created_at'] else None

        response = ChatResponse(
            task_id=str(task.id),
            conversation_id=str(task.conversation_id),
            user_message=ChatMessageResponse(**user_message_json) if user_message else None,
            assistant_responses=[]
        )   
        
        return response 