#!/usr/bin/env python3
"""
Simplified Configuration manager for Psychosonus
"""

import json
import logging
import secrets
from typing import Dict, Any

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager with simplified URL handling"""
    
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
        required_fields = [
            'discord_token',
            'discord_client_id',
            'discord_client_secret'
        ]
        
        for field in required_fields:
            if not self.data.get(field) or self.data[field] in [
                f"YOUR_{field.upper()}_HERE",
                f"{field.upper()}_GOES_HERE",
                ""
            ]:
                logger.error(f"Missing or invalid {field} in config.json")
                raise ValueError(f"Please configure {field} in config.json")
        
        # Auto-generate session secret if not provided
        if not self.data.get('session_secret'):
            self.data['session_secret'] = secrets.token_hex(32)
            logger.info("Auto-generated session secret")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.data.get(key, default)
    
    def get_domain(self) -> str:
        """Get the domain (with smart localhost detection)"""
        domain = self.get('domain', 'localhost')
        # Handle common variations
        if domain in ['localhost', '127.0.0.1', '0.0.0.0']:
            return 'localhost'
        return domain
    
    def get_port(self) -> int:
        """Get the web port (support both 'port' and 'web_port' for compatibility)"""
        return self.get('port', self.get('web_port', 8888))
    
    def is_localhost(self) -> bool:
        """Check if running on localhost"""
        domain = self.get_domain()
        return domain in ['localhost', '127.0.0.1']
    
    def get_protocol(self) -> str:
        """Determine protocol (http for localhost, https for domains)"""
        if self.is_localhost():
            return 'http'
        else:
            # Production domains should use HTTPS
            return 'https'
    
    def get_base_url(self) -> str:
        """Get the complete base URL without port for external use"""
        domain = self.get_domain()
        protocol = self.get_protocol()
        return f"{protocol}://{domain}"

    def get_discord_redirect_uri(self) -> str:
        """Get the Discord OAuth2 redirect URI without port"""
        return f"{self.get_base_url()}/auth/callback"
    
    def get_spotify_redirect_uri(self) -> str:
        """Get the Spotify redirect URI"""
        return f"{self.get_base_url()}/callback/spotify"
    
    def get_session_secret(self) -> str:
        """Get session secret (auto-generated if not provided)"""
        return self.data['session_secret']