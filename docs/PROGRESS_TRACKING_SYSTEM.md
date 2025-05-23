# Real-Time Progress Tracking System

## Overview

The SimiluBot progress tracking system provides real-time progress updates for MEGA downloads, audio conversions, and file uploads with Discord integration. This system reduces user waiting anxiety by providing visual feedback and accurate progress estimates.

## Architecture

### Core Components

1. **Base Progress Framework** (`similubot/progress/base.py`)
   - `ProgressTracker` - Abstract base class for all progress tracking
   - `ProgressInfo` - Data container for progress information
   - `ProgressCallback` - Type alias for progress callback functions
   - `ProgressStatus` - Enumeration of progress states

2. **Specialized Progress Trackers**
   - `MegaProgressTracker` - Parses MegaCMD output for download progress
   - `FFmpegProgressTracker` - Parses FFmpeg output for conversion progress
   - `UploadProgressTracker` - Tracks upload progress with estimation

3. **Discord Integration** (`similubot/progress/discord_updater.py`)
   - `DiscordProgressUpdater` - Updates Discord messages with progress bars
   - Unicode progress bar rendering
   - Rate limiting to prevent API abuse

4. **Enhanced Core Classes**
   - `MegaDownloader.download_with_progress()` - Progress-enabled downloads
   - `AudioConverter.convert_to_aac_with_progress()` - Progress-enabled conversion
   - `CatboxUploader.upload_with_progress()` - Progress-enabled uploads

## Features

### 🔄 Real-Time Progress Parsing

**MEGA Downloads:**
- Parses MegaCMD output: `TRANSFERRING ||################||(1714/1714 MB: 100.00 %)`
- Extracts percentage, file size, and transfer speed
- Handles various size units (B, KB, MB, GB, TB)

**FFmpeg Conversions:**
- Parses FFmpeg output: `size=66816kB time=00:45:47.11 bitrate=199.2kbits/s speed=29.7x`
- Calculates percentage based on duration
- Provides time estimates and speed multipliers

**File Uploads:**
- Tracks bytes uploaded vs total file size
- Calculates upload speed and ETA
- Works with custom file-like objects for real-time tracking

### 📊 Discord Progress Bars

**Visual Progress Indicators:**
```
⏳ MEGA Download
Progress: [████████████░░░░░░░░] 60.5%
Size: 512.3 MB / 847.2 MB
Speed: 2.4 MB/s
ETA: 2m 18s
```

**Features:**
- Unicode progress bars with smooth rendering
- Color-coded embeds based on status
- Automatic rate limiting (updates every 5-10 seconds)
- Detailed information fields (size, speed, ETA)

### ⚡ Event-Driven Architecture

**Callback System:**
```python
def progress_callback(progress: ProgressInfo):
    print(f"Progress: {progress.percentage:.1f}%")

tracker = MegaProgressTracker()
tracker.add_callback(progress_callback)
```

**Discord Integration:**
```python
discord_updater = DiscordProgressUpdater(message)
callback = discord_updater.create_callback()
tracker.add_callback(callback)
```

## Usage Examples

### Basic Progress Tracking

```python
from similubot.downloaders.mega_downloader import MegaDownloader
from similubot.progress.discord_updater import DiscordProgressUpdater

# Create Discord updater
discord_updater = DiscordProgressUpdater(discord_message)
progress_callback = discord_updater.create_callback()

# Download with progress
downloader = MegaDownloader()
success, file_path, error = downloader.download_with_progress(
    url="https://mega.nz/file/...",
    progress_callback=progress_callback
)
```

### Audio Conversion with Progress

```python
from similubot.converters.audio_converter import AudioConverter

converter = AudioConverter()
success, output_file, error = converter.convert_to_aac_with_progress(
    input_file="input.mp4",
    bitrate=128,
    progress_callback=progress_callback
)
```

### Upload with Progress

```python
from similubot.uploaders.catbox_uploader import CatboxUploader

uploader = CatboxUploader()
success, file_url, error = uploader.upload_with_progress(
    file_path="output.m4a",
    progress_callback=progress_callback
)
```

## Technical Implementation

### Progress Parsing

**MEGA Output Parsing:**
```python
# Regex pattern for MEGA progress
TRANSFER_PATTERN = re.compile(
    r'TRANSFERRING\s+\|\|[#\s]*\|\|\s*\((\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\s*(\w+):\s*(\d+(?:\.\d+)?)\s*%\s*\)'
)
```

**FFmpeg Output Parsing:**
```python
# Regex pattern for FFmpeg progress
PROGRESS_PATTERN = re.compile(
    r'size=\s*(\d+(?:\.\d+)?)(kB|MB|GB)?\s+'
    r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})\s+'
    r'bitrate=\s*(\d+(?:\.\d+)?)(kbits/s|Mbits/s)?\s+'
    r'speed=\s*(\d+(?:\.\d+)?)x'
)
```

### Real-Time Output Processing

**Threading-Based Approach:**
```python
def _run_command_with_progress(self, command, progress_tracker):
    process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, text=True)

    def read_output():
        for line in iter(process.stdout.readline, ''):
            progress_tracker.parse_output(line)

    thread = threading.Thread(target=read_output)
    thread.start()
    process.wait()
    thread.join()
```

### Discord Rate Limiting

**Update Throttling:**
```python
class DiscordProgressUpdater:
    def __init__(self, message, update_interval=5.0):
        self.update_interval = update_interval
        self.last_update_time = 0.0

    async def update_progress(self, progress):
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            await self.message.edit(embed=self._create_embed(progress))
            self.last_update_time = current_time
```

## Configuration

### Update Intervals

```python
# Discord message update frequency
discord_updater = DiscordProgressUpdater(
    message=discord_message,
    update_interval=5.0,  # Update every 5 seconds
    progress_bar_length=20  # 20-character progress bar
)
```

### Progress Bar Customization

```python
# Unicode characters for progress bars
filled_char = "█"      # Filled portion
empty_char = "░"       # Empty portion
partial_chars = ["▏", "▎", "▍", "▌", "▋", "▊", "▉"]  # Partial fill
```

## Error Handling

### Robust Failure Recovery

```python
try:
    success, output, error = operation_with_progress(progress_callback)
except Exception as e:
    progress_tracker.fail(f"Operation failed: {str(e)}")
    # Continue with fallback behavior
```

### Callback Error Isolation

```python
def _notify_callbacks(self, progress):
    for callback in self.callbacks:
        try:
            callback(progress)
        except Exception as e:
            # Log error but don't stop progress tracking
            logger.error(f"Progress callback failed: {e}")
```

## Performance Considerations

### Efficient Updates

- **Batched Updates**: Progress updates are batched to avoid excessive Discord API calls
- **Selective Parsing**: Only relevant output lines are processed for progress information
- **Memory Efficient**: Streaming output processing without storing large buffers
- **Thread Safety**: Thread-safe callback execution

### Resource Usage

- **CPU Impact**: Minimal overhead from regex parsing and callback execution
- **Memory Usage**: Small memory footprint with streaming processing
- **Network Usage**: Rate-limited Discord updates prevent API abuse
- **Disk I/O**: No additional disk operations for progress tracking

## Testing

### Unit Tests

```bash
# Test progress tracking components
python -m pytest tests/test_progress_tracking.py -v

# Test integration with existing components
python -m pytest tests/test_mega_downloader.py -v
```

### Demo Scripts

```bash
# Simple progress tracking demo
python test_progress_simple.py

# Comprehensive demo (requires Discord mocking)
python demo_progress_tracking.py
```

## Benefits

### User Experience

- **Reduced Anxiety**: Real-time feedback eliminates uncertainty
- **Accurate Estimates**: ETA calculations help users plan accordingly
- **Visual Feedback**: Progress bars provide intuitive status indication
- **Error Transparency**: Clear error messages when operations fail

### Developer Experience

- **Modular Design**: Easy to extend for new operation types
- **Event-Driven**: Clean separation between progress tracking and UI updates
- **Backward Compatible**: Existing code continues to work without changes
- **Comprehensive Logging**: Detailed debug information for troubleshooting

### System Reliability

- **Fault Tolerant**: Progress tracking failures don't affect core operations
- **Rate Limited**: Prevents Discord API abuse and rate limiting
- **Thread Safe**: Concurrent operations are handled safely
- **Resource Efficient**: Minimal impact on system performance

## Complete Integration Example

### Discord Bot Command with Progress Tracking

```python
import discord
from discord.ext import commands
from similubot.downloaders.mega_downloader import MegaDownloader
from similubot.converters.audio_converter import AudioConverter
from similubot.uploaders.catbox_uploader import CatboxUploader
from similubot.progress.discord_updater import DiscordProgressUpdater

class MediaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.default())
        self.downloader = MegaDownloader()
        self.converter = AudioConverter()
        self.uploader = CatboxUploader()

    @commands.command(name='convert')
    async def convert_media(self, ctx, mega_url: str, bitrate: int = 128):
        """Convert MEGA file to AAC with real-time progress updates."""

        # Create initial progress message
        embed = discord.Embed(
            title="🔄 Media Conversion",
            description="Preparing to download and convert...",
            color=0x3498db
        )
        progress_message = await ctx.send(embed=embed)

        # Create Discord progress updater
        discord_updater = DiscordProgressUpdater(progress_message)
        progress_callback = discord_updater.create_callback()

        try:
            # Step 1: Download with progress
            success, file_path, error = await asyncio.to_thread(
                self.downloader.download_with_progress,
                mega_url,
                progress_callback
            )

            if not success:
                await self._send_error(progress_message, f"Download failed: {error}")
                return

            # Step 2: Convert with progress
            success, converted_file, error = await asyncio.to_thread(
                self.converter.convert_to_aac_with_progress,
                file_path,
                bitrate,
                None,
                progress_callback
            )

            if not success:
                await self._send_error(progress_message, f"Conversion failed: {error}")
                return

            # Step 3: Upload with progress
            success, file_url, error = await asyncio.to_thread(
                self.uploader.upload_with_progress,
                converted_file,
                progress_callback
            )

            if not success:
                await self._send_error(progress_message, f"Upload failed: {error}")
                return

            # Final success message
            final_embed = discord.Embed(
                title="✅ Conversion Complete",
                description=f"Your file has been converted and uploaded successfully!",
                color=0x2ecc71
            )
            final_embed.add_field(name="Download Link", value=file_url, inline=False)
            final_embed.add_field(name="Bitrate", value=f"{bitrate} kbps", inline=True)

            await progress_message.edit(embed=final_embed)

        except Exception as e:
            await self._send_error(progress_message, f"Unexpected error: {str(e)}")

    async def _send_error(self, message, error_text):
        """Send error message to Discord."""
        error_embed = discord.Embed(
            title="❌ Error",
            description=error_text,
            color=0xe74c3c
        )
        await message.edit(embed=error_embed)

# Usage example
bot = MediaBot()
bot.run('YOUR_BOT_TOKEN')
```

### Custom Progress Handler

```python
class CustomProgressHandler:
    def __init__(self, channel):
        self.channel = channel
        self.current_operation = None

    async def handle_progress(self, progress: ProgressInfo):
        """Custom progress handling with logging and notifications."""

        # Log progress for debugging
        logger.info(f"{progress.operation}: {progress.percentage:.1f}% - {progress.message}")

        # Send notifications for major milestones
        if progress.status == ProgressStatus.COMPLETED:
            await self.channel.send(f"✅ {progress.operation} completed!")
        elif progress.status == ProgressStatus.FAILED:
            await self.channel.send(f"❌ {progress.operation} failed: {progress.message}")

        # Update operation tracking
        self.current_operation = progress.operation
```

## Migration Guide

### From Basic to Progress-Enabled Methods

**Before:**
```python
# Old method without progress
success, file_path, error = downloader.download(url)
```

**After:**
```python
# New method with progress
discord_updater = DiscordProgressUpdater(message)
callback = discord_updater.create_callback()

success, file_path, error = downloader.download_with_progress(
    url,
    progress_callback=callback
)
```

### Backward Compatibility

All existing methods continue to work unchanged:
- `MegaDownloader.download()` - Original method still available
- `AudioConverter.convert_to_aac()` - Original method still available
- `CatboxUploader.upload()` - Original method still available

New progress-enabled methods are additive and don't break existing code.
