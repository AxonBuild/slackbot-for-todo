# Slack Todo Bot - Architecture

## Overview

The Slack Todo Bot is a RESTful API service that extracts action items (todos) from Slack messages using Large Language Models (LLMs). It's designed to be called by external schedulers (cron, Airflow, Lambda, etc.) for automated periodic processing.

## Architecture Principles

1. **API-First Design** - All configuration via request body, not environment variables
2. **Stateless** - No built-in scheduler, no internal state
3. **Modular** - Clean separation of concerns (API, LLM, Slack, Extraction)
4. **Flexible** - Works with multiple LLM providers (OpenAI, Groq)
5. **External Scheduling** - Designed to be triggered by external systems

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Scheduler                        │
│              (Cron, Airflow, Lambda, etc.)                   │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP POST with config
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Service                         │
│                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │   API Layer  │   │  LLM Client  │   │    Slack     │   │
│  │   (app.py)   │ → │  (OpenAI/    │ ← │   Service    │   │
│  │              │   │   Groq)      │   │              │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│         ↓                   ↓                   ↓           │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Todo Extractor Service                     │   │
│  │      (Coordinates LLM + Slack data)                │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│                                                               │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │  Slack API   │                    │   LLM APIs   │       │
│  │  (Messages)  │                    │ (OpenAI/Groq)│       │
│  └──────────────┘                    └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. API Layer (`api/app.py`)

**Responsibility:** HTTP endpoints and request handling

**Key Endpoints:**
- `POST /extract-todos` - Main endpoint for todo extraction
- `GET /channels` - List available Slack channels
- `GET /health` - Health check

**Design:**
- Stateless request handling
- Configuration via request body (not env vars)
- Async FastAPI for performance
- Comprehensive error handling

### 2. Slack Service (`services/slack_service.py`)

**Responsibility:** Slack API integration

**Key Methods:**
- `list_channels()` - Get all channels bot is member of
- `get_channel_messages(channel_id, minutes_ago, limit)` - Fetch messages
- `post_message(channel_id, text, blocks)` - Post formatted messages
- `_enrich_messages_with_user_names()` - Replace user IDs with names

**Features:**
- Supports all conversation types (channels, DMs, group DMs)
- User name resolution with caching
- Channel ID and name resolution
- Error handling for API failures

### 3. LLM Client (`llm/client.py`)

**Responsibility:** LLM provider abstraction

**Providers:**
- OpenAI (gpt-4o-mini default)
- Groq (llama-3.1-70b-versatile default)

**Design:**
- Abstract base class `LLMClient`
- Provider-specific implementations
- Factory pattern for client creation
- Consistent interface across providers

### 4. Todo Extractor (`services/todo_extractor.py`)

**Responsibility:** Todo extraction logic

**Process:**
1. Receive Slack messages
2. Format messages for LLM
3. Call LLM with extraction prompt
4. Parse and validate response
5. Return structured todos

**Features:**
- Structured prompting
- JSON response parsing
- Error handling for malformed responses
- Extracts: description, assigned_to fields

### 5. Prompt Templates (`prompts/todo_extraction.py`)

**Responsibility:** LLM prompt engineering

**Key Components:**
- System prompt defining task
- Example messages (few-shot learning)
- Output format specification
- Context about Slack conversations

## Data Flow

### Request → Response Flow

```
1. External Scheduler makes POST request
   ↓
2. FastAPI validates request body
   ↓
3. Get SlackService + TodoExtractor instances
   ↓
4. List channels (or use provided channel_ids)
   ↓
5. For each channel:
   a. Fetch messages from Slack
   b. Pass messages to TodoExtractor
   c. TodoExtractor calls LLM
   d. Parse LLM response → structured todos
   e. Optionally post todos back to Slack
   ↓
6. Aggregate results from all channels
   ↓
7. Return structured JSON response
```

### Example Request

```json
POST /extract-todos
{
  "minutes_ago": 30,
  "message_limit": 100,
  "post_to_slack": true,
  "channel_ids": null
}
```

### Example Response

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

## Configuration

### Environment Variables (Minimal)

Only secrets and tokens in `.env`:

```bash
# Required
SLACK_BOT_TOKEN=xoxb-...
OPENAI_API_KEY=sk-...    # OR
GROQ_API_KEY=gsk_...     # OR

# Optional
LLM_PROVIDER=openai      # or "groq"
LOG_LEVEL=INFO
```

### Runtime Configuration (Request Body)

All operational parameters via API:

```json
{
  "minutes_ago": 30,        // Time window
  "message_limit": 100,     // Max messages per channel
  "post_to_slack": true,    // Post back to Slack
  "channel_ids": null       // Channels to process
}
```

## Deployment Patterns

### Pattern 1: Cron + API

```
┌─────────┐         ┌─────────┐
│  Cron   │ ──────> │   API   │
│ (Every  │  POST   │ (Always │
│ 30 min) │         │  On)    │
└─────────┘         └─────────┘
```

Simple, low overhead, works anywhere.

### Pattern 2: Airflow + API

```
┌─────────┐         ┌─────────┐
│ Airflow │ ──────> │   API   │
│   DAG   │  POST   │ (Docker)│
│ (Sched) │         │         │
└─────────┘         └─────────┘
```

Monitoring, retries, dependencies.

### Pattern 3: Lambda + EventBridge

```
┌──────────┐       ┌─────────┐       ┌─────────┐
│EventBridge│ ───> │ Lambda  │ ───>  │   API   │
│  (Cron)  │       │Function │ POST  │(Fargate)│
└──────────┘       └─────────┘       └─────────┘
```

Serverless, auto-scaling, AWS native.

## Error Handling

### Error Types

1. **Slack API Errors**
   - Invalid token
   - Channel not found
   - Rate limiting
   - Network issues

2. **LLM Errors**
   - Invalid API key
   - Rate limiting
   - Malformed responses
   - Timeout

3. **Validation Errors**
   - Invalid request parameters
   - Missing required fields

### Error Strategy

- **Per-channel isolation**: One channel error doesn't stop others
- **Graceful degradation**: Return partial results on errors
- **Detailed logging**: All errors logged with context
- **HTTP status codes**: Proper REST semantics
  - 400: Bad request
  - 404: Channel not found
  - 500: Server error

## Performance Considerations

### Bottlenecks

1. **LLM API Calls** - Slowest part (1-5s per channel)
2. **Slack API** - Network latency
3. **User lookups** - Cached to minimize

### Optimization Strategies

1. **Concurrent processing**: Process channels in parallel (future)
2. **User cache**: Avoid repeated user lookups
3. **Message limits**: Reasonable defaults (100)
4. **Timeout handling**: Generous timeouts for LLM

### Scalability

- **Horizontal**: Run multiple API instances behind load balancer
- **Vertical**: More CPU/RAM for faster processing
- **Rate limits**: Respect Slack and LLM provider limits

## Security

### Secrets Management

- All secrets in `.env` file (not committed to git)
- Use environment variable injection in production
- Consider AWS Secrets Manager, HashiCorp Vault, etc.

### API Security

- No authentication by default (internal network assumed)
- Add API key middleware if exposing publicly
- Use HTTPS in production
- Rate limiting recommended

### Data Privacy

- Messages processed in memory only
- No persistent storage of Slack data
- LLM provider receives message content (review their privacy policy)

## Monitoring & Observability

### Logging

- Structured logging throughout
- Log levels: DEBUG, INFO, WARNING, ERROR
- Per-request tracing
- Error stack traces

### Metrics (to add)

- Request count
- Response time
- Todos extracted per request
- LLM API latency
- Slack API latency
- Error rates

### Recommended Tools

- **Logging**: Datadog, CloudWatch, ELK
- **Monitoring**: Prometheus + Grafana
- **Alerting**: PagerDuty, OpsGenie

## Extensibility

### Adding a New LLM Provider

1. Create class in `llm/client.py` inheriting from `LLMClient`
2. Implement `generate(prompt)` method
3. Add to `create_llm_client()` factory
4. Document env vars needed

### Adding New Extraction Types

1. Create new prompt template in `prompts/`
2. Add method to `TodoExtractor` or create new service
3. Add API endpoint in `api/app.py`
4. Define request/response models

### Custom Post-Processing

1. Extend `TodoExtractor.extract_todos()`
2. Add filtering, validation, enrichment
3. Maintain backward compatibility

## Testing

### Manual Testing

```bash
# Start API
python run_api.py

# Run test suite
python test_api.py
```

### Automated Testing (future)

- Unit tests for each service
- Integration tests with mocked Slack/LLM
- E2E tests with test Slack workspace

## Dependencies

### Core

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `slack-sdk` - Slack API client
- `openai` - OpenAI client
- `groq` - Groq client
- `pydantic` - Data validation

### Optional

- `python-dotenv` - .env file support
- `requests` - HTTP client (for tests)

## Future Enhancements

### Planned

- [ ] Parallel channel processing
- [ ] Caching layer for recent extractions
- [ ] Webhook support (push instead of pull)
- [ ] Custom extraction rules per channel
- [ ] Metrics and monitoring endpoints
- [ ] Authentication middleware
- [ ] Rate limiting
- [ ] Batch processing API

### Considered

- [ ] Database for historical todos
- [ ] Web UI for configuration
- [ ] Slack slash commands
- [ ] Email notifications
- [ ] Calendar integration

## Version History

### v2.0.0 (Current)

- API-driven configuration (no scheduler)
- Multi-channel processing in single request
- Simplified environment variables
- External scheduler integration

### v1.0.0 (Deprecated)

- Built-in APScheduler
- Configuration via env vars
- Single channel processing
