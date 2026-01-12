# Slack Todo Bot

A REST API that extracts todos from Slack messages using LLM (OpenAI or Groq). Designed to be triggered by external schedulers.

## Features

- 🔍 **Multi-Channel Support** - Process ALL channels/DMs the bot is part of in a single API call
- 🤖 **Smart Todo Extraction** - Uses LLM (OpenAI or Groq) to intelligently extract todos
- 📡 **RESTful API** - Call from any scheduler (cron, Airflow, Lambda, etc.)
- ⚙️ **Flexible Configuration** - All parameters passed via request body
- 💬 **Slack Integration** - Automatically posts extracted todos back to channels
- 🏗️ **Modular Architecture** - Easy to extend and customize

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file with only the essentials:

```bash
# Required
SLACK_BOT_TOKEN=xoxb-your-token-here
OPENAI_API_KEY=your-openai-key    # or GROQ_API_KEY
LLM_PROVIDER=openai               # or "groq"

# Optional
LOG_LEVEL=INFO
```

### 3. Set Up Slack App

1. Go to https://api.slack.com/apps
2. Create or select your app
3. Add **Bot Token Scopes**:
   ```
   channels:read      channels:history
   groups:read        groups:history
   im:read            im:history
   mpim:read          mpim:history
   users:read         chat:write
   ```
4. Install app to workspace
5. Copy Bot User OAuth Token to `.env`
6. Invite bot to channels: `/invite @YourBotName`

### 4. Start the API

```bash
python run_api.py
```

The API starts at `http://localhost:8000`

### 5. Call the API

**Extract todos from all channels:**

```bash
curl -X POST http://localhost:8000/extract-todos \
  -H "Content-Type: application/json" \
  -d '{
    "minutes_ago": 30,
    "message_limit": 100,
    "post_to_slack": true
  }'
```

**Extract from specific channels only:**

```bash
curl -X POST http://localhost:8000/extract-todos \
  -H "Content-Type: application/json" \
  -d '{
    "minutes_ago": 60,
    "message_limit": 200,
    "post_to_slack": true,
    "channel_ids": ["C1234567890", "C0987654321"]
  }'
```

## API Reference

### POST /extract-todos

Extract todos from Slack channels.

**Request Body:**

```json
{
  "minutes_ago": 30,          // Optional, default: 30
  "message_limit": 100,       // Optional, default: 100, max: 1000
  "post_to_slack": true,      // Optional, default: true
  "channel_ids": null         // Optional, null = all channels
}
```

**Response:**

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
        }
      ],
      "total_messages": 15,
      "todos_found": 1
    }
  ],
  "total_channels_processed": 3,
  "total_todos_found": 5,
  "total_messages_processed": 45,
  "time_window_minutes": 30
}
```

### GET /channels

List all channels the bot is a member of.

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

### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "healthy"
}
```

## Scheduling Examples

### With Cron

Add to your crontab to run every 30 minutes:

```bash
*/30 * * * * curl -X POST http://localhost:8000/extract-todos \
  -H "Content-Type: application/json" \
  -d '{"minutes_ago": 30, "message_limit": 100, "post_to_slack": true}'
```

### With Python Script

```python
import requests
import schedule
import time

def extract_todos():
    response = requests.post(
        "http://localhost:8000/extract-todos",
        json={
            "minutes_ago": 30,
            "message_limit": 100,
            "post_to_slack": True
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Todos found: {response.json()['total_todos_found']}")

# Run every 30 minutes
schedule.every(30).minutes.do(extract_todos)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### With Airflow

```python
from airflow import DAG
from airflow.operators.http_operator import SimpleHttpOperator
from datetime import datetime, timedelta

dag = DAG(
    'slack_todo_extraction',
    default_args={
        'owner': 'airflow',
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    schedule_interval=timedelta(minutes=30),
    start_date=datetime(2024, 1, 1),
    catchup=False,
)

extract_todos = SimpleHttpOperator(
    task_id='extract_todos',
    http_conn_id='slack_todo_api',
    endpoint='/extract-todos',
    method='POST',
    data=json.dumps({
        "minutes_ago": 30,
        "message_limit": 100,
        "post_to_slack": True
    }),
    headers={"Content-Type": "application/json"},
    dag=dag,
)
```

### With AWS Lambda (Scheduled)

```python
import json
import urllib3

def lambda_handler(event, context):
    http = urllib3.PoolManager()
    
    response = http.request(
        'POST',
        'http://your-api-url/extract-todos',
        body=json.dumps({
            "minutes_ago": 30,
            "message_limit": 100,
            "post_to_slack": True
        }),
        headers={'Content-Type': 'application/json'}
    )
    
    return {
        'statusCode': response.status,
        'body': response.data.decode('utf-8')
    }
```

Configure EventBridge rule to trigger every 30 minutes.

## LLM Providers

### OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
```

Default model: `gpt-4o-mini`

### Groq (Faster & Cheaper)

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your-key
```

Default model: `llama-3.1-70b-versatile`

Other models: `llama-3.1-8b-instant`, `mixtral-8x7b-32768`

Get free API key: https://console.groq.com/keys

## Configuration

### Environment Variables

Only these are needed in `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | ✅ | - | Slack bot OAuth token |
| `OPENAI_API_KEY` | ✅* | - | OpenAI API key (if using OpenAI) |
| `GROQ_API_KEY` | ✅* | - | Groq API key (if using Groq) |
| `LLM_PROVIDER` | ❌ | `openai` | LLM provider: `openai` or `groq` |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |

\* One of `OPENAI_API_KEY` or `GROQ_API_KEY` is required depending on your `LLM_PROVIDER`

### Request Parameters

All scheduling parameters are passed in the API request body:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `minutes_ago` | int | 30 | How far back to look for messages |
| `message_limit` | int | 100 | Max messages per channel (1-1000) |
| `post_to_slack` | bool | true | Post todos back to Slack |
| `channel_ids` | list[str] | null | Specific channels (null = all) |

## Project Structure

```
slackbot/
├── api/
│   └── app.py              # FastAPI application
├── llm/
│   └── client.py           # LLM provider clients
├── prompts/
│   └── todo_extraction.py  # Prompt templates
├── services/
│   ├── slack_service.py    # Slack API wrapper
│   └── todo_extractor.py   # Todo extraction logic
├── utils/
│   └── logger.py           # Logging configuration
├── run_api.py              # API server entrypoint
├── requirements.txt        # Python dependencies
└── .env                    # Configuration (not in git)
```

## Use Cases

### 1. Daily Standup Summary

```bash
# Run once daily at 9 AM
0 9 * * * curl -X POST http://localhost:8000/extract-todos \
  -H "Content-Type: application/json" \
  -d '{"minutes_ago": 1440, "message_limit": 500, "post_to_slack": true}'
```

### 2. Real-time Support Tickets

```bash
# Run every 5 minutes for quick response
*/5 * * * * curl -X POST http://localhost:8000/extract-todos \
  -H "Content-Type: application/json" \
  -d '{"minutes_ago": 5, "message_limit": 50, "post_to_slack": true, "channel_ids": ["C_SUPPORT"]}'
```

### 3. Project Channel Monitoring

```python
# Monitor multiple project channels
requests.post(
    "http://localhost:8000/extract-todos",
    json={
        "minutes_ago": 60,
        "message_limit": 200,
        "post_to_slack": True,
        "channel_ids": ["C_PROJ_A", "C_PROJ_B", "C_PROJ_C"]
    }
)
```

## Troubleshooting

### Bot Not Seeing Channels

**Issue:** API returns no channels

**Solution:** 
1. Verify bot has correct scopes in Slack app settings
2. Reinstall app after adding scopes
3. Invite bot to channels: `/invite @YourBotName`

### No Todos Extracted

**Issue:** API returns 0 todos

**Possible causes:**
- No action items in messages (LLM found nothing)
- Time window too short
- Message limit too low

**Solution:** Increase `minutes_ago` or `message_limit`

### Todos Not Posting to Slack

**Issue:** Todos extracted but not posted to Slack

**Solution:**
1. Set `"post_to_slack": true` in request
2. Verify bot has `chat:write` scope
3. Check API logs for errors

### Rate Limiting

**Issue:** Slack API rate limit errors

**Solution:**
- Reduce frequency of API calls
- Reduce `message_limit`
- Process fewer channels per call

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run the API
python run_api.py

# Test the endpoint
python test_endpoint.py
```

### Adding Custom Extraction Logic

1. Modify `prompts/todo_extraction.py` for custom prompts
2. Extend `services/todo_extractor.py` for custom parsing
3. Update `services/slack_service.py` for additional Slack features

## Migration from v1.x

If you're upgrading from the scheduler-based version:

**Before (v1.x):**
- Built-in scheduler
- Configuration in `.env`
- `SLACK_CHANNEL_NAME`, `SCHEDULER_INTERVAL_MINUTES`, etc.

**After (v2.0):**
- External scheduler (cron, etc.)
- Configuration in request body
- Only tokens/keys in `.env`

**Migration Steps:**
1. Update `.env` - remove scheduler variables
2. Set up external scheduler (cron job, etc.)
3. Call `POST /extract-todos` from scheduler
4. Pass parameters in request body

## API Keys

### Slack Bot Token

1. Create app at https://api.slack.com/apps
2. Add scopes (see Quick Start)
3. Install to workspace
4. Copy Bot User OAuth Token

### OpenAI API Key

Get from: https://platform.openai.com/api-keys

### Groq API Key

Get from: https://console.groq.com/keys (free tier available!)

## Support

- **Documentation:** See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- **Issues:** Check logs for detailed error messages
- **Examples:** See `test_endpoint.py` for usage examples

## License

MIT License - feel free to use and modify!
