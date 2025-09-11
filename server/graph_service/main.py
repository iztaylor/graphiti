import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from graph_service.config import get_settings
from graph_service.middleware import RequestResponseLoggingMiddleware
from graph_service.routers import ingest, retrieve, metrics
from graph_service.zep_graphiti import initialize_graphiti

# Use uvicorn.error logger for custom messages as recommended in the Stack Overflow answer
logger = logging.getLogger('uvicorn.error')


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up Graph Service")
    settings = get_settings()
    await initialize_graphiti(settings)
    logger.info("Graph Service startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Graph Service")
    # No need to close Graphiti here, as it's handled per-request


app = FastAPI(lifespan=lifespan)

# Add request/response logging middleware
app.add_middleware(RequestResponseLoggingMiddleware)

app.include_router(retrieve.router)
app.include_router(ingest.router)
app.include_router(metrics.router)


@app.get('/healthcheck')
async def healthcheck():
    logger.info("Health check requested")
    return JSONResponse(content={'status': 'healthy'}, status_code=200)
