import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs log records as JSON with consistent fields.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_entry: Dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
            
        if hasattr(record, 'trace_id'):
            log_entry['trace_id'] = record.trace_id
            
        if hasattr(record, 'span_id'):
            log_entry['span_id'] = record.span_id
            
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        # Add any extra fields that were passed to the logger
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                          'relativeCreated', 'thread', 'threadName', 'processName', 
                          'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info'):
                log_entry[key] = value
                
        return json.dumps(log_entry, default=str)


class UvicornAccessJSONFormatter(JSONFormatter):
    """
    Custom JSON formatter for Uvicorn access logs.
    Formats HTTP request logs in a structured way.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the access log record as JSON."""
        log_entry: Dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'type': 'access',
        }
        
        # Extract access log specific information
        if hasattr(record, 'client_addr'):
            log_entry['client_addr'] = record.client_addr
            
        if hasattr(record, 'request_line'):
            log_entry['request_line'] = record.request_line
            
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
            
        # Fallback to the original message if specific fields aren't available
        if not any(hasattr(record, attr) for attr in ['client_addr', 'request_line', 'status_code']):
            log_entry['message'] = record.getMessage()
            
        return json.dumps(log_entry, default=str)
