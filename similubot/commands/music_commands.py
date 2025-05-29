"""Music commands for SimiluBot."""

import logging
import asyncio
from typing import Optional, List, Dict, Any
import discord
from discord.ext import commands

from similubot.core.command_registry import CommandRegistry
from similubot.music.music_player import MusicPlayer
from similubot.progress.discord_updater import DiscordProgressUpdater
from similubot.utils.config_manager import ConfigManager


class MusicCommands:
    """
    Music command handlers for SimiluBot.

    Provides commands for music playback, queue management,
    and voice channel interaction.
    """

    def __init__(self, config: ConfigManager, music_player: MusicPlayer):
        """
        Initialize music commands.

        Args:
            config: Configuration manager
            music_player: Music player instance
        """
        self.logger = logging.getLogger("similubot.commands.music")
        self.config = config
        self.music_player = music_player

        # Check if music functionality is enabled
        self._enabled = config.get('music.enabled', True)

        self.logger.debug("Music commands initialized")

    def is_available(self) -> bool:
        """
        Check if music commands are available.

        Returns:
            True if available, False otherwise
        """
        return self._enabled

    def register_commands(self, registry: CommandRegistry) -> None:
        """
        Register music commands with the command registry.

        Args:
            registry: Command registry instance
        """
        if not self.is_available():
            self.logger.info("Music commands not registered (disabled)")
            return

        usage_examples = [
            "!music <youtube_url> - Add song to queue and start playback",
            "!music queue - Display current queue",
            "!music now - Show current song progress",
            "!music skip - Skip to next song",
            "!music stop - Stop playback and clear queue",
            "!music jump <number> - Jump to specific position in queue"
        ]

        help_text = (
            "Music playback commands for YouTube audio. "
            "You must be in a voice channel to use these commands."
        )

        registry.register_command(
            name="music",
            callback=self.music_command,
            description="Music playback and queue management",
            required_permission="music",
            usage_examples=usage_examples,
            help_text=help_text
        )

        self.logger.debug("Music commands registered")

    async def music_command(self, ctx: commands.Context, *args) -> None:
        """
        Main music command handler.

        Args:
            ctx: Discord command context
            *args: Command arguments
        """
        if not args:
            await self._show_music_help(ctx)
            return

        subcommand = args[0]

        if subcommand in ["queue", "q"]:
            await self._handle_queue_command(ctx)
        elif subcommand in ["now", "current", "playing"]:
            await self._handle_now_command(ctx)
        elif subcommand in ["skip", "next"]:
            await self._handle_skip_command(ctx)
        elif subcommand in ["stop", "disconnect", "leave"]:
            await self._handle_stop_command(ctx)
        elif subcommand in ["jump", "goto"]:
            await self._handle_jump_command(ctx, args[1:])
        elif self.music_player.youtube_client.is_youtube_url(subcommand):
            # First argument is a YouTube URL
            await self._handle_play_command(ctx, subcommand)
        else:
            await self._show_music_help(ctx)

    async def _handle_play_command(self, ctx: commands.Context, url: str) -> None:
        """
        Handle play command (add song to queue).

        Args:
            ctx: Discord command context
            url: YouTube URL
        """
        # Check if user is in voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.reply("❌ You must be in a voice channel to play music!")
            return

        # Connect to voice channel if not already connected
        success, error = await self.music_player.connect_to_user_channel(ctx.author)
        if not success:
            await ctx.reply(f"❌ {error}")
            return

        # Send initial response
        response = await ctx.reply("🔄 Processing YouTube URL...")

        # Create progress updater
        progress_updater = DiscordProgressUpdater(response)
        progress_callback = progress_updater.create_callback()

        try:
            # Add song to queue
            success, position, error = await self.music_player.add_song_to_queue(
                url, ctx.author, progress_callback
            )

            if not success:
                await self._send_error_embed(response, "Failed to Add Song", error or "Unknown error")
                return

            # Get audio info for the added song
            audio_info = await self.music_player.youtube_client.extract_audio_info(url)
            if not audio_info:
                await self._send_error_embed(response, "Error", "Failed to get song information")
                return

            # Create success embed
            embed = discord.Embed(
                title="🎵 Song Added to Queue",
                color=discord.Color.green()
            )

            embed.add_field(
                name="Title",
                value=audio_info.title,
                inline=False
            )

            embed.add_field(
                name="Duration",
                value=self.music_player.youtube_client.format_duration(audio_info.duration),
                inline=True
            )

            embed.add_field(
                name="Uploader",
                value=audio_info.uploader,
                inline=True
            )

            embed.add_field(
                name="Position in Queue",
                value=f"#{position}",
                inline=True
            )

            embed.add_field(
                name="Requested by",
                value=ctx.author.display_name,
                inline=True
            )

            if audio_info.thumbnail_url:
                embed.set_thumbnail(url=audio_info.thumbnail_url)

            await response.edit(content=None, embed=embed)

        except Exception as e:
            self.logger.error(f"Error in play command: {e}", exc_info=True)
            await self._send_error_embed(response, "Unexpected Error", str(e))

    async def _handle_queue_command(self, ctx: commands.Context) -> None:
        """
        Handle queue display command.

        Args:
            ctx: Discord command context
        """
        try:
            queue_info = await self.music_player.get_queue_info(ctx.guild.id)

            if queue_info["is_empty"] and not queue_info["current_song"]:
                embed = discord.Embed(
                    title="🎵 Music Queue",
                    description="Queue is empty",
                    color=discord.Color.blue()
                )
                await ctx.reply(embed=embed)
                return

            embed = discord.Embed(
                title="🎵 Music Queue",
                color=discord.Color.blue()
            )

            # Add current song info
            if queue_info["current_song"]:
                current = queue_info["current_song"]
                embed.add_field(
                    name="🎶 Now Playing",
                    value=f"**{current.title}**\n"
                          f"Duration: {self.music_player.youtube_client.format_duration(current.duration)}\n"
                          f"Requested by: {current.requester.display_name}",
                    inline=False
                )

            # Add queue info
            if not queue_info["is_empty"]:
                queue_manager = self.music_player.get_queue_manager(ctx.guild.id)
                queue_display = await queue_manager.get_queue_display(max_songs=10)

                if queue_display:
                    queue_text = ""
                    for song in queue_display:
                        queue_text += (
                            f"**{song['position']}.** {song['title']}\n"
                            f"    Duration: {song['duration']} | "
                            f"Requested by: {song['requester']}\n\n"
                        )

                    embed.add_field(
                        name="📋 Up Next",
                        value=queue_text[:1024],  # Discord field limit
                        inline=False
                    )

                # Add queue summary
                total_duration = self.music_player.youtube_client.format_duration(
                    queue_info["total_duration"]
                )
                embed.add_field(
                    name="📊 Queue Summary",
                    value=f"Songs: {queue_info['queue_length']}\n"
                          f"Total Duration: {total_duration}",
                    inline=True
                )

            # Add voice connection info
            if queue_info["connected"]:
                embed.add_field(
                    name="🔊 Voice Status",
                    value=f"Channel: {queue_info['channel']}\n"
                          f"Playing: {'Yes' if queue_info['playing'] else 'No'}\n"
                          f"Paused: {'Yes' if queue_info['paused'] else 'No'}",
                    inline=True
                )

            await ctx.reply(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in queue command: {e}", exc_info=True)
            await ctx.reply("❌ Error retrieving queue information")

    async def _handle_now_command(self, ctx: commands.Context) -> None:
        """
        Handle now playing command.

        Args:
            ctx: Discord command context
        """
        try:
            queue_info = await self.music_player.get_queue_info(ctx.guild.id)
            current_song = queue_info.get("current_song")

            if not current_song:
                await ctx.reply("❌ No song is currently playing")
                return

            embed = discord.Embed(
                title="🎶 Now Playing",
                color=discord.Color.green()
            )

            embed.add_field(
                name="Title",
                value=current_song.title,
                inline=False
            )

            embed.add_field(
                name="Duration",
                value=self.music_player.youtube_client.format_duration(current_song.duration),
                inline=True
            )

            embed.add_field(
                name="Uploader",
                value=current_song.uploader,
                inline=True
            )

            embed.add_field(
                name="Requested by",
                value=current_song.requester.display_name,
                inline=True
            )

            # Add progress bar (simplified version)
            if queue_info["playing"]:
                embed.add_field(
                    name="Status",
                    value="▶️ Playing",
                    inline=True
                )
            elif queue_info["paused"]:
                embed.add_field(
                    name="Status",
                    value="⏸️ Paused",
                    inline=True
                )

            if current_song.audio_info.thumbnail_url:
                embed.set_thumbnail(url=current_song.audio_info.thumbnail_url)

            await ctx.reply(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in now command: {e}", exc_info=True)
            await ctx.reply("❌ Error retrieving current song information")

    async def _handle_skip_command(self, ctx: commands.Context) -> None:
        """
        Handle skip command.

        Args:
            ctx: Discord command context
        """
        try:
            success, skipped_title, error = await self.music_player.skip_current_song(ctx.guild.id)

            if not success:
                await ctx.reply(f"❌ {error}")
                return

            embed = discord.Embed(
                title="⏭️ Song Skipped",
                description=f"Skipped: **{skipped_title}**",
                color=discord.Color.orange()
            )

            await ctx.reply(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in skip command: {e}", exc_info=True)
            await ctx.reply("❌ Error skipping song")

    async def _handle_stop_command(self, ctx: commands.Context) -> None:
        """
        Handle stop command.

        Args:
            ctx: Discord command context
        """
        try:
            success, error = await self.music_player.stop_playback(ctx.guild.id)

            if not success:
                await ctx.reply(f"❌ {error}")
                return

            embed = discord.Embed(
                title="⏹️ Playback Stopped",
                description="Stopped playback and cleared queue. Disconnected from voice channel.",
                color=discord.Color.red()
            )

            await ctx.reply(embed=embed)

        except Exception as e:
            self.logger.error(f"Error in stop command: {e}", exc_info=True)
            await ctx.reply("❌ Error stopping playback")

    async def _handle_jump_command(self, ctx: commands.Context, args: List[str]) -> None:
        """
        Handle jump command.

        Args:
            ctx: Discord command context
            args: Command arguments
        """
        if not args:
            await ctx.reply("❌ Please specify a queue position number")
            return

        try:
            position = int(args[0])
            if position < 1:
                await ctx.reply("❌ Queue position must be 1 or greater")
                return

            success, song_title, error = await self.music_player.jump_to_position(
                ctx.guild.id, position
            )

            if not success:
                await ctx.reply(f"❌ {error}")
                return

            embed = discord.Embed(
                title="⏭️ Jumped to Song",
                description=f"Now playing: **{song_title}**",
                color=discord.Color.green()
            )

            await ctx.reply(embed=embed)

        except ValueError:
            await ctx.reply("❌ Invalid position number")
        except Exception as e:
            self.logger.error(f"Error in jump command: {e}", exc_info=True)
            await ctx.reply("❌ Error jumping to position")

    async def _show_music_help(self, ctx: commands.Context) -> None:
        """
        Show music command help.

        Args:
            ctx: Discord command context
        """
        embed = discord.Embed(
            title="🎵 Music Commands",
            description="Music playback and queue management commands",
            color=discord.Color.blue()
        )

        commands_text = (
            "`!music <youtube_url>` - Add song to queue\n"
            "`!music queue` - Show current queue\n"
            "`!music now` - Show current song\n"
            "`!music skip` - Skip current song\n"
            "`!music stop` - Stop and clear queue\n"
            "`!music jump <number>` - Jump to position"
        )

        embed.add_field(
            name="Available Commands",
            value=commands_text,
            inline=False
        )

        embed.add_field(
            name="Requirements",
            value="• You must be in a voice channel\n• Provide valid YouTube URLs",
            inline=False
        )

        await ctx.reply(embed=embed)

    async def _send_error_embed(
        self,
        message: discord.Message,
        title: str,
        description: str
    ) -> None:
        """
        Send an error embed.

        Args:
            message: Message to edit
            title: Error title
            description: Error description
        """
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Color.red()
        )

        await message.edit(content=None, embed=embed)
