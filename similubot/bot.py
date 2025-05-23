"""Main Discord bot implementation for SimiluBot."""
import asyncio
import logging
import os
import re
from typing import Optional, List, Dict, Any

import discord
from discord.ext import commands

from similubot.downloaders.mega_downloader import MegaDownloader
from similubot.converters.audio_converter import AudioConverter
from similubot.uploaders.catbox_uploader import CatboxUploader
from similubot.uploaders.discord_uploader import DiscordUploader
from similubot.utils.config_manager import ConfigManager
from similubot.progress.discord_updater import DiscordProgressUpdater

class SimiluBot:
    """
    Main Discord bot implementation for SimiluBot.

    Handles Discord events and coordinates the different modules.
    """

    def __init__(self, config: ConfigManager):
        """
        Initialize the Discord bot.

        Args:
            config: Configuration manager
        """
        self.logger = logging.getLogger("similubot.bot")
        self.config = config

        # Set up Discord bot
        intents = discord.Intents.default()
        intents.message_content = True

        self.bot = commands.Bot(
            command_prefix=self.config.get('discord.command_prefix', '!'),
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )

        # Initialize modules
        self._init_modules()

        # Set up event handlers
        self._setup_event_handlers()

        # Set up commands
        self._setup_commands()

    def _init_modules(self):
        """Initialize the bot modules."""
        # Create temp directory if it doesn't exist
        temp_dir = self.config.get_download_temp_dir()
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            self.logger.debug(f"Created temporary directory: {temp_dir}")

        # Initialize downloader
        self.downloader = MegaDownloader(temp_dir=temp_dir)

        # Initialize converter
        self.converter = AudioConverter(
            default_bitrate=self.config.get_default_bitrate(),
            supported_formats=self.config.get_supported_formats(),
            temp_dir=temp_dir
        )

        # Initialize uploaders
        self.catbox_uploader = CatboxUploader(
            user_hash=self.config.get_catbox_user_hash()
        )
        self.discord_uploader = DiscordUploader()

    def _setup_event_handlers(self):
        """Set up Discord event handlers."""
        @self.bot.event
        async def on_ready():
            self.logger.info(f"Bot is ready. Logged in as {self.bot.user.name} ({self.bot.user.id})")

            # Set bot status
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{self.bot.command_prefix}about"
            )
            await self.bot.change_presence(activity=activity)

        @self.bot.event
        async def on_message(message):
            # Ignore messages from the bot itself
            if message.author == self.bot.user:
                return

            # Process commands
            await self.bot.process_commands(message)

            # Check for MEGA links in messages
            if not message.content:
                return

            mega_links = self.downloader.extract_mega_links(message.content)
            if mega_links and not message.content.startswith(self.bot.command_prefix):
                self.logger.info(f"Found MEGA links in message: {len(mega_links)}")

                # Process the first link
                await self._process_mega_link(message, mega_links[0])

    def _setup_commands(self):
        """Set up Discord bot commands."""
        @self.bot.command(name="mega")
        async def mega_command(ctx, url: str, bitrate: Optional[int] = None):
            """
            Download a file from MEGA and convert it to AAC.

            Args:
                url: MEGA link to download
                bitrate: AAC bitrate in kbps (optional)
            """
            if not self.downloader.is_mega_link(url):
                await ctx.reply("Invalid MEGA link. Please provide a valid MEGA link.")
                return

            await self._process_mega_link(ctx.message, url, bitrate)

        @self.bot.command(name="about")
        async def about_command(ctx):
            """Show information about the bot."""
            embed = discord.Embed(
                title="About SimiluBot",
                description="A bot for downloading MEGA links and converting media to AAC format.",
                color=discord.Color.blue()
            )

            embed.add_field(
                name=f"{self.bot.command_prefix}mega <url> [bitrate]",
                value="Download a file from MEGA and convert it to AAC format.",
                inline=False
            )

            embed.add_field(
                name="Automatic MEGA Link Detection",
                value="The bot will automatically detect and process MEGA links in messages.",
                inline=False
            )

            embed.add_field(
                name="Supported Formats",
                value=", ".join(self.config.get_supported_formats()),
                inline=False
            )

            embed.add_field(
                name="Default Bitrate",
                value=f"{self.config.get_default_bitrate()} kbps",
                inline=False
            )

            await ctx.send(embed=embed)

    async def _process_mega_link(
        self,
        message: discord.Message,
        url: str,
        bitrate: Optional[int] = None
    ):
        """
        Process a MEGA link with real-time progress tracking.

        Args:
            message: Discord message containing the link
            url: MEGA link to process
            bitrate: AAC bitrate in kbps (optional)
        """
        # Use default bitrate if not specified
        if bitrate is None:
            bitrate = self.config.get_default_bitrate()

        # Create initial progress embed
        embed = discord.Embed(
            title="🔄 Media Processing",
            description=f"Preparing to download and convert... (bitrate: {bitrate} kbps)",
            color=0x3498db
        )
        response = await message.reply(embed=embed)

        # Create Discord progress updater
        discord_updater = DiscordProgressUpdater(response, update_interval=5.0)
        progress_callback = discord_updater.create_callback()

        # Initialize variables for cleanup
        file_path: Optional[str] = None
        converted_file: Optional[str] = None

        try:
            # Step 1: Download with progress
            self.logger.info(f"Starting MEGA download: {url}")
            success, file_path, error = await asyncio.to_thread(
                self.downloader.download_with_progress,
                url,
                progress_callback
            )

            if not success or not file_path:
                await self._send_error_embed(response, "Download Failed", error or "Unknown error")
                return

            # Step 2: Convert with progress
            self.logger.info(f"Starting audio conversion: {file_path}")
            success, converted_file, error = await asyncio.to_thread(
                self.converter.convert_to_aac_with_progress,
                file_path,
                bitrate,
                None,  # Use default output file path
                progress_callback
            )

            if not success or not converted_file:
                await self._send_error_embed(response, "Conversion Failed", error or "Unknown error")
                return

            # Step 3: Upload with progress
            upload_service = self.config.get_default_upload_service()
            self.logger.info(f"Starting upload to {upload_service}: {converted_file}")

            if upload_service == "catbox":
                success, file_url, error = await asyncio.to_thread(
                    self.catbox_uploader.upload_with_progress,
                    converted_file,
                    progress_callback
                )

                if not success or not file_url:
                    await self._send_error_embed(response, "Upload Failed", error or "Unknown error")
                    return

                # Create success embed
                file_name = os.path.basename(converted_file)
                file_size = os.path.getsize(converted_file)

                success_embed = discord.Embed(
                    title="✅ Processing Complete",
                    description="Your file has been successfully downloaded, converted, and uploaded!",
                    color=0x2ecc71
                )
                success_embed.add_field(name="📁 File", value=file_name, inline=True)
                success_embed.add_field(name="🎵 Bitrate", value=f"{bitrate} kbps", inline=True)
                success_embed.add_field(name="📊 Size", value=self._format_file_size(file_size), inline=True)
                success_embed.add_field(name="🔗 Download Link", value=file_url, inline=False)
                success_embed.timestamp = discord.utils.utcnow()

                await response.edit(embed=success_embed)

            else:  # discord upload
                success, discord_msg, error = await self.discord_uploader.upload(
                    converted_file,
                    message.channel,
                    content=f"✅ Converted file ({bitrate} kbps)"
                )

                if not success:
                    await self._send_error_embed(response, "Upload Failed", error or "Unknown error")
                    return

                # Delete the processing message since file is uploaded directly
                await response.delete()

        except Exception as e:
            self.logger.error(f"Error processing MEGA link: {e}", exc_info=True)
            await self._send_error_embed(
                response,
                "Processing Error",
                f"An unexpected error occurred: {str(e)}"
            )

        finally:
            # Clean up temporary files
            self._cleanup_temp_files([file_path, converted_file])

    async def _send_error_embed(self, message: discord.Message, title: str, description: str):
        """
        Send an error embed to Discord.

        Args:
            message: Discord message to edit
            title: Error title
            description: Error description
        """
        error_embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=0xe74c3c
        )
        error_embed.timestamp = discord.utils.utcnow()
        await message.edit(embed=error_embed)

    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in bytes to human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        if size_bytes >= 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        elif size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes} B"

    def _cleanup_temp_files(self, file_paths: List[Optional[str]]):
        """
        Clean up temporary files.

        Args:
            file_paths: List of file paths to clean up
        """
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.logger.debug(f"Removed temporary file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove temporary file {file_path}: {e}")

    def run(self):
        """Run the Discord bot."""
        token = self.config.get_discord_token()
        self.bot.run(token)
