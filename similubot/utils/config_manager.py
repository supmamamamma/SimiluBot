"""Configuration manager for SimiluBot."""
import logging
import os
from typing import Any, Dict, Optional
import yaml

class ConfigManager:
    """
    Configuration manager for SimiluBot.
    
    Handles loading and accessing configuration values from the config file.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the ConfigManager.
        
        Args:
            config_path: Path to the configuration file
        
        Raises:
            FileNotFoundError: If the configuration file does not exist
            yaml.YAMLError: If the configuration file is not valid YAML
        """
        self.logger = logging.getLogger("similubot.config")
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        self._load_config()
        
    def _load_config(self) -> None:
        """
        Load the configuration from the config file.
        
        Raises:
            FileNotFoundError: If the configuration file does not exist
            yaml.YAMLError: If the configuration file is not valid YAML
        """
        if not os.path.exists(self.config_path):
            example_path = f"{self.config_path}.example"
            if os.path.exists(example_path):
                self.logger.error(
                    f"Configuration file {self.config_path} not found. "
                    f"Please copy {example_path} to {self.config_path} and update it."
                )
            else:
                self.logger.error(f"Configuration file {self.config_path} not found.")
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as config_file:
                self.config = yaml.safe_load(config_file)
                self.logger.debug(f"Loaded configuration from {self.config_path}")
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key (dot notation for nested keys)
            default: Default value to return if the key is not found
            
        Returns:
            The configuration value or the default value if not found
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                self.logger.debug(f"Configuration key '{key}' not found, using default: {default}")
                return default
                
        return value
    
    def get_discord_token(self) -> str:
        """
        Get the Discord bot token.
        
        Returns:
            The Discord bot token
            
        Raises:
            ValueError: If the Discord bot token is not set
        """
        token = self.get('discord.token')
        if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
            self.logger.error("Discord bot token not set in configuration")
            raise ValueError("Discord bot token not set in configuration")
        return token
    
    def get_download_temp_dir(self) -> str:
        """
        Get the temporary directory for downloads.
        
        Returns:
            The temporary directory path
        """
        return self.get('download.temp_dir', './temp')
    
    def get_default_bitrate(self) -> int:
        """
        Get the default AAC bitrate.
        
        Returns:
            The default bitrate in kbps
        """
        return self.get('conversion.default_bitrate', 128)
    
    def get_supported_formats(self) -> list:
        """
        Get the list of supported input formats.
        
        Returns:
            List of supported format extensions
        """
        return self.get('conversion.supported_formats', [
            'mp4', 'mp3', 'avi', 'mkv', 'wav', 'flac', 'ogg', 'webm'
        ])
    
    def get_default_upload_service(self) -> str:
        """
        Get the default upload service.
        
        Returns:
            The default upload service name
        """
        return self.get('upload.default_service', 'catbox')
    
    def get_catbox_user_hash(self) -> Optional[str]:
        """
        Get the CatBox user hash.
        
        Returns:
            The CatBox user hash or None if not set
        """
        return self.get('upload.catbox.user_hash', None)
    
    def get_log_level(self) -> str:
        """
        Get the logging level.
        
        Returns:
            The logging level
        """
        return self.get('logging.level', 'INFO')
    
    def get_log_file(self) -> Optional[str]:
        """
        Get the log file path.
        
        Returns:
            The log file path or None if not set
        """
        return self.get('logging.file', None)
    
    def get_log_max_size(self) -> int:
        """
        Get the maximum log file size.
        
        Returns:
            The maximum log file size in bytes
        """
        return self.get('logging.max_size', 10485760)  # 10 MB
    
    def get_log_backup_count(self) -> int:
        """
        Get the number of backup log files to keep.
        
        Returns:
            The number of backup log files
        """
        return self.get('logging.backup_count', 5)
