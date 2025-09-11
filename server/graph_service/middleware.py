import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variables for trace propagation
trace_id_context: ContextVar[str] = ContextVar('trace_id', default='')
span_id_context: ContextVar[str] = ContextVar('span_id', default='')


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log request and response information without bodies.
    Adds request ID for correlation and logs timing information.
    """
    
    def __init__(self, app, logger_name: str = "uvicorn.error"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique IDs for tracing
        trace_id = request.headers.get('x-trace-id', str(uuid.uuid4()))
        span_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())  # Keep request_id for backwards compatibility
        
        # Set context variables for trace propagation
        trace_id_context.set(trace_id)
        span_id_context.set(span_id)
        
        # Record start time
        start_time = time.time()
        
        # Extract request information
        request_info = {
            'request_id': request_id,
            'trace_id': trace_id,
            'span_id': span_id,
            'method': request.method,
            'url': str(request.url),
            'path': request.url.path,
            'query_params': dict(request.query_params),
            'headers': dict(request.headers),
            'client_host': getattr(request.client, 'host', None) if request.client else None,
            'client_port': getattr(request.client, 'port', None) if request.client else None,
        }
        
        # Log incoming request
        self.logger.info(
            "Incoming request",
            extra={
                'type': 'request',
                'request_id': request_id,
                'trace_id': trace_id,
                'span_id': span_id,
                **request_info
            }
        )
        
        # Add IDs to request state for use in other parts of the application
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Extract response information
            response_info = {
                'request_id': request_id,
                'trace_id': trace_id,
                'span_id': span_id,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'duration_seconds': round(duration, 4),
            }
            
            # Add trace headers to response
            response.headers['x-trace-id'] = trace_id
            response.headers['x-span-id'] = span_id
            
            # Log outgoing response
            self.logger.info(
                "Outgoing response",
                extra={
                    'type': 'response',
                    'trace_id': trace_id,
                    'span_id': span_id,
                    **response_info
                }
            )
            
            return response
            
        except Exception as exc:
            # Calculate duration even for errors
            duration = time.time() - start_time
            
            # Log error
            self.logger.error(
                f"Request failed: {str(exc)}",
                extra={
                    'type': 'error',
                    'request_id': request_id,
                    'trace_id': trace_id,
                    'span_id': span_id,
                    'duration_seconds': round(duration, 4),
                    'exception_type': type(exc).__name__,
                }
            )
            
            # Re-raise the exception
            raise


def get_request_id(request: Request) -> str:
    """
    Helper function to get the request ID from the request state.
    Returns empty string if no request ID is found.
    """
    return getattr(request.state, 'request_id', '')


def get_trace_id(request: Request) -> str:
    """
    Helper function to get the trace ID from the request state.
    Returns empty string if no trace ID is found.
    """
    return getattr(request.state, 'trace_id', '')


def get_span_id(request: Request) -> str:
    """
    Helper function to get the span ID from the request state.
    Returns empty string if no span ID is found.
    """
    return getattr(request.state, 'span_id', '')


def get_trace_context() -> dict[str, str]:
    """
    Helper function to get the current trace context from context variables.
    This works across async calls within the same request.
    """
    return {
        'trace_id': trace_id_context.get(''),
        'span_id': span_id_context.get('')
    }


def create_child_span() -> str:
    """
    Create a new child span ID for sub-operations while keeping the same trace ID.
    Returns the new span ID.
    """
    child_span_id = str(uuid.uuid4())
    span_id_context.set(child_span_id)
    return child_span_id


def get_logger_with_request_id(request: Request, logger_name: str = "uvicorn.error") -> logging.LoggerAdapter:
    """
    Helper function to get a logger adapter that automatically includes the request ID.
    """
    logger = logging.getLogger(logger_name)
    request_id = get_request_id(request)
    return logging.LoggerAdapter(logger, {'request_id': request_id})


def get_logger_with_trace_context(request: Request = None, logger_name: str = "uvicorn.error") -> logging.LoggerAdapter:
    """
    Helper function to get a logger adapter that automatically includes trace and span IDs.
    If request is provided, gets context from request state.
    Otherwise, gets context from context variables (works across async calls).
    """
    logger = logging.getLogger(logger_name)
    
    if request:
        # Get from request state
        context = {
            'request_id': get_request_id(request),
            'trace_id': get_trace_id(request),
            'span_id': get_span_id(request)
        }
    else:
        # Get from context variables
        trace_context = get_trace_context()
        context = {
            'trace_id': trace_context['trace_id'],
            'span_id': trace_context['span_id']
        }
    
    return logging.LoggerAdapter(logger, context)
