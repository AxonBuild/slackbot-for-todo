# Slack Todo Bot

A modular Python application that retrieves messages from Slack channels and extracts todos using LLM (OpenAI or Groq).

## Features

- 🔍 Retrieve messages from Slack channels (public & private)
- 🤖 Extract todos from messages using LLM (OpenAI or Groq)
- 🏗️ Modular architecture for easy extensibility
- 🌐 RESTful API for todo extraction
- ⚡ Fast Groq integration for quick responses
- 📝 Structured todo output with assignees, deadlines, and priorities

## Project Structure

```
slack-todo-bot/
├── api/              # FastAPI application
├── llm/              # LLM client layer (OpenAI, Groq)
├── prompts/          # Prompt templates
├── services/         # Business logic
├── get_slack_messages.py      # Slack message fetcher
├── integrate_slack_api.py     # Integration script
└── run_api.py                 # API server
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create your `.env` file:**
   ```bash
   cp example.env .env
   ```

3. **Configure your `.env` file:**
   
   **Slack Configuration:**
   - `SLACK_BOT_TOKEN`: Your Bot User OAuth Token (starts with `xoxb-`)
   - `SLACK_CHANNEL_NAME`: Channel to retrieve messages from
   - `SLACK_MESSAGE_LIMIT`: Maximum messages to retrieve (default: 100)
   - `SLACK_MINUTES_AGO`: Only get messages from last N minutes (optional)
   
   **LLM Configuration:**
   - `LLM_PROVIDER`: "openai" or "groq" (default: openai)
   - `LLM_MODEL`: Model name (optional, uses provider defaults)
   - `OPENAI_API_KEY`: Required if using OpenAI
   - `GROQ_API_KEY`: Required if using Groq

## Getting Your API Keys

### Slack Bot Token
1. Go to https://api.slack.com/apps
2. Create a new app or select an existing one
3. Go to **OAuth & Permissions**
4. Add scopes: 
   - `channels:read` - View basic information about public channels
   - `channels:history` - View messages in public channels
   - `groups:read` - View basic information about private channels (if needed)
   - `groups:history` - View messages in private channels (if needed)
   - `users:read` - View user information (to display names instead of IDs)
   - `chat:write` - Post messages to channels (required to post todos back to Slack)
5. Click **Install App to Workspace**
6. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### OpenAI API Key
- Get your key from: https://platform.openai.com/api-keys

### Groq API Key
- Get your key from: https://console.groq.com/keys
- Free tier available with generous rate limits

## Usage

### Running the API Server

1. **Make sure your `.env` file is configured** with:
   - `SLACK_BOT_TOKEN`
   - `SLACK_CHANNEL_NAME`
   - `SLACK_MINUTES_AGO` (optional)
   - `SLACK_MESSAGE_LIMIT` (optional)
   - `OPENAI_API_KEY` or `GROQ_API_KEY`
   - `LLM_PROVIDER` (optional, defaults to "openai")
   - `SCHEDULER_ENABLED` (optional, defaults to "true")
   - `SCHEDULER_INTERVAL_MINUTES` (optional, defaults to 30)
   - `POST_TODOS_TO_SLACK` (optional, defaults to "true") - Post extracted todos back to Slack

2. **Start the server:**
   ```bash
   python run_api.py
   ```

   The server will start at `http://localhost:8000` with auto-reload enabled.

3. **Test the endpoint:**
   ```bash
   python test_endpoint.py
   ```

   Or use curl:
   ```bash
   curl http://localhost:8000/extract-todos
   ```

**API Endpoints:**
- `GET /extract-todos` - Extract todos from Slack channel (uses env config)
- `GET /health` - Health check
- `GET /` - API information

**Automatic Scheduled Extraction:**
The API automatically extracts todos every 30 minutes (configurable). The scheduler:
- Runs in the background while the server is running
- Uses the same configuration from environment variables
- Logs all extracted todos
- **Automatically posts todos back to the Slack channel** (if `POST_TODOS_TO_SLACK=true`)
- Can be disabled by setting `SCHEDULER_ENABLED=false`
- Interval can be changed with `SCHEDULER_INTERVAL_MINUTES` (default: 30)

**Posting Todos to Slack:**
When todos are extracted (either via scheduler or manual API call), they are automatically posted back to the Slack channel in a nicely formatted message. This can be disabled by setting `POST_TODOS_TO_SLACK=false` in your `.env` file.

**Note:** Make sure your Slack app has the `chat:write` scope to post messages to channels.

**Example Response:**
```json
{
  "todos": [
    {
      "description": "Fix the bug in production",
      "assigned_to": "john_doe"
    }
  ],
  "total_messages": 11,
  "todos_found": 1,
  "channel": "circle-ai",
  "time_window_minutes": 30
}
```

### Option 2: Use the Integration Script

This script fetches Slack messages and sends them to the API:

```bash
python integrate_slack_api.py
```

### Option 3: Just Fetch Messages

```bash
python get_slack_messages.py
```

## LLM Providers

### OpenAI
- Default model: `gpt-4o-mini`
- Set `LLM_PROVIDER=openai` in `.env`
- Requires `OPENAI_API_KEY`

### Groq
- Default model: `llama-3.1-70b-versatile`
- Set `LLM_PROVIDER=groq` in `.env`
- Requires `GROQ_API_KEY`
- **Faster and more cost-effective** for many use cases
- Other models: `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, `gemma-7b-it`

**Example Groq Configuration:**
```env
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-key
LLM_MODEL=llama-3.1-70b-versatile
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## Features

- ✅ Modular design - easy to extend
- ✅ Multiple LLM providers (OpenAI, Groq)
- ✅ Generic API - works with any message source
- ✅ Structured todo extraction
- ✅ Error handling and validation
- ✅ Time-based message filtering

