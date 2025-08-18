# Psychosonus - Discord Music Bot

A modular Discord music bot with web dashboard interface for streaming music from YouTube and Spotify.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the bot:**
   ```bash
   cp config.json.example config.json
   # Edit config.json with your Discord token and Spotify credentials
   ```

3. **Run the bot:**
   ```bash
   python main.py
   ```

4. **Access web dashboard:**
   ```
   http://localhost:8888
   ```

## File Structure

```
psychosonus/
├── main.py                   # Main entry point
├── config.py                 # Configuration management
├── models.py                 # Data models (Song class)
├── queue_manager.py          # Thread-safe music queue
├── discord_bot.py           # Discord bot functionality
├── youtube_manager.py       # YouTube search and audio extraction
├── web_interface.py         # Flask web API and routes
├── search.py                # Spotify integration
├── requirements.txt         # Python dependencies
├── config.json.example      # Configuration template
└── static/
    └── dashboard.html       # Web dashboard interface
```

## Features

- 🎵 Discord music bot with voice channel support
- 🌐 Modern web dashboard for remote control
- 🔍 Multi-platform search (Spotify + YouTube)
- 📋 Queue management with add/remove/clear
- ⏯️ Playback controls (play, pause, skip, stop)
- 🔄 Auto-advance through queue
- 📱 Mobile-responsive web interface

## Commands

- `!join` - Join voice channel
- `!play <song>` - Search and play music
- `!queue` - Show current queue
- `!skip` - Skip current song
- `!stop` - Stop and clear queue
- `!leave` - Leave voice channel

## Architecture

The bot is now modular with separate files for different responsibilities:

- **main.py**: Entry point and application lifecycle
- **config.py**: Configuration loading and validation
- **models.py**: Data structures (Song class)
- **queue_manager.py**: Thread-safe queue operations
- **discord_bot.py**: Discord commands and voice functionality
- **youtube_manager.py**: YouTube search and audio extraction
- **web_interface.py**: Flask web server and API endpoints
- **search.py**: Spotify API integration

This modular design makes the code easier to maintain, test, and extend.