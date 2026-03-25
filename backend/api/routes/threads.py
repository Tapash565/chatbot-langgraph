"""Thread API routes."""
from fastapi import APIRouter, Request

from backend.models import ThreadCreate, ThreadUpdate, ThreadResponse, ThreadListResponse
from backend.services.thread_service import ThreadService
from backend.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["threads"])


def get_thread_service(request: Request) -> ThreadService:
    """Get thread service from app state."""
    return request.app.state.thread_service


@router.get("/threads", response_model=ThreadListResponse)
async def get_threads(request: Request) -> ThreadListResponse:
    """Get all threads sorted by last active."""
    thread_service = get_thread_service(request)
    threads = await thread_service.get_all_threads()
    return ThreadListResponse(threads=threads)


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(body: ThreadCreate, request: Request) -> ThreadResponse:
    """Create a new thread."""
    thread_service = get_thread_service(request)
    thread = await thread_service.create_thread(body.name)
    return ThreadResponse(**thread)


@router.put("/threads/{thread_id}", response_model=ThreadResponse)
async def rename_thread(
    thread_id: str,
    body: ThreadUpdate,
    request: Request,
) -> ThreadResponse:
    """Rename a thread."""
    thread_service = get_thread_service(request)
    await thread_service.rename_thread(thread_id, body.name)
    thread = await thread_service.get_thread(thread_id)
    return ThreadResponse(**thread)


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, request: Request) -> dict:
    """Delete a thread and all related data."""
    thread_service = get_thread_service(request)
    await thread_service.delete_thread(thread_id)
    return {"deleted": True, "thread_id": thread_id}


@router.get("/threads/{thread_id}/document")
async def get_thread_document(
    thread_id: str,
    request: Request,
) -> dict:
    """Get document metadata for a thread."""
    thread_service = get_thread_service(request)
    status = thread_service.get_document_status(thread_id)
    return status


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str,
    request: Request,
) -> dict:
    """Get normalized message history for a thread."""
    thread_service = get_thread_service(request)
    messages = await thread_service.get_thread_messages(thread_id)
    return {"messages": messages}
