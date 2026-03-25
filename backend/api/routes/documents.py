"""Document API routes."""
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException

from backend.models import DocumentUploadResponse
from backend.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["documents"])

# Maximum PDF file size (10MB)
MAX_PDF_SIZE = 10 * 1024 * 1024


def get_document_service_from_request(request: Request):
    """Get document service from app state."""
    return request.app.state.document_service


@router.post("/pdf/upload", response_model=DocumentUploadResponse)
async def upload_pdf(
    request: Request,
    file: UploadFile = File(..., max_length=MAX_PDF_SIZE),
    thread_id: str = Form(...),
):
    """
    Upload and index a PDF document.

    - **file**: PDF file to upload (max 10MB)
    - **thread_id**: Thread ID for the conversation
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read file content
    content = await file.read()

    document_service = get_document_service_from_request(request)

    try:
        result = await document_service.upload_pdf(
            file_content=content,
            thread_id=thread_id,
            filename=file.filename,
        )
        return DocumentUploadResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("pdf_upload_api_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process PDF")
