"""
Storage Service - File management (local or S3)
"""
import os
from pathlib import Path
from typing import Optional
from config.settings import settings


class StorageService:
    """Service for managing file storage"""

    def __init__(self):
        self.storage_type = settings.storage.type
        self.local_path = settings.storage.local_path

        # Create local storage directory if needed
        if self.storage_type == "local":
            Path(self.local_path).mkdir(parents=True, exist_ok=True)

    def save_file(self, file_path: str, content: str) -> bool:
        """Save file to storage"""
        try:
            if self.storage_type == "local":
                full_path = os.path.join(self.local_path, file_path)
                # Create directories if needed
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            else:
                # TODO: S3 implementation
                return False
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    def read_file(self, file_path: str) -> Optional[str]:
        """Read file from storage"""
        try:
            if self.storage_type == "local":
                full_path = os.path.join(self.local_path, file_path)
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        return f.read()
                return None
            else:
                # TODO: S3 implementation
                return None
        except Exception as e:
            print(f"Error reading file: {e}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        try:
            if self.storage_type == "local":
                full_path = os.path.join(self.local_path, file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    return True
                return False
            else:
                # TODO: S3 implementation
                return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        if self.storage_type == "local":
            full_path = os.path.join(self.local_path, file_path)
            return os.path.exists(full_path)
        return False

    def get_file_size(self, file_path: str) -> Optional[int]:
        """Get file size in bytes"""
        if self.storage_type == "local":
            full_path = os.path.join(self.local_path, file_path)
            if os.path.exists(full_path):
                return os.path.getsize(full_path)
        return None
