"""Utility functions."""
import uuid


def generate_thread_id() -> str:
    """Generate a new thread ID."""
    return str(uuid.uuid4())


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    import re
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
