"""Integration script that fetches Slack messages and extracts todos via API."""

import os
import requests
import json
from dotenv import load_dotenv
from get_slack_messages import get_channel_messages

# Load environment variables
load_dotenv()

def send_messages_to_api(messages, api_url="http://localhost:8000/extract-todos"):
    """
    Send messages to the todo extraction API.
    
    Args:
        messages: List of message dictionaries
        api_url: API endpoint URL
    
    Returns:
        Response from API with extracted todos
    """
    # Format messages for API
    api_messages = [
        {
            "text": msg.get("text", ""),
            "user": msg.get("user"),
            "ts": msg.get("ts"),
            "channel": msg.get("channel")
        }
        for msg in messages
    ]
    
    # Send to API
    try:
        response = requests.post(
            api_url,
            json={"messages": api_messages},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {str(e)}")
        return None


def display_todos(todos_data):
    """Display extracted todos in a readable format."""
    if not todos_data or not todos_data.get("todos"):
        print("\nNo todos found in the messages.")
        return
    
    todos = todos_data["todos"]
    print(f"\n{'='*80}")
    print(f"EXTRACTED TODOS ({todos_data['todos_found']} found from {todos_data['total_messages']} messages)")
    print(f"{'='*80}\n")
    
    for i, todo in enumerate(todos, 1):
        print(f"Todo #{i}:")
        print(f"  Description: {todo['description']}")
        if todo.get('assigned_to'):
            print(f"  Assigned to: {todo['assigned_to']}")
        print()


if __name__ == "__main__":
    # Get channel name from environment variable
    channel_name = os.getenv("SLACK_CHANNEL_NAME", "general")
    limit = int(os.getenv("SLACK_MESSAGE_LIMIT", "100"))
    minutes_ago = os.getenv("SLACK_MINUTES_AGO")
    if minutes_ago:
        minutes_ago = int(minutes_ago)
    else:
        minutes_ago = None
    
    api_url = os.getenv("API_URL", "http://localhost:8000/extract-todos")
    
    print(f"Fetching messages from channel: {channel_name}")
    if minutes_ago:
        print(f"Time filter: Last {minutes_ago} minutes")
    print(f"API URL: {api_url}\n")
    
    # Get messages from Slack
    messages = get_channel_messages(
        channel_name=channel_name,
        limit=limit,
        minutes_ago=minutes_ago
    )
    
    if not messages:
        print("No messages to process.")
        exit(0)
    
    print(f"\nSending {len(messages)} messages to API for todo extraction...")
    
    # Send to API and get todos
    todos_data = send_messages_to_api(messages, api_url)
    
    if todos_data:
        display_todos(todos_data)
    else:
        print("Failed to extract todos. Make sure the API server is running.")

