"""
Utility functions for the documents app.
"""
import os
import mimetypes
from pathlib import Path
from django.conf import settings


def get_file_type(filename: str) -> str:
    """Determine file type from filename extension."""
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf':
        return 'pdf'
    elif ext == 'docx':
        return 'docx'
    elif ext == 'txt':
        return 'txt'
    else:
        raise ValueError(f"Unsupported file extension: .{ext}")


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return os.path.getsize(file_path)


def format_file_size(size_bytes: int) -> str:
    """Format file size for display."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def guess_page_count(text: str, file_type: str) -> int:
    """
    Roughly estimate page count based on text length.
    For PDFs this is more accurate since we extract page markers.
    """
    if file_type == 'pdf':
        # Count [Page N] markers
        import re
        pages = re.findall(r'\[Page (\d+)\]', text)
        if pages:
            return max(int(p) for p in pages)
    
    # Rough estimate: ~3000 chars per page
    return max(1, len(text) // 3000)


def allowed_file_size(file_size: int) -> bool:
    """Check if file size is within allowed limit."""
    return file_size <= settings.FILE_UPLOAD_MAX_MEMORY_SIZE