"""Conversation memory management for AI chat functionality."""

import logging
import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from similubot.utils.config_manager import ConfigManager


@dataclass
class ConversationSession:
    """
    Represents a conversation session for a user.

    Attributes:
        user_id: Discord user ID
        messages: List of conversation messages
        last_activity: Timestamp of last activity
        system_prompt: System prompt for this conversation
        mode: Conversation mode (default, danbooru)
    """
    user_id: int
    messages: List[Dict[str, str]] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)
    system_prompt: Optional[str] = None
    mode: str = "default"

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.messages.append({"role": role, "content": content})
        self.last_activity = time.time()

    def get_messages(self, max_history: int) -> List[Dict[str, str]]:
        """
        Get recent messages for the conversation.

        Args:
            max_history: Maximum number of messages to return

        Returns:
            List of recent messages
        """
        # Keep the most recent messages, but always include system messages
        if len(self.messages) <= max_history:
            return self.messages.copy()

        # Separate system messages from conversation messages
        system_messages = [msg for msg in self.messages if msg["role"] == "system"]
        conversation_messages = [msg for msg in self.messages if msg["role"] != "system"]

        # Take the most recent conversation messages
        recent_conversation = conversation_messages[-max_history:]

        # Combine system messages with recent conversation
        return system_messages + recent_conversation

    def is_expired(self, timeout: int) -> bool:
        """
        Check if the conversation session has expired.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if expired, False otherwise
        """
        return time.time() - self.last_activity > timeout

    def clear_history(self) -> None:
        """Clear conversation history but keep system messages."""
        system_messages = [msg for msg in self.messages if msg["role"] == "system"]
        self.messages = system_messages
        self.last_activity = time.time()


class ConversationMemory:
    """
    Manages conversation memory for multiple users with automatic cleanup.

    Features:
    - Per-user conversation sessions
    - Automatic timeout and cleanup
    - Message history management
    - Mode-specific system prompts
    """

    def __init__(self, config: ConfigManager):
        """
        Initialize the conversation memory manager.

        Args:
            config: Configuration manager instance
        """
        self.logger = logging.getLogger("similubot.ai.memory")
        self.config = config

        # Configuration
        self.timeout = config.get_ai_conversation_timeout()
        self.max_history = config.get_ai_max_conversation_history()

        # Active conversations
        self.conversations: Dict[int, ConversationSession] = {}

        # System prompts for different modes
        self.system_prompts = {
            "default": config.get_ai_default_system_prompt(),
            "danbooru": config.get_ai_danbooru_system_prompt()
        }

        # Start cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()

        self.logger.info(f"Conversation memory initialized - Timeout: {self.timeout}s, Max history: {self.max_history}")

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_expired_conversations())
        except RuntimeError:
            # No event loop running (e.g., during testing)
            self.logger.debug("No event loop running, cleanup task not started")
            self._cleanup_task = None

    async def _cleanup_expired_conversations(self) -> None:
        """Background task to clean up expired conversations."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                expired_users = []
                for user_id, session in self.conversations.items():
                    if session.is_expired(self.timeout):
                        expired_users.append(user_id)

                for user_id in expired_users:
                    del self.conversations[user_id]
                    self.logger.debug(f"Cleaned up expired conversation for user {user_id}")

                if expired_users:
                    self.logger.info(f"Cleaned up {len(expired_users)} expired conversations")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in conversation cleanup task: {e}", exc_info=True)

    def get_or_create_session(self, user_id: int, mode: str = "default") -> ConversationSession:
        """
        Get or create a conversation session for a user.

        Args:
            user_id: Discord user ID
            mode: Conversation mode (default, danbooru)

        Returns:
            Conversation session for the user
        """
        # Check if user has an existing session
        if user_id in self.conversations:
            session = self.conversations[user_id]

            # Check if session has expired
            if session.is_expired(self.timeout):
                self.logger.debug(f"Conversation session expired for user {user_id}")
                del self.conversations[user_id]
            else:
                # Update mode if different
                if session.mode != mode:
                    self.logger.debug(f"Switching conversation mode for user {user_id}: {session.mode} -> {mode}")
                    session.mode = mode
                    session.system_prompt = self.system_prompts.get(mode)
                    # Clear history when switching modes
                    session.clear_history()

                session.last_activity = time.time()
                return session

        # Create new session
        session = ConversationSession(
            user_id=user_id,
            mode=mode,
            system_prompt=self.system_prompts.get(mode)
        )

        self.conversations[user_id] = session
        self.logger.debug(f"Created new conversation session for user {user_id} in mode '{mode}'")

        return session

    def add_user_message(self, user_id: int, content: str, mode: str = "default") -> None:
        """
        Add a user message to the conversation.

        Args:
            user_id: Discord user ID
            content: Message content
            mode: Conversation mode
        """
        session = self.get_or_create_session(user_id, mode)
        session.add_message("user", content)
        self.logger.debug(f"Added user message for {user_id}: {len(content)} characters")

    def add_assistant_message(self, user_id: int, content: str) -> None:
        """
        Add an assistant message to the conversation.

        Args:
            user_id: Discord user ID
            content: Message content
        """
        if user_id in self.conversations:
            session = self.conversations[user_id]
            session.add_message("assistant", content)
            self.logger.debug(f"Added assistant message for {user_id}: {len(content)} characters")

    def get_conversation_messages(self, user_id: int, mode: str = "default") -> List[Dict[str, str]]:
        """
        Get conversation messages for a user.

        Args:
            user_id: Discord user ID
            mode: Conversation mode

        Returns:
            List of conversation messages
        """
        session = self.get_or_create_session(user_id, mode)
        messages = session.get_messages(self.max_history)

        self.logger.debug(f"Retrieved {len(messages)} messages for user {user_id}")
        return messages

    def clear_conversation(self, user_id: int) -> bool:
        """
        Clear conversation history for a user.

        Args:
            user_id: Discord user ID

        Returns:
            True if conversation was cleared, False if no conversation existed
        """
        if user_id in self.conversations:
            self.conversations[user_id].clear_history()
            self.logger.debug(f"Cleared conversation history for user {user_id}")
            return True
        return False

    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Get conversation statistics.

        Returns:
            Dictionary with conversation statistics
        """
        active_conversations = len(self.conversations)
        total_messages = sum(len(session.messages) for session in self.conversations.values())

        mode_counts = {}
        for session in self.conversations.values():
            mode_counts[session.mode] = mode_counts.get(session.mode, 0) + 1

        return {
            "active_conversations": active_conversations,
            "total_messages": total_messages,
            "mode_distribution": mode_counts,
            "timeout_seconds": self.timeout,
            "max_history": self.max_history
        }

    async def shutdown(self) -> None:
        """Shutdown the conversation memory manager."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        self.conversations.clear()
        self.logger.info("Conversation memory manager shut down")
