"""Audio converter module for SimiluBot."""
import logging
import os
import subprocess
from typing import List, Optional, Tuple

class AudioConverter:
    """
    Audio converter for media files.
    
    Handles converting various media formats to AAC audio.
    """
    
    def __init__(
        self,
        default_bitrate: int = 128,
        supported_formats: Optional[List[str]] = None,
        temp_dir: str = "./temp"
    ):
        """
        Initialize the audio converter.
        
        Args:
            default_bitrate: Default AAC bitrate in kbps
            supported_formats: List of supported input format extensions
            temp_dir: Directory to store temporary files
        """
        self.logger = logging.getLogger("similubot.converter.audio")
        self.default_bitrate = default_bitrate
        self.supported_formats = supported_formats or [
            'mp4', 'mp3', 'avi', 'mkv', 'wav', 'flac', 'ogg', 'webm'
        ]
        self.temp_dir = temp_dir
        
        # Ensure temp directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            self.logger.debug(f"Created temporary directory: {self.temp_dir}")
        
        # Check if FFmpeg is installed
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if result.returncode == 0:
                self.logger.debug("FFmpeg is installed")
            else:
                self.logger.warning("FFmpeg check returned non-zero exit code")
        except Exception as e:
            self.logger.error(f"FFmpeg check failed: {e}")
            self.logger.error("FFmpeg may not be installed or not in PATH")
    
    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if a file format is supported.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file format is supported, False otherwise
        """
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        return ext in self.supported_formats
    
    def convert_to_aac(
        self,
        input_file: str,
        bitrate: Optional[int] = None,
        output_file: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Convert a media file to AAC format.
        
        Args:
            input_file: Path to the input file
            bitrate: AAC bitrate in kbps (default: self.default_bitrate)
            output_file: Path to the output file (default: auto-generated)
            
        Returns:
            Tuple containing:
                - Success status (True/False)
                - Path to converted file if successful, None otherwise
                - Error message if failed, None otherwise
        """
        if not os.path.exists(input_file):
            error_msg = f"Input file not found: {input_file}"
            self.logger.error(error_msg)
            return False, None, error_msg
        
        if not self.is_supported_format(input_file):
            ext = os.path.splitext(input_file)[1].lower().lstrip('.')
            error_msg = f"Unsupported format: {ext}"
            self.logger.error(error_msg)
            return False, None, error_msg
        
        # Use default bitrate if not specified
        bitrate = bitrate or self.default_bitrate
        
        # Generate output file path if not specified
        if not output_file:
            input_basename = os.path.basename(input_file)
            input_name = os.path.splitext(input_basename)[0]
            output_file = os.path.join(self.temp_dir, f"{input_name}_{bitrate}kbps.m4a")
        
        try:
            self.logger.info(f"Converting {input_file} to AAC ({bitrate} kbps)")
            self.logger.debug(f"Output file: {output_file}")
            
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-i", input_file,
                "-c:a", "aac",
                "-b:a", f"{bitrate}k",
                "-vn",  # No video
                "-y",   # Overwrite output file if it exists
                output_file
            ]
            
            # Run FFmpeg
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Check if conversion was successful
            if process.returncode != 0:
                error_msg = f"Conversion failed: {process.stderr}"
                self.logger.error(error_msg)
                return False, None, error_msg
            
            if not os.path.exists(output_file):
                error_msg = "Conversion failed: Output file not found"
                self.logger.error(error_msg)
                return False, None, error_msg
            
            file_size = os.path.getsize(output_file)
            self.logger.info(f"Conversion successful: {os.path.basename(output_file)} ({file_size} bytes)")
            
            return True, output_file, None
            
        except Exception as e:
            error_msg = f"Conversion failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg
    
    def get_media_info(self, file_path: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Get information about a media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Tuple containing:
                - Success status (True/False)
                - Media info dictionary if successful, None otherwise
                - Error message if failed, None otherwise
        """
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.logger.error(error_msg)
            return False, None, error_msg
        
        try:
            self.logger.info(f"Getting media info for: {file_path}")
            
            # Run FFprobe to get media info
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if process.returncode != 0:
                error_msg = f"Failed to get media info: {process.stderr}"
                self.logger.error(error_msg)
                return False, None, error_msg
            
            import json
            media_info = json.loads(process.stdout)
            
            self.logger.info(f"Media info retrieved successfully")
            self.logger.debug(f"Media info: {media_info}")
            
            return True, media_info, None
            
        except Exception as e:
            error_msg = f"Failed to get media info: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg
