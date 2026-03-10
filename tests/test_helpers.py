"""Tests for utility helpers."""
import uuid

from backend.utils.helpers import generate_thread_id, sanitize_filename, truncate_text


def test_generate_thread_id_is_valid_uuid4_string():
    """Generated thread IDs should be valid UUID strings."""
    thread_id = generate_thread_id()
    parsed = uuid.UUID(thread_id)
    assert str(parsed) == thread_id


def test_sanitize_filename_replaces_unsafe_characters():
    """Unsafe filesystem characters should be replaced by underscores."""
    sanitized = sanitize_filename('bad<>:"/\\|?*name.pdf')
    assert sanitized == "bad_________name.pdf"


def test_truncate_text_leaves_short_text_unchanged():
    """Text shorter than max length should be returned as-is."""
    assert truncate_text("hello", 10) == "hello"


def test_truncate_text_adds_ellipsis_when_truncated():
    """Truncated text should end with ellipsis and obey max length."""
    result = truncate_text("abcdefghijk", 8)
    assert result == "abcde..."
    assert len(result) == 8
