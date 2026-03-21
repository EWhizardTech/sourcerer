"""FastAPI router for Google Drive ingestion.

Endpoint:
    POST /ingest/gdrive
        Accepts a Drive folder_id and returns a list of ingested files
        with metadata and base64-encoded content.
"""

import base64
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.gdrive_service import list_files_in_folder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestGDriveRequest(BaseModel):
    """Request body for the /ingest/gdrive endpoint."""

    folder_id: str  # Google Drive folder ID to ingest from.


class FileResponse(BaseModel):
    """Response schema for a single ingested file.

    content is base64-encoded because raw bytes are not JSON-serialisable.
    Downstream consumers should decode: base64.b64decode(content).
    """

    file_id: str
    file_name: str
    mime_type: str
    file_path: str
    modified_time: str
    content: str  # base64-encoded bytes.


@router.post("/gdrive", response_model=list[FileResponse])
async def ingest_gdrive(request: IngestGDriveRequest) -> list[FileResponse]:
    """Fetch and download all supported files from a Google Drive folder.

    Args:
        request: Contains the Drive folder_id to ingest.

    Returns:
        List of FileResponse objects, one per successfully ingested file.

    Raises:
        HTTPException 500: If the Drive API call fails.
    """
    logger.info("Received ingest request for folder_id=%s", request.folder_id)

    try:
        records = list_files_in_folder(request.folder_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Drive ingestion failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Google Drive ingestion failed: {exc}",
        ) from exc

    # Encode raw bytes to base64 string for JSON transport.
    return [
        FileResponse(
            file_id=r["file_id"],
            file_name=r["file_name"],
            mime_type=r["mime_type"],
            file_path=r["file_path"],
            modified_time=r["modified_time"],
            content=base64.b64encode(r["content"]).decode("utf-8"),
        )
        for r in records
    ]
