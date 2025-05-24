"""Integration tests for MEGA download with file size optimization."""
import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from similubot.bot import SimiluBot
from similubot.utils.config_manager import ConfigManager


class TestMegaIntegration(unittest.TestCase):
    """Test cases for MEGA download integration with file size optimization."""

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

    @pytest.mark.asyncio
    async def test_mega_processing_with_size_optimization(self):
        """Test MEGA processing workflow with file size optimization."""
        # Create bot instance with mocked dependencies
        with patch('similubot.bot.os.makedirs'), \
             patch('similubot.bot.os.path.exists', return_value=True), \
             patch('similubot.bot.MegaDownloader') as mock_downloader_class, \
             patch('similubot.bot.AudioConverter') as mock_converter_class, \
             patch('similubot.bot.CatboxUploader') as mock_catbox_class, \
             patch('similubot.bot.DiscordUploader') as mock_discord_class:
            
            # Set up mock instances
            mock_downloader = MagicMock()
            mock_converter = MagicMock()
            mock_catbox_uploader = MagicMock()
            mock_discord_uploader = MagicMock()
            
            mock_downloader_class.return_value = mock_downloader
            mock_converter_class.return_value = mock_converter
            mock_catbox_class.return_value = mock_catbox_uploader
            mock_discord_class.return_value = mock_discord_uploader
            
            bot = SimiluBot(self.mock_config)
            
            # Create temporary files for testing
            with tempfile.NamedTemporaryFile(delete=False) as downloaded_file, \
                 tempfile.NamedTemporaryFile(delete=False) as large_converted_file, \
                 tempfile.NamedTemporaryFile(delete=False) as optimized_file:
                
                # Write large file (over 200MB)
                large_converted_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
                large_converted_file.flush()
                
                # Write optimized file (under 200MB)
                optimized_file.write(b"x" * (150 * 1024 * 1024))  # 150MB
                optimized_file.flush()
                
                try:
                    # Mock Discord message
                    mock_message = MagicMock()
                    mock_message.reply = AsyncMock()
                    
                    # Mock download success
                    mock_downloader.download_with_progress.return_value = (True, downloaded_file.name, None)
                    
                    # Mock initial conversion (large file)
                    conversion_calls = []
                    def mock_convert(input_file, bitrate, output_file, callback):
                        conversion_calls.append(bitrate)
                        if bitrate == 320:  # Initial conversion
                            return (True, large_converted_file.name, None)
                        elif bitrate == 256:  # Optimization attempt
                            return (True, optimized_file.name, None)
                        else:
                            return (False, None, "Conversion failed")
                    
                    mock_converter.convert_to_aac_with_progress.side_effect = mock_convert
                    
                    # Mock upload success
                    mock_catbox_uploader.upload_with_progress.return_value = (True, "https://files.catbox.moe/test.aac", None)
                    
                    # Test the MEGA processing workflow
                    await bot._process_mega_link(mock_message, "https://mega.nz/file/test", 320)
                    
                    # Verify download was called
                    mock_downloader.download_with_progress.assert_called_once()
                    
                    # Verify conversion was called twice (initial + optimization)
                    assert len(conversion_calls) == 2
                    assert conversion_calls[0] == 320  # Initial conversion
                    assert conversion_calls[1] == 256  # Optimization attempt
                    
                    # Verify upload was called with optimized file
                    mock_catbox_uploader.upload_with_progress.assert_called_once()
                    upload_args = mock_catbox_uploader.upload_with_progress.call_args[0]
                    assert upload_args[0] == optimized_file.name  # Should upload optimized file
                    
                    # Verify success message was sent
                    mock_message.reply.assert_called()
                    
                finally:
                    # Clean up
                    for file_path in [downloaded_file.name, large_converted_file.name, optimized_file.name]:
                        try:
                            os.unlink(file_path)
                        except FileNotFoundError:
                            pass

    @pytest.mark.asyncio
    async def test_mega_processing_optimization_failure(self):
        """Test MEGA processing when file size optimization fails."""
        # Create bot instance with mocked dependencies
        with patch('similubot.bot.os.makedirs'), \
             patch('similubot.bot.os.path.exists', return_value=True), \
             patch('similubot.bot.MegaDownloader') as mock_downloader_class, \
             patch('similubot.bot.AudioConverter') as mock_converter_class, \
             patch('similubot.bot.CatboxUploader') as mock_catbox_class, \
             patch('similubot.bot.DiscordUploader') as mock_discord_class:
            
            # Set up mock instances
            mock_downloader = MagicMock()
            mock_converter = MagicMock()
            mock_catbox_uploader = MagicMock()
            mock_discord_uploader = MagicMock()
            
            mock_downloader_class.return_value = mock_downloader
            mock_converter_class.return_value = mock_converter
            mock_catbox_class.return_value = mock_catbox_uploader
            mock_discord_class.return_value = mock_discord_uploader
            
            bot = SimiluBot(self.mock_config)
            
            # Create temporary files for testing
            with tempfile.NamedTemporaryFile(delete=False) as downloaded_file, \
                 tempfile.NamedTemporaryFile(delete=False) as large_converted_file:
                
                # Write large file (over 200MB)
                large_converted_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
                large_converted_file.flush()
                
                try:
                    # Mock Discord message
                    mock_message = MagicMock()
                    mock_message.reply = AsyncMock()
                    
                    # Mock download success
                    mock_downloader.download_with_progress.return_value = (True, downloaded_file.name, None)
                    
                    # Mock conversion to always return large files (optimization fails)
                    def mock_convert_large(input_file, bitrate, output_file, callback):
                        # Always return large files regardless of bitrate
                        with tempfile.NamedTemporaryFile(delete=False) as temp_large:
                            temp_large.write(b"x" * (250 * 1024 * 1024))  # Still 250MB
                            temp_large.flush()
                            return (True, temp_large.name, None)
                    
                    mock_converter.convert_to_aac_with_progress.side_effect = mock_convert_large
                    
                    # Test the MEGA processing workflow
                    await bot._process_mega_link(mock_message, "https://mega.nz/file/test", 320)
                    
                    # Verify download was called
                    mock_downloader.download_with_progress.assert_called_once()
                    
                    # Verify conversion was called multiple times (trying different bitrates)
                    assert mock_converter.convert_to_aac_with_progress.call_count > 1
                    
                    # Verify upload was NOT called (optimization failed)
                    mock_catbox_uploader.upload_with_progress.assert_not_called()
                    
                    # Verify error message was sent
                    mock_message.reply.assert_called()
                    # Check that the reply contains error information
                    reply_calls = mock_message.reply.call_args_list
                    assert len(reply_calls) > 0
                    
                finally:
                    # Clean up
                    for file_path in [downloaded_file.name, large_converted_file.name]:
                        try:
                            os.unlink(file_path)
                        except FileNotFoundError:
                            pass

    @pytest.mark.asyncio
    async def test_mega_processing_discord_upload_no_optimization(self):
        """Test MEGA processing with Discord upload (no optimization needed)."""
        # Configure for Discord upload
        self.mock_config.get_mega_upload_service.return_value = "discord"
        
        # Create bot instance with mocked dependencies
        with patch('similubot.bot.os.makedirs'), \
             patch('similubot.bot.os.path.exists', return_value=True), \
             patch('similubot.bot.MegaDownloader') as mock_downloader_class, \
             patch('similubot.bot.AudioConverter') as mock_converter_class, \
             patch('similubot.bot.CatboxUploader') as mock_catbox_class, \
             patch('similubot.bot.DiscordUploader') as mock_discord_class:
            
            # Set up mock instances
            mock_downloader = MagicMock()
            mock_converter = MagicMock()
            mock_catbox_uploader = MagicMock()
            mock_discord_uploader = MagicMock()
            
            mock_downloader_class.return_value = mock_downloader
            mock_converter_class.return_value = mock_converter
            mock_catbox_class.return_value = mock_catbox_uploader
            mock_discord_class.return_value = mock_discord_uploader
            
            bot = SimiluBot(self.mock_config)
            
            # Create temporary files for testing
            with tempfile.NamedTemporaryFile(delete=False) as downloaded_file, \
                 tempfile.NamedTemporaryFile(delete=False) as converted_file:
                
                # Write large file (over 200MB) - should not trigger optimization for Discord
                converted_file.write(b"x" * (250 * 1024 * 1024))  # 250MB
                converted_file.flush()
                
                try:
                    # Mock Discord message
                    mock_message = MagicMock()
                    mock_message.reply = AsyncMock()
                    mock_message.channel = MagicMock()
                    
                    # Mock download success
                    mock_downloader.download_with_progress.return_value = (True, downloaded_file.name, None)
                    
                    # Mock conversion success
                    mock_converter.convert_to_aac_with_progress.return_value = (True, converted_file.name, None)
                    
                    # Mock Discord upload success
                    mock_discord_uploader.upload.return_value = (True, MagicMock(), None)
                    
                    # Test the MEGA processing workflow
                    await bot._process_mega_link(mock_message, "https://mega.nz/file/test", 320)
                    
                    # Verify download was called
                    mock_downloader.download_with_progress.assert_called_once()
                    
                    # Verify conversion was called only once (no optimization for Discord)
                    mock_converter.convert_to_aac_with_progress.assert_called_once()
                    
                    # Verify Discord upload was called
                    mock_discord_uploader.upload.assert_called_once()
                    
                    # Verify CatBox upload was NOT called
                    mock_catbox_uploader.upload_with_progress.assert_not_called()
                    
                finally:
                    # Clean up
                    for file_path in [downloaded_file.name, converted_file.name]:
                        try:
                            os.unlink(file_path)
                        except FileNotFoundError:
                            pass


if __name__ == "__main__":
    pytest.main([__file__])
