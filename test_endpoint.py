"""Simple script to test the /extract-todos endpoint."""

import requests
import json
import sys


def test_extract_todos(base_url: str = "http://localhost:8000"):
    """
    Test the extract-todos endpoint.
    
    Args:
        base_url: Base URL of the API server
    """
    endpoint = f"{base_url}/extract-todos"
    
    print(f"Testing endpoint: {endpoint}")
    print("-" * 60)
    
    try:
        # Make GET request
        response = requests.get(endpoint, timeout=30)
        
        # Check status code
        if response.status_code == 200:
            print("✅ Success! Status code: 200")
            print("\nResponse:")
            print("-" * 60)
            
            data = response.json()
            
            # Pretty print the response
            print(json.dumps(data, indent=2))
            
            # Summary
            print("\n" + "-" * 60)
            print(f"Total messages processed: {data.get('total_messages', 0)}")
            print(f"Todos found: {data.get('todos_found', 0)}")
            print(f"Channel: {data.get('channel', 'N/A')}")
            print(f"Time window: {data.get('time_window_minutes', 'N/A')} minutes")
            
            # Display todos
            todos = data.get('todos', [])
            if todos:
                print("\n📋 Extracted Todos:")
                print("-" * 60)
                for i, todo in enumerate(todos, 1):
                    print(f"\n{i}. {todo.get('description', 'N/A')}")
                    if todo.get('assigned_to'):
                        print(f"   Assigned to: {todo['assigned_to']}")
            else:
                print("\n⚠️  No todos found in the messages.")
            
            return True
        else:
            print(f"❌ Error! Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Could not connect to the server.")
        print(f"   Make sure the server is running at {base_url}")
        print("   Start it with: python run_api.py")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout: The request took too long.")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_health(base_url: str = "http://localhost:8000"):
    """Test the health endpoint."""
    endpoint = f"{base_url}/health"
    
    try:
        response = requests.get(endpoint, timeout=5)
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False


if __name__ == "__main__":
    # Get base URL from command line argument or use default
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("=" * 60)
    print("Slack Todo Extraction API - Test Script")
    print("=" * 60)
    print()
    
    # Test health endpoint first
    print("1. Testing health endpoint...")
    health_ok = test_health(base_url)
    print()
    
    if health_ok:
        # Test extract-todos endpoint
        print("2. Testing extract-todos endpoint...")
        test_extract_todos(base_url)
    else:
        print("⚠️  Skipping extract-todos test (server not healthy)")
    
    print("\n" + "=" * 60)

