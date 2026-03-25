
"""FastAPI application entry point."""
import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_groq import ChatGroq

from backend.core.logging import get_logger, configure_logging

# Import backend modules
from backend.core.config import config
from backend.db.repositories import thread_repository
from backend.retrieval.retriever import thread_retriever
from backend.agents.graph import ChatAgent
from backend.tools import tools
from backend.services.chat_service import ChatService
from backend.services.thread_service import ThreadService
from backend.services.document_service import get_document_service
from backend.api.routes import chat, threads, documents, health

# Configure logging
configure_logging(level="INFO", json_format=True)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("application_starting")

    # Initialize database tables
    thread_repository.init_tables()

    # Restore FAISS indices
    try:
        restored = thread_retriever.restore_all()
        logger.info("faiss_indices_restored", count=restored)
    except Exception as e:
        logger.warning("faiss_restore_error", error=str(e))

    # Initialize LLM and agent
    llm = ChatGroq(
        model=config.GROQ_MODEL,
        temperature=config.LLM_TEMPERATURE,
    )
    llm_with_tools = llm.bind_tools(tools)

    # Create agent
    agent = ChatAgent(llm, llm_with_tools)

    # Initialize services
    chat_service = ChatService(agent)
    thread_service = ThreadService(agent)
    document_service = get_document_service(agent)

    # Store in app state
    app.state.chat_service = chat_service
    app.state.thread_service = thread_service
    app.state.document_service = document_service
    app.state.agent = agent

    logger.info("application_started")

    yield

    logger.info("application_shutdown")


# Create FastAPI app
app = FastAPI(
    title="LangGraph Chatbot API",
    description="API for the LangGraph chatbot with streaming support",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    # Log request
    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Log response
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(threads.router, prefix="/api")
app.include_router(documents.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LangGraph Chatbot API",
        "docs": "/docs",
        "health": "/api/health"
    }
