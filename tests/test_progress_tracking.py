"""Test script for progress tracking functionality."""
import asyncio
import logging
import os
import sys
import time
from unittest.mock import MagicMock

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from similubot.utils.progress_tracker import ProgressTracker, ProgressCallback, ProgressInfo, ProgressStatus

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test_progress_tracker():
    """Test the progress tracker functionality."""
    print("\n=== Testing Progress Tracker ===")
    
    # Mock Discord message
    mock_message = MagicMock()
    mock_message.edit = MagicMock()
    
    # Create progress tracker
    tracker = ProgressTracker(mock_message, "Test Operation")
    
    # Test starting operation
    await tracker.start_operation(filename="test_file.mp4", message="Starting test...")
    print("✓ Started operation")
    
    # Test progress updates
    for i in range(0, 101, 20):
        progress_info = ProgressInfo(
            percentage=i,
            current_size=i * 1024 * 1024,  # MB
            total_size=100 * 1024 * 1024,  # 100 MB
            speed=5 * 1024 * 1024,  # 5 MB/s
            eta=max(0, (100 - i) // 5),  # Estimated seconds
            status=ProgressStatus.IN_PROGRESS,
            message=f"Processing... {i}%",
            filename="test_file.mp4"
        )
        
        await tracker.update_progress(progress_info, force_update=True)
        print(f"✓ Updated progress: {i}%")
        await asyncio.sleep(0.5)  # Small delay for demonstration
    
    # Test completion
    await tracker.complete_operation(
        message="Test completed successfully!",
        final_info="Result: test_output.m4a"
    )
    print("✓ Completed operation")
    
    print(f"Total edit calls: {mock_message.edit.call_count}")

async def test_progress_callback():
    """Test the progress callback functionality."""
    print("\n=== Testing Progress Callback ===")
    
    # Mock Discord message
    mock_message = MagicMock()
    mock_message.edit = MagicMock()
    
    # Create progress tracker and callback
    tracker = ProgressTracker(mock_message, "Download Test")
    callback = ProgressCallback(tracker)
    
    # Start operation
    await tracker.start_operation(filename="download_test.mp4", message="Starting download...")
    
    # Simulate download progress
    total_size = 50 * 1024 * 1024  # 50 MB
    
    for i in range(0, 11):
        current_size = int((i / 10) * total_size)
        speed = 2 * 1024 * 1024  # 2 MB/s
        
        await callback(current_size, total_size, speed)
        print(f"✓ Callback progress: {(current_size / total_size) * 100:.1f}%")
        await asyncio.sleep(0.3)
    
    await tracker.complete_operation("Download completed!")
    print("✓ Download test completed")

def test_progress_bar_formatting():
    """Test progress bar formatting functions."""
    print("\n=== Testing Progress Bar Formatting ===")
    
    # Mock Discord message
    mock_message = MagicMock()
    tracker = ProgressTracker(mock_message, "Format Test")
    
    # Test progress bar creation
    test_percentages = [0, 25, 50, 75, 100]
    for percentage in test_percentages:
        bar = tracker.create_progress_bar(percentage)
        print(f"Progress {percentage:3d}%: {bar}")
    
    # Test size formatting
    test_sizes = [512, 1024, 1024*1024, 1024*1024*1024, 1024*1024*1024*1024]
    for size in test_sizes:
        formatted = tracker.format_size(size)
        print(f"Size {size:>12d} bytes: {formatted}")
    
    # Test speed formatting
    test_speeds = [1024, 1024*1024, 5*1024*1024, 100*1024*1024]
    for speed in test_speeds:
        formatted = tracker.format_speed(speed)
        print(f"Speed {speed:>10d} B/s: {formatted}")
    
    # Test time formatting
    test_times = [30, 90, 3600, 7200, 86400]
    for time_val in test_times:
        formatted = tracker.format_time(time_val)
        print(f"Time {time_val:>6d} seconds: {formatted}")
    
    # Test filename truncation
    test_filenames = [
        "short.mp4",
        "medium_length_filename.mp4",
        "very_long_filename_that_should_be_truncated_because_it_is_too_long.mp4",
        "[ã\x81\x82ã\x81\x8aã\x80\x82][2024-12-29][ã\x80\x90ã\x82¢ã\x82¤ã\x83\x86ã\x83\xa0é\x80£å\x8b\x95ã\x80\x91å\x88\x9dã\x82\x81ã\x81¦ã\x81®ã\x81\x8aã\x82\x82ã\x81¡ã\x82\x83ã\x82\x92ä½¿ã\x81£ã\x81¦ã\x81\x8aã\x81\x97ã\x82\x83ã\x81¹ã\x82\x8aã\x81\x97ã\x81ªã\x81\x8cã\x82\x89æ°\x97æ\x8c\x81ã\x81¡ã\x82\x88ã\x81\x8fã\x81ªã\x82\x8bâ\x80¦ï¼\x9fã\x80\x8aWithnyã\x80\x8b][2024-12-29][1].mp4"
    ]
    
    for filename in test_filenames:
        truncated = tracker.truncate_filename(filename)
        print(f"Original: {filename}")
        print(f"Truncated: {truncated}")
        print(f"Length: {len(filename)} -> {len(truncated)}")
        print("-" * 50)

async def test_error_handling():
    """Test error handling in progress tracking."""
    print("\n=== Testing Error Handling ===")
    
    # Mock Discord message
    mock_message = MagicMock()
    mock_message.edit = MagicMock()
    
    # Create progress tracker
    tracker = ProgressTracker(mock_message, "Error Test")
    
    # Test error operation
    await tracker.start_operation(filename="error_test.mp4", message="Starting operation...")
    await asyncio.sleep(0.5)
    
    await tracker.error_operation("Simulated error: File not found")
    print("✓ Error handling test completed")

async def main():
    """Run all tests."""
    print("Starting Progress Tracking Tests")
    print("=" * 50)
    
    # Run tests
    await test_progress_tracker()
    await test_progress_callback()
    test_progress_bar_formatting()
    await test_error_handling()
    
    print("\n" + "=" * 50)
    print("All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
