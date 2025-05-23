# MEGA Downloader Tracking System

## Overview

The MEGA downloader has been enhanced with a robust JSON-based file tracking system that solves the timestamp detection issues with MegaCMD and provides comprehensive download management.

## Problem Solved

**Previous Issue**: MegaCMD sets downloaded file timestamps to January 1, 1970, making time-based file detection unreliable.

**Solution**: JSON-based tracking system that records download metadata and uses file comparison to identify newly downloaded files.

## Key Features

### 🔧 Reliable File Detection
- **Before/After Comparison**: Compares directory contents before and after download
- **No Timestamp Dependency**: Doesn't rely on file modification times
- **Multiple File Handling**: Automatically selects the largest file when multiple files are downloaded

### 📊 Comprehensive Tracking
- **Unique Download IDs**: Each download gets a UUID for tracking
- **Complete Metadata**: Records URL, filename, file size, timestamps, and status
- **Download History**: Maintains history of all downloads with statistics
- **Error Tracking**: Records detailed error information for failed downloads

### 🧹 Automatic Cleanup
- **File Limit Management**: Keeps only the N most recent files (configurable)
- **Old Entry Cleanup**: Removes failed/incomplete downloads older than 24 hours
- **Disk Space Management**: Prevents temp directory from growing indefinitely
- **Orphaned File Removal**: Cleans up files that are no longer tracked

### 🛡️ Robust Error Handling
- **Corrupted JSON Recovery**: Automatically recovers from corrupted tracking files
- **Atomic Operations**: Uses temporary files for crash-safe JSON updates
- **Graceful Degradation**: Continues working even if tracking system fails
- **Detailed Logging**: Enhanced debug information for troubleshooting

## Configuration

### Constructor Parameters

```python
downloader = MegaDownloader(
    temp_dir="./temp",    # Directory for downloaded files
    max_files=50          # Maximum files to keep (default: 50)
)
```

### Tracking File Location

The tracking file is automatically created at `{temp_dir}/download_tracker.json`.

## JSON Structure

### Tracking File Format

```json
{
  "downloads": {
    "uuid-download-id": {
      "url": "https://mega.nz/file/...",
      "download_id": "uuid-download-id",
      "started_at": "2024-01-01T12:00:00.000000",
      "status": "completed",
      "filename": "example.mp4",
      "file_path": "./temp/example.mp4",
      "file_size": 1048576,
      "completed_at": "2024-01-01T12:05:00.000000",
      "all_files": ["example.mp4", "subtitle.srt"]
    }
  },
  "metadata": {
    "created": "2024-01-01T10:00:00.000000",
    "version": "1.0",
    "last_updated": "2024-01-01T12:05:00.000000"
  }
}
```

### Download Status Values

- `"in_progress"`: Download is currently running
- `"completed"`: Download finished successfully
- `"failed"`: Download failed with error
- `"cleaned"`: File was removed during cleanup (entry kept for URL reference)

## API Methods

### Download Method (Enhanced)

```python
success, file_path, error = downloader.download(url)
```

**New Behavior**:
- Creates unique download ID
- Records download start in tracking file
- Compares directory before/after download
- Handles multiple downloaded files
- Updates tracking with success/failure
- Returns same interface as before

### Download History Method (New)

```python
history = downloader.get_download_history(limit=10)
```

**Returns**:
```python
{
    "recent_downloads": [
        {
            "download_id": "uuid",
            "url": "https://mega.nz/...",
            "filename": "file.mp4",
            "status": "completed",
            "started_at": "2024-01-01T12:00:00",
            "completed_at": "2024-01-01T12:05:00",
            "file_size": 1048576,
            "error": ""
        }
    ],
    "statistics": {
        "total_downloads": 25,
        "completed": 20,
        "failed": 3,
        "in_progress": 0,
        "total_size_bytes": 52428800
    },
    "metadata": {
        "created": "2024-01-01T10:00:00",
        "version": "1.0"
    }
}
```

## Cleanup Behavior

### Automatic File Cleanup

1. **Completed Downloads**: Keeps only the `max_files` most recent completed downloads
2. **Old Files Removed**: Files older than the limit are deleted from disk
3. **Tracking Entries**: Old entries are marked as "cleaned" but kept for URL reference
4. **Failed Downloads**: Entries older than 24 hours are completely removed

### Manual Cleanup

The cleanup runs automatically during:
- Downloader initialization
- Each download completion

## Error Recovery

### Corrupted Tracking File

If the JSON file becomes corrupted:
1. Logs warning about corruption
2. Creates fresh tracking file with recovery flag
3. Continues normal operation
4. Previous download history is lost but functionality remains

### Missing Tracking File

If the tracking file is missing:
1. Creates new tracking file automatically
2. Initializes with empty download history
3. Normal operation continues

## Migration from Previous System

### Backward Compatibility

- ✅ **Same API**: `download()` method signature unchanged
- ✅ **Same Return Values**: Returns same tuple format
- ✅ **Same Configuration**: Constructor parameters compatible
- ✅ **Same Dependencies**: No new external dependencies required

### What Changed

- ❌ **No More Timestamp Issues**: Reliable file detection
- ✅ **Better Error Handling**: More detailed error information
- ✅ **Automatic Cleanup**: Prevents disk space issues
- ✅ **Download Analytics**: Track download history and statistics
- ✅ **Enhanced Logging**: Better debugging information

## Testing

All functionality is thoroughly tested with mocked MegaCMD commands:

```bash
# Run all MEGA downloader tests
python -m pytest tests/test_mega_downloader.py -v

# Run specific tracking system test
python -m pytest tests/test_mega_downloader.py::TestMegaDownloader::test_get_download_history -v

# Run demo
python demo_tracking_system.py
```

## Performance Impact

- **Minimal Overhead**: JSON operations are fast for typical download volumes
- **Atomic Updates**: Temporary file operations ensure data integrity
- **Efficient Cleanup**: Only processes files when limits are exceeded
- **Memory Efficient**: Loads tracking data only when needed

## Troubleshooting

### Common Issues

1. **Tracking File Corruption**: Automatically recovered, check logs for details
2. **Disk Space Issues**: Adjust `max_files` parameter to keep fewer files
3. **Permission Errors**: Ensure write access to temp directory
4. **Large JSON Files**: Consider reducing `max_files` if tracking file becomes large

### Debug Information

Enable debug logging to see detailed tracking operations:

```python
import logging
logging.getLogger("similubot.downloader.mega").setLevel(logging.DEBUG)
```

## Future Enhancements

Potential improvements for future versions:
- Download progress tracking with real-time updates
- Bandwidth usage statistics
- Download queue management
- Duplicate download detection
- Export/import of download history
