# API Usage Examples

Quick reference for calling the Slack Todo Bot API.

## Base URL

```bash
API_URL="http://localhost:8000"
```

## 1. Health Check

```bash
curl $API_URL/health
```

**Response:**
```json
{"status": "healthy"}
```

## 2. List Channels

Get all channels the bot is a member of:

```bash
curl $API_URL/channels
```

**Response:**
```json
{
  "channels": [
    {
      "id": "C1234567890",
      "name": "general",
      "is_channel": true,
      "is_group": false,
      "is_im": false,
      "is_mpim": false
    }
  ],
  "total": 5
}
```

## 3. Extract Todos - All Channels

Process all channels the bot is in:

```bash
curl -X POST $API_URL/extract-todos \
  -H "Content-Type: application/json" \
  -d '{
    "minutes_ago": 30,
    "message_limit": 100,
    "post_to_slack": true
  }'
```

## 4. Extract Todos - Specific Channels

Process only specific channels:

```bash
curl -X POST $API_URL/extract-todos \
  -H "Content-Type: application/json" \
  -d '{
    "minutes_ago": 60,
    "message_limit": 200,
    "post_to_slack": true,
    "channel_ids": ["C1234567890", "C0987654321"]
  }'
```

## 5. Extract Todos - Without Posting

Extract todos but don't post back to Slack (for testing):

```bash
curl -X POST $API_URL/extract-todos \
  -H "Content-Type: application/json" \
  -d '{
    "minutes_ago": 30,
    "message_limit": 100,
    "post_to_slack": false
  }'
```

## 6. Long Time Window

Get todos from last 24 hours:

```bash
curl -X POST $API_URL/extract-todos \
  -H "Content-Type: application/json" \
  -d '{
    "minutes_ago": 1440,
    "message_limit": 500,
    "post_to_slack": true
  }'
```

## 7. Quick Check (5 minutes)

For frequent monitoring:

```bash
curl -X POST $API_URL/extract-todos \
  -H "Content-Type: application/json" \
  -d '{
    "minutes_ago": 5,
    "message_limit": 50,
    "post_to_slack": true
  }'
```

## Python Example

```python
import requests

response = requests.post(
    "http://localhost:8000/extract-todos",
    json={
        "minutes_ago": 30,
        "message_limit": 100,
        "post_to_slack": True,
        "channel_ids": None  # All channels
    }
)

data = response.json()
print(f"Total todos: {data['total_todos_found']}")

for channel in data['channels']:
    print(f"\n{channel['channel_name']}:")
    for todo in channel['todos']:
        print(f"  - {todo['description']}")
```

## Cron Job Example

Add to crontab (run every 30 minutes):

```bash
*/30 * * * * curl -X POST http://localhost:8000/extract-todos \
  -H "Content-Type: application/json" \
  -d '{"minutes_ago": 30, "message_limit": 100, "post_to_slack": true}' \
  >> /var/log/slack-todo-bot.log 2>&1
```

## Response Format

```json
{
  "channels": [
    {
      "channel_id": "C1234567890",
      "channel_name": "general",
      "todos": [
        {
          "description": "Review PR #123",
          "assigned_to": "Alice"
        },
        {
          "description": "Deploy new feature",
          "assigned_to": "Bob"
        }
      ],
      "total_messages": 15,
      "todos_found": 2
    }
  ],
  "total_channels_processed": 3,
  "total_todos_found": 5,
  "total_messages_processed": 45,
  "time_window_minutes": 30
}
```

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found

```json
{
  "detail": "None of the specified channels found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Error extracting todos: <error message>"
}
```

## Testing Tips

1. **Start with `post_to_slack: false`** to avoid spamming channels
2. **Use small time windows** (5-10 minutes) for testing
3. **Check `/channels` first** to see what's available
4. **Monitor logs** for detailed processing information
5. **Increase timeouts** - LLM processing can take 30-60 seconds for many channels

## Rate Limiting Considerations

- Slack API: ~1 request per second per method
- OpenAI: Depends on your plan (usually generous)
- Groq: Very generous free tier

If processing many channels frequently, consider:
- Longer intervals between runs
- Processing channels in batches
- Using specific `channel_ids` instead of all channels
