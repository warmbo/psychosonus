#!/usr/bin/env python3
"""
Psychosonus - Discord Music Bot
Main entry point
"""

import logging
import threading

from config import Config
from discord_bot import MusicBot
from web_interface import WebInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function"""
    try:
        # Load configuration
        config = Config()
        
        # Create bot instance
        bot = MusicBot(config)
        
        # Create web interface
        web_interface = WebInterface(bot, config)
        
        # Start Flask in separate thread
        flask_thread = threading.Thread(target=web_interface.run, daemon=True)
        flask_thread.start()
        
        # Start Discord bot
        bot.run(config.get('discord_token'))
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()