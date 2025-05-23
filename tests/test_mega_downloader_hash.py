"""Test script for MEGA downloader with filename hashing."""
import logging
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from similubot.downloaders.mega_downloader import MegaDownloader
from similubot.utils.config_manager import ConfigManager

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def test_hash_filename():
    """Test the filename hashing functionality."""
    # Create a downloader with default config
    downloader = MegaDownloader()
    
    # Test filenames
    test_filenames = [
        "normal_filename.mp4",
        "very_long_filename_with_lots_of_characters_and_special_symbols_!@#$%^&*()_+.mp4",
        "[ã\x81\x82ã\x81\x8aã\x80\x82][2024-12-29][ã\x80\x90ã\x82¢ã\x82¤ã\x83\x86ã\x83\xa0é\x80£å\x8b\x95ã\x80\x91å\x88\x9dã\x82\x81ã\x81¦ã\x81®ã\x81\x8aã\x82\x82ã\x81¡ã\x82\x83ã\x82\x92ä½¿ã\x81£ã\x81¦ã\x81\x8aã\x81\x97ã\x82\x83ã\x81¹ã\x82\x8aã\x81\x97ã\x81ªã\x81\x8cã\x82\x89æ°\x97æ\x8c\x81ã\x81¡ã\x82\x88ã\x81\x8fã\x81ªã\x82\x8bâ\x80¦ï¼\x9fã\x80\x8aWithnyã\x80\x8b][2024-12-29][1].mp4",
    ]
    
    print("\nTesting filename hashing:")
    print("-" * 50)
    
    for filename in test_filenames:
        # Get hash for filename
        filename_hash = downloader._hash_filename(filename)
        
        # Get file extension
        _, ext = os.path.splitext(filename)
        
        # Create new filename with hash
        new_filename = f"{filename_hash}{ext}"
        
        print(f"Original: {filename}")
        print(f"Hashed  : {new_filename}")
        print(f"Length  : {len(filename)} -> {len(new_filename)}")
        print("-" * 50)

def test_hash_algorithms():
    """Test different hash algorithms."""
    # Test filenames
    test_filename = "[ã\x81\x82ã\x81\x8aã\x80\x82][2024-12-29][ã\x80\x90ã\x82¢ã\x82¤ã\x83\x86ã\x83\xa0é\x80£å\x8b\x95ã\x80\x91å\x88\x9dã\x82\x81ã\x81¦ã\x81®ã\x81\x8aã\x82\x82ã\x81¡ã\x82\x83ã\x82\x92ä½¿ã\x81£ã\x81¦ã\x81\x8aã\x81\x97ã\x82\x83ã\x81¹ã\x82\x8aã\x81\x97ã\x81ªã\x81\x8cã\x82\x89æ°\x97æ\x8c\x81ã\x81¡ã\x82\x88ã\x81\x8fã\x81ªã\x82\x8bâ\x80¦ï¼\x9fã\x80\x8aWithnyã\x80\x8b][2024-12-29][1].mp4"
    
    # Test different hash algorithms
    algorithms = ['md5', 'sha1', 'sha256']
    
    print("\nTesting different hash algorithms:")
    print("-" * 50)
    
    for algorithm in algorithms:
        # Create a config with the specified algorithm
        config = ConfigManager()
        # Manually override the hash algorithm
        config.get_hash_algorithm = lambda: algorithm
        
        # Create a downloader with this config
        downloader = MegaDownloader(config=config)
        
        # Get hash for filename
        filename_hash = downloader._hash_filename(test_filename)
        
        # Get file extension
        _, ext = os.path.splitext(test_filename)
        
        # Create new filename with hash
        new_filename = f"{filename_hash}{ext}"
        
        print(f"Algorithm: {algorithm}")
        print(f"Hash     : {filename_hash}")
        print(f"Length   : {len(filename_hash)}")
        print("-" * 50)

if __name__ == "__main__":
    test_hash_filename()
    test_hash_algorithms()
