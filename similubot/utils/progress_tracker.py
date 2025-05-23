"""Progress tracking utilities for SimiluBot."""
import asyncio
import logging
import time
from typing import Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

import discord

class ProgressStatus(Enum):
    """Progress status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class ProgressInfo:
    """Progress information data class."""
    percentage: float = 0.0
    current_size: int = 0
    total_size: int = 0
    speed: float = 0.0  # bytes per second
    eta: Optional[int] = None  # seconds
    status: ProgressStatus = ProgressStatus.PENDING
    message: str = ""
    filename: str = ""

class ProgressTracker:
    """
    Progress tracker for Discord bot operations.
    
    Provides visual progress bars and real-time updates for long-running operations.
    """
    
    def __init__(self, discord_message: discord.Message, operation_name: str):
        """
        Initialize the progress tracker.
        
        Args:
            discord_message: Discord message to update with progress
            operation_name: Name of the operation being tracked
        """
        self.logger = logging.getLogger("similubot.progress")
        self.discord_message = discord_message
        self.operation_name = operation_name
        self.start_time = time.time()
        self.last_update_time = 0
        self.update_interval = 5.0  # Update every 5 seconds to avoid rate limits
        self.is_active = False
        
    def create_progress_bar(self, percentage: float, length: int = 20) -> str:
        """
        Create a visual progress bar using Unicode characters.
        
        Args:
            percentage: Progress percentage (0-100)
            length: Length of the progress bar
            
        Returns:
            Unicode progress bar string
        """
        filled_length = int(length * percentage / 100)
        bar = "█" * filled_length + "░" * (length - filled_length)
        return f"[{bar}] {percentage:.1f}%"
    
    def format_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def format_speed(self, speed_bps: float) -> str:
        """
        Format transfer speed in human-readable format.
        
        Args:
            speed_bps: Speed in bytes per second
            
        Returns:
            Formatted speed string
        """
        return f"{self.format_size(speed_bps)}/s"
    
    def format_time(self, seconds: int) -> str:
        """
        Format time duration in human-readable format.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def truncate_filename(self, filename: str, max_length: int = 40) -> str:
        """
        Truncate filename if too long for display.
        
        Args:
            filename: Original filename
            max_length: Maximum length for display
            
        Returns:
            Truncated filename
        """
        if len(filename) <= max_length:
            return filename
        
        # Keep extension and truncate the name part
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        available_length = max_length - len(ext) - 4  # 4 for "..." and "."
        
        if available_length > 0:
            truncated_name = name[:available_length] + "..."
            return f"{truncated_name}.{ext}" if ext else truncated_name
        else:
            return f"...{ext}" if ext else "..."
    
    def create_embed(self, progress_info: ProgressInfo) -> discord.Embed:
        """
        Create a Discord embed with progress information.
        
        Args:
            progress_info: Progress information
            
        Returns:
            Discord embed object
        """
        # Determine embed color based on status
        color_map = {
            ProgressStatus.PENDING: discord.Color.orange(),
            ProgressStatus.IN_PROGRESS: discord.Color.blue(),
            ProgressStatus.COMPLETED: discord.Color.green(),
            ProgressStatus.ERROR: discord.Color.red()
        }
        
        color = color_map.get(progress_info.status, discord.Color.blue())
        
        # Create embed
        embed = discord.Embed(
            title=f"🔄 {self.operation_name}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        # Add filename if available
        if progress_info.filename:
            truncated_name = self.truncate_filename(progress_info.filename)
            embed.add_field(
                name="📁 File",
                value=f"`{truncated_name}`",
                inline=False
            )
        
        # Add progress bar
        if progress_info.status == ProgressStatus.IN_PROGRESS:
            progress_bar = self.create_progress_bar(progress_info.percentage)
            embed.add_field(
                name="📊 Progress",
                value=f"```{progress_bar}```",
                inline=False
            )
            
            # Add size information if available
            if progress_info.total_size > 0:
                current_size_str = self.format_size(progress_info.current_size)
                total_size_str = self.format_size(progress_info.total_size)
                embed.add_field(
                    name="📦 Size",
                    value=f"{current_size_str} / {total_size_str}",
                    inline=True
                )
            
            # Add speed information if available
            if progress_info.speed > 0:
                speed_str = self.format_speed(progress_info.speed)
                embed.add_field(
                    name="⚡ Speed",
                    value=speed_str,
                    inline=True
                )
            
            # Add ETA if available
            if progress_info.eta is not None:
                eta_str = self.format_time(progress_info.eta)
                embed.add_field(
                    name="⏱️ ETA",
                    value=eta_str,
                    inline=True
                )
        
        # Add status message
        if progress_info.message:
            embed.add_field(
                name="ℹ️ Status",
                value=progress_info.message,
                inline=False
            )
        
        # Add elapsed time
        elapsed_time = int(time.time() - self.start_time)
        embed.set_footer(text=f"Elapsed: {self.format_time(elapsed_time)}")
        
        return embed
    
    async def update_progress(self, progress_info: ProgressInfo, force_update: bool = False) -> bool:
        """
        Update the Discord message with progress information.
        
        Args:
            progress_info: Progress information to display
            force_update: Force update even if within rate limit interval
            
        Returns:
            True if update was successful, False otherwise
        """
        current_time = time.time()
        
        # Check if we should update (rate limiting)
        if not force_update and (current_time - self.last_update_time) < self.update_interval:
            return True
        
        try:
            embed = self.create_embed(progress_info)
            await self.discord_message.edit(content=None, embed=embed)
            self.last_update_time = current_time
            self.logger.debug(f"Updated progress: {progress_info.percentage:.1f}%")
            return True
            
        except discord.HTTPException as e:
            self.logger.warning(f"Failed to update progress message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error updating progress: {e}", exc_info=True)
            return False
    
    async def start_operation(self, filename: str = "", message: str = "") -> None:
        """
        Start tracking an operation.
        
        Args:
            filename: Name of the file being processed
            message: Initial status message
        """
        self.is_active = True
        progress_info = ProgressInfo(
            status=ProgressStatus.IN_PROGRESS,
            filename=filename,
            message=message or f"Starting {self.operation_name.lower()}..."
        )
        await self.update_progress(progress_info, force_update=True)
    
    async def complete_operation(self, message: str = "", final_info: Optional[str] = None) -> None:
        """
        Mark operation as completed.
        
        Args:
            message: Completion message
            final_info: Additional information to display
        """
        self.is_active = False
        progress_info = ProgressInfo(
            percentage=100.0,
            status=ProgressStatus.COMPLETED,
            message=message or f"{self.operation_name} completed successfully!"
        )
        
        # Update embed title for completion
        embed = self.create_embed(progress_info)
        embed.title = f"✅ {self.operation_name} Complete"
        
        if final_info:
            embed.add_field(
                name="🔗 Result",
                value=final_info,
                inline=False
            )
        
        try:
            await self.discord_message.edit(content=None, embed=embed)
        except Exception as e:
            self.logger.error(f"Error updating completion message: {e}")
    
    async def error_operation(self, error_message: str) -> None:
        """
        Mark operation as failed.
        
        Args:
            error_message: Error message to display
        """
        self.is_active = False
        progress_info = ProgressInfo(
            status=ProgressStatus.ERROR,
            message=error_message
        )
        
        # Update embed title for error
        embed = self.create_embed(progress_info)
        embed.title = f"❌ {self.operation_name} Failed"
        
        try:
            await self.discord_message.edit(content=None, embed=embed)
        except Exception as e:
            self.logger.error(f"Error updating error message: {e}")

class ProgressCallback:
    """
    Callback class for progress updates.
    
    This class can be used as a callback for operations that support progress reporting.
    """
    
    def __init__(self, tracker: ProgressTracker):
        """
        Initialize the progress callback.
        
        Args:
            tracker: Progress tracker instance
        """
        self.tracker = tracker
        self.last_update = 0
        
    async def __call__(self, current: int, total: int, speed: float = 0.0) -> None:
        """
        Progress callback function.
        
        Args:
            current: Current progress (bytes or other unit)
            total: Total size (bytes or other unit)
            speed: Current speed (units per second)
        """
        if total > 0:
            percentage = (current / total) * 100
            eta = int((total - current) / speed) if speed > 0 else None
            
            progress_info = ProgressInfo(
                percentage=percentage,
                current_size=current,
                total_size=total,
                speed=speed,
                eta=eta,
                status=ProgressStatus.IN_PROGRESS
            )
            
            await self.tracker.update_progress(progress_info)
