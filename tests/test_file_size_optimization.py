"""Tests for file size optimization functionality."""
import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from similubot.bot import SimiluBot
from similubot.utils.config_manager import ConfigManager


class TestFileSizeOptimization(unittest.TestCase):
    """Test cases for file size optimization functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock config
        self.mock_config = MagicMock(spec=ConfigManager)
        self.mock_config.get_download_temp_dir.return_value = "/tmp"
        self.mock_config.get_default_bitrate.return_value = 320
        self.mock_config.get_supported_formats.return_value = ["mp3", "flac", "wav"]
        self.mock_config.get_catbox_user_hash.return_value = "test_hash"
        self.mock_config.get_mega_upload_service.return_value = "catbox"
        self.mock_config.get_novelai_api_key.side_effect = ValueError("Not configured")
        self.mock_config.get.return_value = "!"

        # Create bot instance with mocked dependencies
        with patch('similubot.bot.os.makedirs'), \
             patch('similubot.bot.os.path.exists', return_value=True), \
             patch('similubot.bot.MegaDownloader') as mock_downloader_class, \
             patch('similubot.bot.AudioConverter') as mock_converter_class, \
             patch('similubot.bot.CatboxUploader') as mock_catbox_class, \
             patch('similubot.bot.DiscordUploader') as mock_discord_class:

            # Set up mock instances
            self.mock_downloader = MagicMock()
            self.mock_converter = MagicMock()
            self.mock_catbox_uploader = MagicMock()
            self.mock_discord_uploader = MagicMock()

            mock_downloader_class.return_value = self.mock_downloader
            mock_converter_class.return_value = self.mock_converter
            mock_catbox_class.return_value = self.mock_catbox_uploader
            mock_discord_class.return_value = self.mock_discord_uploader

            self.bot = SimiluBot(self.mock_config)

    @pytest.mark.asyncio
    async def test_optimize_file_size_within_limit(self):
        """Test optimization when file is already within size limit."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as original_file, \
             tempfile.NamedTemporaryFile(delete=False) as converted_file:

            # Write small amount of data (under 200MB)
            converted_file.write(b"x" * (50 * 1024 * 1024))  # 50MB
            converted_file.flush()

            try:
                # Mock progress callback
                progress_callback = AsyncMock()

                # Test optimization
                result_file, result_bitrate = await self.bot._optimize_file_size_for_catbox(
                    original_file.name,
                    converted_file.name,
                    320,
                    progress_callback
                )

                # Should return original file since it's within limit
                assert result_file == converted_file.name
                assert result_bitrate == 320

                # Progress callback should not be called for optimization
                progress_callback.assert_not_called()

            finally:
                # Clean up
                os.unlink(original_file.name)
                os.unlink(converted_file.name)

    @pytest.mark.asyncio
    async def test_optimize_file_size_exceeds_limit_success(self):
        """Test optimization when file exceeds limit but can be optimized."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as original_file, \
             tempfile.NamedTemporaryFile(delete=False) as converted_file, \
             tempfile.NamedTemporaryFile(delete=False) as optimized_file:

            # Write large amount of data (over 200MB)
            converted_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
            converted_file.flush()

            # Write smaller optimized data
            optimized_file.write(b"x" * (150 * 1024 * 1024))  # 150MB
            optimized_file.flush()

            try:
                # Mock progress callback
                progress_callback = AsyncMock()

                # Mock converter to return optimized file
                mock_convert = AsyncMock()
                self.bot.converter.convert_to_aac_with_progress = mock_convert
                mock_convert.return_value = (True, optimized_file.name, None)

                # Test optimization
                result_file, result_bitrate = await self.bot._optimize_file_size_for_catbox(
                    original_file.name,
                    converted_file.name,
                    320,
                    progress_callback
                )

                # Should return optimized file
                assert result_file == optimized_file.name
                assert result_bitrate == 256  # Next lower bitrate in hierarchy

                # Converter should be called with lower bitrate
                mock_convert.assert_called_once_with(
                    original_file.name,
                    256,
                    None,
                    progress_callback
                )

                # Progress callback should be called
                assert progress_callback.call_count >= 2  # At least start and success

            finally:
                # Clean up
                os.unlink(original_file.name)
                os.unlink(converted_file.name)
                os.unlink(optimized_file.name)

    @pytest.mark.asyncio
    async def test_optimize_file_size_exceeds_limit_failure(self):
        """Test optimization when file exceeds limit and cannot be optimized."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as original_file, \
             tempfile.NamedTemporaryFile(delete=False) as converted_file:

            # Write large amount of data (over 200MB)
            converted_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
            converted_file.flush()

            try:
                # Mock progress callback
                progress_callback = AsyncMock()

                # Mock converter to always return large files
                def mock_convert_large(*args, **kwargs):
                    with tempfile.NamedTemporaryFile(delete=False) as large_file:
                        large_file.write(b"x" * (250 * 1024 * 1024))  # Still 250MB
                        large_file.flush()
                        return (True, large_file.name, None)

                with patch.object(self.bot.converter, 'convert_to_aac_with_progress', side_effect=mock_convert_large):
                    # Test optimization
                    result_file, result_bitrate = await self.bot._optimize_file_size_for_catbox(
                        original_file.name,
                        converted_file.name,
                        320,
                        progress_callback
                    )

                    # Should return None since optimization failed
                    assert result_file is None
                    assert result_bitrate == 320  # Original bitrate returned

                    # Progress callback should be called with failure message
                    progress_callback.assert_called()

            finally:
                # Clean up
                os.unlink(original_file.name)
                os.unlink(converted_file.name)

    @pytest.mark.asyncio
    async def test_optimize_file_size_bitrate_hierarchy(self):
        """Test that optimization follows the correct bitrate hierarchy."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as original_file, \
             tempfile.NamedTemporaryFile(delete=False) as converted_file:

            # Write large amount of data (over 200MB)
            converted_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
            converted_file.flush()

            try:
                # Mock progress callback
                progress_callback = AsyncMock()

                # Track conversion attempts
                conversion_attempts = []

                def mock_convert(original, bitrate, output, callback):
                    conversion_attempts.append(bitrate)
                    if bitrate == 128:  # Succeed at 128 kbps
                        with tempfile.NamedTemporaryFile(delete=False) as small_file:
                            small_file.write(b"x" * (150 * 1024 * 1024))  # 150MB
                            small_file.flush()
                            return (True, small_file.name, None)
                    else:
                        # Still too large for higher bitrates
                        with tempfile.NamedTemporaryFile(delete=False) as large_file:
                            large_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
                            large_file.flush()
                            return (True, large_file.name, None)

                with patch.object(self.bot.converter, 'convert_to_aac_with_progress', side_effect=mock_convert):
                    # Test optimization starting from 384 kbps
                    result_file, result_bitrate = await self.bot._optimize_file_size_for_catbox(
                        original_file.name,
                        converted_file.name,
                        384,
                        progress_callback
                    )

                    # Should succeed at 128 kbps
                    assert result_file is not None
                    assert result_bitrate == 128

                    # Should try bitrates in order: 320, 256, 192, 128
                    expected_attempts = [320, 256, 192, 128]
                    assert conversion_attempts == expected_attempts

            finally:
                # Clean up
                os.unlink(original_file.name)
                os.unlink(converted_file.name)

    @pytest.mark.asyncio
    async def test_optimize_file_size_conversion_error(self):
        """Test optimization when conversion fails."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as original_file, \
             tempfile.NamedTemporaryFile(delete=False) as converted_file:

            # Write large amount of data (over 200MB)
            converted_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
            converted_file.flush()

            try:
                # Mock progress callback
                progress_callback = AsyncMock()

                # Mock converter to fail
                with patch.object(self.bot.converter, 'convert_to_aac_with_progress') as mock_convert:
                    mock_convert.return_value = (False, None, "Conversion failed")

                    # Test optimization
                    result_file, result_bitrate = await self.bot._optimize_file_size_for_catbox(
                        original_file.name,
                        converted_file.name,
                        320,
                        progress_callback
                    )

                    # Should return None since conversion failed
                    assert result_file is None
                    assert result_bitrate == 320  # Original bitrate returned

            finally:
                # Clean up
                os.unlink(original_file.name)
                os.unlink(converted_file.name)

    @pytest.mark.asyncio
    async def test_optimize_file_size_custom_bitrate(self):
        """Test optimization with custom bitrate not in hierarchy."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as original_file, \
             tempfile.NamedTemporaryFile(delete=False) as converted_file:

            # Write large amount of data (over 200MB)
            converted_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
            converted_file.flush()

            try:
                # Mock progress callback
                progress_callback = AsyncMock()

                # Mock converter to succeed at first attempt
                with patch.object(self.bot.converter, 'convert_to_aac_with_progress') as mock_convert:
                    with tempfile.NamedTemporaryFile(delete=False) as small_file:
                        small_file.write(b"x" * (150 * 1024 * 1024))  # 150MB
                        small_file.flush()
                        mock_convert.return_value = (True, small_file.name, None)

                        # Test optimization with custom bitrate (400 kbps)
                        result_file, result_bitrate = await self.bot._optimize_file_size_for_catbox(
                            original_file.name,
                            converted_file.name,
                            400,  # Custom bitrate not in hierarchy
                            progress_callback
                        )

                        # Should succeed with first lower bitrate in hierarchy (512)
                        assert result_file == small_file.name
                        assert result_bitrate == 512

                        # Should try 512 kbps first (highest in hierarchy)
                        mock_convert.assert_called_once_with(
                            original_file.name,
                            512,
                            None,
                            progress_callback
                        )

            finally:
                # Clean up
                os.unlink(original_file.name)
                os.unlink(converted_file.name)


if __name__ == "__main__":
    pytest.main([__file__])
