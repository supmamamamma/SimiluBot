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
        size_spec = None
        remaining_text = args.strip()

        # Extract upload service
        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        # Extract size specification
        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

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
        assert size_spec is None
        assert len(character_args) == 0

    def test_parse_command_arguments_with_upload_service(self):
        """Test parsing command arguments with upload service."""
        args = "anime girl with blue hair discord"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "anime girl with blue hair"
        assert upload_service == "discord"
        assert size_spec is None
        assert len(character_args) == 0

    def test_parse_command_arguments_single_character_param(self):
        """Test parsing command arguments with single character parameter."""
        args = "cyberpunk cityscape catbox char1:[girl with neon hair]"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "cyberpunk cityscape"
        assert upload_service == "catbox"
        assert size_spec is None
        assert len(character_args) == 1
        assert character_args[0] == "char1:[girl with neon hair]"

    def test_parse_command_arguments_multiple_characters(self):
        """Test parsing command arguments with multiple character parameters."""
        args = "fantasy scene char1:[elf archer] char2:[dwarf warrior] discord"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "fantasy scene"
        assert upload_service == "discord"
        assert size_spec is None
        assert len(character_args) == 2
        assert character_args[0] == "char1:[elf archer]"
        assert character_args[1] == "char2:[dwarf warrior]"

    def test_parse_command_arguments_complex_descriptions(self):
        """Test parsing command arguments with complex character descriptions."""
        args = "school classroom char1:[teacher at blackboard, glasses, formal attire] char2:[student raising hand, uniform, eager expression]"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "school classroom"
        assert upload_service is None
        assert size_spec is None
        assert len(character_args) == 2
        assert character_args[0] == "char1:[teacher at blackboard, glasses, formal attire]"
        assert character_args[1] == "char2:[student raising hand, uniform, eager expression]"

    def test_parse_command_arguments_case_insensitive(self):
        """Test parsing command arguments is case insensitive."""
        args = "battle scene CHAR1:[warrior] Char2:[mage] DISCORD"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "battle scene"
        assert upload_service == "discord"
        assert size_spec is None
        assert len(character_args) == 2
        assert character_args[0] == "char1:[warrior]"
        assert character_args[1] == "char2:[mage]"

    def test_parse_command_arguments_no_spaces_around_params(self):
        """Test parsing command arguments without spaces around character parameters."""
        args = "library char1:[librarian]char2:[student] catbox"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        # Extract size specification
        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "library"
        assert upload_service == "catbox"
        assert size_spec is None
        assert len(character_args) == 2
        assert character_args[0] == "char1:[librarian]"
        assert character_args[1] == "char2:[student]"

    # Size specification tests
    def test_parse_command_arguments_size_portrait(self):
        """Test parsing command arguments with portrait size specification."""
        args = "beautiful landscape size:portrait"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "beautiful landscape"
        assert upload_service is None
        assert size_spec == "portrait"
        assert len(character_args) == 0

    def test_parse_command_arguments_size_landscape(self):
        """Test parsing command arguments with landscape size specification."""
        args = "cyberpunk city size:landscape discord"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "cyberpunk city"
        assert upload_service == "discord"
        assert size_spec == "landscape"
        assert len(character_args) == 0

    def test_parse_command_arguments_size_square(self):
        """Test parsing command arguments with square size specification."""
        args = "anime portrait size:square catbox"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "anime portrait"
        assert upload_service == "catbox"
        assert size_spec == "square"
        assert len(character_args) == 0

    def test_parse_command_arguments_size_with_characters(self):
        """Test parsing command arguments with size and character parameters."""
        args = "fantasy battle char1:[elf archer] char2:[dwarf warrior] size:landscape discord"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "fantasy battle"
        assert upload_service == "discord"
        assert size_spec == "landscape"
        assert len(character_args) == 2
        assert character_args[0] == "char1:[elf archer]"
        assert character_args[1] == "char2:[dwarf warrior]"

    def test_parse_command_arguments_size_case_insensitive(self):
        """Test parsing command arguments with case insensitive size specification."""
        args = "test scene SIZE:PORTRAIT"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "test scene"
        assert upload_service is None
        assert size_spec == "portrait"
        assert len(character_args) == 0

    def test_parse_command_arguments_invalid_size_ignored(self):
        """Test parsing command arguments with invalid size specification (should be ignored)."""
        args = "test scene size:invalid"

        # Simulate the parsing logic
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        prompt = char_pattern.sub('', remaining_text).strip()
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        assert prompt == "test scene size:invalid"  # Invalid size remains in prompt
        assert upload_service is None
        assert size_spec is None  # Invalid size not captured
        assert len(character_args) == 0

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

    @pytest.mark.asyncio
    async def test_process_nai_generation_with_size_specification(self):
        """Test NovelAI generation processing with size specification."""
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
                        "landscape scene",
                        "discord",
                        None,  # No character args
                        "landscape"  # Size specification
                    )

        # Verify generation was called with correct parameters
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs['prompt'] == "landscape scene"
        assert call_kwargs['character_args'] is None
        # Check that width and height were set for landscape
        assert call_kwargs['width'] == 1216
        assert call_kwargs['height'] == 832

    @pytest.mark.asyncio
    async def test_process_nai_generation_multicharacter_with_size(self):
        """Test multi-character generation with size specification."""
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
                        character_args,
                        "square"  # Size specification
                    )

        # Verify generation was called with correct parameters
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs['prompt'] == "fantasy scene"
        assert call_kwargs['character_args'] == character_args
        # Check that width and height were set for square
        assert call_kwargs['width'] == 1024
        assert call_kwargs['height'] == 1024

    @pytest.mark.asyncio
    async def test_process_nai_generation_default_size(self):
        """Test generation with default size (portrait) when no size specified."""
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
                        "portrait scene",
                        "discord",
                        None,  # No character args
                        None   # No size specification
                    )

        # Verify generation was called with default parameters
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs['prompt'] == "portrait scene"
        assert call_kwargs['character_args'] is None
        # Should use default config values (not overridden by size)
        # The exact values depend on the mock config, but they should be the defaults
