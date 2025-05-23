"""Tests for the MEGA downloader module using MegaCMD."""
import pytest
from unittest.mock import patch, MagicMock

from similubot.downloaders.mega_downloader import MegaDownloader

class TestMegaDownloader:
    """Test cases for the MEGA downloader."""

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    def test_init_success(self, mock_subprocess):
        """Test successful initialization with MegaCMD available."""
        # Mock successful mega-version command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "MEGAcmd version 1.6.3"
        mock_subprocess.return_value = mock_result

        downloader = MegaDownloader()
        assert downloader.temp_dir == "./temp"

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    def test_init_megacmd_not_found(self, mock_subprocess):
        """Test initialization when MegaCMD is not found."""
        mock_subprocess.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError, match="MegaCMD not found"):
            MegaDownloader()

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    def test_is_mega_link(self, mock_subprocess):
        """Test the is_mega_link method."""
        # Mock successful mega-version command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "MEGAcmd version 1.6.3"
        mock_subprocess.return_value = mock_result

        downloader = MegaDownloader()

        # Valid MEGA links
        assert downloader.is_mega_link("https://mega.nz/file/abcdefgh#ijklmnopqrstuvwxyz123456789")
        assert downloader.is_mega_link("https://mega.nz/#!abcdefgh!ijklmnopqrstuvwxyz123456789")

        # Invalid MEGA links
        assert not downloader.is_mega_link("https://example.com")
        assert not downloader.is_mega_link("https://mega.co.nz/file/abcdefgh")
        assert not downloader.is_mega_link("mega.nz/file/abcdefgh")

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    def test_extract_mega_links(self, mock_subprocess):
        """Test the extract_mega_links method."""
        # Mock successful mega-version command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "MEGAcmd version 1.6.3"
        mock_subprocess.return_value = mock_result

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

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    @patch('similubot.downloaders.mega_downloader.os.listdir')
    @patch('similubot.downloaders.mega_downloader.os.path.isfile')
    @patch('similubot.downloaders.mega_downloader.os.path.getmtime')
    @patch('similubot.downloaders.mega_downloader.os.path.exists')
    @patch('similubot.downloaders.mega_downloader.time.time')
    @patch('similubot.downloaders.mega_downloader.os.path.getsize')
    def test_download_success(self, mock_getsize, mock_time, mock_exists,
                             mock_getmtime, mock_isfile, mock_listdir, mock_subprocess):
        """Test successful download."""
        # Mock successful mega-version command for initialization
        version_result = MagicMock()
        version_result.returncode = 0
        version_result.stdout = "MEGAcmd version 1.6.3"

        # Mock successful mega-get command
        download_result = MagicMock()
        download_result.returncode = 0
        download_result.stdout = "Download completed"
        download_result.stderr = ""

        mock_subprocess.side_effect = [version_result, download_result]

        # Mock file system operations
        mock_listdir.return_value = ["test_file.mp4"]
        mock_isfile.return_value = True
        mock_exists.return_value = True
        mock_time.return_value = 1000.0
        mock_getmtime.return_value = 950.0  # File created 50 seconds ago
        mock_getsize.return_value = 1024

        downloader = MegaDownloader()
        success, file_path, error = downloader.download("https://mega.nz/file/abc#123")

        # Verify results
        assert success is True
        assert file_path is not None and file_path.endswith("test_file.mp4")
        assert error is None

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    def test_download_megacmd_failure(self, mock_subprocess):
        """Test download when MegaCMD command fails."""
        # Mock successful mega-version command for initialization
        version_result = MagicMock()
        version_result.returncode = 0
        version_result.stdout = "MEGAcmd version 1.6.3"

        # Mock failed mega-get command
        download_result = MagicMock()
        download_result.returncode = 1
        download_result.stdout = ""
        download_result.stderr = "Download failed: Invalid link"

        mock_subprocess.side_effect = [version_result, download_result]

        downloader = MegaDownloader()
        success, file_path, error = downloader.download("https://mega.nz/file/abc#123")

        # Verify results
        assert success is False
        assert file_path is None
        assert error is not None and "MegaCMD download failed" in error

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    def test_download_invalid_link(self, mock_subprocess):
        """Test download with invalid MEGA link."""
        # Mock successful mega-version command for initialization
        version_result = MagicMock()
        version_result.returncode = 0
        version_result.stdout = "MEGAcmd version 1.6.3"
        mock_subprocess.return_value = version_result

        downloader = MegaDownloader()
        success, file_path, error = downloader.download("https://example.com")

        # Verify results
        assert success is False
        assert file_path is None
        assert error is not None and "Invalid MEGA link" in error

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    def test_get_file_info_success(self, mock_subprocess):
        """Test successful file info retrieval."""
        # Mock successful mega-version command for initialization
        version_result = MagicMock()
        version_result.returncode = 0
        version_result.stdout = "MEGAcmd version 1.6.3"

        # Mock successful mega-ls command
        ls_result = MagicMock()
        ls_result.returncode = 0
        ls_result.stdout = "test_file.mp4    10.5 MB    2023-01-01 12:00:00"
        ls_result.stderr = ""

        mock_subprocess.side_effect = [version_result, ls_result]

        downloader = MegaDownloader()
        success, file_info, error = downloader.get_file_info("https://mega.nz/file/abc#123")

        # Verify results
        assert success is True
        assert file_info is not None
        assert "name" in file_info
        assert error is None

    @patch('similubot.downloaders.mega_downloader.subprocess.run')
    def test_get_file_info_failure(self, mock_subprocess):
        """Test file info retrieval failure."""
        # Mock successful mega-version command for initialization
        version_result = MagicMock()
        version_result.returncode = 0
        version_result.stdout = "MEGAcmd version 1.6.3"

        # Mock failed mega-ls command
        ls_result = MagicMock()
        ls_result.returncode = 1
        ls_result.stdout = ""
        ls_result.stderr = "Failed to access link"

        mock_subprocess.side_effect = [version_result, ls_result]

        downloader = MegaDownloader()
        success, file_info, error = downloader.get_file_info("https://mega.nz/file/abc#123")

        # Verify results
        assert success is False
        assert file_info is None
        assert error is not None and "Failed to get file info" in error
