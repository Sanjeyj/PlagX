"""File upload service with validation and secure storage."""

import uuid
import logging
from pathlib import Path
from fastapi import UploadFile, HTTPException

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class FileService:
    """Handles secure file uploads with validation."""

    def __init__(self):
        self.upload_dir = settings.upload_path

    async def save_upload(self, file: UploadFile) -> dict:
        """Validate and save an uploaded file."""
        original_name = file.filename or "unknown"
        ext = Path(original_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

        content = await file.read()
        file_size = len(content)

        if file_size > settings.max_upload_bytes:
            raise HTTPException(400, f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB")

        if file_size == 0:
            raise HTTPException(400, "Empty file")

        file_id = str(uuid.uuid4())
        secure_name = f"{file_id}{ext}"
        file_path = self.upload_dir / secure_name
        file_path.write_bytes(content)

        logger.info(f"Saved upload: {original_name} -> {secure_name} ({file_size} bytes)")

        return {
            "filename": secure_name,
            "original_name": original_name,
            "file_type": ext,
            "file_size": file_size,
            "file_path": str(file_path),
        }

    def get_file_path(self, filename: str) -> Path:
        path = self.upload_dir / filename
        if not path.exists():
            raise HTTPException(404, "File not found")
        return path

    def delete_file(self, filename: str):
        path = self.upload_dir / filename
        if path.exists():
            path.unlink()
            logger.info(f"Deleted file: {filename}")
