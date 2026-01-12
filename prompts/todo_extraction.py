"""Prompt templates and function schemas for todo extraction from messages."""

from typing import List, Dict, Any, Optional


def get_todo_extraction_function_schema() -> List[Dict[str, Any]]:
    """
    Get the function schema for todo extraction using tool calling.
    
    Returns:
        List of tool definitions for function calling
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "extract_todos",
                "description": "Extract todos, tasks, and action items from Slack messages. Call this function for each todo found.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todos": {
                            "type": "array",
                            "description": "List of todos extracted from the messages",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {
                                        "type": "string",
                                        "description": "Clear description of the todo/task"
                                    },
                                    "assigned_to": {
                                        "type": "string",
                                        "description": "Username or person assigned to the task (null if not mentioned)",
                                        "nullable": True
                                    }
                                },
                                "required": ["description"]
                            }
                        }
                    },
                    "required": ["todos"]
                }
            }
        }
    ]


def get_todo_extraction_prompt(
    messages: List[Dict[str, Any]], 
    last_bot_message: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a prompt for extracting todos from Slack messages.
    Now simplified since we use function calling for structured output.
    
    Args:
        messages: List of message dictionaries with 'text', 'user', 'ts' keys
        last_bot_message: Optional last message sent by this bot (to avoid duplicates)
    
    Returns:
        Formatted prompt string
    """
    # Format messages for the prompt
    messages_text = ""
    for msg in messages:
        # Use user_name if available (enriched), otherwise fallback to user (which should be name now)
        user = msg.get('user_name') or msg.get('user', 'Unknown')
        text = msg.get('text', '')
        # Use human-readable timestamp if available, otherwise use raw ts
        timestamp = msg.get('timestamp_readable', msg.get('ts', ''))
        messages_text += f"[{timestamp}] {user}: {text}\n"
    
        # Add context about previously extracted todos if available
    if last_bot_message:
        bot_text = last_bot_message.get('text', '')
        # Use human-readable timestamp if available, otherwise use raw ts
        bot_timestamp = last_bot_message.get('timestamp_readable', last_bot_message.get('ts', ''))
        
        bot_message_text = "# Last Bot Message from the Channel:\n"
        bot_message_text += f"[{bot_timestamp}] {bot_text}"
        
        special_instructions = "- Refer to the last bot message from the channel when extracting todos to avoid duplicates."
    else:
        bot_message_text = ""
        special_instructions = ""
    
    prompt = f"""
# Context:
## Slack Channel Conversation:
{messages_text}

{bot_message_text}

# Task
- Analyze the Slack conversation and extract all todos and action items that are still pending and need to be done.
- If an imperative sentence is said by person X, that is a todo for person Y.
{special_instructions}
    
For each todo, identify:
- The task description
- Who it's assigned to (if mentioned)

Use the extract_todos function to record all found todos. If no todos are found, call the function with an empty array."""

    return prompt
