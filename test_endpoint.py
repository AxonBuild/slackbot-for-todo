"""Test script for the Slack Todo Extraction API."""

import requests
import json
import sys


def test_health(base_url: str = "http://localhost:8000"):
    """Test the health endpoint."""
    print("Testing /health endpoint...")
    print("-" * 60)
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False


def test_list_channels(base_url: str = "http://localhost:8000"):
    """Test the channels listing endpoint."""
    print("\nTesting /channels endpoint...")
    print("-" * 60)
    
    try:
        response = requests.get(f"{base_url}/channels", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} channels:")
            for ch in data['channels']:
                ch_type = "Channel" if ch['is_channel'] else "DM" if ch['is_im'] else "Group"
                name = ch.get('name', ch['id'])
                print(f"  - {name} ({ch_type}, ID: {ch['id']})")
            return True, data['channels']
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False, []
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False, []


def test_extract_todos(
    base_url: str = "http://localhost:8000",
    minutes_ago: int = 30,
    message_limit: int = 100,
    post_to_slack: bool = False,
    channel_ids: list = None
):
    """Test the extract-todos endpoint."""
    print("\nTesting /extract-todos endpoint...")
    print("-" * 60)
    
    # Prepare request
    request_data = {
        "minutes_ago": minutes_ago,
        "message_limit": message_limit,
        "post_to_slack": post_to_slack,
        "channel_ids": channel_ids
    }
    
    print(f"Request parameters:")
    print(json.dumps(request_data, indent=2))
    print()
    
    try:
        response = requests.post(
            f"{base_url}/extract-todos",
            json=request_data,
            timeout=120  # Longer timeout for LLM processing
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Success!")
            print("=" * 60)
            print(f"Total channels processed: {data['total_channels_processed']}")
            print(f"Total messages processed: {data['total_messages_processed']}")
            print(f"Total todos found: {data['total_todos_found']}")
            print(f"Time window: {data['time_window_minutes']} minutes")
            print("=" * 60)
            
            # Show results per channel
            for ch in data['channels']:
                ch_name = ch['channel_name'] or ch['channel_id']
                print(f"\n📱 {ch_name}")
                print(f"   Messages: {ch['total_messages']}, Todos: {ch['todos_found']}")
                
                if ch['todos']:
                    for i, todo in enumerate(ch['todos'], 1):
                        print(f"   {i}. {todo['description']}")
                        if todo.get('assigned_to'):
                            print(f"      👤 Assigned to: {todo['assigned_to']}")
            
            if data['total_todos_found'] == 0:
                print("\n⚠️  No todos found in any messages.")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout: The request took too long (LLM processing may take time)")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Main test runner."""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("=" * 60)
    print("Slack Todo Extraction API - Test Suite")
    print("=" * 60)
    print(f"API URL: {base_url}")
    print()
    
    # Test 1: Health check
    health_ok = test_health(base_url)
    if not health_ok:
        print("\n⚠️  API is not healthy. Make sure it's running:")
        print("   python run_api.py")
        return
    
    # Test 2: List channels
    channels_ok, channels = test_list_channels(base_url)
    if not channels_ok:
        print("\n⚠️  Could not list channels. Check Slack token and permissions.")
        return
    
    if not channels:
        print("\n⚠️  No channels found. Invite the bot to channels:")
        print("   /invite @YourBotName")
        return
    
    # Test 3: Extract todos (without posting to Slack)
    print("\n" + "=" * 60)
    print("Running todo extraction (test mode - not posting to Slack)")
    print("=" * 60)
    
    test_extract_todos(
        base_url=base_url,
        minutes_ago=60,  # Last hour
        message_limit=100,
        post_to_slack=False,  # Don't spam Slack during testing
        channel_ids=None  # Process all channels
    )
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
    print("\nTo extract todos and post to Slack:")
    print(f'  curl -X POST {base_url}/extract-todos \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"minutes_ago": 30, "message_limit": 100, "post_to_slack": true}\'')
    print()


if __name__ == "__main__":
    main()