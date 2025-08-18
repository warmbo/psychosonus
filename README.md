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
   # Edit config.json with your Discord token, domain, and Spotify credentials
   ```

3. **Run the bot:**
   ```bash
   python main.py
   ```

4. **Access web dashboard:**
   ```
   http://your-domain.com:8888  # or your configured domain
   ```

## Configuration

### Domain Setup

The bot now supports custom domain configuration for production deployments:

```json
{
  "domain": "music.example.com",
  "use_https": true,
  "web_port": 443
}
```

**Configuration Options:**
- `domain`: Your domain or subdomain (e.g., `music.example.com`, `localhost`)
- `use_https`: Whether to use HTTPS (recommended for production)
- `web_port`: Port for the web interface (80/443 for standard HTTP/HTTPS)

**Examples:**

**Local Development:**
```json
{
  "domain": "localhost",
  "use_https": false,
  "web_port": 8888
}
```

**Production with Custom Domain:**
```json
{
  "domain": "music.mydomain.com",
  "use_https": true,
  "web_port": 443
}
```

**Production with Subdomain and Custom Port:**
```json
{
  "domain": "bot.example.com",
  "use_https": true,
  "web_port": 3000
}
```

### Spotify Integration

When configuring Spotify, make sure to update your Spotify app settings:

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Edit your app settings
3. Add the redirect URI based on your domain configuration:
   - Local: `http://localhost:8888/callback/spotify`
   - Production: `https://music.example.com/callback/spotify`

The bot automatically generates the correct redirect URI based on your domain configuration.

## File Structure

```
psychosonus/
├── main.py                   # Main entry point
├── config.py                 # Configuration management with domain support
├── models.py                 # Data models (Song class)
├── queue_manager.py          # Thread-safe music queue
├── discord_bot.py           # Discord bot functionality with domain-aware URLs
├── youtube_manager.py       # YouTube search and audio extraction
├── web_interface.py         # Flask web API with domain configuration
├── search.py                # Spotify integration with dynamic redirect URIs
├── requirements.txt         # Python dependencies
├── config.json.example      # Configuration template with domain options
└── static/
    ├── dashboard.html       # Web dashboard interface
    ├── dashboard.css        # Dashboard styling
    └── dashboard.js         # Dashboard functionality with dynamic URLs
```

## Features

- 🎵 Discord music bot with voice channel support
- 🌐 Modern web dashboard for remote control
- 🔗 **Custom domain support for production deployments**
- 🔒 **HTTPS support for secure connections**
- 🔍 Multi-platform search (Spotify + YouTube)
- 📋 Queue management with add/remove/clear
- ⏯️ Playbook controls (play, pause, skip, stop)
- 🔄 Auto-advance through queue
- 📱 Mobile-responsive web interface
- ⌨️ **Keyboard shortcuts for quick control**

## Commands

### Discord Commands
- `!join` - Join voice channel
- `!play <song>` - Search and play music
- `!queue` - Show current queue
- `!skip` - Skip current song
- `!stop` - Stop and clear queue
- `!leave` - Leave voice channel
- `!dashboard` - Show web dashboard URL

### Web Dashboard Keyboard Shortcuts
- `Space` - Play/Pause toggle
- `→` - Skip current song
- `S` - Shuffle queue
- `C` - Clear queue (with confirmation)
- `/` - Focus search input

## Deployment

### Local Development
```bash
# Use default localhost configuration
python main.py
# Access at http://localhost:8888
```

### Production with Reverse Proxy (Recommended)

1. **Configure domain in config.json:**
```json
{
  "domain": "music.example.com",
  "use_https": true,
  "web_port": 8888
}
```

2. **Set up reverse proxy (nginx example):**
```nginx
server {
    listen 443 ssl;
    server_name music.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Run the bot:**
```bash
python main.py
# Bot shows: Dashboard accessible at: https://music.example.com
```

### Direct HTTPS (Alternative)

Configure the bot to handle HTTPS directly:
```json
{
  "domain": "music.example.com",
  "use_https": true,
  "web_port": 443
}
```

Note: You'll need to implement SSL certificate handling in the Flask app for direct HTTPS.

## Architecture

The bot is modular with domain-aware components:

- **main.py**: Entry point and application lifecycle
- **config.py**: Configuration loading with domain URL generation
- **models.py**: Data structures (Song class)
- **queue_manager.py**: Thread-safe queue operations
- **discord_bot.py**: Discord commands with dynamic dashboard URLs
- **youtube_manager.py**: YouTube search and audio extraction
- **web_interface.py**: Flask web server with domain-aware endpoints
- **search.py**: Spotify API integration with dynamic redirect URIs
- **static/dashboard.js**: Frontend with dynamic URL handling

This modular design makes the code easier to maintain, test, extend, and deploy across different environments while maintaining proper domain configuration throughout the application.