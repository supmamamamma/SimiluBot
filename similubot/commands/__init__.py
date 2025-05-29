"""Command modules for SimiluBot."""

from .mega_commands import MegaCommands
from .novelai_commands import NovelAICommands
from .auth_commands import AuthCommands
from .general_commands import GeneralCommands
from .ai_commands import AICommands
from .music_commands import MusicCommands

__all__ = [
    "MegaCommands",
    "NovelAICommands",
    "AuthCommands",
    "GeneralCommands",
    "AICommands",
    "MusicCommands"
]
