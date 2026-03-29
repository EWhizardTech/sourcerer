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
from app.services.metadata_service import extract_folder_metadata
from app.workers.celery_app import celery
from app.workers.tasks import process_file_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestGDriveRequest(BaseModel):
    """Request body for the /ingest/gdrive endpoint."""

    folder_id: str  # Google Drive folder ID to ingest from.
    course_code: str | None = None
    year: str | None = None
    include_root_as_tag: bool = False


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
    folder_metadata: dict


@router.post("/gdrive", response_model=list[FileResponse])
async def ingest_gdrive(request: IngestGDriveRequest) -> list[FileResponse]:
    """Fetch and download all supported files from a Google Drive folder.

    Args:
        request: Ingestion config (folder_id, course_code, year, etc.).

    Returns:
        List of FileResponse objects with metadata.

    Raises:
        HTTPException 500: If the Drive API call fails.
    """
    logger.info(
        "Received ingest request for folder_id=%s (course=%s)",
        request.folder_id,
        request.course_code,
    )

    try:
        records = list_files_in_folder(request.folder_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Drive ingestion failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Google Drive ingestion failed: {exc}",
        ) from exc

    results = []
    for r in records:
        # Step 3: Metadata extraction (after Step 1 Ingestion and Step 2 Incremental check — implicit here)
        metadata = extract_folder_metadata(
            file_path=r["file_path"],
            course_code=request.course_code,
            year=request.year,
            include_root=request.include_root_as_tag,
        )

        results.append(
            FileResponse(
                file_id=r["file_id"],
                file_name=r["file_name"],
                mime_type=r["mime_type"],
                file_path=r["file_path"],
                modified_time=r["modified_time"],
                content=base64.b64encode(r["content"]).decode("utf-8"),
                folder_metadata=metadata,
            )
        )

        process_file_task.delay(
            file_id=r["file_id"],
            file_name=r["file_name"],
            mime_type=r["mime_type"],
            file_bytes=base64.b64encode(r["content"]).decode(),
            metadata=metadata,
        )

    return results
