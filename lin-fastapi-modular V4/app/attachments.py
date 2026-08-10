"""Phase 8 attachment contract, validation, and object key generation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import mimetypes
from pathlib import PurePath
from typing import Any
from uuid import uuid4

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}
FILE_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/json",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_FILE_BYTES = 25 * 1024 * 1024


class AttachmentValidationError(ValueError):
    """Raised before an attachment is allowed into object storage."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_filename(filename: str | None) -> str:
    value = PurePath(str(filename or "upload")).name.strip()
    if not value or value in {".", ".."}:
        return "upload"
    return value[:180]


def normalize_mime_type(filename: str, content_type: str | None) -> str:
    supplied = (content_type or "").split(";", 1)[0].strip().lower()
    if supplied and supplied != "application/octet-stream":
        return supplied
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def attachment_kind(mime_type: str) -> str:
    return "image" if mime_type in IMAGE_MIME_TYPES else "file"


def validate_upload(filename: str | None, content_type: str | None, content: bytes) -> tuple[str, str, str]:
    safe_filename = normalize_filename(filename)
    mime_type = normalize_mime_type(safe_filename, content_type)
    kind = attachment_kind(mime_type)
    allowed = IMAGE_MIME_TYPES if kind == "image" else FILE_MIME_TYPES
    if mime_type not in allowed:
        raise AttachmentValidationError(f"unsupported_mime_type:{mime_type}")
    if not content:
        raise AttachmentValidationError("empty_file")
    max_bytes = MAX_IMAGE_BYTES if kind == "image" else MAX_FILE_BYTES
    if len(content) > max_bytes:
        raise AttachmentValidationError(f"file_too_large:{max_bytes}")
    return safe_filename, mime_type, kind


def build_attachment(filename: str | None, content_type: str | None, content: bytes, *, owner_type: str = "chat") -> dict[str, Any]:
    if owner_type not in {"chat", "agent"}:
        raise AttachmentValidationError("invalid_owner_type")
    safe_filename, mime_type, kind = validate_upload(filename, content_type, content)
    attachment_id = str(uuid4())
    created_at = utc_now()
    suffix = PurePath(safe_filename).suffix.lower()
    object_key = f"{owner_type}/{created_at[:10].replace('-', '/')}/{attachment_id}{suffix}"
    return {
        "attachment_id": attachment_id,
        "owner_type": owner_type,
        "kind": kind,
        "filename": safe_filename,
        "object_key": object_key,
        "mime_type": mime_type,
        "size_bytes": len(content),
        "sha256": sha256(content).hexdigest(),
        "status": "uploaded",
        "metadata": {},
        "created_at": created_at,
    }


def public_attachment(row: dict[str, Any]) -> dict[str, Any]:
    """Return the stable chat/agent contract without exposing storage internals."""
    return {
        key: row.get(key)
        for key in (
            "attachment_id",
            "owner_type",
            "kind",
            "filename",
            "mime_type",
            "size_bytes",
            "sha256",
            "status",
            "url",
            "metadata",
            "created_at",
            "deleted_at",
        )
    }
