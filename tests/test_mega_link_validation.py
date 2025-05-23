"""Test script for MEGA link validation."""
import logging
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from similubot.downloaders.mega_downloader import MegaDownloader

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

@patch('similubot.downloaders.mega_downloader.subprocess.run')
def test_mega_link_validation(mock_subprocess):
    """Test MEGA link validation with various link formats."""
    # Mock successful mega-version command
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "MEGAcmd version 1.6.3"
    mock_subprocess.return_value = mock_result

    downloader = MegaDownloader()

    # Test links
    test_links = [
        # Valid links
        "https://mega.nz/file/9y1GTRbR#SczG1HaHxUc_Lgh5xAXIF-jt7TrMhYPeDk8wrY9OUJ0",  # New format
        "https://mega.nz/#!abcdefgh!ijklmnopqrstuvwxyz123456789",  # Old format
        "https://mega.nz/folder/abcdefgh#ijklmnopqrstuvwxyz",  # Folder link

        # Invalid links
        "https://example.com",
        "https://mega.co.nz/file/abcdefgh",
        "mega.nz/file/abcdefgh",
    ]

    print("\nTesting MEGA link validation:")
    print("-" * 50)

    for link in test_links:
        is_valid = downloader.is_mega_link(link)
        print(f"Link: {link}")
        print(f"Valid: {is_valid}")
        print("-" * 50)

if __name__ == "__main__":
    from unittest.mock import patch, MagicMock

    # Mock subprocess for standalone execution
    with patch('similubot.downloaders.mega_downloader.subprocess.run') as mock_subprocess:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "MEGAcmd version 1.6.3"
        mock_subprocess.return_value = mock_result

        # Call the function with the mock parameter
        test_mega_link_validation(mock_subprocess)
