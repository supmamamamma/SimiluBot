"""Comprehensive tests for MEGA functionality."""
import unittest
import tempfile
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from similubot.downloaders.mega_downloader import MegaDownloader
from similubot.converters.audio_converter import AudioConverter
from similubot.commands.mega_commands import MegaCommands


class TestMegaDownloader(unittest.TestCase):
    """Test MEGA downloader functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.downloader = MegaDownloader()

    def test_downloader_initialization(self):
        """Test MEGA downloader initialization."""
        self.assertIsNotNone(self.downloader)


class TestAudioConverter(unittest.TestCase):
    """Test audio conversion functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.converter = AudioConverter()

    def test_converter_initialization(self):
        """Test audio converter initialization."""
        self.assertIsNotNone(self.converter)


class TestMegaCommands(unittest.TestCase):
    """Test MEGA commands functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_config.get_mega_upload_service.return_value = "catbox"
        self.mock_config.get_default_bitrate.return_value = 128

        self.mock_downloader = MagicMock()
        self.mock_converter = MagicMock()
        self.mock_catbox_uploader = MagicMock()
        self.mock_discord_uploader = MagicMock()

        self.mega_commands = MegaCommands(
            config=self.mock_config,
            downloader=self.mock_downloader,
            converter=self.mock_converter,
            catbox_uploader=self.mock_catbox_uploader,
            discord_uploader=self.mock_discord_uploader
        )

    def test_mega_commands_initialization(self):
        """Test MEGA commands initialization."""
        self.assertIsNotNone(self.mega_commands)

    def test_mega_commands_registration(self):
        """Test MEGA commands registration."""
        # Create mock registry
        mock_registry = MagicMock()

        # Register commands
        self.mega_commands.register_commands(mock_registry)

        # Verify registration was called
        mock_registry.register_command.assert_called_once()
        call_args = mock_registry.register_command.call_args[1]
        self.assertEqual(call_args['name'], 'mega')
        self.assertIsNotNone(call_args['usage_examples'])
        self.assertIsNotNone(call_args['help_text'])


if __name__ == "__main__":
    unittest.main()
