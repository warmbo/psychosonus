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