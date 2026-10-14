"""
Report storage.

Each uploaded report is stored as two files inside DATA_DIR:
  - <report_id>_<sanitized_name>.<ext>   the original upload
  - <report_id>.json                     metadata, token hash, extraction and cached AI output

Files are deleted automatically after REPORT_RETENTION_HOURS and can be deleted on
request by the report owner (DELETE /api/reports/{id}).
"""
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, UploadFile, status

from app.config import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    REPORT_RETENTION_HOURS,
    UPLOAD_DIR,
)
from app.security import (
    generate_access_token,
    generate_report_id,
    hash_token,
    is_valid_report_id,
    token_matches,
)

logger = logging.getLogger(__name__)

_CURRENT_ID_FILE = re.compile(r"^rep_[0-9a-f]{24}_")

# File signatures ("magic bytes") used to check that content matches the extension
_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}


def ensure_upload_dir_exists() -> Path:
    """Ensures that the upload directory exists."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def sanitize_filename(filename: str) -> str:
    """Sanitizes user-provided filename to prevent path traversal attacks."""
    # Normalise Windows separators so Path().name strips every directory component
    safe_name = Path((filename or "").replace("\\", "/")).name
    # Replace anything other than letters, digits, dots, underscores and dashes
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", safe_name)
    safe_name = safe_name.lstrip(".")[:120]
    return safe_name or "report.pdf"


def _record_path(report_id: str) -> Path:
    return ensure_upload_dir_exists() / f"{report_id}.json"


def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


async def save_upload_file(file: UploadFile) -> Tuple[str, str, Path, str]:
    """
    Validates and saves an uploaded file.

    Returns:
        Tuple[report_id, display_filename, saved_file_path, access_token]

    Raises:
        HTTPException 400: unsupported extension, content type, mismatched content or empty file.
        HTTPException 413: file larger than the configured limit.
    """
    original_filename = file.filename or "report.pdf"
    sanitized_name = sanitize_filename(original_filename)
    allowed_list = ", ".join(ext.upper() for ext in sorted(ALLOWED_EXTENSIONS))

    # 1. Validate file extension
    extension = sanitized_name.rsplit(".", 1)[-1].lower() if "." in sanitized_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{extension}'. Allowed formats are: {allowed_list}.",
        )

    # 2. Validate MIME content-type (if provided)
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media type '{file.content_type}'. Allowed file types are: {allowed_list}.",
        )

    # 3. Read at most limit + 1 bytes so oversized uploads are rejected without buffering everything
    contents = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    file_size = len(contents)

    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the maximum allowed size of {MAX_UPLOAD_SIZE_MB} MB.",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty. Please upload a valid laboratory report.",
        )

    # 4. Check that the content really is the declared type
    if not any(contents.startswith(sig) for sig in _SIGNATURES[extension]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The file content does not look like a valid {extension.upper()} file.",
        )

    # 5. Persist file and its metadata record
    report_id = generate_report_id()
    access_token = generate_access_token()
    target_path = ensure_upload_dir_exists() / f"{report_id}_{sanitized_name}"

    try:
        with open(target_path, "wb") as f:
            f.write(contents)
        _write_json_atomic(_record_path(report_id), {
            "reportId": report_id,
            "tokenHash": hash_token(access_token),
            "fileName": sanitized_name,
            "storedFile": target_path.name,
            "createdAt": time.time(),
            "extraction": None,
            "explanations": {},
        })
    except Exception:
        logger.exception("Failed to store uploaded report")
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file to backend storage.",
        )

    return report_id, sanitized_name, target_path, access_token


def load_record(report_id: str) -> Optional[Dict[str, Any]]:
    if not is_valid_report_id(report_id):
        return None
    path = _record_path(report_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        logger.warning("Unreadable report record for a stored report; ignoring it.")
        return None


def save_record(record: Dict[str, Any]) -> None:
    _write_json_atomic(_record_path(record["reportId"]), record)


def get_authorized_record(report_id: str, token: Optional[str]) -> Dict[str, Any]:
    """Returns the record only when the access token matches; otherwise 404 (no existence leak)."""
    record = load_record(report_id)
    if not record or not token_matches(token or "", record.get("tokenHash", "")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    if is_expired(record):
        delete_report(report_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return record


def get_file_by_report_id(report_id: str) -> Optional[Path]:
    """Finds the stored report file for a report ID (IDs are validated to block path tricks)."""
    if not is_valid_report_id(report_id):
        return None
    record = load_record(report_id)
    target_dir = ensure_upload_dir_exists()
    if record and record.get("storedFile"):
        candidate = (target_dir / record["storedFile"]).resolve()
        if candidate.parent == target_dir.resolve() and candidate.exists():
            return candidate
    matches = [p for p in target_dir.glob(f"{report_id}_*") if p.is_file()]
    return matches[0] if matches else None


def is_expired(record: Dict[str, Any]) -> bool:
    if REPORT_RETENTION_HOURS <= 0:
        return False
    return time.time() - float(record.get("createdAt", 0)) > REPORT_RETENTION_HOURS * 3600


def delete_report(report_id: str) -> bool:
    """Deletes a report's file and record. Returns True if anything was removed."""
    if not is_valid_report_id(report_id):
        return False
    removed = False
    target_dir = ensure_upload_dir_exists()
    for path in list(target_dir.glob(f"{report_id}_*")) + [_record_path(report_id)]:
        try:
            if path.exists():
                path.unlink()
                removed = True
        except OSError:
            logger.warning("Could not delete a stored report file.")
    return removed


def purge_expired_reports() -> int:
    """Deletes expired reports and orphaned uploads. Returns the number of reports removed."""
    target_dir = ensure_upload_dir_exists()
    removed = 0
    cutoff = time.time() - REPORT_RETENTION_HOURS * 3600
    if REPORT_RETENTION_HOURS <= 0:
        return 0
    for record_path in target_dir.glob("rep_*.json"):
        record = load_record(record_path.stem)
        if record is None or is_expired(record):
            if delete_report(record_path.stem):
                removed += 1
    # Orphaned uploads (current ID format, record missing) are removed by file age.
    # Files from older app versions (8-hex IDs) are left untouched for the owner to review.
    for path in target_dir.glob("rep_*_*"):
        if not _CURRENT_ID_FILE.match(path.name):
            continue
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed