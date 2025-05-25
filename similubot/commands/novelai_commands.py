"""NovelAI image generation commands."""
import asyncio
import logging
import os
import re
from typing import Optional, List
import discord
from discord.ext import commands

from similubot.core.command_registry import CommandRegistry
from similubot.generators.image_generator import ImageGenerator
from similubot.uploaders.catbox_uploader import CatboxUploader
from similubot.uploaders.discord_uploader import DiscordUploader
from similubot.progress.discord_updater import DiscordProgressUpdater
from similubot.utils.config_manager import ConfigManager


class NovelAICommands:
    """
    NovelAI image generation command handlers.
    
    Handles AI image generation with multi-character support,
    size specifications, and flexible upload options.
    """

    def __init__(
        self,
        config: ConfigManager,
        image_generator: Optional[ImageGenerator],
        catbox_uploader: CatboxUploader,
        discord_uploader: DiscordUploader
    ):
        """
        Initialize NovelAI commands.

        Args:
            config: Configuration manager
            image_generator: NovelAI image generator instance (None if not configured)
            catbox_uploader: CatBox uploader instance
            discord_uploader: Discord uploader instance
        """
        self.logger = logging.getLogger("similubot.commands.novelai")
        self.config = config
        self.image_generator = image_generator
        self.catbox_uploader = catbox_uploader
        self.discord_uploader = discord_uploader

    def register_commands(self, registry: CommandRegistry) -> None:
        """
        Register NovelAI commands with the command registry.

        Args:
            registry: Command registry instance
        """
        registry.register_command(
            name="nai",
            callback=self.nai_command,
            description="Generate an image using NovelAI",
            required_permission="nai"
        )

        self.logger.debug("NovelAI commands registered")

    async def nai_command(self, ctx: commands.Context, *, args: str) -> None:
        """
        Generate an image using NovelAI.

        Usage:
            !nai <prompt>
            !nai <prompt> discord
            !nai <prompt> catbox
            !nai <prompt> [discord/catbox] char1:[description] char2:[description]
            !nai <prompt> [discord/catbox] [char1:[desc]...] [size:portrait/landscape/square]

        Args:
            ctx: Discord command context
            args: Prompt text followed by optional upload service, character parameters, and size specification
        """
        if not self.image_generator:
            await ctx.reply("❌ NovelAI image generation is not configured. Please check your API key in the config.")
            return

        if not args.strip():
            await ctx.reply("❌ Please provide a prompt for image generation.")
            return

        # Parse arguments for upload service, character parameters, and size specification
        upload_service, character_args, size_spec, prompt = self._parse_nai_arguments(args)

        if not prompt:
            await ctx.reply("❌ Please provide a prompt for image generation.")
            return

        # Validate character parameters if provided
        if character_args:
            validation_error = self._validate_character_args(character_args)
            if validation_error:
                await ctx.reply(validation_error)
                return

        await self.process_nai_generation(ctx.message, prompt, upload_service, character_args, size_spec)

    def _parse_nai_arguments(self, args: str) -> tuple:
        """
        Parse NovelAI command arguments.

        Args:
            args: Raw argument string

        Returns:
            Tuple of (upload_service, character_args, size_spec, prompt)
        """
        upload_service = None
        character_args = []
        size_spec = None
        remaining_text = args.strip()

        # Extract upload service (discord/catbox) - must be a standalone word
        upload_match = re.search(r'\b(discord|catbox)\b', remaining_text, re.IGNORECASE)
        if upload_match:
            upload_service = upload_match.group(1).lower()
            remaining_text = remaining_text.replace(upload_match.group(0), '', 1).strip()

        # Extract size specification (size:portrait, size:landscape, size:square)
        size_pattern = re.compile(r'\bsize:(portrait|landscape|square)\b', re.IGNORECASE)
        size_match = size_pattern.search(remaining_text)
        if size_match:
            size_spec = size_match.group(1).lower()
            remaining_text = size_pattern.sub('', remaining_text).strip()

        # Extract character parameters using regex
        char_pattern = re.compile(r'char(\d+):\[([^\]]+)\]', re.IGNORECASE)
        char_matches = char_pattern.findall(remaining_text)

        for char_num, char_desc in char_matches:
            character_args.append(f"char{char_num}:[{char_desc}]")

        # Remove character parameters from the text to get the prompt
        prompt = char_pattern.sub('', remaining_text).strip()
        # Clean up extra spaces
        prompt = re.sub(r'\s+', ' ', prompt).strip()

        return upload_service, character_args, size_spec, prompt

    def _validate_character_args(self, character_args: List[str]) -> Optional[str]:
        """
        Validate character arguments.

        Args:
            character_args: List of character argument strings

        Returns:
            Error message if validation fails, None if valid
        """
        self.logger.info(f"Multi-character generation requested with {len(character_args)} characters")
        
        for char_arg in character_args:
            if not char_arg.lower().startswith("char") or ":[" not in char_arg or not char_arg.endswith("]"):
                return f"❌ Invalid character syntax: '{char_arg}'. Expected format: 'char1:[description]'"
        
        return None

    async def process_nai_generation(
        self,
        message: discord.Message,
        prompt: str,
        upload_service_override: Optional[str] = None,
        character_args: Optional[List[str]] = None,
        size_spec: Optional[str] = None
    ) -> None:
        """
        Process NovelAI image generation with real-time progress tracking.

        Args:
            message: Discord message that triggered the generation
            prompt: Text prompt for image generation
            upload_service_override: Override upload service (discord/catbox)
            character_args: Character parameters for multi-character generation
            size_spec: Size specification (portrait/landscape/square)
        """
        if not self.image_generator:
            await message.reply("❌ NovelAI image generation is not configured.")
            return

        # Create initial progress embed
        embed = discord.Embed(
            title="🎨 AI Image Generation",
            description=f"Generating image with prompt: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`",
            color=0x9b59b6
        )
        response = await message.reply(embed=embed)

        # Create Discord progress updater
        discord_updater = DiscordProgressUpdater(response, update_interval=5.0)
        progress_callback = discord_updater.create_callback()

        # Initialize variables for cleanup
        file_paths: List[str] = []

        try:
            # Get default parameters from config
            default_params = self.config.get_novelai_default_parameters()
            model = self.config.get_novelai_default_model()

            # Apply size specification if provided
            if size_spec:
                size_params = self._get_size_parameters(size_spec)
                default_params.update(size_params)

            # Log generation type
            if character_args:
                self.logger.info(f"Starting NovelAI multi-character generation: '{prompt[:100]}...' with {len(character_args)} characters")
            else:
                self.logger.info(f"Starting NovelAI single-character generation: '{prompt[:100]}...'")

            # Generate image with progress
            if not hasattr(self.image_generator, 'generate_image_with_progress'):
                await self._send_error_embed(response, "Generation Error", "Image generator method not available")
                return

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
            await self._upload_images(response, file_paths, prompt, upload_service, progress_callback, message)

        except Exception as e:
            self.logger.error(f"Error processing NovelAI generation: {e}", exc_info=True)
            await self._send_error_embed(
                response,
                "Generation Error",
                f"An unexpected error occurred: {str(e)}"
            )

        finally:
            # Clean up temporary files
            self._cleanup_temp_files(file_paths)

    def _get_size_parameters(self, size_spec: str) -> dict:
        """
        Get size parameters for the specified size.

        Args:
            size_spec: Size specification (portrait/landscape/square)

        Returns:
            Dictionary with width and height parameters
        """
        size_mappings = {
            "portrait": {"width": 832, "height": 1216},
            "landscape": {"width": 1216, "height": 832},
            "square": {"width": 1024, "height": 1024}
        }
        
        return size_mappings.get(size_spec, {"width": 1024, "height": 1024})

    async def _upload_images(
        self,
        response: discord.Message,
        file_paths: List[str],
        prompt: str,
        upload_service: str,
        progress_callback,
        original_message: discord.Message
    ) -> None:
        """Upload generated images to the specified service."""
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

            # Create success embed with all URLs
            success_embed = discord.Embed(
                title="✅ Image Generation Complete",
                description=f"Generated {len(file_paths)} image(s) successfully!",
                color=0x2ecc71
            )
            
            success_embed.add_field(
                name="🎨 Prompt",
                value=f"`{prompt[:200]}{'...' if len(prompt) > 200 else ''}`",
                inline=False
            )

            for i, url in enumerate(upload_urls):
                success_embed.add_field(
                    name=f"🔗 Image {i+1}" if len(upload_urls) > 1 else "🔗 Download Link",
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
                    original_message.channel,
                    content=content
                )

                if not success:
                    await self._send_error_embed(response, "Upload Failed", error or "Unknown error")
                    return

            # Delete the processing message since images are uploaded directly
            await response.delete()

    async def _send_error_embed(self, response: discord.Message, title: str, description: str) -> None:
        """Send an error embed."""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=0xe74c3c
        )
        embed.timestamp = discord.utils.utcnow()
        await response.edit(embed=embed)

    def _cleanup_temp_files(self, file_paths: List[str]) -> None:
        """Clean up temporary files."""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.logger.debug(f"Cleaned up temporary file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary file {file_path}: {e}")

    def is_available(self) -> bool:
        """
        Check if NovelAI commands are available.

        Returns:
            True if NovelAI is configured and available, False otherwise
        """
        return self.image_generator is not None
