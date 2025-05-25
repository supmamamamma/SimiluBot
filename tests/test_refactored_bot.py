"""Tests for the refactored bot architecture."""
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import tempfile
import os
import pytest

from similubot.core.command_registry import CommandRegistry, CommandInfo
from similubot.core.event_handler import EventHandler
from similubot.commands.mega_commands import MegaCommands
from similubot.commands.novelai_commands import NovelAICommands
from similubot.commands.auth_commands import AuthCommands
from similubot.commands.general_commands import GeneralCommands
from similubot.auth.authorization_manager import AuthorizationManager
from similubot.auth.unauthorized_handler import UnauthorizedAccessHandler


class TestCommandRegistry(unittest.TestCase):
    """Test cases for CommandRegistry."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_bot = MagicMock()
        self.mock_auth_manager = MagicMock()
        self.mock_unauthorized_handler = MagicMock()
        
        self.registry = CommandRegistry(
            bot=self.mock_bot,
            auth_manager=self.mock_auth_manager,
            unauthorized_handler=self.mock_unauthorized_handler
        )

    def test_command_registration(self):
        """Test command registration."""
        async def test_callback(ctx):
            pass

        self.registry.register_command(
            name="test",
            callback=test_callback,
            description="Test command",
            required_permission="test"
        )

        # Check command was registered
        commands = self.registry.get_registered_commands()
        assert "test" in commands
        assert commands["test"].name == "test"
        assert commands["test"].description == "Test command"
        assert commands["test"].required_permission == "test"

        # Check bot.add_command was called
        self.mock_bot.add_command.assert_called_once()

    def test_command_group_registration(self):
        """Test command group registration."""
        group = self.registry.register_command_group(
            name="testgroup",
            description="Test group",
            admin_only=True
        )

        assert group.name == "testgroup"
        self.mock_bot.add_command.assert_called_once()

    def test_group_command_registration(self):
        """Test registering commands within a group."""
        group = self.registry.register_command_group("testgroup", "Test group")
        
        async def test_callback(ctx):
            pass

        self.registry.register_group_command(
            group=group,
            name="subcmd",
            callback=test_callback,
            description="Sub command"
        )

        # Check group has the command
        assert len(group.commands) == 1

    @pytest.mark.asyncio
    async def test_authorization_wrapper(self):
        """Test that commands are wrapped with authorization."""
        self.mock_auth_manager.is_authorized.return_value = True
        
        callback_called = False
        
        async def test_callback(ctx):
            nonlocal callback_called
            callback_called = True

        self.registry.register_command(
            name="test",
            callback=test_callback,
            description="Test command",
            required_permission="test"
        )

        # Get the wrapped command
        wrapped_command = self.mock_bot.add_command.call_args[0][0]
        
        # Create mock context
        mock_ctx = MagicMock()
        mock_ctx.author.id = "123456789"

        # Execute wrapped command
        await wrapped_command.callback(mock_ctx)

        # Check authorization was checked
        self.mock_auth_manager.is_authorized.assert_called_once_with(
            "123456789", command_name="test"
        )
        
        # Check original callback was called
        assert callback_called

    @pytest.mark.asyncio
    async def test_unauthorized_access_handling(self):
        """Test unauthorized access handling."""
        self.mock_auth_manager.is_authorized.return_value = False
        
        async def test_callback(ctx):
            pass

        self.registry.register_command(
            name="test",
            callback=test_callback,
            description="Test command",
            required_permission="test"
        )

        # Get the wrapped command
        wrapped_command = self.mock_bot.add_command.call_args[0][0]
        
        # Create mock context
        mock_ctx = MagicMock()
        mock_ctx.author.id = "123456789"
        mock_ctx.channel = MagicMock()

        # Execute wrapped command
        await wrapped_command.callback(mock_ctx)

        # Check unauthorized handler was called
        self.mock_unauthorized_handler.handle_unauthorized_access.assert_called_once()


class TestEventHandler(unittest.TestCase):
    """Test cases for EventHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_bot = MagicMock()
        self.mock_auth_manager = MagicMock()
        self.mock_unauthorized_handler = MagicMock()
        self.mock_mega_downloader = MagicMock()
        self.mock_mega_processor = AsyncMock()

        self.event_handler = EventHandler(
            bot=self.mock_bot,
            auth_manager=self.mock_auth_manager,
            unauthorized_handler=self.mock_unauthorized_handler,
            mega_downloader=self.mock_mega_downloader,
            mega_processor_callback=self.mock_mega_processor
        )

    def test_event_registration(self):
        """Test that events are registered with the bot."""
        # Check that bot.event was called for each event
        assert self.mock_bot.event.call_count >= 3  # on_ready, on_message, on_command_error

    @pytest.mark.asyncio
    async def test_mega_auto_detection_authorized(self):
        """Test MEGA auto-detection with authorization."""
        # Setup mocks
        self.mock_auth_manager.is_authorized.return_value = True
        self.mock_mega_downloader.extract_mega_links.return_value = ["https://mega.nz/test"]
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.content = "Check out this file: https://mega.nz/test"
        mock_message.author = MagicMock()
        mock_message.author.id = "123456789"
        mock_message.channel = MagicMock()

        # Test auto-detection
        await self.event_handler._handle_mega_auto_detection(mock_message)

        # Check authorization was checked
        self.mock_auth_manager.is_authorized.assert_called_once_with(
            "123456789", feature_name="mega_auto_detection"
        )

        # Check processor was called
        self.mock_mega_processor.assert_called_once_with(mock_message, "https://mega.nz/test")

    @pytest.mark.asyncio
    async def test_mega_auto_detection_unauthorized(self):
        """Test MEGA auto-detection without authorization."""
        # Setup mocks
        self.mock_auth_manager.is_authorized.return_value = False
        self.mock_mega_downloader.extract_mega_links.return_value = ["https://mega.nz/test"]
        
        # Create mock message
        mock_message = MagicMock()
        mock_message.content = "Check out this file: https://mega.nz/test"
        mock_message.author = MagicMock()
        mock_message.author.id = "123456789"
        mock_message.channel = MagicMock()

        # Test auto-detection
        await self.event_handler._handle_mega_auto_detection(mock_message)

        # Check unauthorized handler was called
        self.mock_unauthorized_handler.handle_unauthorized_access.assert_called_once()

        # Check processor was NOT called
        self.mock_mega_processor.assert_not_called()

    def test_get_event_stats(self):
        """Test event statistics."""
        self.mock_bot.is_ready.return_value = True
        self.mock_bot.user = MagicMock()
        self.mock_bot.guilds = [MagicMock(), MagicMock()]
        self.mock_auth_manager.auth_enabled = True

        stats = self.event_handler.get_event_stats()

        assert stats["bot_ready"] is True
        assert stats["guild_count"] == 2
        assert stats["authorization_enabled"] is True


class TestMegaCommands(unittest.TestCase):
    """Test cases for MegaCommands."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
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

    def test_command_registration(self):
        """Test that MEGA commands are registered."""
        mock_registry = MagicMock()
        
        self.mega_commands.register_commands(mock_registry)
        
        # Check that register_command was called
        mock_registry.register_command.assert_called_once_with(
            name="mega",
            callback=self.mega_commands.mega_command,
            description="Download a file from MEGA and convert it to AAC",
            required_permission="mega"
        )

    @pytest.mark.asyncio
    async def test_mega_command_invalid_link(self):
        """Test MEGA command with invalid link."""
        self.mock_downloader.is_mega_link.return_value = False
        
        mock_ctx = MagicMock()
        mock_ctx.reply = AsyncMock()

        await self.mega_commands.mega_command(mock_ctx, "invalid_url")

        mock_ctx.reply.assert_called_once_with("❌ Invalid MEGA link. Please provide a valid MEGA link.")

    def test_format_file_size(self):
        """Test file size formatting."""
        assert self.mega_commands._format_file_size(1024) == "1.0 KB"
        assert self.mega_commands._format_file_size(1024 * 1024) == "1.0 MB"
        assert self.mega_commands._format_file_size(1024 * 1024 * 1024) == "1.0 GB"


class TestGeneralCommands(unittest.TestCase):
    """Test cases for GeneralCommands."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
        self.mock_config.get_supported_formats.return_value = ["mp4", "mp3", "wav"]
        self.mock_config.get_default_bitrate.return_value = 128
        
        self.general_commands = GeneralCommands(
            config=self.mock_config,
            image_generator=None
        )

    def test_command_registration(self):
        """Test that general commands are registered."""
        mock_registry = MagicMock()
        
        self.general_commands.register_commands(mock_registry)
        
        # Check that commands were registered
        assert mock_registry.register_command.call_count == 3  # about, help, status

    @pytest.mark.asyncio
    async def test_about_command(self):
        """Test about command."""
        mock_ctx = MagicMock()
        mock_ctx.send = AsyncMock()
        mock_ctx.bot.command_prefix = "!"
        mock_ctx.bot.guilds = []

        await self.general_commands.about_command(mock_ctx)

        # Check that an embed was sent
        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        assert "embed" in call_args[1]

    def test_get_command_count(self):
        """Test command count."""
        assert self.general_commands.get_command_count() == 3


class TestAuthCommands(unittest.TestCase):
    """Test cases for AuthCommands."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_auth_manager = MagicMock()
        self.mock_auth_manager.auth_enabled = True
        
        self.auth_commands = AuthCommands(
            auth_manager=self.mock_auth_manager
        )

    def test_command_registration(self):
        """Test that auth commands are registered."""
        mock_registry = MagicMock()
        mock_group = MagicMock()
        mock_registry.register_command_group.return_value = mock_group
        
        self.auth_commands.register_commands(mock_registry)
        
        # Check that group was created
        mock_registry.register_command_group.assert_called_once()
        
        # Check that subcommands were registered
        assert mock_registry.register_group_command.call_count == 4  # status, user, add, remove

    def test_is_available(self):
        """Test availability check."""
        assert self.auth_commands.is_available() is True
        
        self.mock_auth_manager.auth_enabled = False
        assert self.auth_commands.is_available() is False


if __name__ == "__main__":
    pytest.main([__file__])
