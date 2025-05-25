"""General bot commands."""
import logging
from typing import Optional
import discord
from discord.ext import commands

from similubot.core.command_registry import CommandRegistry
from similubot.utils.config_manager import ConfigManager
from similubot.generators.image_generator import ImageGenerator


class GeneralCommands:
    """
    General bot command handlers.
    
    Handles informational commands and bot status information.
    """

    def __init__(self, config: ConfigManager, image_generator: Optional[ImageGenerator] = None):
        """
        Initialize general commands.

        Args:
            config: Configuration manager
            image_generator: NovelAI image generator instance (None if not configured)
        """
        self.logger = logging.getLogger("similubot.commands.general")
        self.config = config
        self.image_generator = image_generator

    def register_commands(self, registry: CommandRegistry) -> None:
        """
        Register general commands with the command registry.

        Args:
            registry: Command registry instance
        """
        registry.register_command(
            name="about",
            callback=self.about_command,
            description="Show information about the bot",
            required_permission="about"
        )

        registry.register_command(
            name="help",
            callback=self.help_command,
            description="Show help information",
            required_permission="help"
        )

        registry.register_command(
            name="status",
            callback=self.status_command,
            description="Show bot status information",
            required_permission="status"
        )

        self.logger.debug("General commands registered")

    async def about_command(self, ctx: commands.Context) -> None:
        """
        Show information about the bot.

        Args:
            ctx: Discord command context
        """
        embed = discord.Embed(
            title="About SimiluBot",
            description="A bot for downloading MEGA links and converting media to AAC format.",
            color=discord.Color.blue()
        )

        # MEGA command information
        embed.add_field(
            name=f"{ctx.bot.command_prefix}mega <url> [bitrate]",
            value="Download a file from MEGA and convert it to AAC format.",
            inline=False
        )

        # Add NovelAI command if available
        if self.image_generator:
            nai_description = "Generate an AI image using NovelAI with the given text prompt."
            nai_description += f"\nDefault upload: {self.config.get_novelai_upload_service()}"
            nai_description += "\nAdd `discord` or `catbox` to override upload service."
            nai_description += "\nAdd `char1:[description] char2:[description]` for multi-character generation."
            nai_description += "\nAdd `size:portrait/landscape/square` to specify image dimensions."
            embed.add_field(
                name=f"{ctx.bot.command_prefix}nai <prompt> [discord/catbox] [char1:[desc]...] [size:xxx]",
                value=nai_description,
                inline=False
            )

        # Automatic MEGA link detection
        embed.add_field(
            name="Automatic MEGA Link Detection",
            value="The bot will automatically detect and process MEGA links in messages.",
            inline=False
        )

        # Supported formats
        embed.add_field(
            name="Supported Formats",
            value=", ".join(self.config.get_supported_formats()),
            inline=False
        )

        # Default bitrate
        embed.add_field(
            name="Default Bitrate",
            value=f"{self.config.get_default_bitrate()} kbps",
            inline=False
        )

        # Bot information
        embed.add_field(
            name="Bot Information",
            value=f"Guilds: {len(ctx.bot.guilds)}\nUsers: {sum(guild.member_count or 0 for guild in ctx.bot.guilds)}",
            inline=True
        )

        # Version and links
        embed.add_field(
            name="Links",
            value="[GitHub](https://github.com/yourusername/similubot) • [Support](https://discord.gg/yourinvite)",
            inline=True
        )

        embed.set_footer(text="SimiluBot • Powered by Python & discord.py")
        embed.timestamp = discord.utils.utcnow()

        await ctx.send(embed=embed)

    async def help_command(self, ctx: commands.Context, command_name: Optional[str] = None) -> None:
        """
        Show help information.

        Args:
            ctx: Discord command context
            command_name: Specific command to get help for (optional)
        """
        if command_name:
            # Show help for specific command
            command = ctx.bot.get_command(command_name)
            if command:
                embed = discord.Embed(
                    title=f"Help: {ctx.bot.command_prefix}{command.name}",
                    description=command.help or "No description available.",
                    color=0x3498db
                )
                
                if command.usage:
                    embed.add_field(
                        name="Usage",
                        value=f"`{ctx.bot.command_prefix}{command.name} {command.usage}`",
                        inline=False
                    )
                
                if command.aliases:
                    embed.add_field(
                        name="Aliases",
                        value=", ".join([f"`{alias}`" for alias in command.aliases]),
                        inline=False
                    )
                
                await ctx.send(embed=embed)
            else:
                await ctx.reply(f"❌ Command `{command_name}` not found.")
        else:
            # Show general help
            embed = discord.Embed(
                title="SimiluBot Help",
                description="Available commands and features",
                color=0x3498db
            )

            # Core commands
            core_commands = []
            core_commands.append(f"`{ctx.bot.command_prefix}mega <url> [bitrate]` - Download and convert MEGA files")
            
            if self.image_generator:
                core_commands.append(f"`{ctx.bot.command_prefix}nai <prompt>` - Generate AI images")
            
            core_commands.append(f"`{ctx.bot.command_prefix}about` - Bot information")
            core_commands.append(f"`{ctx.bot.command_prefix}status` - Bot status")

            embed.add_field(
                name="📋 Core Commands",
                value="\n".join(core_commands),
                inline=False
            )

            # Features
            features = [
                "🔗 Automatic MEGA link detection",
                "🎵 Audio format conversion",
                "📤 Multiple upload services",
                "🔐 Permission system"
            ]

            embed.add_field(
                name="✨ Features",
                value="\n".join(features),
                inline=False
            )

            # Get help for specific command
            embed.add_field(
                name="💡 Need More Help?",
                value=f"Use `{ctx.bot.command_prefix}help <command>` for detailed command information.",
                inline=False
            )

            embed.set_footer(text="SimiluBot Help System")
            await ctx.send(embed=embed)

    async def status_command(self, ctx: commands.Context) -> None:
        """
        Show bot status information.

        Args:
            ctx: Discord command context
        """
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=0x2ecc71
        )

        # Bot basic info
        embed.add_field(
            name="Bot Information",
            value=f"**Name:** {ctx.bot.user.name}\n**ID:** {ctx.bot.user.id}\n**Latency:** {round(ctx.bot.latency * 1000)}ms",
            inline=True
        )

        # Server stats
        embed.add_field(
            name="Server Statistics",
            value=f"**Guilds:** {len(ctx.bot.guilds)}\n**Users:** {sum(guild.member_count or 0 for guild in ctx.bot.guilds)}\n**Channels:** {len(list(ctx.bot.get_all_channels()))}",
            inline=True
        )

        # Feature availability
        features_status = []
        features_status.append(f"🔗 MEGA Downloads: ✅ Available")
        
        if self.image_generator:
            features_status.append(f"🎨 NovelAI Generation: ✅ Available")
        else:
            features_status.append(f"🎨 NovelAI Generation: ❌ Not Configured")

        embed.add_field(
            name="Feature Status",
            value="\n".join(features_status),
            inline=False
        )

        # Configuration info
        config_info = []
        config_info.append(f"**Default Bitrate:** {self.config.get_default_bitrate()} kbps")
        config_info.append(f"**MEGA Upload Service:** {self.config.get_mega_upload_service()}")
        
        if self.image_generator:
            config_info.append(f"**NovelAI Upload Service:** {self.config.get_novelai_upload_service()}")

        embed.add_field(
            name="Configuration",
            value="\n".join(config_info),
            inline=False
        )

        # System status
        embed.add_field(
            name="System Status",
            value="🟢 All systems operational",
            inline=False
        )

        embed.set_thumbnail(url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text="SimiluBot Status")

        await ctx.send(embed=embed)

    def get_command_count(self) -> int:
        """
        Get the number of registered general commands.

        Returns:
            Number of commands registered by this module
        """
        return 3  # about, help, status
