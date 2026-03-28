"""Metadata extraction service for Sourcerer.

Handles folder-based tag extraction and merging with user-provided metadata.
"""

import logging
from typing import TypedDict, List, Optional

logger = logging.getLogger(__name__)


class FolderMetadata(TypedDict):
    """Structured folder metadata."""

    course_code: Optional[str]
    year: Optional[str]
    tags: List[str]


def extract_folder_metadata(
    file_path: str, 
    course_code: Optional[str] = None, 
    year: Optional[str] = None, 
    include_root: bool = False
) -> FolderMetadata:
    """Extract tags from file path and merge with course/year metadata.

    The file_path is expected to be "/" separated (Google Drive breadcrumb format).
    Example: "Root / Folder / Sub / file.pdf"
    
    Args:
        file_path: Full breadcrumb path from gdrive_service.
        course_code: Provided course code.
        year: Provided year.
        include_root: If True, include the first segment of the path in tags.

    Returns:
        FolderMetadata dict.
    """
    # Split by '/' to be resilient to spacing differences
    segments = [s.strip() for s in file_path.split("/") if s.strip()]
    
    # Remove the last segment (the file name)
    if segments:
        segments.pop()
    
    # If not including root, remove the first segment
    if not include_root and segments:
        segments.pop(0)
    
    # Normalize segments: lowercase (empty strings were already filtered out)
    tags = [s.lower() for s in segments]
    
    metadata: FolderMetadata = {
        "course_code": course_code,
        "year": year,
        "tags": tags,
    }
    
    logger.debug("Extracted metadata for %s: %s", file_path, metadata)
    return metadata
