# app/utils/file_validator.py
import hashlib
import os
from fastapi import UploadFile, HTTPException
from app.config import settings

ALLOWED_MIME_MAP = {
    "pdf": {"application/pdf"},
    "txt": {"text/plain"},
}


async def validate_and_read_file(file: UploadFile) -> tuple[bytes, str, str]:
    # 1. Sanitise and check extension
    original_name = file.filename or ""
    original_name = os.path.basename(original_name)
    parts = original_name.rsplit(".", 1)
    if len(parts) != 2 or not parts[1]:
        raise HTTPException(status_code=400, detail="Filename must have a valid extension")

    ext = parts[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension '.{ext}' is not permitted")

    # 2. Read file then check size
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_BYTES // (1024*1024)} MB")

    # 3. Magic-byte MIME detection
    try:
        import magic
        detected_mime = magic.from_buffer(content[:4096], mime=True)
    except Exception:
        detected_mime = file.content_type or "application/octet-stream"

    allowed_mimes = ALLOWED_MIME_MAP.get(ext, set())
    if detected_mime not in allowed_mimes:
        raise HTTPException(status_code=400, detail=f"File content type '{detected_mime}' does not match extension '.{ext}'")

    # 4. SHA-256
    sha256 = hashlib.sha256(content).hexdigest()

    return content, sha256, detected_mime