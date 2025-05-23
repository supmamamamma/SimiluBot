"""Discord uploader module for SimiluBot."""
import asyncio
import logging
import os
import time
from typing import Optional, Tuple, Any, Callable

import discord

class DiscordUploader:
    """
    Uploader for Discord.

    Handles uploading files directly to Discord channels.
    """

    def __init__(self):
        """Initialize the Discord uploader."""
        self.logger = logging.getLogger("similubot.uploader.discord")

    async def upload(
        self,
        file_path: str,
        channel: Any,
        content: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[bool, Optional[discord.Message], Optional[str]]:
        """
        Upload a file to a Discord channel.

        Args:
            file_path: Path to the file to upload
            channel: Discord channel to upload to
            content: Optional message content to include with the file
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple containing:
                - Success status (True/False)
                - Discord Message object if successful, None otherwise
                - Error message if failed, None otherwise
        """
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.logger.error(error_msg)
            return False, None, error_msg

        try:
            self.logger.info(f"Uploading file to Discord: {file_path}")

            # Get file size for progress tracking
            file_size = os.path.getsize(file_path)

            # Simulate progress if callback is provided
            if progress_callback:
                # Discord uploads are usually fast, so we'll simulate progress
                start_time = time.time()
                estimated_duration = max(file_size / (5 * 1024 * 1024), 2)  # Estimate based on 5MB/s, minimum 2 seconds

                # Start progress updates
                progress_task = asyncio.create_task(
                    self._simulate_upload_progress(file_size, estimated_duration, progress_callback)
                )

            # Create Discord file object
            discord_file = discord.File(file_path)

            # Send file to channel
            message = await channel.send(content=content, file=discord_file)

            # Complete progress if callback was provided
            if progress_callback:
                progress_task.cancel()
                try:
                    await progress_callback(file_size, file_size, 0)
                except Exception as e:
                    self.logger.warning(f"Final progress callback error: {e}")

            self.logger.info(f"Upload successful: Message ID {message.id}")

            return True, message, None

        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    async def _simulate_upload_progress(self, file_size: int, estimated_duration: float, progress_callback: Callable):
        """
        Simulate upload progress for Discord uploads.

        Args:
            file_size: Size of the file being uploaded
            estimated_duration: Estimated upload duration
            progress_callback: Progress callback function
        """
        start_time = time.time()

        try:
            while True:
                elapsed = time.time() - start_time
                progress = min((elapsed / estimated_duration) * 100, 95)  # Cap at 95% until upload completes

                await progress_callback(
                    int(progress * file_size / 100),
                    file_size,
                    file_size / estimated_duration
                )

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            # Upload completed, task was cancelled
            pass
        except Exception as e:
            self.logger.warning(f"Progress simulation error: {e}")

    async def get_attachment_url(self, message: discord.Message) -> Optional[str]:
        """
        Get the URL of the first attachment in a Discord message.

        Args:
            message: Discord Message object

        Returns:
            URL of the first attachment, or None if no attachments
        """
        if not message.attachments:
            self.logger.warning("No attachments found in message")
            return None

        attachment = message.attachments[0]
        self.logger.debug(f"Attachment URL: {attachment.url}")

        return attachment.url
