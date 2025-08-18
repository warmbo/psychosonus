# Psychosonus - Discord Music Bot

A modular Discord music bot with Discord OAuth2 authentication and web dashboard interface for streaming music from YouTube and Spotify. Only Discord server members can control the bot's queue.

## Features

- 🎵 Discord music bot with voice channel support
- 🔐 Discord OAuth2 authentication for web dashboard
- 🌐 Modern web dashboard for remote control
- 🔍 Multi-platform search (Spotify + YouTube)
- 📋 Queue management with add/remove/clear
- ⏯️ Playback controls (play, pause, skip, stop)
- 🔄 Auto-advance through queue
- 📱 Mobile-responsive web interface
- 🛡️ Server-specific access control

## Quick Start

### 1. Discord Application Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to **Bot** section:
   - Create a bot
   - Copy the **Token** (for `discord_token`)
   - Enable "Message Content Intent"
4. Go to **OAuth2** section:
   - Copy **Client ID** and **Client Secret** (for Discord OAuth)
   - Add redirect URI: `http://localhost:8888/auth/callback`

### 2. Spotify Setup (Optional)

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app
3. Copy **Client ID** and **Client Secret**
4. Add redirect URI: `http://localhost:8888/callback/spotify`

### 3. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/psychosonus.git
cd psychosonus

# Install dependencies
pip install -r requirements.txt

# Configure the bot
cp config.json.example config.json
# Edit config.json with your tokens and credentials
```

### 4. Configuration

Edit `config.json`:

```json
{
  "discord_token": "YOUR_DISCORD_BOT_TOKEN",
  "discord_client_id": "YOUR_DISCORD_CLIENT_ID", 
  "discord_client_secret": "YOUR_DISCORD_CLIENT_SECRET",
  "spotify_client_id": "YOUR_SPOTIFY_CLIENT_ID",
  "spotify_client_secret": "YOUR_SPOTIFY_CLIENT_SECRET",
  "web_port": 8888,
  "command_prefix": "!",
  "max_queue_size": 100,
  "default_volume": 0.5,
  "session_secret": "RANDOM_SECRET_KEY_FOR_JWT_SESSIONS",
  "github_repo": "https://github.com/yourusername/psychosonus"
}
```

### 5. Run the Bot

```bash
python main.py
```

### 6. Invite Bot to Server

Use the `!invite` command in Discord or manually create an invite URL with these permissions:
- Connect
- Speak  
- Use Voice Activity
- Read Messages
- Send Messages
- Embed Links
- Read Message History

### 7. Access Web Dashboard

1. Visit `http://localhost:8888`
2. Sign in with Discord
3. You must be a member of a server where the bot is installed

## Commands

### Music Commands
- `!join` - Join voice channel
- `!play <song>` - Search and play music
- `!queue` - Show current queue
- `!skip` - Skip current song
- `!stop` - Stop and clear queue
- `!leave` - Leave voice channel

### Info Commands
- `!invite` - Get bot invite link
- `!dashboard` - Web dashboard info
- `!github` - View source code
- `!help` - Show all commands

## Web Dashboard Authentication

The web dashboard uses Discord OAuth2 for authentication:

1. **Authentication Required**: Users must sign in with Discord
2. **Server Access Control**: Only members of servers where the bot is installed can access the dashboard
3. **Queue Control**: Only authenticated users with server access can add/remove songs
4. **Session Management**: Secure JWT-based sessions with automatic expiry

### Access Control Flow

1. User visits dashboard → Redirected to Discord OAuth
2. User authorizes → System checks server membership  
3. Access granted only if user is in a server with the bot
4. Queue controls enabled only for authorized users

## File Structure

```
psychosonus/
├── main.py                   # Main entry point
├── config.py                 # Configuration management
├── models.py                 # Data models (Song class)
├── queue_manager.py          # Thread-safe music queue
├── discord_bot.py           # Discord bot functionality
├── youtube_manager.py       # YouTube search and audio extraction
├── web_interface.py         # Flask web API with OAuth2
├── discord_auth.py          # Discord OAuth2 authentication
├── search.py                # Spotify integration
├── requirements.txt         # Python dependencies
├── config.json.example      # Configuration template
└── static/
    ├── dashboard.html       # Web dashboard interface
    ├── dashboard.css        # Dashboard styling
    └── dashboard.js         # Dashboard JavaScript with auth
```

## Architecture

The bot uses a modular architecture with Discord OAuth2 authentication:

- **main.py**: Entry point and application lifecycle
- **config.py**: Configuration loading and validation
- **models.py**: Data structures (Song class)
- **queue_manager.py**: Thread-safe queue operations
- **discord_bot.py**: Discord commands and voice functionality
- **youtube_manager.py**: YouTube search and audio extraction
- **web_interface.py**: Flask web server with OAuth2 endpoints
- **discord_auth.py**: Discord OAuth2 flow and session management
- **search.py**: Spotify API integration

## Security Features

- **Discord OAuth2**: Secure authentication using Discord accounts
- **Server-based Access Control**: Users can only control bots in their servers
- **JWT Sessions**: Secure session management with automatic expiry
- **CSRF Protection**: Built-in Flask CSRF protection
- **Input Validation**: Comprehensive input sanitization and validation

## Troubleshooting

### Authentication Issues
- Ensure Discord redirect URI matches exactly: `http://localhost:8888/auth/callback`
- Check Discord application has proper OAuth2 scopes: `identify guilds`
- Verify bot is in the same server as the user

### Bot Connection Issues  
- Use `!join` command first to connect bot to voice channel
- Check bot has voice permissions in the Discord server
- Ensure FFmpeg is installed for audio processing

### Web Dashboard Issues
- Clear browser cookies if authentication fails
- Check console for JavaScript errors
- Verify all configuration values are set correctly

## Development

To contribute or modify:

1. Follow the modular architecture
2. Keep authentication middleware in place
3. Test OAuth2 flow thoroughly
4. Ensure server access controls work correctly
5. Update documentation for any new features

## License

MIT License - see LICENSE file for details