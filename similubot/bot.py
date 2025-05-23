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
        Process a MEGA link.

        Args:
            message: Discord message containing the link
            url: MEGA link to process
            bitrate: AAC bitrate in kbps (optional)
        """
        # Use default bitrate if not specified
        if bitrate is None:
            bitrate = self.config.get_default_bitrate()

        # Send initial response
        response = await message.reply(f"Processing MEGA link... (bitrate: {bitrate} kbps)")

        try:
            # Update status
            await response.edit(content="Downloading file from MEGA...")

            # Download file
            success, file_path, error = self.downloader.download(url)

            if not success:
                await response.edit(content=f"Error downloading file: {error}")
                return

            # Update status
            await response.edit(content=f"Converting file to AAC ({bitrate} kbps)...")

            # Convert file
            success, converted_file, error = self.converter.convert_to_aac(file_path, bitrate)

            if not success:
                await response.edit(content=f"Error converting file: {error}")
                return

            # Update status
            upload_service = self.config.get_default_upload_service()
            await response.edit(content=f"Uploading file to {upload_service.capitalize()}...")

            # Upload file
            if upload_service == "catbox":
                success, url, error = self.catbox_uploader.upload(converted_file)

                if not success:
                    await response.edit(content=f"Error uploading file: {error}")
                    return

                # Send success message
                file_name = os.path.basename(converted_file)
                await response.edit(
                    content=f"✅ Converted and uploaded: {file_name} ({bitrate} kbps)\n"
                            f"Download: {url}"
                )
            else:  # discord
                success, discord_msg, error = await self.discord_uploader.upload(
                    converted_file,
                    message.channel,
                    content=f"✅ Converted file ({bitrate} kbps)"
                )

                if not success:
                    await response.edit(content=f"Error uploading file: {error}")
                    return

                # Delete the processing message
                await response.delete()

        except Exception as e:
            self.logger.error(f"Error processing MEGA link: {e}", exc_info=True)
            await response.edit(content=f"An error occurred while processing the MEGA link: {str(e)}")

        finally:
            # Clean up temporary files
            self._cleanup_temp_files([file_path, converted_file])

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
