import logging
from typing import Any, Dict, List, Optional

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import (ExternalTermination,
                                          SourceMatchTermination)
from autogen_agentchat.messages import (ToolCallSummaryMessage, ToolCallRequestEvent,
                                        TextMessage)
from autogen_agentchat.teams import SelectorGroupChat
from autogen_core import CancellationToken

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from app.core.config import settings
try:
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover
    build = None


def search_song(query: str, language: str = None) -> str:
    """
    Args:
        query (str): Description of user's music preferences like genre, mood, artist, era etc.
        language (str, optional): Preferred song language. Defaults to None.

    Returns:
        str: YouTube video URL wrapped in <youtube_url> tags if successful.
             Error message if API key is missing or search fails.

    Example:
        >>> search_song("upbeat jazz", "english")
        '<youtube_url>https://www.youtube.com/watch?v=abc123</youtube_url>'
        >>> search_song("", None) 
        'YouTube search unavailable. Please configure YOUTUBE_API_KEY.'
    """
    query = f"{(query or "").strip() or "popular music"} in {language}"

    api_key = None
    try:
        api_key = settings.youtube_api_key.get_secret_value() if settings.youtube_api_key else None
    except Exception:
        api_key = None

    if not api_key or build is None:
        logger.warning("YouTube API key not configured or client not available.")
        return "YouTube search unavailable. Please configure YOUTUBE_API_KEY."

    try:
        yt = build("youtube", "v3", developerKey=api_key)
        req = yt.search().list(
            q=query,
            part="snippet",
            type="video",
            videoCategoryId=10,
            maxResults=1,
            order="relevance",
            safeSearch="moderate",
        )
        res = req.execute()
        items = res.get("items", [])
        if items:
            print(f"---- YouTube search results: {items[0]}")
            video_id = items[0].get("id", {}).get("videoId")
            video_detail = yt.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id,
            ).execute()
            print(f"---- YouTube video detail: {video_detail}")
            if video_id:
                return f"<youtube_url>https://www.youtube.com/watch?v={video_id}</youtube_url>"
        return "No matching song found on YouTube."
    except Exception as e:
        logger.error(f"YouTube search failed: {e}")
        return "Failed to search YouTube."


class SoulcareTeam:
    """Soul Care Team using autogen framework with life advisor and song recommender agents"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.max_turns = 10
        self.cancellation_token = CancellationToken()
        self.initial_message = ""
        self.external_termination = ExternalTermination()
        
        # Create agents
        self._create_agents()
        self._create_team()
    
    def _create_agents(self):
        """Create the life advisor and song recommender agents"""
        
        # Create the Life Advisor assistant agent
        self.life_advisor = AssistantAgent(
            name="LifeAdvisor",
            model_client=self.llm_client,
            system_message="""
            You are an empathetic life advisor who helps users explore and understand their life situations.
            Your role is to:
            1. Ask thoughtful questions about their current situation
            2. Listen actively and show understanding
            3. Provide supportive and constructive feedback
            4. Help them gain clarity about their challenges and goals
        
            """
        )

        # Create the Song Recommender assistant agent
        self.song_recommender = AssistantAgent(
            name="SongRecommender",
            model_client=self.llm_client,
            tools=[search_song],
            system_message="""
            You are a song recommender that provides music based on people's life situations.
            When it's your turn:
            1. Analyze the conversation context and emotional state
            2. Use the search_song tool to find an appropriate song
            3. Share the song link
            """
        )

        # Create the user proxy agent
        self.user_proxy = UserProxyAgent(
            name="UserProxy",
            input_func=self._get_user_input,  # Custom input function
        )
    
    def _create_team(self):
        """Create the selector team"""
        
        # Create the selector prompt for intelligent agent selection
        selector_prompt = """Select the most appropriate agent to respond next.

        Roles:
        - LifeAdvisor: Explores user's situation, provides guidance and emotional support
        - SongRecommender: Searches for songs to match the user's emotional needs
        - UserProxy: User's input and feedback

        Current conversation context:
        {history}

        Select the next agent from {participants} based on these rules:
        1. If the user just shared new information about their situation, select LifeAdvisor
        2. If LifeAdvisor has provided guidance AND has gathered sufficient emotional context about the user's situation AND has suggested music, select SongRecommender
        3. After SongRecommender shares a song, select User for feedback
        4. If unsure or need more emotional context, select LifeAdvisor to gather more information
        5. If the user has provided feedback, select User to gather more information

        Select only one agent.
        """
        # Create the selector team
        self.team = SelectorGroupChat(
            participants=[self.life_advisor, self.song_recommender, self.user_proxy],
            selector_prompt=selector_prompt,
            model_client=self.llm_client,
            max_turns=self.max_turns,
            termination_condition=SourceMatchTermination(sources=["UserProxy", "SongRecommender"]) | self.external_termination
        )
    
    async def _get_user_input(self, prompt: str, cancellation_token: Optional[CancellationToken] = None) -> str:
        """Custom input function that returns the initial user message"""
        # For now, we'll use the initial message stored in the class
        # In a real implementation, this could be connected to a web interface
        return "Handover to user"
    
    async def run_conversation_with_socket(
        self, 
        user_message: str, 
        user_sid: str, 
        task_id: str,
        socketio_service=None,
        output_stats: bool = True
    ) -> Dict[str, Any]:
        """Run the soul care conversation with Socket.IO streaming"""
        try:
            logger.info(f"Starting soul care conversation for task {task_id}")
            self.initial_message = user_message

            # Run the conversation stream
            async for message in self.team.run_stream(
                task=TextMessage(content=user_message, source="User"),
                cancellation_token=self.cancellation_token
            ):
                if socketio_service and isinstance(message, TextMessage):
                    # Emit streaming message
                    print("--------------------------------")
                    print(f"---- Message Source: {message.source}")
                    print(f"---- Message Type: {message.type}")
                    print(f"---- Message Content: {message.content}")
                    print("--------------------------------")
                    await socketio_service.sio.emit('task_message', {
                            'task_id': task_id,
                            'type': 'stream',
                            'data': {
                                'message': str(message.content),
                                'agent': getattr(message, 'source', 'system')
                            }
                        }, room=user_sid)
                elif isinstance(message, ToolCallSummaryMessage):
                    print("--------------------------------")
                    print(f"---- Message Source: {message.source}")
                    print(f"---- Message Type: {message.type}")
                    print(f"---- Message Content: {message.content}")
                    print(f"---- Message Tool Call Results: {message.results}")
                    print("--------------------------------")
                    await socketio_service.sio.emit('task_message', {
                        'task_id': task_id,
                        'type': 'stream',
                        'data': {
                            'message': message.content,
                            'agent': getattr(message, 'source', 'system')
                        }
                    }, room=user_sid)
                elif isinstance(message, ToolCallRequestEvent):
                    print("--------------------------------")
                    print(f"---- Message Source: {message.source}")
                    print(f"---- Message Type: {message.type}")
                    print(f"---- Message Content: {message.content}")
                    print("--------------------------------")

            if socketio_service:
                # Emit completion event
                await socketio_service.sio.emit('task_message', {
                    'task_id': task_id,
                    'type': 'complete',
                    'data': {
                        'message': 'Soul care conversation completed'
                    }
                }, room=user_sid)

            return {
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"Error in soul care conversation: {str(e)}")
            
            if socketio_service:
                # Emit error event
                await socketio_service.sio.emit('task_message', {
                    'task_id': task_id,
                    'type': 'error',
                    'data': {
                        'message': f"Error in conversation: {str(e)}"
                    }
                }, room=user_sid)
                
            return {
                "error": str(e)
            }
    
    async def save_state(self) -> Dict[str, Any]:
        """Save the current state of the team"""
        try:
            state = await self.team.save_state()
            return state
        except Exception as e:
            logger.error(f"Failed to save state: {str(e)}")
            return {"error": f"Failed to save state: {str(e)}"}
    
    async def load_state(self, state: Dict[str, Any]) -> bool:
        """Load a previously saved state"""
        try:
            await self.team.load_state(state)
            return True
        except Exception as e:
            logger.error(f"Failed to load state: {str(e)}")
            return False
    
    def cancel_conversation(self):
        """Cancel the ongoing conversation"""
        self.cancellation_token.cancel()
        logger.info("Soul care conversation cancelled")
    