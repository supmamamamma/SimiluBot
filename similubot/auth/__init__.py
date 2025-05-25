"""Authorization module for SimiluBot."""

from .authorization_manager import AuthorizationManager
from .permission_types import (
    PermissionLevel,
    ModulePermission,
    UserPermissions,
    get_command_module,
    get_feature_module
)
from .unauthorized_handler import UnauthorizedAccessHandler

__all__ = [
    "AuthorizationManager",
    "PermissionLevel",
    "ModulePermission",
    "UserPermissions",
    "get_command_module",
    "get_feature_module",
    "UnauthorizedAccessHandler"
]




