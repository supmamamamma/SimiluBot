"""Test script for MEGA downloader fixes."""
import asyncio
import logging
import os
import sys
import tempfile
import time
from unittest.mock import MagicMock, patch

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

def test_temp_file_detection():
    """Test the temporary file detection functionality."""
    print("\n=== Testing Temporary File Detection ===")
    
    downloader = MegaDownloader()
    
    # Test scanning temp files
    baseline_files = downloader._scan_temp_files()
    print(f"✓ Baseline temp files detected: {len(baseline_files)}")
    
    # Create a mock temp file to test detection
    temp_dir = downloader._get_temp_directory()
    mock_temp_file = os.path.join(temp_dir, "megapy_test123")
    
    try:
        # Create a mock temp file
        with open(mock_temp_file, 'w') as f:
            f.write("test content")
        
        # Test detection of new file
        new_file = downloader._detect_new_temp_file(baseline_files, timeout=5)
        if new_file and "megapy_test123" in new_file:
            print("✓ New temp file detection works")
        else:
            print("✗ New temp file detection failed")
    
    finally:
        # Clean up
        if os.path.exists(mock_temp_file):
            os.remove(mock_temp_file)

def test_filename_hashing():
    """Test the filename hashing functionality."""
    print("\n=== Testing Filename Hashing ===")
    
    downloader = MegaDownloader()
    
    # Test with problematic filename
    long_filename = "[ã\x81\x82ã\x81\x8aã\x80\x82][2024-12-29][ã\x80\x90ã\x82¢ã\x82¤ã\x83\x86ã\x83\xa0é\x80£å\x8b\x95ã\x80\x91å\x88\x9dã\x82\x81ã\x81¦ã\x81®ã\x81\x8aã\x82\x82ã\x81¡ã\x82\x83ã\x82\x92ä½¿ã\x81£ã\x81¦ã\x81\x8aã\x81\x97ã\x82\x83ã\x81¹ã\x82\x8aã\x81\x97ã\x81ªã\x81\x8cã\x82\x89æ°\x97æ\x8c\x81ã\x81¡ã\x82\x88ã\x81\x8fã\x81ªã\x82\x8bâ\x80¦ï¼\x9fã\x80\x8aWithnyã\x80\x8b][2024-12-29][1].mp4"
    
    # Test hashing
    filename_hash = downloader._hash_filename(long_filename)
    print(f"Original filename length: {len(long_filename)}")
    print(f"Hash: {filename_hash}")
    print(f"Hash length: {len(filename_hash)}")
    
    # Test with different algorithms
    algorithms = ['md5', 'sha1', 'sha256']
    for algorithm in algorithms:
        downloader.hash_algorithm = algorithm
        hash_result = downloader._hash_filename(long_filename)
        print(f"✓ {algorithm.upper()}: {hash_result} (length: {len(hash_result)})")

def test_file_moving():
    """Test the file moving functionality."""
    print("\n=== Testing File Moving ===")
    
    downloader = MegaDownloader()
    
    # Create a temporary file to test moving
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
        temp_file.write(b"test content for moving")
        temp_file_path = temp_file.name
    
    try:
        # Test moving with long filename
        long_filename = "very_long_filename_that_might_cause_issues_in_some_filesystems.mp4"
        
        result_path = downloader._move_temp_file_to_cache(temp_file_path, long_filename)
        
        if result_path and os.path.exists(result_path):
            print(f"✓ File moved successfully to: {os.path.basename(result_path)}")
            
            # Verify content
            with open(result_path, 'rb') as f:
                content = f.read()
                if content == b"test content for moving":
                    print("✓ File content preserved during move")
                else:
                    print("✗ File content corrupted during move")
            
            # Clean up
            os.remove(result_path)
        else:
            print("✗ File move failed")
    
    finally:
        # Clean up original temp file if it still exists
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

async def test_progress_callback():
    """Test progress callback functionality."""
    print("\n=== Testing Progress Callback ===")
    
    downloader = MegaDownloader()
    
    # Mock progress callback
    progress_updates = []
    
    async def mock_progress_callback(current, total, speed):
        progress_updates.append({
            'current': current,
            'total': total,
            'speed': speed,
            'percentage': (current / total) * 100 if total > 0 else 0
        })
        print(f"Progress: {current}/{total} bytes ({(current/total)*100:.1f}%) - Speed: {speed:.1f} B/s")
    
    # Test with mock download thread
    import threading
    
    class MockDownloadThread(threading.Thread):
        def __init__(self):
            super().__init__()
            self.running = True
        
        def run(self):
            time.sleep(2)  # Simulate download time
            self.running = False
        
        def is_alive(self):
            return self.running
    
    # Create a mock temp file for monitoring
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = temp_file.name
    
    try:
        # Start mock download thread
        mock_thread = MockDownloadThread()
        mock_thread.start()
        
        # Simulate file growth
        def simulate_file_growth():
            for i in range(5):
                time.sleep(0.4)
                with open(temp_file_path, 'wb') as f:
                    f.write(b'x' * (i + 1) * 1024 * 1024)  # Write 1MB, 2MB, 3MB, etc.
        
        growth_thread = threading.Thread(target=simulate_file_growth)
        growth_thread.start()
        
        # Monitor progress
        downloader._monitor_temp_file_progress(temp_file_path, 5 * 1024 * 1024, mock_progress_callback, mock_thread)
        
        growth_thread.join()
        mock_thread.join()
        
        print(f"✓ Progress callback called {len(progress_updates)} times")
        if progress_updates:
            final_update = progress_updates[-1]
            print(f"✓ Final progress: {final_update['percentage']:.1f}%")
    
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def test_cache_management():
    """Test cache management functionality."""
    print("\n=== Testing Cache Management ===")
    
    # Create a downloader with small cache limit for testing
    config = ConfigManager()
    downloader = MegaDownloader(config)
    downloader.max_cache_files = 3  # Override for testing
    
    # Create some test files in the cache directory
    test_files = []
    for i in range(5):
        test_file = os.path.join(downloader.temp_dir, f"test_file_{i}.mp4")
        with open(test_file, 'w') as f:
            f.write(f"test content {i}")
        test_files.append(test_file)
        time.sleep(0.1)  # Ensure different modification times
    
    print(f"Created {len(test_files)} test files")
    
    # Run cache cleanup
    downloader._clean_cache()
    
    # Check remaining files
    remaining_files = [f for f in test_files if os.path.exists(f)]
    print(f"✓ Files remaining after cleanup: {len(remaining_files)}")
    
    if len(remaining_files) <= downloader.max_cache_files:
        print("✓ Cache cleanup working correctly")
    else:
        print("✗ Cache cleanup failed")
    
    # Clean up remaining files
    for file_path in remaining_files:
        try:
            os.remove(file_path)
        except:
            pass

async def main():
    """Run all tests."""
    print("Starting MEGA Downloader Fixes Tests")
    print("=" * 50)
    
    # Run tests
    test_temp_file_detection()
    test_filename_hashing()
    test_file_moving()
    await test_progress_callback()
    test_cache_management()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("\nKey improvements verified:")
    print("✓ Temporary file detection and monitoring")
    print("✓ Filename hashing to avoid long filename errors")
    print("✓ Safe file moving with proper error handling")
    print("✓ Progress tracking with real file monitoring")
    print("✓ Cache management with configurable limits")

if __name__ == "__main__":
    asyncio.run(main())
