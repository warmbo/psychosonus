#!/usr/bin/env python3
"""
Discord OAuth2 authentication for Psychosonus
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
import jwt
import time

logger = logging.getLogger(__name__)

class DiscordAuth:
    """Discord OAuth2 authentication handler"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.api_endpoint = "https://discord.com/api/v10"
        self.oauth_url = "https://discord.com/api/oauth2/token"
        
    def get_authorization_url(self, state: str = None, include_bot: bool = True) -> str:
        """Generate Discord OAuth2 authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'identify guilds',
        }

        if include_bot:
            # Add bot + slash command scopes for invite flow
            params['scope'] += ' bot applications.commands'
            # Adjust permissions as needed (example: connect, speak, etc.)
            params['permissions'] = '3145728'

        if state:
            params['state'] = state

        return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh the access token using a refresh token"""
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            response = requests.post(self.oauth_url, data=data, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    def exchange_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri,
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            response = requests.post(self.oauth_url, data=data, headers=headers)

            if response.status_code == 200:
                token_data = response.json()
                if 'refresh_token' not in token_data:
                    logger.warning("No refresh token provided in the response.")
                return token_data
            else:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error exchanging code: {e}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Discord"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(f"{self.api_endpoint}/users/@me", headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Get user info failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def get_user_guilds(self, access_token: str) -> List[Dict[str, Any]]:
        """Get user's Discord guilds"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(f"{self.api_endpoint}/users/@me/guilds", headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Get user guilds failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting user guilds: {e}")
            return []
    
    def create_session_token(self, user_data: Dict[str, Any], guilds: List[Dict[str, Any]], secret_key: str) -> str:
        """Create a JWT session token"""
        payload = {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'discriminator': user_data.get('discriminator', '0'),
            'avatar': user_data.get('avatar'),
            'guilds': [{'id': g['id'], 'name': g['name']} for g in guilds],
            'exp': int(time.time()) + 3600,  # 1 hour expiry
            'iat': int(time.time())
        }
        
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    def verify_session_token(self, token: str, secret_key: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT session token"""
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid session token: {e}")
            return None


class ServerPermissions:
    """Manage server-specific permissions and queue access"""
    
    def __init__(self, bot):
        self.bot = bot
        self.authorized_users = {}  # guild_id -> [user_ids]
    
    def user_has_access(self, user_id: str, guild_id: str) -> bool:
        """Check if user has access to guild's queue"""
        # Check if bot is in the guild
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return False
        
        # Check if user is in the guild
        member = guild.get_member(int(user_id))
        return member is not None
    
    def get_user_accessible_guilds(self, user_guilds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get guilds where user has access and bot is present"""
        accessible_guilds = []
        
        for user_guild in user_guilds:
            guild_id = user_guild['id']
            bot_guild = self.bot.get_guild(int(guild_id))
            
            if bot_guild:
                accessible_guilds.append({
                    'id': guild_id,
                    'name': user_guild['name'],
                    'icon': user_guild.get('icon'),
                    'bot_connected': self.bot.voice_client is not None and 
                                   self.bot.voice_client.guild.id == int(guild_id)
                })
        
        return accessible_guilds