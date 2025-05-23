# SimiluBot

A Discord bot that downloads media from MEGA links, converts them to AAC format, and uploads them to CatBox or Discord.

## Features

- **Automatic MEGA Link Detection**: Automatically detects and processes MEGA links in Discord messages
- **Media Download**: Downloads media files from MEGA links with real-time progress tracking
- **Audio Conversion**: Converts media files to AAC format with configurable bitrate and progress monitoring
- **File Upload**: Uploads converted files to CatBox (default) or Discord with upload progress
- **Format Support**: Supports various input formats (MP4, MP3, AVI, MKV, WAV, FLAC, OGG, WebM)
- **Progress Tracking**: Visual progress bars with real-time updates for all operations
- **Smart Caching**: Filename hashing and cache management to avoid duplicate downloads
- **Modular Architecture**: Clean, extensible codebase with comprehensive error handling

## Requirements

- Python 3.8 or higher
- FFmpeg (must be installed and available in PATH)
- Discord Bot Token
- MEGA account (optional, for better download speeds)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/SimiluBot.git
   cd SimiluBot
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a configuration file:
   ```
   cp config/config.yaml.example config/config.yaml
   ```

4. Edit the configuration file and add your Discord bot token:
   ```yaml
   discord:
     token: "YOUR_DISCORD_BOT_TOKEN_HERE"
   ```

## Configuration

The `config/config.yaml` file contains all the configuration options for the bot:

- `discord.token`: Your Discord bot token
- `discord.command_prefix`: Command prefix for the bot (default: `!`)
- `download.temp_dir`: Directory to store temporary files
- `conversion.default_bitrate`: Default AAC bitrate in kbps (default: `128`)
- `conversion.supported_formats`: List of supported input formats
- `upload.default_service`: Default upload service (`catbox` or `discord`)
- `upload.catbox.user_hash`: CatBox user hash (optional)
- `logging.level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logging.file`: Log file path
- `logging.max_size`: Maximum log file size in bytes
- `logging.backup_count`: Number of backup log files to keep

## Usage

1. Start the bot:
   ```
   python main.py
   ```

2. In Discord, you can use the following commands:
   - `!mega <url> [bitrate]`: Download a file from MEGA and convert it to AAC format
   - `!about`: Show information about the bot

The bot will also automatically detect and process MEGA links in messages.

## Progress Tracking Features

SimiluBot provides comprehensive real-time progress tracking for all major operations:

### Visual Progress Bars
- **Unicode Progress Bars**: Beautiful visual progress indicators using Unicode characters
- **Real-time Updates**: Progress updates every 5-10 seconds to avoid Discord rate limits
- **Color-coded Status**: Blue for in-progress, green for complete, red for errors

### Download Progress
- **File Information**: Shows original filename (truncated if too long)
- **Download Speed**: Real-time download speed in MB/s or KB/s
- **Progress Percentage**: Accurate progress based on file size
- **Time Estimation**: Estimated time remaining for download completion
- **Cache Detection**: Instantly detects if file already exists in cache

### Conversion Progress
- **FFmpeg Integration**: Real-time progress tracking during audio conversion
- **Duration-based Progress**: Progress calculated based on media file duration
- **Processing Speed**: Shows conversion speed and efficiency
- **Stage Information**: Clear indication of current conversion stage

### Upload Progress
- **Service-specific Tracking**: Different progress tracking for CatBox and Discord uploads
- **Upload Speed**: Real-time upload speed monitoring
- **File Size Information**: Shows current and total upload progress
- **Completion Confirmation**: Clear success/failure indication with result links

### Error Handling
- **Graceful Degradation**: Falls back to simple text messages if progress tracking fails
- **Rate Limit Protection**: Intelligent update intervals to avoid Discord API limits
- **Detailed Error Messages**: User-friendly error descriptions with troubleshooting hints

### Example Progress Display
```
🔄 MEGA Download
📁 File: `example_video.mp4`
📊 Progress: [████████████░░░░░░░░] 65.2%
📦 Size: 45.2 MB / 69.4 MB
⚡ Speed: 2.3 MB/s
⏱️ ETA: 10s
ℹ️ Status: Downloading from MEGA...
Elapsed: 19s
```

## Project Structure

```
SimiluBot/
├── config/
│   └── config.yaml
├── similubot/
│   ├── bot.py                 # Main Discord bot implementation
│   ├── downloaders/
│   │   └── mega_downloader.py # MEGA download functionality
│   ├── converters/
│   │   └── audio_converter.py # FFmpeg audio conversion
│   ├── uploaders/
│   │   ├── catbox_uploader.py # CatBox upload functionality
│   │   └── discord_uploader.py # Discord upload functionality
│   └── utils/
│       ├── config_manager.py  # Configuration management
│       ├── logger.py          # Logging functionality
│       └── progress_tracker.py # Progress tracking and visual indicators
├── tests/                     # Unit tests
├── .gitignore
├── README.md
├── requirements.txt
└── main.py                    # Entry point
```

## Development

### Running Tests

```
pytest
```

### Adding New Features

The modular architecture makes it easy to add new features:

- Add new downloaders in `similubot/downloaders/`
- Add new converters in `similubot/converters/`
- Add new uploaders in `similubot/uploaders/`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper for Python
- [mega.py](https://github.com/odwyersoftware/mega.py) - Python library for the MEGA API
- [FFmpeg](https://ffmpeg.org/) - Audio/video conversion tool
