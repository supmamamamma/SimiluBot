"""Test script for MEGA link validation."""
import logging
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from similubot.downloaders.mega_downloader import MegaDownloader

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def test_mega_link_validation():
    """Test MEGA link validation with various link formats."""
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
    test_mega_link_validation()
