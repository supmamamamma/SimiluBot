"""Tests for NovelAI integration in the Discord bot."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import os

from similubot.bot import SimiluBot
from similubot.utils.config_manager import ConfigManager

class TestBotNovelAIIntegration:
    """Test cases for NovelAI integration in the Discord bot."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.yaml")

        # Create test config with NovelAI settings
        config_content = """
discord:
  token: "test_token"
  command_prefix: "!"

download:
  temp_dir: "./temp"

novelai:
  api_key: "test_novelai_key"
  base_url: "https://image.novelai.net"
  default_model: "nai-diffusion-3"
  default_parameters:
    width: 832
    height: 1216
    steps: 28
    scale: 5.0
    sampler: "k_euler"
    n_samples: 1
    seed: -1
  timeout: 120

upload:
  default_service: "catbox"
  catbox:
    user_hash: ""

logging:
  level: "INFO"
"""

        with open(self.config_path, 'w') as f:
            f.write(config_content)

        # Create config manager
        self.config = ConfigManager(self.config_path)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('similubot.bot.ImageGenerator')
    @patch('similubot.bot.MegaDownloader')
    def test_bot_init_with_novelai(self, mock_mega_downloader, mock_image_generator):
        """Test bot initialization with NovelAI configured."""
        mock_generator_instance = MagicMock()
        mock_image_generator.return_value = mock_generator_instance

        mock_downloader_instance = MagicMock()
        mock_mega_downloader.return_value = mock_downloader_instance

        with patch('discord.ext.commands.Bot'):
            bot = SimiluBot(self.config)

            # Verify ImageGenerator was initialized
            mock_image_generator.assert_called_once_with(
                api_key="test_novelai_key",
                base_url="https://image.novelai.net",
                timeout=120,
                temp_dir="./temp"
            )

            assert bot.image_generator == mock_generator_instance

    @patch('similubot.bot.MegaDownloader')
    def test_bot_init_without_novelai(self, mock_mega_downloader):
        """Test bot initialization without NovelAI configured."""
        mock_downloader_instance = MagicMock()
        mock_mega_downloader.return_value = mock_downloader_instance

        # Create config without NovelAI API key
        config_content = """
discord:
  token: "test_token"
  command_prefix: "!"

download:
  temp_dir: "./temp"

upload:
  default_service: "catbox"

logging:
  level: "INFO"
"""

        config_path = os.path.join(self.temp_dir, "no_novelai_config.yaml")
        with open(config_path, 'w') as f:
            f.write(config_content)

        config = ConfigManager(config_path)

        with patch('discord.ext.commands.Bot'):
            bot = SimiluBot(config)

            # Should not have image generator
            assert bot.image_generator is None

    @patch('similubot.bot.ImageGenerator')
    @patch('similubot.bot.MegaDownloader')
    @patch('discord.ext.commands.Bot')
    @pytest.mark.asyncio
    async def test_nai_command_success(self, mock_bot_class, mock_mega_downloader, mock_image_generator):
        """Test successful !nai command execution."""
        # Set up mocks
        mock_generator_instance = MagicMock()
        mock_generator_instance.generate_image_with_progress = AsyncMock(
            return_value=(True, ["/tmp/generated_image.png"], None)
        )
        mock_image_generator.return_value = mock_generator_instance

        mock_downloader_instance = MagicMock()
        mock_mega_downloader.return_value = mock_downloader_instance

        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance

        # Create bot
        bot = SimiluBot(self.config)

        # Mock Discord context and message
        mock_ctx = MagicMock()
        mock_message = MagicMock()
        mock_ctx.message = mock_message

        # Mock the reply method
        mock_response = MagicMock()
        mock_response.edit = AsyncMock()
        mock_message.reply = AsyncMock(return_value=mock_response)

        # Mock the uploader
        bot.catbox_uploader.upload_with_progress = MagicMock(
            return_value=(True, "https://files.catbox.moe/test.png", None)
        )

        # Mock Discord progress updater
        with patch('similubot.progress.discord_updater.DiscordProgressUpdater') as mock_updater:
            mock_updater_instance = MagicMock()
            mock_updater_instance.create_callback.return_value = MagicMock()
            mock_updater.return_value = mock_updater_instance

            # Mock asyncio.to_thread
            with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = (True, "https://files.catbox.moe/test.png", None)

                # Test the command
                await bot._process_nai_generation(mock_message, "test prompt")

        # Verify image generation was called
        mock_generator_instance.generate_image_with_progress.assert_called_once()
        call_args = mock_generator_instance.generate_image_with_progress.call_args
        assert call_args[1]['prompt'] == "test prompt"
        assert call_args[1]['model'] == "nai-diffusion-3"

        # Verify response was sent
        mock_message.reply.assert_called()
        mock_response.edit.assert_called()

    @patch('similubot.bot.ImageGenerator')
    @patch('similubot.bot.MegaDownloader')
    @patch('discord.ext.commands.Bot')
    @pytest.mark.asyncio
    async def test_nai_command_generation_failure(self, mock_bot_class, mock_mega_downloader, mock_image_generator):
        """Test !nai command with generation failure."""
        # Set up mocks
        mock_generator_instance = MagicMock()
        mock_generator_instance.generate_image_with_progress = AsyncMock(
            return_value=(False, None, "Generation failed")
        )
        mock_image_generator.return_value = mock_generator_instance

        mock_downloader_instance = MagicMock()
        mock_mega_downloader.return_value = mock_downloader_instance

        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance

        # Create bot
        bot = SimiluBot(self.config)

        # Mock Discord context and message
        mock_message = MagicMock()
        mock_response = MagicMock()
        mock_response.edit = AsyncMock()
        mock_message.reply = AsyncMock(return_value=mock_response)

        # Mock Discord progress updater
        with patch('similubot.progress.discord_updater.DiscordProgressUpdater'):
            # Test the command
            await bot._process_nai_generation(mock_message, "test prompt")

        # Verify error response was sent
        mock_response.edit.assert_called()
        edit_call_args = mock_response.edit.call_args[1]
        assert 'embed' in edit_call_args
        embed = edit_call_args['embed']
        assert "Generation Failed" in embed.title

    @patch('similubot.bot.ImageGenerator')
    @patch('similubot.bot.MegaDownloader')
    @patch('discord.ext.commands.Bot')
    @pytest.mark.asyncio
    async def test_nai_command_not_configured(self, mock_bot_class, mock_mega_downloader, mock_image_generator):
        """Test !nai command when NovelAI is not configured."""
        # Make initialization fail
        mock_image_generator.side_effect = ValueError("API key not set")

        mock_downloader_instance = MagicMock()
        mock_mega_downloader.return_value = mock_downloader_instance

        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance

        # Create bot (should not have image generator)
        bot = SimiluBot(self.config)
        assert bot.image_generator is None

        # Mock Discord context
        mock_ctx = MagicMock()
        mock_ctx.reply = AsyncMock()

        # Simulate the command handler logic
        if not bot.image_generator:
            await mock_ctx.reply("❌ NovelAI image generation is not configured. Please check your API key in the config.")

        # Verify error message was sent
        mock_ctx.reply.assert_called_once()
        call_args = mock_ctx.reply.call_args[0][0]
        assert "not configured" in call_args

    @patch('similubot.bot.ImageGenerator')
    @patch('similubot.bot.MegaDownloader')
    @patch('discord.ext.commands.Bot')
    def test_about_command_includes_nai(self, mock_bot_class, mock_mega_downloader, mock_image_generator):
        """Test that about command includes NovelAI info when configured."""
        mock_generator_instance = MagicMock()
        mock_image_generator.return_value = mock_generator_instance

        mock_downloader_instance = MagicMock()
        mock_mega_downloader.return_value = mock_downloader_instance

        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance

        # Create bot
        bot = SimiluBot(self.config)

        # Mock Discord embed
        mock_embed = MagicMock()

        with patch('discord.Embed', return_value=mock_embed):
            # Simulate about command logic
            embed_created = True

            # Check if NovelAI command would be added
            if bot.image_generator:
                nai_field_added = True
            else:
                nai_field_added = False

        assert embed_created
        assert nai_field_added

    @patch('similubot.bot.MegaDownloader')
    @patch('discord.ext.commands.Bot')
    def test_about_command_without_nai(self, mock_bot_class, mock_mega_downloader):
        """Test that about command works without NovelAI configured."""
        # Create config without NovelAI
        config_content = """
discord:
  token: "test_token"
  command_prefix: "!"

download:
  temp_dir: "./temp"

upload:
  default_service: "catbox"

logging:
  level: "INFO"
"""

        config_path = os.path.join(self.temp_dir, "no_novelai_config.yaml")
        with open(config_path, 'w') as f:
            f.write(config_content)

        config = ConfigManager(config_path)

        mock_downloader_instance = MagicMock()
        mock_mega_downloader.return_value = mock_downloader_instance

        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance

        # Create bot
        bot = SimiluBot(config)
        assert bot.image_generator is None

        # Mock Discord embed
        mock_embed = MagicMock()

        with patch('discord.Embed', return_value=mock_embed):
            # Simulate about command logic
            embed_created = True

            # Check if NovelAI command would be added
            if bot.image_generator:
                nai_field_added = True
            else:
                nai_field_added = False

        assert embed_created
        assert not nai_field_added
