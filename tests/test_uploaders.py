"""Tests for the uploader modules."""
import os
import pytest
from unittest.mock import patch, MagicMock

from similubot.uploaders.catbox_uploader import CatboxUploader
from similubot.uploaders.discord_uploader import DiscordUploader

class TestCatboxUploader:
    """Test cases for the CatBox uploader."""
    
    @patch('requests.post')
    @patch('os.path.exists')
    def test_upload_success(self, mock_exists, mock_post):
        """Test successful upload to CatBox."""
        # Set up mocks
        mock_exists.return_value = True
        
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "https://files.catbox.moe/abcdef.m4a"
        mock_post.return_value = mock_response
        
        # Create uploader and run test
        uploader = CatboxUploader()
        success, url, error = uploader.upload("test.m4a")
        
        # Verify results
        assert success is True
        assert url == "https://files.catbox.moe/abcdef.m4a"
        assert error is None
        
        # Verify mock calls
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == CatboxUploader.CATBOX_API_URL
        assert "fileToUpload" in kwargs["files"]
    
    @patch('requests.post')
    @patch('os.path.exists')
    def test_upload_failure(self, mock_exists, mock_post):
        """Test failed upload to CatBox."""
        # Set up mocks
        mock_exists.return_value = True
        
        # Mock failed HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        # Create uploader and run test
        uploader = CatboxUploader()
        success, url, error = uploader.upload("test.m4a")
        
        # Verify results
        assert success is False
        assert url is None
        assert "HTTP 500" in error
    
    def test_upload_file_not_found(self):
        """Test upload with non-existent file."""
        with patch('os.path.exists', return_value=False):
            uploader = CatboxUploader()
            success, url, error = uploader.upload("nonexistent.m4a")
            
            # Verify results
            assert success is False
            assert url is None
            assert "not found" in error.lower()
    
    @patch('requests.post')
    def test_delete_success(self, mock_post):
        """Test successful file deletion from CatBox."""
        # Set up mocks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Create uploader and run test
        uploader = CatboxUploader(user_hash="test_hash")
        success, error = uploader.delete("https://files.catbox.moe/abcdef.m4a")
        
        # Verify results
        assert success is True
        assert error is None
        
        # Verify mock calls
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == CatboxUploader.CATBOX_API_URL
        assert kwargs["data"]["reqtype"] == "deletefiles"
        assert kwargs["data"]["userhash"] == "test_hash"
    
    def test_delete_no_user_hash(self):
        """Test file deletion without user hash."""
        uploader = CatboxUploader()
        success, error = uploader.delete("https://files.catbox.moe/abcdef.m4a")
        
        # Verify results
        assert success is False
        assert "no user hash" in error.lower()

class TestDiscordUploader:
    """Test cases for the Discord uploader."""
    
    @pytest.mark.asyncio
    @patch('discord.File')
    @patch('os.path.exists')
    async def test_upload_success(self, mock_exists, mock_discord_file):
        """Test successful upload to Discord."""
        # Set up mocks
        mock_exists.return_value = True
        mock_discord_file.return_value = "mock_file_object"
        
        # Mock Discord channel
        mock_channel = MagicMock()
        mock_message = MagicMock()
        mock_message.id = "12345"
        mock_channel.send = MagicMock(return_value=mock_message)
        
        # Create uploader and run test
        uploader = DiscordUploader()
        success, message, error = await uploader.upload(
            "test.m4a",
            mock_channel,
            content="Test message"
        )
        
        # Verify results
        assert success is True
        assert message == mock_message
        assert error is None
        
        # Verify mock calls
        mock_discord_file.assert_called_once_with("test.m4a")
        mock_channel.send.assert_called_once_with(
            content="Test message",
            file="mock_file_object"
        )
    
    @pytest.mark.asyncio
    async def test_upload_file_not_found(self):
        """Test upload with non-existent file."""
        with patch('os.path.exists', return_value=False):
            uploader = DiscordUploader()
            success, message, error = await uploader.upload(
                "nonexistent.m4a",
                MagicMock()
            )
            
            # Verify results
            assert success is False
            assert message is None
            assert "not found" in error.lower()
    
    @pytest.mark.asyncio
    async def test_get_attachment_url(self):
        """Test getting attachment URL from a Discord message."""
        # Mock Discord message with attachment
        mock_attachment = MagicMock()
        mock_attachment.url = "https://cdn.discordapp.com/attachments/123/456/test.m4a"
        
        mock_message = MagicMock()
        mock_message.attachments = [mock_attachment]
        
        # Create uploader and run test
        uploader = DiscordUploader()
        url = await uploader.get_attachment_url(mock_message)
        
        # Verify results
        assert url == "https://cdn.discordapp.com/attachments/123/456/test.m4a"
    
    @pytest.mark.asyncio
    async def test_get_attachment_url_no_attachments(self):
        """Test getting attachment URL from a Discord message with no attachments."""
        # Mock Discord message without attachments
        mock_message = MagicMock()
        mock_message.attachments = []
        
        # Create uploader and run test
        uploader = DiscordUploader()
        url = await uploader.get_attachment_url(mock_message)
        
        # Verify results
        assert url is None
