#!/usr/bin/env python3
"""
Configuration manager for Psychosonus
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager"""
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.data = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file {self.config_path} not found!")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise
    
    def _validate_config(self):
        """Validate required configuration"""
        required_fields = ['discord_token']
        for field in required_fields:
            if not self.data.get(field) or self.data[field] == f"YOUR_{field.upper()}_HERE":
                logger.error(f"Missing or invalid {field} in config.json")
                raise ValueError(f"Please configure {field} in config.json")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.data.get(key, default)
    
    def get_base_url(self) -> str:
        """Get the base URL for the web interface"""
        domain = self.get('domain', 'localhost')
        use_https = self.get('use_https', False)
        web_port = self.get('web_port', 8888)
        
        # Determine protocol
        protocol = 'https' if use_https else 'http'
        
        # Handle port - don't include if it's standard (80 for http, 443 for https)
        if (use_https and web_port == 443) or (not use_https and web_port == 80):
            return f"{protocol}://{domain}"
        else:
            return f"{protocol}://{domain}:{web_port}"
    
    def get_spotify_redirect_uri(self) -> str:
        """Get the Spotify redirect URI based on configured domain"""
        base_url = self.get_base_url()
        return f"{base_url}/callback/spotify"