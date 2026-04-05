"""Filesystem tools for reading, writing, and listing files."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool


@tool
def read_file(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: Absolute or relative path to the file
    """
    filepath = Path(path)
    if not filepath.exists():
        return f"Error: File not found: {path}"
    if not filepath.is_file():
        return f"Error: Not a file: {path}"
    return filepath.read_text(encoding="utf-8")


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed.

    Args:
        path: Absolute or relative path to the file
        content: Content to write
    """
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    return f"Written {len(content)} chars to {path}"


@tool
def list_files(directory: str, pattern: str = "*") -> str:
    """List files in a directory matching an optional glob pattern.

    Args:
        directory: Path to directory
        pattern: Glob pattern to filter files (default: *)
    """
    dirpath = Path(directory)
    if not dirpath.is_dir():
        return f"Error: Directory not found: {directory}"
    files = sorted(str(p.relative_to(dirpath)) for p in dirpath.glob(pattern) if p.is_file())
    if not files:
        return f"No files matching '{pattern}' in {directory}"
    return "\n".join(files)
