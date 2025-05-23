"""Tests for the MEGA downloader module."""
import os
import pytest
from unittest.mock import patch, MagicMock

from similubot.downloaders.mega_downloader import MegaDownloader

class TestMegaDownloader:
    """Test cases for the MEGA downloader."""
    
    def test_is_mega_link(self):
        """Test the is_mega_link method."""
        downloader = MegaDownloader()
        
        # Valid MEGA links
        assert downloader.is_mega_link("https://mega.nz/file/abcdefgh#ijklmnopqrstuvwxyz123456789")
        assert downloader.is_mega_link("https://mega.nz/#!abcdefgh!ijklmnopqrstuvwxyz123456789")
        
        # Invalid MEGA links
        assert not downloader.is_mega_link("https://example.com")
        assert not downloader.is_mega_link("https://mega.co.nz/file/abcdefgh")
        assert not downloader.is_mega_link("mega.nz/file/abcdefgh")
    
    def test_extract_mega_links(self):
        """Test the extract_mega_links method."""
        downloader = MegaDownloader()
        
        # Test with a single link
        text = "Check out this file: https://mega.nz/file/abcdefgh#ijklmnopqrstuvwxyz123456789"
        links = downloader.extract_mega_links(text)
        assert len(links) == 1
        assert links[0] == "https://mega.nz/file/abcdefgh#ijklmnopqrstuvwxyz123456789"
        
        # Test with multiple links
        text = (
            "Link 1: https://mega.nz/file/abc#123 "
            "Link 2: https://mega.nz/#!def!456"
        )
        links = downloader.extract_mega_links(text)
        assert len(links) == 2
        assert links[0] == "https://mega.nz/file/abc#123"
        assert links[1] == "https://mega.nz/#!def!456"
        
        # Test with no links
        text = "This text contains no MEGA links."
        links = downloader.extract_mega_links(text)
        assert len(links) == 0
    
    @patch('mega.Mega')
    def test_download_success(self, mock_mega_class):
        """Test successful download."""
        # Set up mocks
        mock_mega = MagicMock()
        mock_mega_class.return_value = mock_mega
        
        mock_client = MagicMock()
        mock_mega.login.return_value = mock_client
        
        # Mock successful download
        test_file_path = "/tmp/test_file.mp4"
        mock_client.download_url.return_value = test_file_path
        
        # Mock os.path.exists to return True for the downloaded file
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):
            
            downloader = MegaDownloader()
            success, file_path, error = downloader.download("https://mega.nz/file/abc#123")
            
            # Verify results
            assert success is True
            assert file_path == test_file_path
            assert error is None
            
            # Verify mock calls
            mock_client.download_url.assert_called_once_with(
                "https://mega.nz/file/abc#123",
                dest_path=downloader.temp_dir
            )
    
    @patch('mega.Mega')
    def test_download_failure(self, mock_mega_class):
        """Test failed download."""
        # Set up mocks
        mock_mega = MagicMock()
        mock_mega_class.return_value = mock_mega
        
        mock_client = MagicMock()
        mock_mega.login.return_value = mock_client
        
        # Mock failed download
        mock_client.download_url.side_effect = Exception("Download failed")
        
        downloader = MegaDownloader()
        success, file_path, error = downloader.download("https://mega.nz/file/abc#123")
        
        # Verify results
        assert success is False
        assert file_path is None
        assert "Download failed" in error
        
        # Verify mock calls
        mock_client.download_url.assert_called_once_with(
            "https://mega.nz/file/abc#123",
            dest_path=downloader.temp_dir
        )
    
    def test_download_invalid_link(self):
        """Test download with invalid link."""
        downloader = MegaDownloader()
        success, file_path, error = downloader.download("https://example.com")
        
        # Verify results
        assert success is False
        assert file_path is None
        assert "Invalid MEGA link" in error
