"""FastAPI application for todo extraction API."""

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from llm.client import create_llm_client
from services.todo_extractor import TodoExtractor
from services.slack_service import SlackService
from utils.logger import setup_logging

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Slack Todo Extraction API",
    description="API to extract todos from Slack messages using LLM",
    version="1.0.0"
)

# Initialize services
llm_client = None
todo_extractor = None
slack_service = None
scheduler = None


def initialize_services():
    """Initialize LLM client, todo extractor, and Slack service."""
    global llm_client, todo_extractor, slack_service
    
    if llm_client is None:
        provider = os.getenv("LLM_PROVIDER", "openai")
        model = os.getenv("LLM_MODEL")  # Optional model override
        kwargs = {}
        if model:
            kwargs["model"] = model
        logger.info(f"Initializing LLM client with provider: {provider}, model: {model or 'default'}")
        llm_client = create_llm_client(provider=provider, **kwargs)
        todo_extractor = TodoExtractor(llm_client)
        logger.info("LLM client and TodoExtractor initialized")
    
    if slack_service is None:
        logger.info("Initializing Slack service")
        slack_service = SlackService()
        logger.info("Slack service initialized")


def perform_todo_extraction():
    """
    Perform todo extraction from Slack messages.
    This function is called by the scheduler.
    """
    logger.info("=" * 80)
    logger.info("SCHEDULED TODO EXTRACTION STARTED")
    logger.info("=" * 80)
    
    try:
        if not todo_extractor:
            initialize_services()
        
        # Get configuration from environment
        channel_name = os.getenv("SLACK_CHANNEL_NAME")
        if not channel_name:
            logger.error("SLACK_CHANNEL_NAME environment variable is missing")
            return
        
        minutes_ago = os.getenv("SLACK_MINUTES_AGO")
        if minutes_ago:
            minutes_ago = int(minutes_ago)
        else:
            minutes_ago = None
        
        limit = int(os.getenv("SLACK_MESSAGE_LIMIT", "100"))
        
        logger.info(f"Configuration: channel={channel_name}, minutes_ago={minutes_ago}, limit={limit}")
        
        # Initialize services if needed
        if not slack_service:
            initialize_services()
        
        # Fetch messages from Slack
        logger.info(f"Fetching messages from Slack channel: {channel_name}")
        try:
            messages = slack_service.get_channel_messages(channel_name, minutes_ago, limit)
            logger.info(f"Retrieved {len(messages)} messages from Slack")
        except Exception as e:
            logger.error(f"Error fetching messages: {str(e)}", exc_info=True)
            return
        
        if not messages:
            logger.warning("No messages found in the specified time window")
            return
        
        # Extract todos
        logger.info(f"Extracting todos from {len(messages)} messages using LLM")
        todos = todo_extractor.extract_todos(messages)
        logger.info(f"Extracted {len(todos)} todos from messages")
        
        # Log the results
        if todos:
            logger.info("Extracted Todos:")
            for i, todo in enumerate(todos, 1):
                logger.info(f"  {i}. {todo.get('description', 'N/A')} (Assigned to: {todo.get('assigned_to', 'N/A')})")
            
            # Post todos to Slack channel if enabled
            post_to_slack = os.getenv("POST_TODOS_TO_SLACK", "true").lower() == "true"
            if post_to_slack:
                try:
                    _post_todos_to_slack(channel_name, todos)
                except Exception as e:
                    logger.error(f"Error posting todos to Slack: {str(e)}", exc_info=True)
        else:
            logger.info("No todos found in the messages")
        
        logger.info("=" * 80)
        logger.info("SCHEDULED TODO EXTRACTION COMPLETED")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error in scheduled todo extraction: {str(e)}", exc_info=True)


def _post_todos_to_slack(channel_name: str, todos: List[Dict[str, Any]]):
    """
    Post extracted todos to Slack channel.
    
    Args:
        channel_name: Name of the Slack channel
        todos: List of todo dictionaries
    """
    if not slack_service:
        initialize_services()
    
    logger.info(f"Posting {len(todos)} todos to Slack channel: {channel_name}")
    
    # Format todos for Slack
    if len(todos) == 1:
        header = f"📋 *1 Todo Found*"
    else:
        header = f"📋 *{len(todos)} Todos Found*"
    
    # Build message text
    message_text = f"{header}\n\n"
    for i, todo in enumerate(todos, 1):
        description = todo.get('description', 'N/A')
        assigned_to = todo.get('assigned_to')
        
        todo_line = f"*{i}.* {description}"
        if assigned_to:
            todo_line += f" (Assigned to: {assigned_to})"
        message_text += f"{todo_line}\n"
    
    # Create Slack blocks for better formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header,
                "emoji": True
            }
        },
        {
            "type": "divider"
        }
    ]
    
    # Add each todo as a section
    for i, todo in enumerate(todos, 1):
        description = todo.get('description', 'N/A')
        assigned_to = todo.get('assigned_to')
        
        todo_text = f"*{i}.* {description}"
        if assigned_to:
            todo_text += f"\n👤 Assigned to: {assigned_to}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": todo_text
            }
        })
        
        # Add divider between todos (except after the last one)
        if i < len(todos):
            blocks.append({"type": "divider"})
    
    # Post to Slack
    slack_service.post_message(channel_name, message_text, blocks=blocks)
    logger.info("Successfully posted todos to Slack")


# Initialize on startup
@app.on_event("startup")
async def startup_event():
    global scheduler
    
    logger.info("Starting up Slack Todo Extraction API")
    initialize_services()
    
    # Set up scheduler for automatic todo extraction
    scheduler_interval = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "30"))
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    
    if scheduler_enabled:
        logger.info(f"Setting up scheduler to run every {scheduler_interval} minutes")
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            perform_todo_extraction,
            trigger=IntervalTrigger(minutes=scheduler_interval),
            id="todo_extraction_job",
            name="Extract todos from Slack",
            replace_existing=True
        )
        scheduler.start()
        logger.info("Scheduler started successfully")
    else:
        logger.info("Scheduler is disabled (set SCHEDULER_ENABLED=false to disable)")
    
    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    global scheduler
    
    logger.info("Shutting down Slack Todo Extraction API")
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    logger.info("API shutdown complete")


# Response models
class Todo(BaseModel):
    """Todo model."""
    description: str
    assigned_to: Optional[str] = None


class ExtractTodosResponse(BaseModel):
    """Response model for todo extraction."""
    todos: List[Todo]
    total_messages: int
    todos_found: int
    channel: Optional[str] = None
    time_window_minutes: Optional[int] = None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Slack Todo Extraction API",
        "version": "1.0.0",
        "endpoints": {
            "GET /extract-todos": "Extract todos from Slack channel (uses env config)"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {"status": "healthy"}




@app.get("/extract-todos", response_model=ExtractTodosResponse)
async def extract_todos_from_slack():
    """
    Extract todos from Slack channel based on environment configuration.
    
    Uses environment variables:
    - SLACK_CHANNEL_NAME: Channel to fetch messages from
    - SLACK_MINUTES_AGO: Number of minutes to look back (optional)
    - SLACK_MESSAGE_LIMIT: Maximum messages to retrieve (default: 100)
    
    Returns:
        ExtractTodosResponse with extracted todos
    """
    logger.info("Extract todos endpoint called")
    
    if not todo_extractor:
        initialize_services()
    
    # Get configuration from environment
    channel_name = os.getenv("SLACK_CHANNEL_NAME")
    if not channel_name:
        logger.error("SLACK_CHANNEL_NAME environment variable is missing")
        raise HTTPException(
            status_code=400,
            detail="SLACK_CHANNEL_NAME environment variable is required"
        )
    
    minutes_ago = os.getenv("SLACK_MINUTES_AGO")
    if minutes_ago:
        minutes_ago = int(minutes_ago)
    else:
        minutes_ago = None
    
    limit = int(os.getenv("SLACK_MESSAGE_LIMIT", "100"))
    
    logger.info(f"Configuration: channel={channel_name}, minutes_ago={minutes_ago}, limit={limit}")
    
    # Initialize services if needed
    if not slack_service:
        initialize_services()
    
    # Fetch messages from Slack
    logger.info(f"Fetching messages from Slack channel: {channel_name}")
    try:
        messages = slack_service.get_channel_messages(channel_name, minutes_ago, limit)
        logger.info(f"Retrieved {len(messages)} messages from Slack")
    except ValueError as e:
        logger.error(f"Error fetching messages: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching messages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    if not messages:
        logger.warning("No messages found in the specified time window")
        return ExtractTodosResponse(
            todos=[],
            total_messages=0,
            todos_found=0,
            channel=channel_name,
            time_window_minutes=minutes_ago
        )
    
    # Extract todos
    logger.info(f"Extracting todos from {len(messages)} messages using LLM")
    todos = todo_extractor.extract_todos(messages)
    logger.info(f"Extracted {len(todos)} todos from messages")
    
    # Post todos to Slack if enabled and todos found
    if todos:
        post_to_slack = os.getenv("POST_TODOS_TO_SLACK", "true").lower() == "true"
        if post_to_slack:
            try:
                _post_todos_to_slack(channel_name, todos)
            except Exception as e:
                logger.error(f"Error posting todos to Slack: {str(e)}", exc_info=True)
                # Don't fail the request if posting to Slack fails
    
    # Convert to response model
    todos_response = [
        Todo(
            description=todo["description"],
            assigned_to=todo.get("assigned_to")
        )
        for todo in todos
    ]
    
    logger.info(f"Returning {len(todos_response)} todos")
    return ExtractTodosResponse(
        todos=todos_response,
        total_messages=len(messages),
        todos_found=len(todos_response),
        channel=channel_name,
        time_window_minutes=minutes_ago
    )


def create_app():
    """Factory function to create the FastAPI app."""
    return app

