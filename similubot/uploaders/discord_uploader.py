"""Discord uploader module for SimiluBot."""
import logging
import os
from typing import Optional, Tuple, Any

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
        content: Optional[str] = None
    ) -> Tuple[bool, Optional[discord.Message], Optional[str]]:
        """
        Upload a file to a Discord channel.
        
        Args:
            file_path: Path to the file to upload
            channel: Discord channel to upload to
            content: Optional message content to include with the file
            
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
            
            # Create Discord file object
            discord_file = discord.File(file_path)
            
            # Send file to channel
            message = await channel.send(content=content, file=discord_file)
            
            self.logger.info(f"Upload successful: Message ID {message.id}")
            
            return True, message, None
            
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg
    
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
