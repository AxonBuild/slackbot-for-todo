"""Test script for the Slack Todo Extraction API."""

import requests
import json
import sys


def test_health(base_url):
    """Test the health endpoint."""
    print("Testing /health endpoint...")
    print("-" * 60)
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"Success: {response.json()}")
            return True
        else:
            print(f"Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


def test_list_channels(base_url):
    """Test the channels listing endpoint."""
    print("\nTesting /channels endpoint...")
    print("-" * 60)
    
    try:
        response = requests.get(f"{base_url}/channels", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {data['total']} channels:")
            for ch in data['channels']:
                name = ch.get('name', ch['id'])
                print(f"  - {name} (ID: {ch['id']})")
            return True, data['channels']
        else:
            print(f"Error: {response.status_code}")
            return False, []
    except Exception as e:
        print(f"Error: {str(e)}")
        return False, []


def test_extract_todos(base_url, minutes_ago=30, message_limit=100, post_to_slack=False):
    """Test the extract-todos endpoint."""
    print("\nTesting /extract-todos endpoint...")
    print("-" * 60)
    
    request_data = {
        "minutes_ago": minutes_ago,
        "message_limit": message_limit,
        "post_to_slack": post_to_slack
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{base_url}/extract-todos",
            json=request_data,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print("\nSuccess!")
            print(f"Channels: {data['total_channels_processed']}")
            print(f"Messages: {data['total_messages_processed']}")
            print(f"Todos: {data['total_todos_found']}")
            
            for ch in data['channels']:
                ch_name = ch['channel_name'] or ch['channel_id']
                if ch['todos']:
                    print(f"\n{ch_name}:")
                    for i, todo in enumerate(ch['todos'], 1):
                        print(f"  {i}. {todo['description']}")
            
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("Slack Todo Extraction API - Test Suite")
    print("=" * 60)
    
    if test_health(base_url):
        test_list_channels(base_url)
        test_extract_todos(base_url, minutes_ago=60, post_to_slack=False)
    
    print("\n" + "=" * 60)
