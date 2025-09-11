# Request Tracing Guide

This document explains how to use the request tracing functionality in the Graphiti Graph Service.

## Overview

The service now includes comprehensive request tracing that allows you to track requests across all sub-function calls. Each request is assigned:

- **Trace ID**: A unique identifier that remains constant throughout the entire request lifecycle
- **Span ID**: A unique identifier for each operation within a request (can change for sub-operations)

## How It Works

### Automatic Trace Generation

1. **Middleware**: The `RequestResponseLoggingMiddleware` automatically generates trace and span IDs for each incoming request
2. **Header Support**: If a client sends an `x-trace-id` header, that trace ID will be used instead of generating a new one
3. **Context Propagation**: Trace context is propagated across async operations using Python's `contextvars`

### Trace Information in Logs

All log entries now include trace information:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "logger": "uvicorn.error",
  "message": "Performing search with query: machine learning...",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "trace_id": "trace-12345678-abcd-ef12-3456-789012345678",
  "span_id": "span-87654321-dcba-21fe-6543-210987654321"
}
```

### Response Headers

Each response includes trace headers:
- `x-trace-id`: The trace ID for correlation
- `x-span-id`: The span ID for the main request

## Usage Examples

### Client-Side Tracing

Send a request with an existing trace ID:

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -H "x-trace-id: my-custom-trace-id-12345" \
  -d '{"query": "test query", "max_facts": 10}'
```

### Log Correlation

Use the trace ID to find all log entries related to a specific request:

```bash
# Search logs for a specific trace
grep "trace-12345678-abcd-ef12-3456-789012345678" application.log
```

### Sub-Function Tracing

The trace context is automatically propagated to:

1. **Graphiti Core Operations**: `add_episode`, `search`, etc.
2. **Async Worker Tasks**: Background processing maintains trace context
3. **Database Operations**: All graph operations include trace information
4. **LLM Client Calls**: AI model calls are traced
5. **Embedding Operations**: Vector embedding generation is traced

## Integration with Monitoring Systems

The structured JSON logs with trace information make it easy to integrate with:

- **Jaeger**: Use trace_id for distributed tracing
- **Zipkin**: Compatible trace format
- **DataDog APM**: Automatic trace correlation
- **New Relic**: Trace-based monitoring
- **ELK Stack**: Log aggregation by trace_id
- **Splunk**: Trace-based log analysis

## Programmatic Access

### Server-Side Code

Access trace information in your code:

```python
from graph_service.middleware import (
    get_trace_id, 
    get_span_id, 
    get_logger_with_trace_context
)

async def my_endpoint(request: Request):
    # Get trace information
    trace_id = get_trace_id(request)
    span_id = get_span_id(request)
    
    # Use logger with trace context
    logger = get_logger_with_trace_context(request)
    logger.info("Processing request with custom logic")
    
    # Trace context is automatically passed to Graphiti methods
    await graphiti.search(query="test", trace_id=trace_id, span_id=span_id)
```

### Graphiti Core

The Graphiti core methods now accept trace parameters:

```python
# In your application code
results = await graphiti.add_episode(
    name="test episode",
    episode_body="content",
    source_description="test",
    reference_time=datetime.now(),
    trace_id="custom-trace-id",
    span_id="custom-span-id"
)

edges = await graphiti.search(
    query="search query",
    trace_id="custom-trace-id", 
    span_id="custom-span-id"
)
```

## Performance Considerations

- **Minimal Overhead**: Context variables add negligible performance impact
- **Async Safe**: Full compatibility with async/await patterns
- **Memory Efficient**: Context is automatically cleaned up after requests
- **Non-Blocking**: Tracing doesn't affect request processing speed

## Best Practices

1. **Unique Trace IDs**: Use UUIDs for trace IDs to avoid collisions
2. **Meaningful Span IDs**: Create child spans for major sub-operations
3. **Log Correlation**: Always include trace context in custom logs
4. **Error Handling**: Trace context is preserved in error scenarios
5. **Testing**: Use fixed trace IDs in tests for reproducible results

## Example Request Flow

```
1. Client Request → [trace-123, span-abc]
   ├── Middleware Logging → [trace-123, span-abc]
   ├── API Endpoint → [trace-123, span-abc]
   ├── Graphiti Search → [trace-123, span-abc]
   │   ├── Vector Search → [trace-123, span-def] (child)
   │   ├── Text Search → [trace-123, span-ghi] (child)
   │   └── Reranking → [trace-123, span-jkl] (child)
   ├── Response Building → [trace-123, span-abc]
   └── Client Response → Headers: x-trace-id: trace-123
```

All operations maintain the same trace ID while potentially creating new span IDs for sub-operations.
