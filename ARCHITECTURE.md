# Architecture Overview

This project follows a modular architecture for extracting todos from Slack messages using LLM.

## Project Structure

```
slack-todo-bot/
├── api/                    # API layer
│   ├── __init__.py
│   └── app.py             # FastAPI application
├── llm/                    # LLM client layer
│   ├── __init__.py
│   └── client.py          # Generic LLM client interface
├── prompts/                # Prompt templates
│   ├── __init__.py
│   └── todo_extraction.py # Todo extraction prompts
├── services/               # Business logic layer
│   ├── __init__.py
│   └── todo_extractor.py  # Todo extraction service
├── get_slack_messages.py   # Slack message fetcher
├── integrate_slack_api.py  # Integration script
├── run_api.py             # API server runner
└── requirements.txt       # Dependencies
```

## Module Responsibilities

### `llm/` - LLM Client Layer
- **Purpose**: Abstract interface for interacting with LLM providers
- **Key Components**:
  - `LLMClient`: Abstract base class for LLM clients
  - `OpenAIClient`: OpenAI implementation
  - `create_llm_client()`: Factory function for creating clients
- **Extensibility**: Easy to add new LLM providers (Anthropic, Cohere, etc.)

### `prompts/` - Prompt Management
- **Purpose**: Centralized prompt templates
- **Key Components**:
  - `get_todo_extraction_prompt()`: Generates prompts for todo extraction
- **Benefits**: Easy to modify prompts without changing business logic

### `services/` - Business Logic
- **Purpose**: Core business logic for todo extraction
- **Key Components**:
  - `TodoExtractor`: Service that uses LLM to extract todos from messages
- **Responsibilities**:
  - Orchestrates LLM calls
  - Parses and validates LLM responses
  - Returns structured todo data

### `api/` - API Layer
- **Purpose**: HTTP API for todo extraction
- **Key Components**:
  - FastAPI application
  - RESTful endpoints
  - Request/Response models
- **Endpoints**:
  - `POST /extract-todos`: Extract todos from messages
  - `GET /health`: Health check
  - `GET /`: API information

## Data Flow

1. **Slack Messages** → `get_slack_messages.py` fetches messages
2. **Messages** → `integrate_slack_api.py` sends to API
3. **API** → `TodoExtractor` processes messages
4. **TodoExtractor** → Uses `LLMClient.generate_with_tools()` with function schema
5. **LLM Function Call** → Structured todo data returned via function calling
6. **Todos** → Parsed from function call arguments and returned via API

## Function Calling

The system uses **function/tool calling** instead of JSON parsing for more robust structured output:

- **Function Schema**: Defined in `prompts/todo_extraction.py` with `get_todo_extraction_function_schema()`
- **Benefits**:
  - More reliable than JSON parsing
  - Native LLM support (OpenAI, Groq)
  - Better error handling
  - Type validation built-in
- **Implementation**: `LLMClient.generate_with_tools()` method handles function calling for both OpenAI and Groq

## Usage

### Running the API Server
```bash
python run_api.py
```

### Using the Integration Script
```bash
python integrate_slack_api.py
```

### API Endpoint Example
```bash
curl -X POST "http://localhost:8000/extract-todos" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "text": "We need to fix the bug in production",
        "user": "U12345",
        "ts": "1234567890.123456"
      }
    ]
  }'
```

## Configuration

All configuration is done via environment variables in `.env`:
- `SLACK_BOT_TOKEN`: Slack bot token
- `OPENAI_API_KEY`: OpenAI API key
- `LLM_PROVIDER`: LLM provider (default: openai)
- `SLACK_CHANNEL_NAME`: Channel to fetch messages from
- `SLACK_MESSAGE_LIMIT`: Max messages to fetch
- `SLACK_MINUTES_AGO`: Time filter for messages

## Extensibility

### Adding a New LLM Provider
1. Create a new class in `llm/client.py` that inherits from `LLMClient`
2. Implement the `generate()` method
3. Add provider to `create_llm_client()` factory function

### Adding New Extraction Tasks
1. Create new prompt template in `prompts/`
2. Create new service in `services/` (or extend `TodoExtractor`)
3. Add new API endpoint in `api/app.py`

