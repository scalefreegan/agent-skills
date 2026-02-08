"""Path utilities for expanding and normalizing filesystem paths."""

from pathlib import Path


def expand_path(path: str) -> Path:
    """Expand and normalize a path, resolving ~ and relative paths.

    Args:
        path: Path string that may contain ~ or be relative

    Returns:
        Absolute Path object
    """
    return Path(path).expanduser().resolve()


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        The path that was ensured
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
