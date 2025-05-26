"""Comprehensive tests for NovelAI functionality."""
import unittest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from similubot.generators.novelai_client import NovelAIClient
from similubot.commands.novelai_commands import NovelAICommands


class TestNovelAIClient(unittest.TestCase):
    """Test NovelAI API client functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = NovelAIClient("test_api_key")

    def test_client_initialization(self):
        """Test NovelAI client initialization."""
        self.assertEqual(self.client.api_key, "test_api_key")
        self.assertEqual(self.client.base_url, "https://api.novelai.net")


class TestNovelAICommands(unittest.TestCase):
    """Test NovelAI commands functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_config.get_novelai_upload_service.return_value = "discord"

        self.mock_image_generator = MagicMock()
        self.mock_catbox_uploader = MagicMock()
        self.mock_discord_uploader = MagicMock()

        self.novelai_commands = NovelAICommands(
            config=self.mock_config,
            image_generator=self.mock_image_generator,
            catbox_uploader=self.mock_catbox_uploader,
            discord_uploader=self.mock_discord_uploader
        )

    def test_novelai_commands_initialization(self):
        """Test NovelAI commands initialization."""
        self.assertIsNotNone(self.novelai_commands)

    def test_novelai_commands_registration(self):
        """Test NovelAI commands registration."""
        # Create mock registry
        mock_registry = MagicMock()

        # Register commands
        self.novelai_commands.register_commands(mock_registry)

        # Verify registration was called
        mock_registry.register_command.assert_called_once()
        call_args = mock_registry.register_command.call_args[1]
        self.assertEqual(call_args['name'], 'nai')
        self.assertIsNotNone(call_args['usage_examples'])
        self.assertIsNotNone(call_args['help_text'])


if __name__ == "__main__":
    unittest.main()
