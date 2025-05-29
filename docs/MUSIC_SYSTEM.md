# Music Playback System

## Overview

The SimiluBot music system provides comprehensive YouTube audio playback functionality with queue management, voice channel integration, and Discord command interface. The system is built with a modular architecture following the existing project patterns.

## Features

### Core Functionality
- **YouTube Audio Extraction**: Download audio from YouTube videos using pytubefix
- **Queue Management**: Multi-song queue with position tracking and metadata
- **Voice Channel Integration**: Automatic connection and playback management
- **Progress Tracking**: Real-time download and playback progress updates
- **Real-time Progress Bar**: Visual progress bar with automatic updates every 5 seconds
- **Authorization Integration**: Seamless integration with existing permission system

### Command Set
- `!music <youtube_url>` - Add song to queue and start playback
- `!music queue` - Display current queue with song details
- `!music now` - Show real-time progress bar with current playback position
- `!music skip` - Skip to next song in queue
- `!music stop` - Stop playback and clear queue, disconnect from voice
- `!music jump <number>` - Jump to specific position in queue (1-indexed)

## Architecture

### Module Structure
```
similubot/music/
├── __init__.py              # Module exports
├── youtube_client.py        # YouTube audio extraction
├── queue_manager.py         # Song queue management
├── voice_manager.py         # Discord voice connections
└── music_player.py          # Core orchestration

similubot/progress/
├── music_progress.py        # Music progress tracking and real-time progress bar

similubot/commands/
└── music_commands.py        # Discord command handlers
```

### Component Responsibilities

#### YouTubeClient
- YouTube URL validation and audio extraction
- Progress tracking during downloads
- File management and cleanup
- Audio metadata extraction

#### QueueManager
- Thread-safe queue operations
- Song position tracking
- Queue persistence and metadata
- Display formatting for Discord embeds

#### VoiceManager
- Discord voice connection management
- Audio playback control (play, pause, stop)
- Connection state tracking
- Error handling and recovery

#### MusicPlayer
- Orchestrates all components
- Manages playback loops per guild
- Handles audio file lifecycle
- Tracks playback timing and position
- Provides unified API for commands

#### MusicProgressTracker (similubot/progress/music_progress.py)
- Extends base ProgressTracker for music-specific progress tracking
- Tracks playback timing with pause/resume state management
- Provides accurate playback position calculation
- Integrates with existing progress tracking architecture

#### MusicProgressUpdater (similubot/progress/music_progress.py)
- Creates visual progress bars with Unicode characters
- Provides real-time Discord embed updates every 5 seconds
- Calculates current playback position from timing data
- Shows play/pause/stop status indicators
- Handles Discord API rate limiting gracefully
- Follows established progress module patterns

#### MusicCommands
- Discord command interface
- User input validation
- Progress feedback via embeds
- Error handling and user messaging

## Configuration

### config.yaml Settings
```yaml
music:
  enabled: true                    # Enable/disable music functionality
  max_queue_size: 100             # Maximum songs per guild queue
  max_song_duration: 3600         # Maximum song length (1 hour)
  auto_disconnect_timeout: 300    # Auto-disconnect timeout (5 minutes)
  volume: 0.5                     # Default playback volume (0.0-1.0)
  ffmpeg_options:
    before: "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    options: "-vn"                # No video processing
```

### Authorization
Music commands require the `music_playback` module permission:

```bash
# Grant music access to a user
!auth add <user_id> module music_playback

# Grant full access (includes music)
!auth add <user_id> full
```

## Dependencies

### Required Packages
- `pytubefix>=6.0.0` - YouTube audio extraction
- `discord.py[voice]>=2.0.0` - Discord voice support
- `python-ffmpeg>=1.0.0` - Audio processing

### System Requirements
- FFmpeg installed and accessible in PATH
- Stable internet connection for YouTube downloads
- Sufficient disk space for temporary audio files

## Usage Examples

### Basic Playback
```
User: !music https://www.youtube.com/watch?v=dQw4w9WgXcQ
Bot: 🎵 Song Added to Queue
     Title: Never Gonna Give You Up
     Duration: 03:32
     Position in Queue: #1
```

### Queue Management
```
User: !music queue
Bot: 🎵 Music Queue
     🎶 Now Playing
     **Never Gonna Give You Up**
     Duration: 03:32 | Requested by: User123

     📋 Up Next
     1. Another Song - 04:15 | Requested by: User456
     2. Third Song - 02:45 | Requested by: User789
```

### Queue Navigation
```
User: !music jump 3
Bot: ⏭️ Jumped to Song
     Now playing: **Third Song**
```

### Real-time Progress Bar
```
User: !music now
Bot: 🎵 Now Playing
     Track: **Never Gonna Give You Up**

     Progress: ▶ ▬▬▬▬▬▬🔘▬▬▬▬▬ [1:45/3:32] 🔊

     Artist: Rick Astley
     Requested by: User123

     [Updates automatically every 5 seconds]
```

The progress bar features:
- **Visual Progress**: Unicode progress bar with position indicator (🔘)
- **Status Icons**: ▶ (playing), ⏸ (paused), ⏹ (stopped)
- **Time Display**: Current position / Total duration in MM:SS or HH:MM:SS format
- **Auto Updates**: Refreshes every 5 seconds while song is playing
- **Smart Cleanup**: Stops updating when song ends or user navigates away

## Error Handling

### Common Scenarios
- **User not in voice channel**: Clear error message with instructions
- **Invalid YouTube URL**: URL validation with helpful feedback
- **Network errors**: Retry logic with progress updates
- **Voice connection issues**: Automatic reconnection attempts
- **Queue overflow**: Configurable limits with user notification

### Logging
All operations are logged with appropriate levels:
- `INFO`: Successful operations, queue changes
- `WARNING`: Recoverable errors, timeouts
- `ERROR`: Failed operations, connection issues
- `DEBUG`: Detailed operation traces

## Performance Considerations

### Memory Management
- Automatic cleanup of downloaded audio files
- Queue size limits to prevent memory issues
- Efficient audio streaming with FFmpeg

### Network Optimization
- Progressive download with progress tracking
- Connection pooling for YouTube requests
- Retry logic for network failures

### Concurrency
- Thread-safe queue operations
- Async/await pattern throughout
- Per-guild isolation for scalability

## Testing

### Test Coverage
- Unit tests for all components
- Mock-based testing to avoid API calls
- Integration tests for command workflows
- Error scenario validation

### Running Tests
```bash
python -m pytest tests/test_music_functionality.py -v
```

## Troubleshooting

### Common Issues

#### "No audio stream available"
- YouTube video may be restricted or unavailable
- Check video accessibility and try different URL

#### "Failed to connect to voice channel"
- Verify bot has voice permissions in the channel
- Check if channel is full or restricted

#### "FFmpeg not found"
- Ensure FFmpeg is installed and in system PATH
- Verify discord.py[voice] is properly installed

#### "Permission denied"
- User needs `music_playback` module permission
- Check authorization configuration

### Debug Mode
Enable debug logging for detailed troubleshooting:
```yaml
logging:
  level: "DEBUG"
```

## Future Enhancements

### Planned Features
- Playlist support for YouTube playlists
- Search functionality for finding songs
- Volume control per guild
- Repeat and shuffle modes
- Song history and favorites

### Integration Opportunities
- Spotify playlist import
- SoundCloud support
- Local file playback
- Web dashboard for queue management

## Security Considerations

### Input Validation
- Strict YouTube URL validation
- Filename sanitization for downloads
- Queue size and duration limits

### Resource Protection
- Temporary file cleanup
- Memory usage monitoring
- Rate limiting for API requests

### Privacy
- No persistent storage of user data
- Automatic cleanup of downloaded content
- Minimal logging of user activities
