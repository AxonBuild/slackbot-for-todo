"""Service for interacting with Slack API."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class SlackService:
    """Service to interact with Slack API for fetching messages."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Slack service.
        
        Args:
            token: Slack bot token. If None, will try to get from SLACK_BOT_TOKEN env var.
        """
        logger.debug("Initializing SlackService")
        load_dotenv()
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        if not self.token:
            logger.error("SLACK_BOT_TOKEN not found in environment variables")
            raise ValueError("SLACK_BOT_TOKEN not found. Set it in environment variables or pass as argument.")
        
        self.client = WebClient(token=self.token)
        logger.info("SlackService initialized successfully")
    
    def get_channel_messages(
        self, 
        channel_name_or_id: str, 
        minutes_ago: Optional[int] = None, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a Slack channel or conversation.
        
        Args:
            channel_name_or_id: Name of the Slack channel or channel ID (for DMs)
            minutes_ago: Number of minutes to look back (None = all messages)
            limit: Maximum number of messages to retrieve
        
        Returns:
            List of message dictionaries
        
        Raises:
            ValueError: If channel is not found
            Exception: If there's an error fetching messages
        """
        logger.info(f"Fetching messages from '{channel_name_or_id}' (limit={limit}, minutes_ago={minutes_ago})")
        
        try:
            # Check if it's already a channel ID (starts with C, D, or G)
            if channel_name_or_id.startswith(('C', 'D', 'G')):
                channel_id = channel_name_or_id
                logger.info(f"Using provided channel ID: {channel_id}")
            else:
                # Find channel ID by name
                logger.debug("Listing available channels")
                response = self.client.conversations_list(types="public_channel,private_channel,mpim,im")
                channels = response["channels"]
                logger.debug(f"Found {len(channels)} available channels")
                
                channel_id = None
                for channel in channels:
                    if channel.get("name", "").lower() == channel_name_or_id.lower():
                        channel_id = channel["id"]
                        logger.info(f"Found channel ID: {channel_id} for channel '{channel_name_or_id}'")
                        break
                
                if not channel_id:
                    available_channels = [c.get('name', c.get('id')) for c in channels]
                    logger.error(f"Channel '{channel_name_or_id}' not found. Available: {', '.join(available_channels)}")
                    raise ValueError(
                        f"Channel '{channel_name_or_id}' not found. "
                        f"Available channels: {', '.join(available_channels)}"
                    )
            
            # Calculate oldest timestamp if minutes_ago is specified
            oldest_ts = None
            if minutes_ago is not None:
                cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
                oldest_ts = cutoff_time.timestamp()
                logger.debug(f"Filtering messages from last {minutes_ago} minutes (timestamp: {oldest_ts})")
            
            # Fetch conversation history
            logger.debug(f"Fetching conversation history for channel {channel_id}")
            result = self.client.conversations_history(
                channel=channel_id,
                limit=limit,
                oldest=oldest_ts
            )
            
            messages = result["messages"]
            logger.info(f"Successfully retrieved {len(messages)} messages from channel '{channel_name}'")
            
            # Enrich messages with user names
            messages = self._enrich_messages_with_user_names(messages)
            
            # Log raw messages data
            logger.debug("=" * 80)
            logger.debug("RAW SLACK MESSAGES RECEIVED:")
            logger.debug("=" * 80)
            for i, msg in enumerate(messages, 1):
                logger.debug(f"\nMessage #{i}:")
                logger.debug(f"  User: {msg.get('user', 'N/A')} ({msg.get('user_name', 'N/A')})")
                logger.debug(f"  Timestamp: {msg.get('ts', 'N/A')}")
                logger.debug(f"  Text: {msg.get('text', 'N/A')}")
                logger.debug(f"  Type: {msg.get('type', 'N/A')}")
                logger.debug(f"  Subtype: {msg.get('subtype', 'N/A')}")
                logger.debug(f"  Full message data: {msg}")
            logger.debug("=" * 80)
            
            return messages
        
        except SlackApiError as e:
            error_msg = e.response.get('error', str(e)) if hasattr(e, 'response') else str(e)
            logger.error(f"Slack API error: {error_msg}", exc_info=True)
            raise Exception(f"Error fetching messages from Slack: {error_msg}")
    
    def list_channels(self) -> List[Dict[str, Any]]:
        """
        List all available channels and conversations that the bot is a member of.
        This includes public channels, private channels, and direct messages.
        
        Returns:
            List of channel/conversation dictionaries
        """
        try:
            # Get all conversations the bot is a member of
            # Types: public_channel, private_channel, mpim (multi-party DM), im (direct message)
            response = self.client.conversations_list(
                types="public_channel,private_channel,mpim,im",
                exclude_archived=True,
                limit=1000  # Increase limit to get more channels
            )
            channels = response["channels"]
            
            # Filter to only conversations the bot is a member of
            member_channels = [ch for ch in channels if ch.get('is_member', False)]
            
            logger.info(f"Bot is a member of {len(member_channels)} out of {len(channels)} total conversations")
            return member_channels
        except SlackApiError as e:
            error_msg = e.response.get('error', str(e)) if hasattr(e, 'response') else str(e)
            raise Exception(f"Error listing channels: {error_msg}")
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information by user ID.
        
        Args:
            user_id: Slack user ID
        
        Returns:
            User information dictionary
        """
        try:
            response = self.client.users_info(user=user_id)
            return response["user"]
        except SlackApiError as e:
            error_msg = e.response.get('error', str(e)) if hasattr(e, 'response') else str(e)
            raise Exception(f"Error fetching user info: {error_msg}")
    
    def _enrich_messages_with_user_names(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Replace user IDs with user names in messages.
        
        Args:
            messages: List of message dictionaries
        
        Returns:
            List of messages with user names added
        """
        # Cache for user info to avoid multiple API calls
        user_cache = {}
        
        def get_user_name(user_id: Optional[str]) -> str:
            """Get user name from cache or API."""
            if not user_id:
                return "Unknown"
            
            # Handle special Slack user IDs
            if user_id == 'USLACKBOT':
                return "Slackbot"
            
            # Check cache first
            if user_id in user_cache:
                return user_cache[user_id]
            
            # Try to get user info from API
            try:
                user_info = self.get_user_info(user_id)
                user = user_info
                # Prefer real_name, fallback to display_name, then name
                username = user.get('real_name') or user.get('profile', {}).get('display_name') or user.get('name') or user_id
                user_cache[user_id] = username
                return username
            except Exception as e:
                # If we can't get user info, use the ID
                logger.warning(f"Could not fetch user info for {user_id}: {str(e)}")
                user_cache[user_id] = user_id
                return user_id
        
        # Enrich each message
        enriched_messages = []
        for msg in messages:
            enriched_msg = msg.copy()
            user_id = msg.get('user')
            
            if user_id:
                user_name = get_user_name(user_id)
                enriched_msg['user_name'] = user_name
                # Replace user ID with name in the message for LLM processing
                enriched_msg['user'] = user_name
            
            enriched_messages.append(enriched_msg)
        
        logger.debug(f"Enriched {len(enriched_messages)} messages with user names")
        return enriched_messages
    
    def post_message(self, channel_name_or_id: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Post a message to a Slack channel or conversation.
        
        Args:
            channel_name_or_id: Name of the Slack channel or channel ID (for DMs)
            text: Message text (fallback if blocks fail to render)
            blocks: Optional Slack Block Kit blocks for rich formatting
        
        Returns:
            Response dictionary from Slack API
        
        Raises:
            ValueError: If channel is not found
            Exception: If there's an error posting the message
        """
        logger.info(f"Posting message to '{channel_name_or_id}'")
        
        try:
            # Check if it's already a channel ID (starts with C, D, or G)
            if channel_name_or_id.startswith(('C', 'D', 'G')):
                channel_id = channel_name_or_id
                logger.info(f"Using provided channel ID: {channel_id}")
            else:
                # Find channel ID by name
                response = self.client.conversations_list(types="public_channel,private_channel,mpim,im")
                channels = response["channels"]
                
                channel_id = None
                for channel in channels:
                    if channel.get("name", "").lower() == channel_name_or_id.lower():
                        channel_id = channel["id"]
                        break
                
                if not channel_id:
                    available_channels = [c.get('name', c.get('id')) for c in channels]
                    raise ValueError(
                        f"Channel '{channel_name_or_id}' not found. "
                        f"Available channels: {', '.join(available_channels)}"
                    )
            
            # Post message
            kwargs = {
                "channel": channel_id,
                "text": text
            }
            
            if blocks:
                kwargs["blocks"] = blocks
            
            result = self.client.chat_postMessage(**kwargs)
            logger.info(f"Successfully posted message to '{channel_name_or_id}'")
            return result
        
        except SlackApiError as e:
            error_msg = e.response.get('error', str(e)) if hasattr(e, 'response') else str(e)
            logger.error(f"Slack API error posting message: {error_msg}", exc_info=True)
            raise Exception(f"Error posting message to Slack: {error_msg}")

