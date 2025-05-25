"""Unauthorized access handler for SimiluBot."""
import logging
from typing import List, Optional
import discord

from .authorization_manager import AuthorizationManager
from .permission_types import ModulePermission


class UnauthorizedAccessHandler:
    """
    Handles unauthorized access attempts and admin notifications.
    """

    def __init__(self, auth_manager: AuthorizationManager, bot: discord.Client):
        """
        Initialize the unauthorized access handler.

        Args:
            auth_manager: Authorization manager instance
            bot: Discord bot client
        """
        self.logger = logging.getLogger("similubot.auth.unauthorized")
        self.auth_manager = auth_manager
        self.bot = bot

    async def handle_unauthorized_access(
        self,
        user: discord.User,
        command_name: Optional[str] = None,
        feature_name: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None
    ) -> None:
        """
        Handle an unauthorized access attempt.

        Args:
            user: Discord user who attempted unauthorized access
            command_name: Name of the command attempted (optional)
            feature_name: Name of the feature attempted (optional)
            channel: Discord channel where the attempt occurred (optional)
        """
        # Log the unauthorized access attempt
        access_type = command_name or feature_name or "unknown"
        self.logger.warning(
            f"Unauthorized access attempt by {user.display_name} ({user.id}) "
            f"for {access_type} in channel {channel.name if channel else 'DM'}"
        )

        # Send public unauthorized message
        if channel:
            await self._send_public_unauthorized_message(channel, user, command_name, feature_name)

        # Send admin notification if enabled
        if self.auth_manager.notify_admins_on_unauthorized:
            await self._send_admin_notification(user, command_name, feature_name, channel)

    async def _send_public_unauthorized_message(
        self,
        channel: discord.TextChannel,
        user: discord.User,
        command_name: Optional[str] = None,
        feature_name: Optional[str] = None
    ) -> None:
        """
        Send a public unauthorized access message to the channel.

        Args:
            channel: Discord channel to send message to
            user: User who attempted unauthorized access
            command_name: Command that was attempted
            feature_name: Feature that was attempted
        """
        try:
            # Determine what was attempted
            if command_name:
                attempted_action = f"command `{command_name}`"
            elif feature_name:
                attempted_action = f"feature `{feature_name}`"
            else:
                attempted_action = "this action"

            embed = discord.Embed(
                title="🚫 Unauthorized Access",
                description=f"{user.mention}, you don't have permission to use {attempted_action}.",
                color=0xe74c3c
            )
            
            embed.add_field(
                name="Need Access?",
                value="Contact a server administrator to request permissions.",
                inline=False
            )
            
            embed.set_footer(text="SimiluBot Authorization System")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error sending public unauthorized message: {e}")

    async def _send_admin_notification(
        self,
        user: discord.User,
        command_name: Optional[str] = None,
        feature_name: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None
    ) -> None:
        """
        Send notification to administrators about unauthorized access attempt.

        Args:
            user: User who attempted unauthorized access
            command_name: Command that was attempted
            feature_name: Feature that was attempted
            channel: Channel where attempt occurred
        """
        try:
            # Get admin users
            admin_ids = self.auth_manager.admin_ids
            if not admin_ids:
                return

            # Create notification embed
            embed = await self._create_admin_notification_embed(user, command_name, feature_name, channel)
            
            # Send to each admin
            for admin_id in admin_ids:
                try:
                    admin_user = await self.bot.fetch_user(int(admin_id))
                    if admin_user:
                        await admin_user.send(embed=embed)
                        self.logger.debug(f"Sent unauthorized access notification to admin {admin_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to send notification to admin {admin_id}: {e}")

        except Exception as e:
            self.logger.error(f"Error sending admin notifications: {e}")

    async def _create_admin_notification_embed(
        self,
        user: discord.User,
        command_name: Optional[str] = None,
        feature_name: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None
    ) -> discord.Embed:
        """
        Create an admin notification embed for unauthorized access.

        Args:
            user: User who attempted unauthorized access
            command_name: Command that was attempted
            feature_name: Feature that was attempted
            channel: Channel where attempt occurred

        Returns:
            Discord embed for admin notification
        """
        # Determine what was attempted
        if command_name:
            attempted_action = f"Command: `{command_name}`"
            required_module = self._get_command_module_name(command_name)
        elif feature_name:
            attempted_action = f"Feature: `{feature_name}`"
            required_module = self._get_feature_module_name(feature_name)
        else:
            attempted_action = "Unknown action"
            required_module = "Unknown"

        embed = discord.Embed(
            title="🚨 Unauthorized Access Attempt",
            description=f"User attempted to access restricted functionality",
            color=0xff9500,
            timestamp=discord.utils.utcnow()
        )

        # User information
        embed.add_field(
            name="👤 User",
            value=f"{user.display_name}\n`{user.name}`\nID: `{user.id}`",
            inline=True
        )

        # Attempted action
        embed.add_field(
            name="🎯 Attempted Action",
            value=f"{attempted_action}\nRequired: `{required_module}`",
            inline=True
        )

        # Location
        if channel:
            embed.add_field(
                name="📍 Location",
                value=f"#{channel.name}\nServer: {channel.guild.name if channel.guild else 'DM'}",
                inline=True
            )
        else:
            embed.add_field(
                name="📍 Location",
                value="Direct Message",
                inline=True
            )

        # User avatar
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)

        # Quick actions
        embed.add_field(
            name="⚡ Quick Actions",
            value=(
                f"**Grant Full Access:**\n"
                f"`!auth add {user.id} full`\n\n"
                f"**Grant Module Access:**\n"
                f"`!auth add {user.id} module {required_module.lower()}`\n\n"
                f"**View User Info:**\n"
                f"`!auth user {user.id}`"
            ),
            inline=False
        )

        embed.set_footer(text="SimiluBot Authorization System")

        return embed

    def _get_command_module_name(self, command_name: str) -> str:
        """Get human-readable module name for a command."""
        from .permission_types import get_command_module
        
        module = get_command_module(command_name)
        module_names = {
            ModulePermission.MEGA_DOWNLOAD: "MEGA Download",
            ModulePermission.NOVELAI_GENERATION: "NovelAI Generation",
            ModulePermission.GENERAL_COMMANDS: "General Commands"
        }
        return module_names.get(module, "Unknown Module")

    def _get_feature_module_name(self, feature_name: str) -> str:
        """Get human-readable module name for a feature."""
        from .permission_types import get_feature_module
        
        module = get_feature_module(feature_name)
        module_names = {
            ModulePermission.MEGA_DOWNLOAD: "MEGA Download",
            ModulePermission.NOVELAI_GENERATION: "NovelAI Generation",
            ModulePermission.GENERAL_COMMANDS: "General Commands"
        }
        return module_names.get(module, "Unknown Module")

    async def send_permission_denied_dm(self, user: discord.User, reason: str = "") -> bool:
        """
        Send a private message to user about permission denial.

        Args:
            user: User to send message to
            reason: Optional reason for denial

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            embed = discord.Embed(
                title="🚫 Access Denied",
                description="You don't have permission to use this bot feature.",
                color=0xe74c3c
            )
            
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            
            embed.add_field(
                name="Need Access?",
                value="Contact a server administrator to request permissions for this bot.",
                inline=False
            )
            
            embed.set_footer(text="SimiluBot Authorization System")
            
            await user.send(embed=embed)
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to send permission denied DM to {user.id}: {e}")
            return False
