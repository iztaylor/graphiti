"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Context variables for trace propagation across async calls
trace_id_context: ContextVar[str] = ContextVar('trace_id', default='')
span_id_context: ContextVar[str] = ContextVar('span_id', default='')


class TraceContext:
    """
    Utility class for managing trace context in Graphiti core operations.
    Provides methods to get, set, and propagate trace information across
    function calls and async operations.
    """
    
    @staticmethod
    def get_current_trace_context() -> Dict[str, str]:
        """
        Get the current trace context from context variables.
        
        Returns:
            Dict containing trace_id and span_id
        """
        return {
            'trace_id': trace_id_context.get(''),
            'span_id': span_id_context.get('')
        }
    
    @staticmethod
    def set_trace_context(trace_id: str, span_id: str) -> None:
        """
        Set the trace context for the current execution context.
        
        Args:
            trace_id: The trace ID to set
            span_id: The span ID to set
        """
        trace_id_context.set(trace_id)
        span_id_context.set(span_id)
    
    @staticmethod
    def create_child_span(parent_span_id: Optional[str] = None) -> str:
        """
        Create a new child span while keeping the same trace ID.
        
        Args:
            parent_span_id: Optional parent span ID. If not provided, uses current span.
            
        Returns:
            The new child span ID
        """
        child_span_id = str(uuid.uuid4())
        span_id_context.set(child_span_id)
        return child_span_id
    
    @staticmethod
    def get_logger_with_trace(logger_name: str = __name__) -> logging.LoggerAdapter:
        """
        Get a logger adapter that includes trace context in all log entries.
        
        Args:
            logger_name: Name of the logger to create
            
        Returns:
            LoggerAdapter with trace context
        """
        logger = logging.getLogger(logger_name)
        context = TraceContext.get_current_trace_context()
        return logging.LoggerAdapter(logger, context)
    
    @staticmethod
    def add_trace_to_extra(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add trace context to an extra dictionary for logging.
        
        Args:
            extra: Existing extra dict to add trace context to
            
        Returns:
            Dictionary with trace context added
        """
        if extra is None:
            extra = {}
        
        trace_context = TraceContext.get_current_trace_context()
        extra.update(trace_context)
        return extra
