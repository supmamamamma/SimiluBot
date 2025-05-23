# SimiluBot

A Discord bot that downloads media from MEGA links, converts them to AAC format, and uploads them to CatBox or Discord.

## Features

- Automatically detects MEGA links in Discord messages
- Downloads media files from MEGA links
- Converts media files to AAC format with configurable bitrate
- Uploads converted files to CatBox (default) or Discord
- Supports various input formats (MP4, MP3, AVI, MKV, etc.)
- Modular and extensible architecture

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
│       └── logger.py          # Logging functionality
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
