"""Upload progress tracker for various upload services."""

import logging
import time
from typing import Optional, Dict, Any

from .base import ProgressTracker


class UploadProgressTracker(ProgressTracker):
    """
    Progress tracker for file uploads.
    
    Provides progress tracking for uploads to various services like Catbox and Discord.
    Since most upload libraries don't provide detailed progress, this tracker
    provides estimated progress based on file size and elapsed time.
    """
    
    def __init__(self, service_name: str, file_size: Optional[int] = None):
        """
        Initialize the upload progress tracker.
        
        Args:
            service_name: Name of the upload service (e.g., "Catbox", "Discord")
            file_size: Size of the file being uploaded in bytes
        """
        super().__init__(f"{service_name} Upload")
        self.logger = logging.getLogger(f"similubot.progress.upload.{service_name.lower()}")
        self.service_name = service_name
        self.file_size = file_size
        self.upload_start_time: Optional[float] = None
        self.last_update_time: Optional[float] = None
        self.estimated_speed: Optional[float] = None
        
    def start_upload(self, file_size: Optional[int] = None) -> None:
        """
        Start tracking upload progress.
        
        Args:
            file_size: Size of the file being uploaded in bytes
        """
        if file_size:
            self.file_size = file_size
            
        self.upload_start_time = time.time()
        self.last_update_time = self.upload_start_time
        
        message = f"Starting upload to {self.service_name}..."
        if self.file_size:
            size_str = self._format_size(self.file_size)
            message += f" ({size_str})"
            
        self.start()
        self.update(message=message)
        
    def update_progress(
        self,
        bytes_uploaded: Optional[int] = None,
        percentage: Optional[float] = None,
        speed: Optional[float] = None
    ) -> None:
        """
        Update upload progress.
        
        Args:
            bytes_uploaded: Number of bytes uploaded so far
            percentage: Upload percentage (0-100)
            speed: Upload speed in bytes/second
        """
        current_time = time.time()
        
        # Calculate percentage if not provided
        if percentage is None and bytes_uploaded is not None and self.file_size:
            percentage = min((bytes_uploaded / self.file_size) * 100, 100.0)
        
        # Estimate speed if not provided
        if speed is None and bytes_uploaded is not None and self.upload_start_time:
            elapsed_time = current_time - self.upload_start_time
            if elapsed_time > 0:
                speed = bytes_uploaded / elapsed_time
                self.estimated_speed = speed
        
        # Create progress message
        message = f"Uploading to {self.service_name}..."
        
        if percentage is not None:
            message += f" {percentage:.1f}%"
            
        if bytes_uploaded is not None and self.file_size:
            uploaded_str = self._format_size(bytes_uploaded)
            total_str = self._format_size(self.file_size)
            message += f" ({uploaded_str}/{total_str})"
            
        if speed is not None:
            speed_str = self._format_speed(speed)
            message += f" - {speed_str}"
            
            # Calculate ETA
            if self.file_size and bytes_uploaded is not None:
                remaining_bytes = self.file_size - bytes_uploaded
                if remaining_bytes > 0 and speed > 0:
                    eta = remaining_bytes / speed
                    eta_str = self._format_time(eta)
                    message += f" - ETA: {eta_str}"
        
        self.update(
            percentage=percentage,
            current_size=bytes_uploaded,
            total_size=self.file_size,
            speed=speed,
            message=message,
            details={
                'service': self.service_name,
                'elapsed_time': current_time - self.upload_start_time if self.upload_start_time else 0
            }
        )
        
        self.last_update_time = current_time
        
    def simulate_progress(self, duration_estimate: float = 30.0) -> None:
        """
        Simulate upload progress when real progress is not available.
        
        This provides a smooth progress bar that estimates completion time
        based on file size and typical upload speeds.
        
        Args:
            duration_estimate: Estimated upload duration in seconds
        """
        if not self.upload_start_time:
            self.start_upload()
            
        current_time = time.time()
        elapsed_time = current_time - self.upload_start_time
        
        # Calculate estimated percentage based on elapsed time
        percentage = min((elapsed_time / duration_estimate) * 100, 95.0)  # Cap at 95% until completion
        
        # Estimate bytes uploaded if file size is known
        bytes_uploaded = None
        if self.file_size:
            bytes_uploaded = int((percentage / 100) * self.file_size)
            
        # Estimate speed
        estimated_speed = None
        if self.file_size and elapsed_time > 0:
            estimated_speed = (percentage / 100) * self.file_size / elapsed_time
            
        self.update_progress(
            bytes_uploaded=bytes_uploaded,
            percentage=percentage,
            speed=estimated_speed
        )
        
    def complete_upload(self, final_url: Optional[str] = None) -> None:
        """
        Mark upload as completed.
        
        Args:
            final_url: Final URL of the uploaded file (if applicable)
        """
        message = f"Upload to {self.service_name} completed successfully"
        if final_url:
            message += f": {final_url}"
            
        self.complete(message)
        
    def fail_upload(self, error_message: str) -> None:
        """
        Mark upload as failed.
        
        Args:
            error_message: Error message describing the failure
        """
        self.fail(f"Upload to {self.service_name} failed: {error_message}")
        
    def parse_output(self, output_line: str) -> bool:
        """
        Parse output line for upload progress.
        
        Most upload libraries don't provide detailed progress output,
        so this method is mainly for compatibility with the base class.
        
        Args:
            output_line: Line of output to parse
            
        Returns:
            False (upload progress is typically tracked differently)
        """
        # Most upload services don't provide parseable progress output
        # Progress is typically tracked through callbacks or API responses
        return False
        
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable format."""
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes} B"
            
    def _format_speed(self, speed_bytes_per_sec: float) -> str:
        """Format speed in bytes/second to human-readable format."""
        if speed_bytes_per_sec >= 1024 * 1024:
            return f"{speed_bytes_per_sec / (1024 * 1024):.1f} MB/s"
        elif speed_bytes_per_sec >= 1024:
            return f"{speed_bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{speed_bytes_per_sec:.0f} B/s"
            
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human-readable format."""
        if seconds >= 3600:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        elif seconds >= 60:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            return f"{seconds:.0f}s"
