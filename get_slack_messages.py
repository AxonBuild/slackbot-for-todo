import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load environment variables from .env file
load_dotenv()

# Get Slack bot token from environment variable
slack_token = os.getenv("SLACK_BOT_TOKEN")
if not slack_token:
    raise ValueError("SLACK_BOT_TOKEN not found in environment variables. Please check your .env file.")

# Initialize Slack client
client = WebClient(token=slack_token)

def list_available_channels():
    """
    List all available channels that the bot can access.
    
    Returns:
        list: List of channel dictionaries
    """
    try:
        response = client.conversations_list(types="public_channel,private_channel")
        return response["channels"]
    except SlackApiError as e:
        print(f"Error listing channels: {e.response['error']}")
        return []

def get_channel_messages(channel_name=None, channel_id=None, limit=100, minutes_ago=None):
    """
    Retrieve messages from a Slack channel.
    
    Args:
        channel_name (str): Name of the channel (e.g., "general")
        channel_id (str): ID of the channel (e.g., "C1234567890")
        limit (int): Maximum number of messages to retrieve (default: 100)
        minutes_ago (int): Only get messages from the last N minutes (None = all messages)
    
    Returns:
        list: List of message dictionaries
    """
    try:
        # If channel_name is provided, find the channel ID
        if channel_name and not channel_id:
            print(f"Looking for channel: {channel_name}")
            response = client.conversations_list(types="public_channel,private_channel")
            channels = response["channels"]
            
            channel_id = None
            for channel in channels:
                # Case-insensitive matching
                if channel["name"].lower() == channel_name.lower():
                    channel_id = channel["id"]
                    print(f"Found channel ID: {channel_id}")
                    break
            
            if not channel_id:
                print(f"Channel '{channel_name}' not found.")
                print("\nAvailable channels:")
                print("-" * 50)
                for channel in channels:
                    channel_type = "private" if channel.get("is_private") else "public"
                    print(f"  • {channel['name']} ({channel_type})")
                print("-" * 50)
                return []
        
        if not channel_id:
            raise ValueError("Either channel_name or channel_id must be provided")
        
        # Calculate oldest timestamp if minutes_ago is specified
        oldest_ts = None
        if minutes_ago is not None:
            cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
            oldest_ts = cutoff_time.timestamp()
            print(f"Fetching messages from channel {channel_id} (last {minutes_ago} minutes)...")
        else:
            print(f"Fetching messages from channel {channel_id}...")
        
        # Fetch conversation history with optional oldest timestamp filter
        result = client.conversations_history(
            channel=channel_id,
            limit=limit,
            oldest=oldest_ts  # Slack API will only return messages after this timestamp
        )
        
        messages = result["messages"]
        if minutes_ago:
            print(f"Retrieved {len(messages)} messages from the last {minutes_ago} minutes")
        else:
            print(f"Retrieved {len(messages)} messages")
        
        return messages
    
    except SlackApiError as e:
        print(f"Error fetching messages: {e.response['error']}")
        return []

def display_messages(messages):
    """
    Display messages in a readable format.
    
    Args:
        messages (list): List of message dictionaries
    """
    if not messages:
        print("No messages to display.")
        return
    
    # Cache user info to avoid multiple API calls
    user_cache = {}
    
    def get_username(user_id):
        """Get username from cache or API."""
        if not user_id or user_id == 'Unknown':
            return 'Unknown'
        
        # Handle special Slack user IDs
        if user_id == 'USLACKBOT':
            return 'Slackbot'
        
        # Check cache first
        if user_id in user_cache:
            return user_cache[user_id]
        
        # Try to get user info from API
        try:
            user_info = client.users_info(user=user_id)
            user = user_info.get('user', {})
            # Prefer real_name, fallback to display_name, then name
            username = user.get('real_name') or user.get('profile', {}).get('display_name') or user.get('name') or user_id
            user_cache[user_id] = username
            return username
        except Exception as e:
            # If we can't get user info, return the ID
            # This might happen if bot doesn't have users:read scope
            user_cache[user_id] = user_id
            return user_id
    
    print("\n" + "="*80)
    print("MESSAGES")
    print("="*80)
    
    for message in reversed(messages):  # Reverse to show oldest first
        user_id = message.get('user', 'Unknown')
        text = message.get('text', '')
        timestamp = message.get('ts', '')
        
        username = get_username(user_id)
        
        print(f"\n[{timestamp}] {username}:")
        print(f"  {text}")

if __name__ == "__main__":
    # Get channel name from environment variable or use default
    channel_name = os.getenv("SLACK_CHANNEL_NAME", "general")
    
    # Get limit from environment variable or use default
    limit = int(os.getenv("SLACK_MESSAGE_LIMIT", "100"))
    
    # Get time filter from environment variable (None = all messages)
    minutes_ago = os.getenv("SLACK_MINUTES_AGO")
    if minutes_ago:
        minutes_ago = int(minutes_ago)
    else:
        minutes_ago = None
    
    print(f"Fetching messages from channel: {channel_name}")
    print(f"Limit: {limit} messages")
    if minutes_ago:
        print(f"Time filter: Last {minutes_ago} minutes")
    print()
    
    # Get messages
    messages = get_channel_messages(
        channel_name=channel_name, 
        limit=limit,
        minutes_ago=minutes_ago
    )
    
    # Display messages
    display_messages(messages)
    
    # Optionally return messages for further processing
    print(f"\n\nTotal messages retrieved: {len(messages)}")

