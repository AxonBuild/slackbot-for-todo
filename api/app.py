"""FastAPI application for todo extraction API."""

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

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
    description="API to extract todos from Slack messages using LLM - triggered by external schedulers",
    version="2.0.0"
)

# Initialize services (lazy initialization)
llm_client = None
todo_extractor = None
slack_service = None


def get_services():
    """Get or initialize services."""
    global llm_client, todo_extractor, slack_service
    
    if llm_client is None:
        provider = os.getenv("LLM_PROVIDER", "openai")
        logger.info(f"Initializing LLM client with provider: {provider}")
        llm_client = create_llm_client(provider=provider)
        todo_extractor = TodoExtractor(llm_client)
        logger.info("LLM client and TodoExtractor initialized")
    
    if slack_service is None:
        logger.info("Initializing Slack service")
        slack_service = SlackService()
        logger.info("Slack service initialized")
    
    return slack_service, todo_extractor


# Removed scheduler function - API is now triggered by external schedulers


def _post_todos_to_slack(channel_name_or_id: str, todos: List[Dict[str, Any]], service: SlackService):
    """
    Post extracted todos to Slack channel.
    
    Args:
        channel_name_or_id: Name or ID of the Slack channel
        todos: List of todo dictionaries
        service: SlackService instance
    """
    logger.info(f"Posting {len(todos)} todos to Slack channel: {channel_name_or_id}")
    
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
    service.post_message(channel_name_or_id, message_text, blocks=blocks)
    logger.info("Successfully posted todos to Slack")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Slack Todo Extraction API v2.0")
    logger.info("API ready - waiting for external scheduler to trigger requests")
    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Slack Todo Extraction API")
    logger.info("API shutdown complete")


# Request and Response models
class Todo(BaseModel):
    """Todo model."""
    description: str
    assigned_to: Optional[str] = None


class ExtractTodosRequest(BaseModel):
    """Request model for todo extraction."""
    minutes_ago: Optional[int] = Field(default=30, description="Number of minutes to look back for messages")
    message_limit: int = Field(default=100, description="Maximum messages to retrieve per channel", ge=1, le=1000)
    post_to_slack: bool = Field(default=True, description="Whether to post extracted todos back to Slack")
    channel_ids: Optional[List[str]] = Field(default=None, description="Specific channel IDs to process (None = all channels)")


class ChannelResult(BaseModel):
    """Result for a single channel."""
    channel_id: str
    channel_name: Optional[str] = None
    todos: List[Todo]
    total_messages: int
    todos_found: int


class ExtractTodosResponse(BaseModel):
    """Response model for todo extraction."""
    channels: List[ChannelResult]
    total_channels_processed: int
    total_todos_found: int
    total_messages_processed: int
    time_window_minutes: int


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Slack Todo Extraction API",
        "version": "2.0.0",
        "description": "Extract todos from Slack channels - designed to be triggered by external schedulers",
        "endpoints": {
            "POST /extract-todos": "Extract todos from all or specific Slack channels",
            "GET /channels": "List all channels the bot is a member of",
            "GET /health": "Health check"
        },
        "environment": {
            "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
            "slack_configured": bool(os.getenv("SLACK_BOT_TOKEN"))
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {"status": "healthy"}




@app.get("/channels")
async def list_channels():
    """
    List all channels the bot is a member of.
    
    Returns:
        List of channels with their IDs and names
    """
    logger.info("List channels endpoint called")
    
    slack_svc, _ = get_services()
    
    try:
        channels = slack_svc.list_channels()
        
        result = []
        for channel in channels:
            result.append({
                "id": channel.get("id"),
                "name": channel.get("name"),
                "is_channel": channel.get("is_channel", False),
                "is_group": channel.get("is_group", False),
                "is_im": channel.get("is_im", False),
                "is_mpim": channel.get("is_mpim", False),
            })
        
        logger.info(f"Returning {len(result)} channels")
        return {
            "channels": result,
            "total": len(result)
        }
    except Exception as e:
        logger.error(f"Error listing channels: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing channels: {str(e)}")


@app.post("/extract-todos", response_model=ExtractTodosResponse)
async def extract_todos_from_slack(request: ExtractTodosRequest):
    """
    Extract todos from Slack channels.
    
    Processes all channels the bot is a member of (or specific channels if provided).
    Designed to be called by external schedulers (e.g., cron, Airflow, etc.).
    
    Request body parameters:
    - minutes_ago: Number of minutes to look back (default: 30)
    - message_limit: Max messages per channel (default: 100)
    - post_to_slack: Whether to post todos back to channels (default: true)
    - channel_ids: Specific channel IDs to process (optional, default: all channels)
    
    Returns:
        ExtractTodosResponse with todos per channel
    """
    logger.info("=" * 80)
    logger.info("TODO EXTRACTION REQUEST RECEIVED")
    logger.info("=" * 80)
    logger.info(f"Config: minutes_ago={request.minutes_ago}, limit={request.message_limit}, post={request.post_to_slack}")
    
    slack_svc, extractor = get_services()
    
    try:
        # Get channels to process
        if request.channel_ids:
            logger.info(f"Processing specific channels: {request.channel_ids}")
            # Filter to requested channels
            all_channels = slack_svc.list_channels()
            channels = [ch for ch in all_channels if ch.get("id") in request.channel_ids]
            if not channels:
                raise HTTPException(status_code=404, detail=f"None of the specified channels found")
        else:
            logger.info("Processing all channels the bot is a member of")
            channels = slack_svc.list_channels()
        
        channel_names = [c.get('name', c.get('id', 'Unknown')) for c in channels]
        logger.info(f"Found {len(channels)} channels/conversations: {', '.join(channel_names)}")
        
        if not channels:
            logger.warning("No channels found")
            return ExtractTodosResponse(
                channels=[],
                total_channels_processed=0,
                total_todos_found=0,
                total_messages_processed=0,
                time_window_minutes=request.minutes_ago
            )
        
        # Process each channel
        channel_results = []
        total_todos = 0
        total_messages = 0
        
        for channel in channels:
            channel_name = channel.get('name', None)
            channel_id = channel.get('id', 'Unknown')
            
            channel_identifier = channel_name if channel_name else channel_id
            channel_display = f"#{channel_name}" if channel_name else f"DM:{channel_id}"
            
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing: {channel_display} (ID: {channel_id})")
            logger.info(f"{'=' * 60}")
            
            try:
                # Fetch messages
                messages = slack_svc.get_channel_messages(channel_id, request.minutes_ago, request.message_limit)
                logger.info(f"Retrieved {len(messages)} messages from {channel_display}")
                
                if not messages:
                    logger.info(f"No messages found in {channel_display}")
                    channel_results.append(ChannelResult(
                        channel_id=channel_id,
                        channel_name=channel_name,
                        todos=[],
                        total_messages=0,
                        todos_found=0
                    ))
                    continue
                
                total_messages += len(messages)
                
                # Extract todos
                logger.info(f"Extracting todos from {len(messages)} messages in {channel_display}")
                todos = extractor.extract_todos(messages)
                logger.info(f"Extracted {len(todos)} todos from {channel_display}")
                
                # Convert to response model
                todos_response = [
                    Todo(
                        description=todo["description"],
                        assigned_to=todo.get("assigned_to")
                    )
                    for todo in todos
                ]
                
                # Log todos
                if todos:
                    total_todos += len(todos)
                    logger.info(f"Extracted Todos from {channel_display}:")
                    for i, todo in enumerate(todos, 1):
                        logger.info(f"  {i}. {todo.get('description', 'N/A')} (Assigned to: {todo.get('assigned_to', 'N/A')})")
                    
                    # Post to Slack if requested
                    if request.post_to_slack and channel_identifier:
                        try:
                            _post_todos_to_slack(channel_identifier, todos, slack_svc)
                        except Exception as e:
                            logger.error(f"Error posting todos to {channel_display}: {str(e)}", exc_info=True)
                else:
                    logger.info(f"No todos found in {channel_display}")
                
                # Add to results
                channel_results.append(ChannelResult(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    todos=todos_response,
                    total_messages=len(messages),
                    todos_found=len(todos_response)
                ))
                
            except Exception as e:
                logger.error(f"Error processing {channel_display}: {str(e)}", exc_info=True)
                # Add error result
                channel_results.append(ChannelResult(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    todos=[],
                    total_messages=0,
                    todos_found=0
                ))
                continue
        
        logger.info("=" * 80)
        logger.info(f"TODO EXTRACTION COMPLETED - Total: {total_todos} todos, {total_messages} messages, {len(channels)} channels")
        logger.info("=" * 80)
        
        return ExtractTodosResponse(
            channels=channel_results,
            total_channels_processed=len(channels),
            total_todos_found=total_todos,
            total_messages_processed=total_messages,
            time_window_minutes=request.minutes_ago
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in todo extraction: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error extracting todos: {str(e)}")


def create_app():
    """Factory function to create the FastAPI app."""
    return app

