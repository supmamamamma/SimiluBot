#!/usr/bin/env python3
"""
SimiluBot - Discord bot for downloading MEGA links and converting media to AAC format.
"""
import logging
from similubot.bot import SimiluBot
from similubot.utils.config_manager import ConfigManager
from similubot.utils.logger import setup_logger

def main():
    """Main entry point for the SimiluBot application."""
    # Set up logging
    setup_logger()
    logger = logging.getLogger("similubot")
    
    try:
        # Load configuration
        config = ConfigManager()
        
        # Initialize and run the bot
        bot = SimiluBot(config)
        logger.info("Starting SimiluBot...")
        bot.run()
    except Exception as e:
        logger.error(f"Error starting SimiluBot: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
