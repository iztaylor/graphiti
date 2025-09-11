# JSON Logging Configuration

This FastAPI application has been configured to output structured JSON logs for better observability and parsing.

## Features

### 1. JSON Formatted Logs
- All logs are output in structured JSON format
- Consistent timestamp, level, logger name, and message fields
- Support for additional custom fields

### 2. Request/Response Logging Middleware
- Automatically logs all incoming requests and outgoing responses
- Includes request ID for correlation across log entries
- Logs request method, URL, headers, client info
- Logs response status code, headers, and duration
- Does NOT log request/response bodies for security and performance

### 3. Uvicorn Integration
- Uses `uvicorn.error` logger for custom application messages
- Access logs formatted as JSON with structured fields
- Configurable log levels via uvicorn CLI options

## Log Output Examples

### Application Log
```json
{
  "timestamp": "2023-12-01T10:30:45.123456",
  "level": "INFO",
  "logger": "uvicorn.error",
  "message": "Starting up Graph Service"
}
```

### Request Log
```json
{
  "timestamp": "2023-12-01T10:30:45.123456",
  "level": "INFO",
  "logger": "uvicorn.error",
  "message": "Incoming request",
  "type": "request",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "POST",
  "url": "http://localhost:8000/search",
  "path": "/search",
  "query_params": {},
  "headers": {...},
  "client_host": "127.0.0.1"
}
```

### Response Log
```json
{
  "timestamp": "2023-12-01T10:30:45.234567",
  "level": "INFO",
  "logger": "uvicorn.error",
  "message": "Outgoing response",
  "type": "response",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status_code": 200,
  "headers": {...},
  "duration_seconds": 0.1234
}
```

### Business Logic Log with Request ID
```json
{
  "timestamp": "2023-12-01T10:30:45.200000",
  "level": "INFO",
  "logger": "uvicorn.error",
  "message": "Performing search with query: machine learning algorithms...",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## Usage in Application Code

### Basic Logging
```python
import logging

logger = logging.getLogger('uvicorn.error')
logger.info("This will be logged as JSON")
```

### Request-Aware Logging
```python
from fastapi import Request
from graph_service.middleware import get_logger_with_request_id

async def my_endpoint(request: Request):
    logger = get_logger_with_request_id(request)
    logger.info("This log will include the request ID automatically")
```

### Getting Request ID
```python
from fastapi import Request
from graph_service.middleware import get_request_id

async def my_endpoint(request: Request):
    request_id = get_request_id(request)
    # Use request_id for correlation
```

## Configuration

### Log Levels
Control log level via uvicorn CLI:
```bash
uvicorn main:app --log-level debug
uvicorn main:app --log-level info
uvicorn main:app --log-level warning
```

### Log Configuration File
The JSON formatters are configured in `log_conf.yaml`:
- `default` formatter: For general application logs
- `access` formatter: For HTTP access logs

### Disable Access Logs
To disable access logs while keeping other logs:
```bash
uvicorn main:app --no-access-log
```

## Integration with Log Aggregation

The JSON format makes it easy to integrate with log aggregation systems:
- **ELK Stack**: Direct JSON parsing in Logstash
- **Fluentd**: Native JSON support
- **Splunk**: JSON parsing with automatic field extraction
- **CloudWatch**: Structured log queries
- **Datadog**: Automatic log parsing and filtering

## Security Considerations

- Request and response bodies are NOT logged
- Sensitive headers can be filtered by modifying the middleware
- Request IDs are UUIDs and don't contain sensitive information
- Consider scrubbing authorization headers if needed
