"""
Attachment helpers for chat file drop (text/code files).
Used for drag-and-drop attachments in chat input.
"""

import os
from typing import Optional, Tuple

# Allowed extensions for text/code attachments (lowercase, with dot)
ALLOWED_ATTACHMENT_EXTENSIONS = frozenset({
    ".txt", ".md", ".json", ".yaml", ".yml", ".xml", ".csv", ".log", ".ini", ".cfg",
    ".toml", ".env", ".gitignore", ".dockerignore",
    ".py", ".pyw", ".pyi", ".pyx",
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".rs", ".go", ".java", ".kt", ".kts", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
    ".cs", ".vb", ".fs", ".r", ".R", ".sql", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd",
    ".rb", ".php", ".pl", ".lua", ".swift", ".m", ".mm", ".zig", ".v", ".sv", ".vhd",
})


def is_allowed_attachment(path: str) -> bool:
    """Return True if path has an allowed text/code extension."""
    ext = os.path.splitext(path)[1].lower()
    return ext in ALLOWED_ATTACHMENT_EXTENSIONS


def format_file_size(size_bytes: int) -> str:
    """Format size as '12 KB', '1.2 MB', etc."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def is_probably_binary(path: str, max_sample: int = 8192) -> bool:
    """
    Heuristic: treat as binary if file contains null bytes or too many non-printable chars.
    Reads up to max_sample bytes.
    """
    try:
        with open(path, "rb") as f:
            data = f.read(max_sample)
    except OSError:
        return True
    if b"\x00" in data:
        return True
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return True
    non_printable = sum(1 for c in text if c != "\n" and c != "\r" and ord(c) < 32 and c not in "\t")
    if len(text) == 0:
        return False
    return (non_printable / len(text)) > 0.1


def read_text_file_with_limits(
    path: str,
    max_chars: int = 50_000,
    encoding: str = "utf-8",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Read file as text. Returns (content, error_message).
    If content is truncated, appends \"\\n[... truncated ...]\".
    error_message is set on failure.
    """
    try:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            raw = f.read(max_chars + 1)
    except OSError as e:
        return None, str(e)
    truncated = len(raw) > max_chars
    content = raw[:max_chars] if truncated else raw
    if truncated:
        content += "\n[... truncated ...]"
    return content, None
