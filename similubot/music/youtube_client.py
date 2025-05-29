"""YouTube audio extraction client using pytubefix."""

import logging
import os
import re
import asyncio
from typing import Optional, Tuple, Callable, Dict, Any
from dataclasses import dataclass
from pytubefix import YouTube
from pytubefix.exceptions import PytubeFixError


@dataclass
class AudioInfo:
    """Information about extracted audio."""
    title: str
    duration: int  # Duration in seconds
    file_path: str
    url: str
    uploader: str
    thumbnail_url: Optional[str] = None


class YouTubeClient:
    """
    YouTube audio extraction client using pytubefix.
    
    Handles downloading audio-only streams from YouTube videos
    with progress tracking and error handling.
    """

    def __init__(self, temp_dir: str = "./temp"):
        """
        Initialize the YouTube client.
        
        Args:
            temp_dir: Directory for temporary audio files
        """
        self.logger = logging.getLogger("similubot.music.youtube_client")
        self.temp_dir = temp_dir
        
        # Ensure temp directory exists
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            self.logger.debug(f"Created temp directory: {temp_dir}")

    def is_youtube_url(self, url: str) -> bool:
        """
        Check if a URL is a valid YouTube URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid YouTube URL, False otherwise
        """
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+'
        ]
        
        return any(re.match(pattern, url) for pattern in youtube_patterns)

    async def extract_audio_info(self, url: str) -> Optional[AudioInfo]:
        """
        Extract audio information from a YouTube URL without downloading.
        
        Args:
            url: YouTube URL
            
        Returns:
            AudioInfo object if successful, None otherwise
        """
        if not self.is_youtube_url(url):
            self.logger.error(f"Invalid YouTube URL: {url}")
            return None
            
        try:
            self.logger.debug(f"Extracting info from: {url}")
            
            # Run in thread to avoid blocking
            yt = await asyncio.to_thread(YouTube, url)
            
            # Get audio stream info
            audio_stream = yt.streams.get_audio_only()
            if not audio_stream:
                self.logger.error(f"No audio stream found for: {url}")
                return None
            
            return AudioInfo(
                title=yt.title or "Unknown Title",
                duration=yt.length or 0,
                file_path="",  # Will be set during download
                url=url,
                uploader=yt.author or "Unknown",
                thumbnail_url=yt.thumbnail_url
            )
            
        except PytubeFixError as e:
            self.logger.error(f"PytubeFixError extracting info from {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error extracting info from {url}: {e}", exc_info=True)
            return None

    async def download_audio(
        self, 
        url: str, 
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Tuple[bool, Optional[AudioInfo], Optional[str]]:
        """
        Download audio from a YouTube URL.
        
        Args:
            url: YouTube URL
            progress_callback: Optional progress callback function
            
        Returns:
            Tuple of (success, AudioInfo, error_message)
        """
        if not self.is_youtube_url(url):
            return False, None, f"Invalid YouTube URL: {url}"
            
        try:
            self.logger.info(f"Starting audio download: {url}")
            
            # Create progress wrapper if callback provided
            def on_progress(stream, chunk, bytes_remaining):
                if progress_callback:
                    total_size = stream.filesize
                    downloaded = total_size - bytes_remaining
                    progress_callback("Downloading audio", downloaded, total_size)
            
            # Initialize YouTube object with progress callback
            yt = await asyncio.to_thread(
                YouTube, 
                url, 
                on_progress_callback=on_progress if progress_callback else None
            )
            
            # Get best audio stream
            audio_stream = yt.streams.get_audio_only()
            if not audio_stream:
                return False, None, "No audio stream available"
            
            # Generate safe filename
            safe_title = self._sanitize_filename(yt.title or "audio")
            filename = f"{safe_title}.{audio_stream.subtype}"
            
            # Download audio
            self.logger.debug(f"Downloading to: {self.temp_dir}/{filename}")
            file_path = await asyncio.to_thread(
                audio_stream.download,
                output_path=self.temp_dir,
                filename=filename
            )
            
            # Create AudioInfo object
            audio_info = AudioInfo(
                title=yt.title or "Unknown Title",
                duration=yt.length or 0,
                file_path=file_path,
                url=url,
                uploader=yt.author or "Unknown",
                thumbnail_url=yt.thumbnail_url
            )
            
            self.logger.info(f"Audio download completed: {file_path}")
            return True, audio_info, None
            
        except PytubeFixError as e:
            error_msg = f"PytubeFixError downloading {url}: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error downloading {url}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe file system usage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length and strip whitespace
        filename = filename.strip()[:100]
        
        # Ensure filename is not empty
        if not filename:
            filename = "audio"
            
        return filename

    def cleanup_file(self, file_path: str) -> bool:
        """
        Clean up a downloaded audio file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"Cleaned up file: {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error cleaning up file {file_path}: {e}")
            return False

    def format_duration(self, seconds: int) -> str:
        """
        Format duration in seconds to MM:SS or HH:MM:SS format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 3600:  # Less than 1 hour
            minutes, secs = divmod(seconds, 60)
            return f"{minutes:02d}:{secs:02d}"
        else:  # 1 hour or more
            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
