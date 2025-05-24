"""Main Discord bot implementation for SimiluBot."""
import asyncio
import logging
import os
import re
from typing import Optional, List, Dict, Any, Union

import discord
from discord.ext import commands

from similubot.downloaders.mega_downloader import MegaDownloader
from similubot.converters.audio_converter import AudioConverter
from similubot.uploaders.catbox_uploader import CatboxUploader
from similubot.uploaders.discord_uploader import DiscordUploader
from similubot.generators.image_generator import ImageGenerator
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

        # Initialize image generator (if NovelAI is configured)
        try:
            self.image_generator = ImageGenerator(
                api_key=self.config.get_novelai_api_key(),
                base_url=self.config.get_novelai_base_url(),
                timeout=self.config.get_novelai_timeout(),
                temp_dir=temp_dir
            )
            self.logger.info("NovelAI image generator initialized successfully")
        except ValueError as e:
            self.logger.warning(f"NovelAI not configured: {e}")
            self.image_generator = None

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

            # Add NovelAI command if available
            if self.image_generator:
                nai_description = "Generate an AI image using NovelAI with the given text prompt."
                nai_description += f"\nDefault upload: {self.config.get_novelai_upload_service()}"
                nai_description += "\nAdd `discord` or `catbox` to override upload service."
                nai_description += "\nAdd `char1:[description] char2:[description]` for multi-character generation."
                embed.add_field(
                    name=f"{self.bot.command_prefix}nai <prompt> [discord/catbox] [char1:[desc] char2:[desc]...]",
                    value=nai_description,
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

        @self.bot.command(name="nai")
        async def nai_command(ctx, *, args: str):
            """
            Generate an image using NovelAI.

            Usage:
                !nai <prompt>
                !nai <prompt> discord
                !nai <prompt> catbox
                !nai <prompt> [discord/catbox] char1:[description] char2:[description]

            Args:
                args: Prompt text followed by optional upload service and character parameters
            """
            if not self.image_generator:
                await ctx.reply("❌ NovelAI image generation is not configured. Please check your API key in the config.")
                return

            if not args.strip():
                await ctx.reply("❌ Please provide a prompt for image generation.")
                return

            # Parse arguments for upload service and character parameters
            # Use regex to properly extract character parameters with spaces
            import re

            upload_service = None
            character_args = []
            remaining_text = args.strip()

            # Extract upload service (discord/catbox) - must be a standalone word
            upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
            if upload_match:
                upload_service = upload_match.group(1).lower()
                remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

            # Extract character parameters using regex
            char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
            char_matches = char_pattern.findall(remaining_text)

            for char_num, char_desc in char_matches:
                character_args.append(f"char{char_num}:[{char_desc}]")

            # Remove character parameters from the text to get the prompt
            prompt = char_pattern.sub('', remaining_text).strip()
            # Clean up extra spaces
            prompt = re.sub(r'\s+', ' ', prompt).strip()

            if not prompt:
                await ctx.reply("❌ Please provide a prompt for image generation.")
                return

            # Validate character parameters if provided
            if character_args:
                self.logger.info(f"Multi-character generation requested with {len(character_args)} characters")
                # Basic validation - detailed validation will happen in the client
                for char_arg in character_args:
                    if not char_arg.lower().startswith("char") or ":[" not in char_arg or not char_arg.endswith("]"):
                        await ctx.reply(f"❌ Invalid character syntax: '{char_arg}'. Expected format: 'char1:[description]'")
                        return

            await self._process_nai_generation(ctx.message, prompt, upload_service, character_args)

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
            upload_service = self.config.get_mega_upload_service()
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

    async def _process_nai_generation(
        self,
        message: discord.Message,
        prompt: str,
        upload_service_override: Optional[str] = None,
        character_args: Optional[List[str]] = None
    ):
        """
        Process a NovelAI image generation request with real-time progress tracking.

        Args:
            message: Discord message containing the request
            prompt: Text prompt for image generation
            upload_service_override: Optional upload service override
            character_args: Optional list of character argument strings
        """
        # Create initial progress embed
        generation_type = "Multi-character" if character_args else "Single-character"
        char_info = f" ({len(character_args)} characters)" if character_args else ""
        embed = discord.Embed(
            title="🎨 AI Image Generation",
            description=f"{generation_type} generation{char_info}\nPrompt: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`",
            color=0x9b59b6
        )
        response = await message.reply(embed=embed)

        # Create Discord progress updater
        discord_updater = DiscordProgressUpdater(response, update_interval=3.0)
        progress_callback = discord_updater.create_callback()

        # Initialize variables for cleanup
        file_paths: Optional[List[str]] = None

        try:
            # Get default parameters from config
            default_params = self.config.get_novelai_default_parameters()
            model = self.config.get_novelai_default_model()

            if character_args:
                self.logger.info(f"Starting NovelAI multi-character generation: '{prompt[:100]}...' with {len(character_args)} characters")
            else:
                self.logger.info(f"Starting NovelAI single-character generation: '{prompt[:100]}...'")

            # Generate image with progress
            success, file_paths, error = await self.image_generator.generate_image_with_progress(
                prompt=prompt,
                model=model,
                progress_callback=progress_callback,
                character_args=character_args,
                **default_params
            )

            if not success or not file_paths:
                await self._send_error_embed(response, "Generation Failed", error or "Unknown error")
                return

            # Upload images
            upload_service = upload_service_override or self.config.get_novelai_upload_service()
            self.logger.info(f"Starting upload to {upload_service}: {len(file_paths)} image(s)")

            if upload_service == "catbox":
                # Upload to CatBox
                upload_urls = []
                for i, file_path in enumerate(file_paths):
                    success, file_url, error = await asyncio.to_thread(
                        self.catbox_uploader.upload_with_progress,
                        file_path,
                        progress_callback
                    )

                    if not success or not file_url:
                        await self._send_error_embed(response, "Upload Failed", error or "Unknown error")
                        return

                    upload_urls.append(file_url)

                # Create success embed
                success_embed = discord.Embed(
                    title="✅ Image Generation Complete",
                    description="Your AI-generated image is ready!",
                    color=0x2ecc71
                )
                success_embed.add_field(name="🎨 Prompt", value=f"`{prompt[:200]}{'...' if len(prompt) > 200 else ''}`", inline=False)
                success_embed.add_field(name="🤖 Model", value=model, inline=True)
                success_embed.add_field(name="📊 Images", value=str(len(upload_urls)), inline=True)

                # Add download links
                for i, url in enumerate(upload_urls):
                    success_embed.add_field(
                        name=f"🔗 Download Link {i+1}" if len(upload_urls) > 1 else "🔗 Download Link",
                        value=url,
                        inline=False
                    )

                success_embed.timestamp = discord.utils.utcnow()
                await response.edit(embed=success_embed)

            else:  # discord upload
                # Upload directly to Discord
                for i, file_path in enumerate(file_paths):
                    content = f"✅ AI-generated image {i+1}/{len(file_paths)}" if len(file_paths) > 1 else "✅ AI-generated image"
                    content += f"\n**Prompt:** `{prompt[:150]}{'...' if len(prompt) > 150 else ''}`"

                    success, discord_msg, error = await self.discord_uploader.upload(
                        file_path,
                        message.channel,
                        content=content
                    )

                    if not success:
                        await self._send_error_embed(response, "Upload Failed", error or "Unknown error")
                        return

                # Delete the processing message since files are uploaded directly
                await response.delete()

        except Exception as e:
            self.logger.error(f"Error processing NovelAI generation: {e}", exc_info=True)
            await self._send_error_embed(
                response,
                "Generation Error",
                f"An unexpected error occurred: {str(e)}"
            )

        finally:
            # Clean up temporary files
            if file_paths:
                self._cleanup_temp_files(file_paths)

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

    def _cleanup_temp_files(self, file_paths: Union[List[str], List[Optional[str]]]):
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
