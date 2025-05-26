"""Comprehensive tests for AI functionality."""

import unittest
import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch, Mock
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from similubot.ai.ai_client import AIClient
from similubot.ai.conversation_memory import ConversationMemory, ConversationSession
from similubot.ai.ai_tracker import AITracker
from similubot.commands.ai_commands import AICommands
from similubot.utils.config_manager import ConfigManager


class TestAIClient(unittest.TestCase):
    """Test AI client functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock(spec=ConfigManager)
        self.mock_config.is_ai_configured.return_value = True
        self.mock_config.get_default_ai_provider.return_value = "openrouter"
        self.mock_config.get_ai_provider_config.return_value = {
            'base_url': 'https://openrouter.ai/api/v1',
            'api_key': 'test_key',
            'model': 'test_model'
        }
        self.mock_config.get_ai_max_tokens.return_value = 2048
        self.mock_config.get_ai_temperature.return_value = 0.7

    @patch('similubot.ai.ai_client.AsyncOpenAI')
    def test_ai_client_initialization(self, mock_openai):
        """Test AI client initialization."""
        client = AIClient(self.mock_config)

        self.assertEqual(client.provider, "openrouter")
        self.assertEqual(client.model, "test_model")
        self.assertEqual(client.max_tokens, 2048)
        self.assertEqual(client.temperature, 0.7)
        mock_openai.assert_called_once()

    @patch('similubot.ai.ai_client.AsyncOpenAI')
    def test_ai_client_invalid_provider(self, mock_openai):
        """Test AI client with invalid provider configuration."""
        self.mock_config.get_ai_provider_config.side_effect = ValueError("Provider not configured")

        with self.assertRaises(ValueError):
            AIClient(self.mock_config)

    @patch('similubot.ai.ai_client.AsyncOpenAI')
    def test_generate_response(self, mock_openai):
        """Test AI response generation."""
        async def run_test():
            # Mock OpenAI response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"

            mock_client_instance = AsyncMock()
            mock_client_instance.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client_instance

            client = AIClient(self.mock_config)
            messages = [{"role": "user", "content": "Hello"}]

            response = await client.generate_response(messages)

            self.assertEqual(response, "Test response")
            mock_client_instance.chat.completions.create.assert_called_once()

        asyncio.run(run_test())

    @patch('similubot.ai.ai_client.AsyncOpenAI')
    def test_generate_streaming_response(self, mock_openai):
        """Test AI streaming response generation."""
        async def run_test():
            # Mock streaming response
            mock_chunk1 = MagicMock()
            mock_chunk1.choices = [MagicMock()]
            mock_chunk1.choices[0].delta.content = "Hello "

            mock_chunk2 = MagicMock()
            mock_chunk2.choices = [MagicMock()]
            mock_chunk2.choices[0].delta.content = "world!"

            async def mock_stream():
                yield mock_chunk1
                yield mock_chunk2

            mock_client_instance = AsyncMock()
            mock_client_instance.chat.completions.create.return_value = mock_stream()
            mock_openai.return_value = mock_client_instance

            client = AIClient(self.mock_config)
            messages = [{"role": "user", "content": "Hello"}]

            chunks = []
            async for chunk in client.generate_streaming_response(messages):
                chunks.append(chunk)

            self.assertEqual(chunks, ["Hello ", "world!"])

        asyncio.run(run_test())

    @patch('similubot.ai.ai_client.AsyncOpenAI')
    def test_test_connection(self, mock_openai):
        """Test AI connection testing."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test"

            mock_client_instance = AsyncMock()
            mock_client_instance.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client_instance

            client = AIClient(self.mock_config)
            result = await client.test_connection()

            self.assertTrue(result)

        asyncio.run(run_test())

    @patch('similubot.ai.ai_client.AsyncOpenAI')
    def test_is_available(self, mock_openai):
        """Test AI client availability check."""
        client = AIClient(self.mock_config)
        self.assertTrue(client.is_available())


class TestConversationMemory(unittest.TestCase):
    """Test conversation memory functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock(spec=ConfigManager)
        self.mock_config.get_ai_conversation_timeout.return_value = 1800
        self.mock_config.get_ai_max_conversation_history.return_value = 10
        self.mock_config.get_ai_default_system_prompt.return_value = "Default prompt"
        self.mock_config.get_ai_danbooru_system_prompt.return_value = "Danbooru prompt"

    @patch('asyncio.create_task')
    def test_conversation_memory_initialization(self, mock_create_task):
        """Test conversation memory initialization."""
        memory = ConversationMemory(self.mock_config)

        self.assertEqual(memory.timeout, 1800)
        self.assertEqual(memory.max_history, 10)
        self.assertEqual(len(memory.conversations), 0)
        mock_create_task.assert_called_once()

    @patch('asyncio.create_task')
    def test_get_or_create_session(self, mock_create_task):
        """Test getting or creating conversation sessions."""
        memory = ConversationMemory(self.mock_config)

        # Create new session
        session = memory.get_or_create_session(12345, "default")
        self.assertEqual(session.user_id, 12345)
        self.assertEqual(session.mode, "default")
        self.assertEqual(len(memory.conversations), 1)

        # Get existing session
        same_session = memory.get_or_create_session(12345, "default")
        self.assertEqual(session, same_session)
        self.assertEqual(len(memory.conversations), 1)

    @patch('asyncio.create_task')
    def test_add_messages(self, mock_create_task):
        """Test adding messages to conversations."""
        memory = ConversationMemory(self.mock_config)

        memory.add_user_message(12345, "Hello", "default")
        memory.add_assistant_message(12345, "Hi there!")

        messages = memory.get_conversation_messages(12345, "default")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Hello")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "Hi there!")

    @patch('asyncio.create_task')
    def test_mode_switching(self, mock_create_task):
        """Test switching conversation modes."""
        memory = ConversationMemory(self.mock_config)

        # Start in default mode
        memory.add_user_message(12345, "Hello", "default")
        self.assertEqual(len(memory.get_conversation_messages(12345, "default")), 1)

        # Switch to danbooru mode (should clear history)
        session = memory.get_or_create_session(12345, "danbooru")
        self.assertEqual(session.mode, "danbooru")
        # History should be cleared when switching modes
        messages = memory.get_conversation_messages(12345, "danbooru")
        # Should only have system messages, no user messages
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        self.assertEqual(len(user_messages), 0)

    @patch('asyncio.create_task')
    def test_clear_conversation(self, mock_create_task):
        """Test clearing conversation history."""
        memory = ConversationMemory(self.mock_config)

        memory.add_user_message(12345, "Hello", "default")
        memory.add_assistant_message(12345, "Hi there!")

        result = memory.clear_conversation(12345)
        self.assertTrue(result)

        messages = memory.get_conversation_messages(12345, "default")
        # Should only have system messages after clearing
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        self.assertEqual(len(user_messages), 0)

    @patch('asyncio.create_task')
    def test_conversation_stats(self, mock_create_task):
        """Test conversation statistics."""
        memory = ConversationMemory(self.mock_config)

        memory.add_user_message(12345, "Hello", "default")
        memory.add_user_message(67890, "Hi", "danbooru")

        stats = memory.get_conversation_stats()
        self.assertEqual(stats["active_conversations"], 2)
        self.assertGreater(stats["total_messages"], 0)
        self.assertIn("default", stats["mode_distribution"])
        self.assertIn("danbooru", stats["mode_distribution"])


class TestAITracker(unittest.TestCase):
    """Test AI progress tracking functionality."""

    def test_ai_tracker_initialization(self):
        """Test AI tracker initialization."""
        tracker = AITracker("Test AI Operation")
        self.assertEqual(tracker.operation_name, "Test AI Operation")
        self.assertEqual(tracker.tokens_generated, 0)

    def test_start_request(self):
        """Test starting AI request tracking."""
        tracker = AITracker()
        tracker.start_request(100, 500)

        self.assertIsNotNone(tracker.request_start_time)
        self.assertEqual(tracker.estimated_total_tokens, 500)
        self.assertIsNotNone(tracker.current_progress)

    def test_update_token_progress(self):
        """Test updating token generation progress."""
        tracker = AITracker()
        tracker.start_request(100, 500)
        tracker.start_response_generation()

        tracker.update_token_progress(250, "Partial response")

        self.assertEqual(tracker.tokens_generated, 250)
        self.assertIsNotNone(tracker.current_progress)
        self.assertGreater(tracker.current_progress.percentage, 15.0)

    def test_complete_generation(self):
        """Test completing AI generation."""
        tracker = AITracker()
        tracker.start_request(100, 500)
        tracker.start_response_generation()

        tracker.complete_generation("Final response", 500)

        self.assertIsNotNone(tracker.current_progress)
        self.assertEqual(tracker.current_progress.percentage, 100.0)

    def test_fail_generation(self):
        """Test failing AI generation."""
        tracker = AITracker()
        tracker.start_request(100, 500)

        tracker.fail_generation("Test error")

        self.assertIsNotNone(tracker.current_progress)
        self.assertIn("failed", tracker.current_progress.message.lower())

    def test_generation_stats(self):
        """Test getting generation statistics."""
        tracker = AITracker()
        tracker.start_request(100, 500)
        tracker.start_response_generation()
        tracker.update_token_progress(250)

        stats = tracker.get_generation_stats()

        self.assertEqual(stats["tokens_generated"], 250)
        self.assertEqual(stats["estimated_total_tokens"], 500)
        self.assertIn("total_elapsed", stats)
        self.assertIn("generation_elapsed", stats)


class TestAICommands(unittest.TestCase):
    """Test AI commands functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock(spec=ConfigManager)
        self.mock_config.get_default_ai_provider.return_value = "openrouter"
        self.mock_config.get_ai_provider_config.return_value = {
            'base_url': 'https://openrouter.ai/api/v1',
            'api_key': 'test_key',
            'model': 'test_model'
        }
        self.mock_config.get_ai_max_tokens.return_value = 2048
        self.mock_config.get_ai_temperature.return_value = 0.7
        self.mock_config.get_ai_conversation_timeout.return_value = 1800
        self.mock_config.get_ai_max_conversation_history.return_value = 10
        self.mock_config.get_ai_default_system_prompt.return_value = "Default prompt"
        self.mock_config.get_ai_danbooru_system_prompt.return_value = "Danbooru prompt"

    @patch('similubot.ai.ai_client.AsyncOpenAI')
    @patch('asyncio.create_task')
    def test_ai_commands_initialization(self, mock_create_task, mock_openai):
        """Test AI commands initialization."""
        commands = AICommands(self.mock_config)

        self.assertTrue(commands.is_available())
        self.assertIsNotNone(commands.ai_client)
        self.assertIsNotNone(commands.conversation_memory)

    @patch('similubot.ai.ai_client.AsyncOpenAI')
    @patch('asyncio.create_task')
    def test_ai_commands_not_configured(self, mock_create_task, mock_openai):
        """Test AI commands when not configured."""
        self.mock_config.is_ai_configured.return_value = False

        commands = AICommands(self.mock_config)

        self.assertFalse(commands.is_available())
        self.assertIsNone(commands.ai_client)

    def test_parse_ai_arguments(self):
        """Test parsing AI command arguments."""
        commands = AICommands(self.mock_config)
        commands._available = True  # Mock availability

        # Test default mode
        mode, prompt = commands._parse_ai_arguments("Hello world")
        self.assertEqual(mode, "default")
        self.assertEqual(prompt, "Hello world")

        # Test danbooru mode
        mode, prompt = commands._parse_ai_arguments("anime girl mode:danbooru")
        self.assertEqual(mode, "danbooru")
        self.assertEqual(prompt, "anime girl")

        # Test invalid mode (should default to default and remove mode specification)
        mode, prompt = commands._parse_ai_arguments("test mode:invalid")
        self.assertEqual(mode, "default")
        self.assertEqual(prompt, "test")  # Mode specification should be removed

    def test_get_command_count(self):
        """Test getting command count."""
        # Mock available commands
        commands = AICommands(self.mock_config)
        commands._available = True
        self.assertEqual(commands.get_command_count(), 1)

        # Mock unavailable commands
        commands._available = False
        self.assertEqual(commands.get_command_count(), 0)


if __name__ == '__main__':
    unittest.main()
