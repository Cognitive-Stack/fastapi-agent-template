import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient, AzureOpenAIChatCompletionClient

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def search_song(song_name: str) -> str:
    """
    Search for a song on the internet.
    Args:
        song_name: The name of the song to search for.
    Returns:
        A URL of the song.
    """
    songs = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Never Gonna Give You Up
        "https://www.youtube.com/watch?v=y6120QOlsfU",  # Darude - Sandstorm
        "https://www.youtube.com/watch?v=L_jWHffIx5E",  # All Star
        "https://www.youtube.com/watch?v=9bZkp7q19f0",  # Gangnam Style
        "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",  # Bohemian Rhapsody
        "https://www.youtube.com/watch?v=YykjpeuMNEk",  # Hymn for the Weekend
        "https://www.youtube.com/watch?v=09R8_2nJtjg",  # Maroon 5 - Sugar
        "https://www.youtube.com/watch?v=OPf0YbXqDm0",  # Mark Ronson - Uptown Funk
        "https://www.youtube.com/watch?v=pRpeEdMmmQ0",  # Imagine Dragons - Believer
        "https://www.youtube.com/watch?v=YVkUvmDQ3HY"   # Ed Sheeran - Shape of You
    ]
    return random.choice(songs)


class SoulcareTeam:
    """Soul Care Team using autogen framework with life advisor and song recommender agents"""
    
    def __init__(self):
        self.llm_client = create_llm_client()
        self.max_turns = 10
        self.cancellation_token = CancellationToken()
        self.conversation_history: List[Dict[str, Any]] = []
        self.initial_message = ""
        
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
            
            After understanding their situation, suggest moving to song recommendation 
            by ending your message with: "Let's find a song that resonates with your situation."
            """,
            model_client_stream=True
        )

        # Create the Song Recommender assistant agent
        self.song_recommender = AssistantAgent(
            name="SongRecommender",
            model_client=self.llm_client,
            tools=[search_song],
            max_tool_iterations=2,
            system_message="""
            You are a thoughtful song recommender that suggests music based on people's life situations.
            When it's your turn:
            1. Analyze the conversation context and emotional state
            2. Explain why you think a particular type of song would be meaningful
            3. Use the search_song tool to find a song
            4. Share the song link and explain why you think it might resonate
            
            Then ask for user feedback with:
            "How does this song resonate with your situation?"
            """,
            model_client_stream=True
        )

        # Create the user proxy agent
        self.user_proxy = UserProxyAgent(
            name="User",
            input_func=self._get_user_input,  # Custom input function
        )
    
    def _create_team(self):
        """Create the selector team"""
        
        # Create the selector prompt for intelligent agent selection
        selector_prompt = """Select the most appropriate agent to respond next.

        Roles:
        - LifeAdvisor: Explores user's situation, provides guidance and emotional support
        - SongRecommender: Suggests music based on user's emotional state and situation
        - User: User's input and feedback

        Current conversation context:
        {history}

        Select the next agent from {participants} based on these rules:
        1. If the user just shared new information about their situation, select LifeAdvisor
        2. If LifeAdvisor has provided guidance and suggested music, select SongRecommender
        3. After SongRecommender shares a song, select User for feedback
        4. If unsure, select User to gather more information
        5. If the user has provided feedback, select User to gather more information

        Select only one agent.
        """

        # Create the selector team
        self.team = SelectorGroupChat(
            participants=[self.life_advisor, self.song_recommender, self.user_proxy],
            selector_prompt=selector_prompt,
            model_client=self.llm_client,
            allow_repeated_speaker=True,
            max_turns=self.max_turns,
        )
    
    async def _get_user_input(self, prompt: str, cancellation_token: Optional[CancellationToken] = None) -> str:
        """Custom input function that returns the initial user message"""
        # For now, we'll use the initial message stored in the class
        # In a real implementation, this could be connected to a web interface
        return self.initial_message
    
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
            self.conversation_history = []

            if socketio_service:
                # Emit start event
                await socketio_service.sio.emit('task_message', {
                    'task_id': task_id,
                    'type': 'start',
                    'data': {
                        'message': 'Soul care team is starting...'
                    }
                }, room=user_sid)

            # Run the conversation stream
            async for message in self.team.run_stream(
                task=user_message,
                cancellation_token=self.cancellation_token
            ):
                # Store message in conversation history
                self.conversation_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'message': message
                })
                
                if socketio_service:
                    # Emit streaming message
                    await socketio_service.sio.emit('task_message', {
                        'task_id': task_id,
                        'type': 'stream',
                        'data': {
                            'message': str(message),
                            'agent': getattr(message, 'source', 'system')
                        }
                    }, room=user_sid)

            if socketio_service:
                # Emit completion event
                await socketio_service.sio.emit('task_message', {
                    'task_id': task_id,
                    'type': 'complete',
                    'data': {
                        'message': 'Soul care conversation completed',
                        'conversation_history': self.conversation_history
                    }
                }, room=user_sid)

            return {
                "success": True,
                "conversation_history": self.conversation_history
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
                "error": str(e),
                "conversation_history": self.conversation_history
            }
    
    async def run_conversation(self, user_message: str) -> Dict[str, Any]:
        """Run the soul care conversation (legacy method for backward compatibility)"""
        try:
            logger.info("Starting soul care conversation")
            self.initial_message = user_message
            self.conversation_history = []
            
            # Run conversation and collect messages
            async for message in self.team.run_stream(
                task=user_message,
                cancellation_token=self.cancellation_token
            ):
                self.conversation_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'message': str(message),
                    'agent': getattr(message, 'source', 'system')
                })
            
            return {
                "success": True,
                "conversation_history": self.conversation_history
            }
            
        except Exception as e:
            logger.error(f"Error in soul care conversation: {str(e)}")
            return {
                "error": str(e),
                "conversation_history": self.conversation_history
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
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation"""
        return {
            "total_messages": len(self.conversation_history),
            "agents_involved": list(set([msg.get('agent', 'unknown') for msg in self.conversation_history])),
            "start_time": self.conversation_history[0]['timestamp'] if self.conversation_history else None,
            "last_message_time": self.conversation_history[-1]['timestamp'] if self.conversation_history else None
        }
    