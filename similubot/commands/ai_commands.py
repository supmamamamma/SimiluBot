"""AI conversation commands for SimiluBot."""

import logging
import re
from typing import Optional, Tuple
import discord
from discord.ext import commands

from similubot.core.command_registry import CommandRegistry
from similubot.ai.ai_client import AIClient
from similubot.ai.conversation_memory import ConversationMemory
from similubot.ai.ai_tracker import AITracker
from similubot.progress.discord_updater import DiscordProgressUpdater
from similubot.utils.config_manager import ConfigManager


class AICommands:
    """
    AI conversation command handler for SimiluBot.

    Provides AI conversation functionality with:
    - Default conversation mode
    - Danbooru tag generation mode
    - Conversation memory management
    - Progress tracking for AI operations
    """

    def __init__(self, config: ConfigManager):
        """
        Initialize AI commands.

        Args:
            config: Configuration manager instance
        """
        self.logger = logging.getLogger("similubot.commands.ai")
        self.config = config

        # Initialize AI components if configured
        if config.is_ai_configured():
            try:
                self.ai_client = AIClient(config)
                self.conversation_memory = ConversationMemory(config)
                self._available = True
                self.logger.info("AI commands initialized successfully")
            except ValueError as e:
                self.logger.warning(f"AI initialization failed: {e}")
                self.ai_client = None
                self.conversation_memory = None
                self._available = False
        else:
            self.logger.info("AI not configured, commands will be unavailable")
            self.ai_client = None
            self.conversation_memory = None
            self._available = False

    def is_available(self) -> bool:
        """
        Check if AI commands are available.

        Returns:
            True if AI is configured and available, False otherwise
        """
        return self._available and self.ai_client is not None

    def register_commands(self, registry: CommandRegistry) -> None:
        """
        Register AI commands with the command registry.

        Args:
            registry: Command registry instance
        """
        if not self.is_available():
            self.logger.info("AI commands not registered (not configured)")
            return

        usage_examples = [
            "!ai - Show AI help and available modes",
            "!ai Hello, how are you? - Start a conversation with the AI",
            "!ai What is the weather like? - Ask the AI a question",
            "!ai mode:danbooru anime girl with blue hair - Generate Danbooru tags for image description",
            "!ai set:provider openrouter - Switch to OpenRouter provider",
            "!ai set:model anthropic/claude-3.5-sonnet - Change model for current provider"
        ]

        help_text = (
            "Interact with AI for conversations and assistance. "
            "Supports conversation memory and specialized modes like Danbooru tag generation. "
            f"Conversations timeout after {self.config.get_ai_conversation_timeout() // 60} minutes of inactivity."
        )

        registry.register_command(
            name="ai",
            callback=self.ai_command,
            description="AI conversation and assistance",
            required_permission="ai_conversation",
            usage_examples=usage_examples,
            help_text=help_text
        )

        self.logger.debug("AI commands registered")

    async def ai_command(self, ctx: commands.Context, *, args: str = "") -> None:
        """
        Handle AI conversation command.

        Usage:
            !ai - Show help message
            !ai <prompt> - Default AI conversation
            !ai <prompt> [mode:danbooru] - AI with Danbooru tag generation mode

        Args:
            ctx: Discord command context
            args: Command arguments (prompt and optional mode)
        """
        if not self.is_available():
            await ctx.reply("❌ AI functionality is not configured. Please check your .env file.")
            return

        # Show help if no arguments provided
        if not args.strip():
            await self._show_ai_help(ctx)
            return

        # Check for set commands first
        if args.strip().startswith("set:"):
            await self._handle_set_command(ctx, args.strip())
            return

        # Parse arguments for mode and prompt
        mode, prompt = self._parse_ai_arguments(args)

        if not prompt.strip():
            await ctx.reply("❌ Please provide a prompt for the AI.")
            return

        self.logger.info(f"AI command invoked by {ctx.author} in mode '{mode}': {len(prompt)} characters")

        # Process AI conversation
        await self._process_ai_conversation(ctx, prompt, mode)

    def _parse_ai_arguments(self, args: str) -> Tuple[str, str]:
        """
        Parse AI command arguments to extract mode and prompt.

        Args:
            args: Raw command arguments

        Returns:
            Tuple of (mode, prompt)
        """
        # Look for mode specification: mode:danbooru
        mode_pattern = r'\bmode:(\w+)\b'
        mode_match = re.search(mode_pattern, args, re.IGNORECASE)

        if mode_match:
            mode = mode_match.group(1).lower()
            # Remove mode specification from prompt
            prompt = re.sub(mode_pattern, '', args, flags=re.IGNORECASE).strip()
        else:
            mode = "default"
            prompt = args.strip()

        # Validate mode
        if mode not in ["default", "danbooru"]:
            self.logger.warning(f"Invalid AI mode specified: {mode}, defaulting to 'default'")
            mode = "default"

        return mode, prompt

    async def _handle_set_command(self, ctx: commands.Context, args: str) -> None:
        """
        Handle AI set commands for changing providers and models.

        Args:
            ctx: Discord command context
            args: Command arguments starting with "set:"
        """
        # Parse set command: set:provider value or set:model value
        parts = args.split(" ", 1)
        if len(parts) < 2:
            await ctx.reply("❌ Please specify a value. Usage: `!ai set:provider <name>` or `!ai set:model <name>`")
            return

        set_command = parts[0]
        value = parts[1].strip()

        if set_command == "set:provider":
            await self._set_ai_provider(ctx, value)
        elif set_command == "set:model":
            await self._set_ai_model(ctx, value)
        else:
            await ctx.reply("❌ Unknown set command. Use `set:provider` or `set:model`.")

    async def _set_ai_provider(self, ctx: commands.Context, provider: str) -> None:
        """
        Set the default AI provider.

        Args:
            ctx: Discord command context
            provider: Provider name to set
        """
        try:
            # Get available providers
            available_providers = self.config.get_available_ai_providers()

            if provider not in available_providers:
                embed = discord.Embed(
                    title="❌ Invalid AI Provider",
                    description=f"Provider '{provider}' is not available.",
                    color=0xe74c3c
                )
                embed.add_field(
                    name="Available Providers",
                    value="\n".join(f"• {p}" for p in available_providers) if available_providers else "None configured",
                    inline=False
                )
                await ctx.reply(embed=embed)
                return

            # Set the provider
            success = self.config.set_ai_provider(provider)

            if success:
                # Reinitialize AI client with new provider
                try:
                    self.ai_client = AIClient(self.config)

                    embed = discord.Embed(
                        title="✅ AI Provider Updated",
                        description=f"Successfully switched to **{provider}**",
                        color=0x2ecc71
                    )

                    # Show provider info
                    provider_info = self.ai_client.get_provider_info()
                    embed.add_field(
                        name="Current Configuration",
                        value=f"**Model:** {provider_info['model']}\n**Provider:** {provider_info['provider']}",
                        inline=False
                    )

                    await ctx.reply(embed=embed)
                    self.logger.info(f"AI provider changed to {provider} by {ctx.author}")

                except Exception as e:
                    await ctx.reply(f"❌ Failed to initialize new provider: {str(e)}")
                    self.logger.error(f"Failed to reinitialize AI client after provider change: {e}")
            else:
                await ctx.reply(f"❌ Failed to set AI provider to '{provider}'.")

        except Exception as e:
            await ctx.reply(f"❌ Error setting AI provider: {str(e)}")
            self.logger.error(f"Error in _set_ai_provider: {e}", exc_info=True)

    async def _set_ai_model(self, ctx: commands.Context, model: str) -> None:
        """
        Set the model for the current AI provider.

        Args:
            ctx: Discord command context
            model: Model name to set
        """
        try:
            current_provider = self.config.get_default_ai_provider()

            # Set the model
            success = self.config.set_ai_model(current_provider, model)

            if success:
                # Reinitialize AI client with new model
                try:
                    self.ai_client = AIClient(self.config)

                    embed = discord.Embed(
                        title="✅ AI Model Updated",
                        description=f"Successfully changed model for **{current_provider}**",
                        color=0x2ecc71
                    )

                    # Show updated info
                    provider_info = self.ai_client.get_provider_info()
                    embed.add_field(
                        name="Current Configuration",
                        value=f"**Model:** {provider_info['model']}\n**Provider:** {provider_info['provider']}",
                        inline=False
                    )

                    await ctx.reply(embed=embed)
                    self.logger.info(f"AI model changed to {model} for {current_provider} by {ctx.author}")

                except Exception as e:
                    await ctx.reply(f"❌ Failed to initialize with new model: {str(e)}")
                    self.logger.error(f"Failed to reinitialize AI client after model change: {e}")
            else:
                await ctx.reply(f"❌ Failed to set model '{model}' for provider '{current_provider}'.")

        except Exception as e:
            await ctx.reply(f"❌ Error setting AI model: {str(e)}")
            self.logger.error(f"Error in _set_ai_model: {e}", exc_info=True)

    async def _show_ai_help(self, ctx: commands.Context) -> None:
        """
        Show AI help message.

        Args:
            ctx: Discord command context
        """
        embed = discord.Embed(
            title="🤖 AI Assistant Help",
            description="Interact with AI for conversations and specialized assistance",
            color=0x00ff88
        )

        # Provider information
        if self.ai_client:
            provider_info = self.ai_client.get_provider_info()
            embed.add_field(
                name="Current Provider",
                value=f"**Provider:** {provider_info['provider']}\n**Model:** {provider_info['model']}",
                inline=True
            )

        # Usage examples
        embed.add_field(
            name="Basic Usage",
            value=(
                f"`{ctx.bot.command_prefix}ai Hello!` - Start a conversation\n"
                f"`{ctx.bot.command_prefix}ai What is Python?` - Ask questions\n"
                f"`{ctx.bot.command_prefix}ai Tell me a joke` - Request content"
            ),
            inline=False
        )

        # Danbooru mode
        embed.add_field(
            name="Danbooru Tag Mode",
            value=(
                f"`{ctx.bot.command_prefix}ai mode:danbooru anime girl with blue hair` - Generate Danbooru tags\n"
                "Perfect for creating image generation prompts!"
            ),
            inline=False
        )

        # Configuration commands
        embed.add_field(
            name="Configuration",
            value=(
                f"`{ctx.bot.command_prefix}ai set:provider <name>` - Switch AI provider\n"
                f"`{ctx.bot.command_prefix}ai set:model <name>` - Change model for current provider"
            ),
            inline=False
        )

        # Features
        embed.add_field(
            name="Features",
            value=(
                "✅ Conversation memory (30 minutes)\n"
                "✅ Multiple AI providers\n"
                "✅ Specialized modes\n"
                "✅ Real-time progress tracking"
            ),
            inline=True
        )

        # Statistics
        if self.conversation_memory:
            stats = self.conversation_memory.get_conversation_stats()
            embed.add_field(
                name="Current Stats",
                value=(
                    f"**Active conversations:** {stats['active_conversations']}\n"
                    f"**Total messages:** {stats['total_messages']}"
                ),
                inline=True
            )

        embed.set_footer(text="SimiluBot AI Assistant")
        await ctx.send(embed=embed)

    async def _process_ai_conversation(self, ctx: commands.Context, prompt: str, mode: str) -> None:
        """
        Process AI conversation with progress tracking.

        Args:
            ctx: Discord command context
            prompt: User prompt
            mode: Conversation mode (default, danbooru)
        """
        # Ensure AI components are available
        if not self.ai_client or not self.conversation_memory:
            await ctx.reply("❌ AI functionality is not available.")
            return

        user_id = ctx.author.id

        # Create progress tracker
        tracker = AITracker(f"AI {mode.title()} Generation")

        # Send initial progress message
        progress_message = await ctx.send("🤖 Starting AI conversation...")

        # Create Discord progress updater
        progress_updater = DiscordProgressUpdater(
            progress_message,
            update_interval=2.0  # Update every 2 seconds
        )

        # Add progress callback
        tracker.add_callback(progress_updater.create_callback())

        try:
            # Start tracking
            tracker.start_request(len(prompt), estimated_response_tokens=500)

            # Add user message to conversation memory
            self.conversation_memory.add_user_message(user_id, prompt, mode)

            # Get conversation messages
            messages = self.conversation_memory.get_conversation_messages(user_id, mode)

            # Get system prompt for the mode
            system_prompt = None
            if mode == "danbooru":
                system_prompt = self.config.get_ai_danbooru_system_prompt()
            else:
                system_prompt = self.config.get_ai_default_system_prompt()

            # Start response generation
            tracker.start_response_generation()

            # Generate AI response
            response = await self.ai_client.generate_response(
                messages=messages,
                system_prompt=system_prompt
            )

            # Complete tracking
            tracker.complete_generation(response, len(response.split()))

            # Add assistant response to memory
            self.conversation_memory.add_assistant_message(user_id, response)

            # Send response and delete progress message
            await self._send_ai_response(ctx, response, mode)
            await progress_message.delete()

        except Exception as e:
            self.logger.error(f"AI conversation failed: {e}", exc_info=True)
            tracker.fail_generation(str(e))
            await progress_message.delete()
            await ctx.reply(f"❌ AI conversation failed: {str(e)}")

    async def _send_ai_response(self, ctx: commands.Context, response: str, mode: str) -> None:
        """
        Send AI response to Discord with appropriate formatting.

        Args:
            ctx: Discord command context
            response: AI response text
            mode: Conversation mode
        """
        # Truncate response if too long for Discord
        max_length = 1900  # Leave room for embed formatting
        if len(response) > max_length:
            response = response[:max_length] + "..."
            self.logger.warning(f"AI response truncated to {max_length} characters")

        # Create embed based on mode
        if mode == "danbooru":
            embed = discord.Embed(
                title="🏷️ Danbooru Tags Generated",
                description=f"```\n{response}\n```",
                color=0xff6b9d
            )
            embed.set_footer(text="Copy these tags for image generation!")
        else:
            embed = discord.Embed(
                title="🤖 AI Assistant",
                description=response,
                color=0x00ff88
            )
            embed.set_footer(text=f"Conversation continues for {self.config.get_ai_conversation_timeout() // 60} minutes")

        await ctx.reply(embed=embed)

    def get_command_count(self) -> int:
        """
        Get the number of registered AI commands.

        Returns:
            Number of commands registered by this module
        """
        return 1 if self.is_available() else 0

    async def shutdown(self) -> None:
        """Shutdown AI commands and clean up resources."""
        if self.conversation_memory:
            await self.conversation_memory.shutdown()

        if self.ai_client:
            await self.ai_client.close()

        self.logger.info("AI commands shut down")
