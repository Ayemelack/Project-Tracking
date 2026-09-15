import uuid
import os
import re
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings
from app.core.logging import logger


class StorageService:
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).stem
        ext = Path(filename).suffix
        safe = re.sub(r'[^\w\s\-]', '', name)
        safe = re.sub(r'\s+', '_', safe).strip('_')
        unique_id = uuid.uuid4().hex[:12]
        return f"{safe}_{unique_id}{ext}"

    async def save_upload(self, file: UploadFile) -> tuple[str, str]:
        original_filename = file.filename or "unknown.pdf"
        stored_filename = self._safe_filename(original_filename)
        file_path = self.storage_path / stored_filename

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"File saved: {original_filename} -> {stored_filename}")
        return original_filename, stored_filename

    def get_file_path(self, stored_filename: str) -> Path:
        return self.storage_path / stored_filename

    def save_bytes(self, filename: str, content: bytes) -> tuple[str, str]:
        original_filename = filename or "evidence.file"
        stored_filename = self._safe_filename(original_filename)
        file_path = self.storage_path / stored_filename
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"Bytes saved: {original_filename} -> {stored_filename}")
        return original_filename, stored_filename

    def file_exists(self, stored_filename: str) -> bool:
        return self.get_file_path(stored_filename).exists()


def path_suffix_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "application/octet-stream")


storage_service = StorageService()
