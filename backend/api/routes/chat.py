"""Chat API routes."""
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.models import ChatStreamRequest
from backend.services.chat_service import ChatService
from backend.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])


def get_chat_service(request: Request) -> ChatService:
    """Get chat service from app state."""
    return request.app.state.chat_service


@router.post("/chat/stream")
async def stream_chat(
    body: ChatStreamRequest,
    request: Request,
):
    """
    Stream chat responses using Server-Sent Events.

    Event types:
    - ai: AI message content
    - tool_call: Tool being invoked
    - tool: Tool result
    - done: Streaming complete
    - error: Error occurred
    """
    chat_service = get_chat_service(request)

    async def generate():
        try:
            async for event in chat_service.stream_chat(
                message=body.message,
                thread_id=body.thread_id,
            ):
                event_type = event.get("type")

                if event_type == "ai":
                    yield f"data: {json.dumps(event)}\n\n"

                elif event_type == "tool_call":
                    yield f"data: {json.dumps(event)}\n\n"

                elif event_type == "tool":
                    yield f"data: {json.dumps(event)}\n\n"

                elif event_type == "done":
                    yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error("chat_stream_error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
