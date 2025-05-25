"""Command registry system for SimiluBot."""
import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
import discord
from discord.ext import commands

from similubot.auth.authorization_manager import AuthorizationManager
from similubot.auth.unauthorized_handler import UnauthorizedAccessHandler


@dataclass
class CommandInfo:
    """Information about a registered command."""
    name: str
    callback: Callable
    description: str
    required_permission: Optional[str] = None
    admin_only: bool = False


class CommandRegistry:
    """
    Registry for managing bot commands with authorization integration.
    
    Provides a centralized way to register commands with automatic
    authorization checking and consistent error handling.
    """

    def __init__(self, bot: commands.Bot, auth_manager: AuthorizationManager, 
                 unauthorized_handler: UnauthorizedAccessHandler):
        """
        Initialize the command registry.

        Args:
            bot: Discord bot instance
            auth_manager: Authorization manager
            unauthorized_handler: Unauthorized access handler
        """
        self.logger = logging.getLogger("similubot.command_registry")
        self.bot = bot
        self.auth_manager = auth_manager
        self.unauthorized_handler = unauthorized_handler
        self._commands: Dict[str, CommandInfo] = {}
        self._command_groups: Dict[str, List[CommandInfo]] = {}

    def register_command(
        self,
        name: str,
        callback: Callable,
        description: str,
        required_permission: Optional[str] = None,
        admin_only: bool = False
    ) -> None:
        """
        Register a command with the bot.

        Args:
            name: Command name
            callback: Command callback function
            description: Command description
            required_permission: Required permission (command name or feature name)
            admin_only: Whether command requires admin privileges
        """
        command_info = CommandInfo(
            name=name,
            callback=callback,
            description=description,
            required_permission=required_permission,
            admin_only=admin_only
        )
        
        self._commands[name] = command_info
        
        # Create wrapped command with authorization
        wrapped_callback = self._wrap_command_with_auth(command_info)
        
        # Register with Discord.py
        command = commands.Command(wrapped_callback, name=name, help=description)
        self.bot.add_command(command)
        
        self.logger.debug(f"Registered command: {name}")

    def register_command_group(
        self,
        name: str,
        description: str,
        admin_only: bool = True
    ) -> commands.Group:
        """
        Register a command group with the bot.

        Args:
            name: Group name
            description: Group description
            admin_only: Whether group requires admin privileges

        Returns:
            Discord command group
        """
        async def group_callback(ctx):
            """Default group callback."""
            if admin_only and not self.auth_manager.is_admin(ctx.author.id):
                await ctx.reply("❌ You don't have permission to use these commands.")
                return
            
            # Show group help
            await ctx.send_help(ctx.command)

        # Create wrapped group callback with authorization
        if admin_only:
            wrapped_callback = self._wrap_admin_command(group_callback)
        else:
            wrapped_callback = group_callback

        group = commands.Group(wrapped_callback, name=name, help=description, invoke_without_command=True)
        self.bot.add_command(group)
        
        self._command_groups[name] = []
        self.logger.debug(f"Registered command group: {name}")
        
        return group

    def register_group_command(
        self,
        group: commands.Group,
        name: str,
        callback: Callable,
        description: str,
        admin_only: bool = True
    ) -> None:
        """
        Register a command within a group.

        Args:
            group: Parent command group
            name: Command name
            callback: Command callback function
            description: Command description
            admin_only: Whether command requires admin privileges
        """
        command_info = CommandInfo(
            name=f"{group.name}.{name}",
            callback=callback,
            description=description,
            admin_only=admin_only
        )
        
        # Create wrapped command with authorization
        if admin_only:
            wrapped_callback = self._wrap_admin_command(callback)
        else:
            wrapped_callback = callback
        
        # Register with group
        command = commands.Command(wrapped_callback, name=name, help=description)
        group.add_command(command)
        
        # Track in registry
        if group.name in self._command_groups:
            self._command_groups[group.name].append(command_info)
        
        self.logger.debug(f"Registered group command: {group.name}.{name}")

    def _wrap_command_with_auth(self, command_info: CommandInfo) -> Callable:
        """
        Wrap a command callback with authorization checking.

        Args:
            command_info: Command information

        Returns:
            Wrapped callback function
        """
        async def wrapped_callback(ctx, *args, **kwargs):
            try:
                # Check admin-only commands
                if command_info.admin_only:
                    if not self.auth_manager.is_admin(ctx.author.id):
                        await self.unauthorized_handler.handle_unauthorized_access(
                            user=ctx.author,
                            command_name=command_info.name,
                            channel=ctx.channel
                        )
                        return

                # Check permission-based commands
                elif command_info.required_permission:
                    if not self.auth_manager.is_authorized(
                        ctx.author.id, 
                        command_name=command_info.required_permission
                    ):
                        await self.unauthorized_handler.handle_unauthorized_access(
                            user=ctx.author,
                            command_name=command_info.required_permission,
                            channel=ctx.channel
                        )
                        return

                # Execute the original command
                await command_info.callback(ctx, *args, **kwargs)

            except Exception as e:
                self.logger.error(f"Error in command {command_info.name}: {e}", exc_info=True)
                await ctx.reply(f"❌ An error occurred while executing the command: {str(e)}")

        # Preserve function metadata
        wrapped_callback.__name__ = command_info.callback.__name__
        wrapped_callback.__doc__ = command_info.callback.__doc__
        
        return wrapped_callback

    def _wrap_admin_command(self, callback: Callable) -> Callable:
        """
        Wrap a command callback with admin authorization checking.

        Args:
            callback: Original callback function

        Returns:
            Wrapped callback function
        """
        async def wrapped_callback(ctx, *args, **kwargs):
            try:
                # Check admin privileges
                if not self.auth_manager.is_admin(ctx.author.id):
                    await ctx.reply("❌ You don't have permission to use this command.")
                    return

                # Execute the original command
                await callback(ctx, *args, **kwargs)

            except Exception as e:
                self.logger.error(f"Error in admin command: {e}", exc_info=True)
                await ctx.reply(f"❌ An error occurred while executing the command: {str(e)}")

        # Preserve function metadata
        wrapped_callback.__name__ = callback.__name__
        wrapped_callback.__doc__ = callback.__doc__
        
        return wrapped_callback

    def get_registered_commands(self) -> Dict[str, CommandInfo]:
        """
        Get all registered commands.

        Returns:
            Dictionary of command name to CommandInfo
        """
        return self._commands.copy()

    def get_command_groups(self) -> Dict[str, List[CommandInfo]]:
        """
        Get all registered command groups.

        Returns:
            Dictionary of group name to list of CommandInfo
        """
        return self._command_groups.copy()

    def is_command_registered(self, name: str) -> bool:
        """
        Check if a command is registered.

        Args:
            name: Command name

        Returns:
            True if command is registered, False otherwise
        """
        return name in self._commands
