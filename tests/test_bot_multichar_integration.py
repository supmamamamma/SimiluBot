"""Tests for Discord bot multi-character NovelAI integration."""
import pytest
import re
from unittest.mock import patch, MagicMock, AsyncMock
import discord
from discord.ext import commands

from similubot.bot import SimiluBot
from similubot.utils.config_manager import ConfigManager


class TestBotMultiCharacterIntegration:
    """Test cases for Discord bot multi-character functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock config
        self.mock_config = MagicMock(spec=ConfigManager)
        self.mock_config.get_discord_token.return_value = "test_token"
        self.mock_config.get.return_value = "!"
        self.mock_config.get_novelai_default_parameters.return_value = {
            'width': 832,
            'height': 1216,
            'steps': 23,
            'scale': 5.0,
            'sampler': 'k_euler_ancestral',
            'n_samples': 1,
            'seed': -1,
            'ucPreset': 0
        }
        self.mock_config.get_novelai_default_model.return_value = "nai-diffusion-4-5-curated"
        self.mock_config.get_novelai_upload_service.return_value = "discord"

        # Create bot instance with mocked dependencies
        with patch('similubot.bot.ImageGenerator'), \
             patch('similubot.bot.MegaDownloader'), \
             patch('similubot.bot.AudioConverter'), \
             patch('similubot.bot.CatboxUploader'), \
             patch('similubot.bot.DiscordUploader'):
            self.bot = SimiluBot(self.mock_config)

    def test_parse_command_arguments_single_character(self):
        """Test parsing command arguments for single character (traditional)."""
        args = "beautiful sunset over mountains"

        # Simulate the parsing logic from bot.py
        upload_service = None
        character_args = []
        remaining_text = args.strip()

        # Extract upload service
        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        # Extract character parameters
        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        # Remove character parameters to get prompt
        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "beautiful sunset over mountains"
        assert upload_service is None
        assert len(character_args) == 0

    def test_parse_command_arguments_with_upload_service(self):
        """Test parsing command arguments with upload service."""
        args = "anime girl with blue hair discord"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "anime girl with blue hair"
        assert upload_service == "discord"
        assert len(character_args) == 0

    def test_parse_command_arguments_single_character_param(self):
        """Test parsing command arguments with single character parameter."""
        args = "cyberpunk cityscape catbox char1:[girl with neon hair]"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "cyberpunk cityscape"
        assert upload_service == "catbox"
        assert len(character_args) == 1
        assert character_args[0] == "char1:[girl with neon hair]"

    def test_parse_command_arguments_multiple_characters(self):
        """Test parsing command arguments with multiple character parameters."""
        args = "fantasy scene char1:[elf archer] char2:[dwarf warrior] discord"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "fantasy scene"
        assert upload_service == "discord"
        assert len(character_args) == 2
        assert character_args[0] == "char1:[elf archer]"
        assert character_args[1] == "char2:[dwarf warrior]"

    def test_parse_command_arguments_complex_descriptions(self):
        """Test parsing command arguments with complex character descriptions."""
        args = "school classroom char1:[teacher at blackboard, glasses, formal attire] char2:[student raising hand, uniform, eager expression]"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "school classroom"
        assert upload_service is None
        assert len(character_args) == 2
        assert character_args[0] == "char1:[teacher at blackboard, glasses, formal attire]"
        assert character_args[1] == "char2:[student raising hand, uniform, eager expression]"

    def test_parse_command_arguments_case_insensitive(self):
        """Test parsing command arguments is case insensitive."""
        args = "battle scene CHAR1:[warrior] Char2:[mage] DISCORD"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "battle scene"
        assert upload_service == "discord"
        assert len(character_args) == 2
        assert character_args[0] == "char1:[warrior]"
        assert character_args[1] == "char2:[mage]"

    def test_parse_command_arguments_no_spaces_around_params(self):
        """Test parsing command arguments without spaces around character parameters."""
        args = "library char1:[librarian]char2:[student] catbox"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "library"
        assert upload_service == "catbox"
        assert len(character_args) == 2
        assert character_args[0] == "char1:[librarian]"
        assert character_args[1] == "char2:[student]"

    @pytest.mark.asyncio
    async def test_process_nai_generation_multicharacter_success(self):
        """Test successful multi-character NovelAI generation processing."""
        # Mock Discord message
        mock_message = MagicMock()
        mock_message.reply = AsyncMock()
        mock_message.channel = MagicMock()

        # Mock successful generation
        mock_file_paths = ["/tmp/test_image.png"]
        with patch.object(self.bot.image_generator, 'generate_image_with_progress') as mock_generate:
            mock_generate.return_value = (True, mock_file_paths, None)

            with patch.object(self.bot.discord_uploader, 'upload') as mock_upload:
                mock_upload.return_value = (True, MagicMock(), None)

                with patch.object(self.bot, '_cleanup_temp_files'):
                    character_args = ["char1:[girl with blue hair]", "char2:[boy with red eyes]"]
                    await self.bot._process_nai_generation(
                        mock_message,
                        "fantasy scene",
                        "discord",
                        character_args
                    )

        # Verify generation was called with character args
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs['character_args'] == character_args
        assert call_kwargs['prompt'] == "fantasy scene"

    @pytest.mark.asyncio
    async def test_process_nai_generation_single_character_fallback(self):
        """Test single character generation (traditional behavior)."""
        # Mock Discord message
        mock_message = MagicMock()
        mock_message.reply = AsyncMock()
        mock_message.channel = MagicMock()

        # Mock successful generation
        mock_file_paths = ["/tmp/test_image.png"]
        with patch.object(self.bot.image_generator, 'generate_image_with_progress') as mock_generate:
            mock_generate.return_value = (True, mock_file_paths, None)

            with patch.object(self.bot.discord_uploader, 'upload') as mock_upload:
                mock_upload.return_value = (True, MagicMock(), None)

                with patch.object(self.bot, '_cleanup_temp_files'):
                    await self.bot._process_nai_generation(
                        mock_message,
                        "simple scene",
                        "discord",
                        None  # No character args
                    )

        # Verify generation was called without character args
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs['character_args'] is None
        assert call_kwargs['prompt'] == "simple scene"
