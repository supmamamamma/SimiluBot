"""Core music player for SimiluBot."""

import logging
import asyncio
import os
import time
from typing import Optional, Dict, Callable, Any
import discord
from discord.ext import commands

from .youtube_client import YouTubeClient, AudioInfo
from .queue_manager import QueueManager, Song
from .voice_manager import VoiceManager
from similubot.progress.base import ProgressCallback


class MusicPlayer:
    """
    Core music player that orchestrates YouTube downloading, queue management,
    and Discord voice playback.
    """

    def __init__(self, bot: commands.Bot, temp_dir: str = "./temp"):
        """
        Initialize the music player.

        Args:
            bot: Discord bot instance
            temp_dir: Directory for temporary audio files
        """
        self.logger = logging.getLogger("similubot.music.music_player")
        self.bot = bot
        self.temp_dir = temp_dir

        # Initialize components
        self.youtube_client = YouTubeClient(temp_dir)
        self.voice_manager = VoiceManager(bot)

        # Guild-specific queue managers
        self._queue_managers: Dict[int, QueueManager] = {}

        # Playback state tracking
        self._playback_tasks: Dict[int, asyncio.Task] = {}
        self._current_audio_files: Dict[int, str] = {}

        # Playback timing tracking
        self._playback_start_times: Dict[int, float] = {}
        self._playback_paused_times: Dict[int, float] = {}
        self._total_paused_duration: Dict[int, float] = {}

        self.logger.info("Music player initialized")

    def get_queue_manager(self, guild_id: int) -> QueueManager:
        """
        Get or create a queue manager for a guild.

        Args:
            guild_id: Discord guild ID

        Returns:
            QueueManager instance
        """
        if guild_id not in self._queue_managers:
            self._queue_managers[guild_id] = QueueManager(guild_id)
            self.logger.debug(f"Created queue manager for guild {guild_id}")

        return self._queue_managers[guild_id]

    async def add_song_to_queue(
        self,
        url: str,
        requester: discord.Member,
        progress_callback: Optional[ProgressCallback] = None
    ) -> tuple[bool, Optional[int], Optional[str]]:
        """
        Add a song to the queue and start playback if not already playing.

        Args:
            url: YouTube URL
            requester: User who requested the song
            progress_callback: Optional progress callback

        Returns:
            Tuple of (success, queue_position, error_message)
        """
        guild_id = requester.guild.id

        try:
            # Extract audio info first
            audio_info = await self.youtube_client.extract_audio_info(url)
            if not audio_info:
                return False, None, "Failed to extract audio information from URL"

            # Add to queue
            queue_manager = self.get_queue_manager(guild_id)
            position = await queue_manager.add_song(audio_info, requester)

            self.logger.info(f"Added song to queue: {audio_info.title} (position {position})")

            # Start playback if not already playing
            if not self.voice_manager.is_playing(guild_id):
                await self._start_playback(guild_id, progress_callback)

            return True, position, None

        except Exception as e:
            error_msg = f"Error adding song to queue: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    async def connect_to_user_channel(self, member: discord.Member) -> tuple[bool, Optional[str]]:
        """
        Connect to the voice channel the user is in.

        Args:
            member: Discord member

        Returns:
            Tuple of (success, error_message)
        """
        if not member.voice or not member.voice.channel:
            return False, "You must be in a voice channel to use music commands"

        # Check if it's a voice channel (not stage channel)
        if not isinstance(member.voice.channel, discord.VoiceChannel):
            return False, "Bot can only connect to voice channels, not stage channels"

        voice_client = await self.voice_manager.connect_to_voice_channel(member.voice.channel)
        if not voice_client:
            return False, "Failed to connect to voice channel"

        return True, None

    async def skip_current_song(self, guild_id: int) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Skip the current song.

        Args:
            guild_id: Discord guild ID

        Returns:
            Tuple of (success, skipped_song_title, error_message)
        """
        try:
            queue_manager = self.get_queue_manager(guild_id)
            current_song = await queue_manager.get_current_song()

            if not current_song:
                return False, None, "No song is currently playing"

            # Stop current playback
            self.voice_manager.stop_audio(guild_id)

            # Clean up current audio file
            await self._cleanup_current_audio(guild_id)

            self.logger.info(f"Skipped song: {current_song.title}")
            return True, current_song.title, None

        except Exception as e:
            error_msg = f"Error skipping song: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    async def stop_playback(self, guild_id: int) -> tuple[bool, Optional[str]]:
        """
        Stop playback and clear the queue.

        Args:
            guild_id: Discord guild ID

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Stop audio playback
            self.voice_manager.stop_audio(guild_id)

            # Clear queue
            queue_manager = self.get_queue_manager(guild_id)
            cleared_count = await queue_manager.clear_queue()

            # Clean up audio file
            await self._cleanup_current_audio(guild_id)

            # Cancel playback task
            if guild_id in self._playback_tasks:
                self._playback_tasks[guild_id].cancel()
                del self._playback_tasks[guild_id]

            # Disconnect from voice
            await self.voice_manager.disconnect_from_guild(guild_id)

            self.logger.info(f"Stopped playback and cleared {cleared_count} songs from queue")
            return True, None

        except Exception as e:
            error_msg = f"Error stopping playback: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    async def jump_to_position(self, guild_id: int, position: int) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Jump to a specific position in the queue.

        Args:
            guild_id: Discord guild ID
            position: Queue position (1-indexed)

        Returns:
            Tuple of (success, song_title, error_message)
        """
        try:
            queue_manager = self.get_queue_manager(guild_id)

            # Stop current playback
            self.voice_manager.stop_audio(guild_id)

            # Clean up current audio file
            await self._cleanup_current_audio(guild_id)

            # Jump to position
            song = await queue_manager.jump_to_position(position)
            if not song:
                return False, None, f"Invalid queue position: {position}"

            self.logger.info(f"Jumped to position {position}: {song.title}")
            return True, song.title, None

        except Exception as e:
            error_msg = f"Error jumping to position {position}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    async def get_queue_info(self, guild_id: int) -> Dict[str, Any]:
        """
        Get comprehensive queue information.

        Args:
            guild_id: Discord guild ID

        Returns:
            Dictionary with queue details
        """
        queue_manager = self.get_queue_manager(guild_id)
        queue_info = await queue_manager.get_queue_info()

        # Add voice connection info
        voice_info = self.voice_manager.get_connection_info(guild_id)
        queue_info.update(voice_info)

        return queue_info

    def get_current_playback_position(self, guild_id: int) -> Optional[float]:
        """
        Get the current playback position in seconds.

        Args:
            guild_id: Discord guild ID

        Returns:
            Current position in seconds, or None if not playing
        """
        if guild_id not in self._playback_start_times:
            return None

        start_time = self._playback_start_times[guild_id]
        current_time = time.time()

        # Calculate elapsed time
        elapsed = current_time - start_time

        # Subtract any paused duration
        total_paused = self._total_paused_duration.get(guild_id, 0.0)

        # If currently paused, add the current pause duration
        if guild_id in self._playback_paused_times:
            current_pause_duration = current_time - self._playback_paused_times[guild_id]
            total_paused += current_pause_duration

        return max(0.0, elapsed - total_paused)

    def _start_playback_timing(self, guild_id: int) -> None:
        """
        Start tracking playback timing for a guild.

        Args:
            guild_id: Discord guild ID
        """
        self._playback_start_times[guild_id] = time.time()
        self._total_paused_duration[guild_id] = 0.0

        # Clear any existing pause state
        if guild_id in self._playback_paused_times:
            del self._playback_paused_times[guild_id]

    def _pause_playback_timing(self, guild_id: int) -> None:
        """
        Mark playback as paused for timing calculations.

        Args:
            guild_id: Discord guild ID
        """
        if guild_id in self._playback_start_times and guild_id not in self._playback_paused_times:
            self._playback_paused_times[guild_id] = time.time()

    def _resume_playback_timing(self, guild_id: int) -> None:
        """
        Resume playback timing after a pause.

        Args:
            guild_id: Discord guild ID
        """
        if guild_id in self._playback_paused_times:
            pause_start = self._playback_paused_times[guild_id]
            pause_duration = time.time() - pause_start

            # Add to total paused duration
            self._total_paused_duration[guild_id] = self._total_paused_duration.get(guild_id, 0.0) + pause_duration

            # Remove from paused state
            del self._playback_paused_times[guild_id]

    def _stop_playback_timing(self, guild_id: int) -> None:
        """
        Stop tracking playback timing for a guild.

        Args:
            guild_id: Discord guild ID
        """
        # Clean up timing state
        if guild_id in self._playback_start_times:
            del self._playback_start_times[guild_id]
        if guild_id in self._playback_paused_times:
            del self._playback_paused_times[guild_id]
        if guild_id in self._total_paused_duration:
            del self._total_paused_duration[guild_id]

    async def _start_playback(
        self,
        guild_id: int,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        """
        Start playback for a guild.

        Args:
            guild_id: Discord guild ID
            progress_callback: Optional progress callback
        """
        if guild_id in self._playback_tasks:
            return  # Already playing

        # Create playback task
        task = asyncio.create_task(self._playback_loop(guild_id, progress_callback))
        self._playback_tasks[guild_id] = task

    async def _playback_loop(
        self,
        guild_id: int,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        """
        Main playback loop for a guild.

        Args:
            guild_id: Discord guild ID
            progress_callback: Optional progress callback
        """
        queue_manager = self.get_queue_manager(guild_id)

        try:
            while True:
                # Get next song
                song = await queue_manager.get_next_song()
                if not song:
                    self.logger.debug(f"No more songs in queue for guild {guild_id}")
                    break

                # Download audio
                success, audio_info, error = await self.youtube_client.download_audio(
                    song.url, progress_callback
                )

                if not success or not audio_info:
                    self.logger.error(f"Failed to download audio for {song.title}: {error}")
                    continue

                # Store current audio file path
                self._current_audio_files[guild_id] = audio_info.file_path

                # Create audio source
                audio_source = discord.FFmpegPCMAudio(
                    audio_info.file_path,
                    options='-vn'  # No video
                )

                # Play audio
                playback_finished = asyncio.Event()

                def after_playback(error):
                    if error:
                        self.logger.error(f"Playback error: {error}")
                    playback_finished.set()

                success = await self.voice_manager.play_audio(
                    guild_id, audio_source, after_playback
                )

                if not success:
                    self.logger.error(f"Failed to start playback for {song.title}")
                    await self._cleanup_current_audio(guild_id)
                    continue

                # Start timing tracking
                self._start_playback_timing(guild_id)

                self.logger.info(f"Now playing: {song.title}")

                # Wait for playback to finish
                await playback_finished.wait()

                # Stop timing tracking
                self._stop_playback_timing(guild_id)

                # Clean up audio file
                await self._cleanup_current_audio(guild_id)

        except asyncio.CancelledError:
            self.logger.debug(f"Playback loop cancelled for guild {guild_id}")
        except Exception as e:
            self.logger.error(f"Error in playback loop for guild {guild_id}: {e}", exc_info=True)
        finally:
            # Clean up
            if guild_id in self._playback_tasks:
                del self._playback_tasks[guild_id]
            await self._cleanup_current_audio(guild_id)

    async def _cleanup_current_audio(self, guild_id: int) -> None:
        """
        Clean up the current audio file for a guild.

        Args:
            guild_id: Discord guild ID
        """
        if guild_id in self._current_audio_files:
            file_path = self._current_audio_files[guild_id]
            self.youtube_client.cleanup_file(file_path)
            del self._current_audio_files[guild_id]

    async def cleanup_all(self) -> None:
        """Clean up all resources."""
        self.logger.info("Cleaning up music player resources")

        # Cancel all playback tasks
        for task in self._playback_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self._playback_tasks:
            await asyncio.gather(*self._playback_tasks.values(), return_exceptions=True)

        # Clean up audio files
        for guild_id in list(self._current_audio_files.keys()):
            await self._cleanup_current_audio(guild_id)

        # Clean up voice connections
        await self.voice_manager.cleanup_all_connections()

        # Clear state
        self._playback_tasks.clear()
        self._current_audio_files.clear()
        self._queue_managers.clear()

        # Clear timing state
        self._playback_start_times.clear()
        self._playback_paused_times.clear()
        self._total_paused_duration.clear()
