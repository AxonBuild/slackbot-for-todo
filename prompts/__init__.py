"""Prompt templates for various tasks."""

from .todo_extraction import (
    get_todo_extraction_prompt,
    get_todo_extraction_function_schema
)

__all__ = ['get_todo_extraction_prompt', 'get_todo_extraction_function_schema']

