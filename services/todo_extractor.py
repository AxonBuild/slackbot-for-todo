"""Service for extracting todos from messages using LLM with function calling."""

import logging
import json
from typing import List, Dict, Any, Optional
from llm.client import LLMClient

logger = logging.getLogger(__name__)


class TodoExtractor:
    """Service to extract todos from messages using LLM with function calling."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize TodoExtractor.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
    
    def extract_todos(
        self, 
        messages: List[Dict[str, Any]], 
        last_bot_message: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract todos from a list of messages using function calling.
        
        Args:
            messages: List of message dictionaries with 'text', 'user', 'ts' keys
            last_bot_message: Optional last message sent by the bot (to avoid duplicates)
        
        Returns:
            List of extracted todo dictionaries
        """
        if not messages:
            logger.warning("No messages provided for todo extraction")
            return []
        
        logger.info(f"Starting todo extraction from {len(messages)} messages")
        if last_bot_message:
            logger.info("Including last bot message context to avoid duplicates")
        
        # Import here to avoid circular imports
        from prompts.todo_extraction import (
            get_todo_extraction_prompt,
            get_todo_extraction_function_schema
        )
        
        # Generate prompt with optional last bot message context
        prompt = get_todo_extraction_prompt(messages, last_bot_message)
        
        # Log the prompt
        logger.debug("=" * 80)
        logger.debug("PROMPT FORMED:")
        logger.debug("=" * 80)
        logger.debug(prompt)
        logger.debug("=" * 80)
        
        # Get function schema
        tools = get_todo_extraction_function_schema()
        
        # Get LLM response with function calling
        try:
            response = self.llm_client.generate_with_tools(
                prompt=prompt,
                tools=tools,
                temperature=0.3,
                max_tokens=2000
            )
            
            # Log the LLM response
            logger.debug("=" * 80)
            logger.debug("LLM CALL RESPONSE:")
            logger.debug("=" * 80)
            import json
            logger.debug(json.dumps(response, indent=2))
            logger.debug("=" * 80)
            
            # Parse tool call results
            todos = self._parse_tool_calls(response)
            logger.info(f"Successfully extracted {len(todos)} todos")
            
            # Log the final parsed todos
            logger.debug("=" * 80)
            logger.debug("PARSED TODOS RESULT:")
            logger.debug("=" * 80)
            for i, todo in enumerate(todos, 1):
                logger.debug(f"\nTodo #{i}:")
                logger.debug(f"  Description: {todo.get('description', 'N/A')}")
                logger.debug(f"  Assigned to: {todo.get('assigned_to', 'N/A')}")
                logger.debug(f"  Full todo data: {todo}")
            logger.debug("=" * 80)
            
            return todos
        except Exception as e:
            logger.error(f"Error extracting todos: {str(e)}", exc_info=True)
            return []
    
    def _parse_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse tool call response into structured todos.
        
        Args:
            response: Dictionary with 'content' and 'tool_calls' keys
        
        Returns:
            List of todo dictionaries
        """
        todos = []
        
        try:
            # Check if we have tool calls
            if not response.get("tool_calls"):
                logger.warning("No tool calls found in LLM response")
                return []
            
            logger.debug(f"Processing {len(response['tool_calls'])} tool calls")
            
            # Process each tool call
            for tool_call in response["tool_calls"]:
                function = tool_call.get("function", {})
                function_name = function.get("name")
                arguments_str = function.get("arguments", "{}")
                
                logger.debug(f"Processing tool call: {function_name}")
                
                if function_name == "extract_todos":
                    # Parse the arguments JSON
                    try:
                        arguments = json.loads(arguments_str)
                        todos_list = arguments.get("todos", [])
                        logger.debug(f"Found {len(todos_list)} todos in tool call arguments")
                        
                        # Validate and normalize todos
                        for todo in todos_list:
                            if isinstance(todo, dict) and "description" in todo:
                                validated_todo = {
                                    "description": todo.get("description", ""),
                                    "assigned_to": todo.get("assigned_to")
                                }
                                todos.append(validated_todo)
                                logger.debug(f"Validated todo: {validated_todo['description'][:50]}...")
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing function arguments: {str(e)}")
                        logger.debug(f"Arguments were: {arguments_str[:200]}...")
                        continue
            
            return todos
        except Exception as e:
            logger.error(f"Error processing tool calls: {str(e)}", exc_info=True)
            return []

