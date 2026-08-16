# app/services/parsing/types.py

from typing import Any, Dict, List, TypedDict


class Section(TypedDict):
    type: str
    content: str


class ParsedDocument(TypedDict):
    text: str
    sections: List[Section]
    images: List[Dict[str, Any]]
    external_content: List[str]
    metadata: Dict[str, Any]

    tables: List[Dict[str, Any]]
    images: List[Dict[str, Any]]
    lists: List[Dict[str, Any]]
