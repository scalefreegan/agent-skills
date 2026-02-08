"""Resolver for URLs and sources.

This module provides functionality to:
- Parse GitHub URLs into components
- Resolve named sources to concrete URLs
- Handle local paths (absolute/relative)
- Resolve compose items to fetchable locations
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

from skill_manager.config.schema import ComposeItemConfig, SourceConfig
from skill_manager.utils.paths import expand_path


@dataclass
class ResolvedSource:
    """A resolved source ready for fetching.

    Attributes:
        type: Type of source ("github" or "local")
        owner: GitHub repository owner (for GitHub sources)
        repo: GitHub repository name (for GitHub sources)
        path: Path within repository (for GitHub sources)
        ref: Git branch/tag/commit reference (for GitHub sources)
        local_path: Absolute filesystem path (for local sources)
    """
    type: Literal["github", "local"]
    # For GitHub
    owner: Optional[str] = None
    repo: Optional[str] = None
    path: Optional[str] = None
    ref: Optional[str] = None  # branch/tag/commit
    # For local
    local_path: Optional[Path] = None


def parse_github_url(url: str) -> ResolvedSource:
    """Parse a GitHub URL into components.

    Handles various GitHub URL formats:
    - https://github.com/owner/repo/tree/main/path/to/skill
    - https://github.com/owner/repo/tree/v1.0/skills/my-skill
    - github.com/owner/repo (assumes main branch, no path)
    - github.com/owner/repo/tree/branch

    Args:
        url: GitHub URL to parse

    Returns:
        ResolvedSource with GitHub components extracted

    Raises:
        ValueError: If URL is not a valid GitHub URL
    """
    # Normalize URL: add https:// if missing
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)

    # Validate it's a GitHub URL
    if parsed.netloc not in ("github.com", "www.github.com"):
        raise ValueError(f"Not a GitHub URL: {url}")

    # Remove leading slash and split path components
    path_parts = parsed.path.lstrip("/").split("/")

    # Need at least owner/repo
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GitHub URL format: {url}. Expected owner/repo at minimum")

    owner = path_parts[0]
    repo = path_parts[1]
    ref = None
    path = None

    # Check if there's more structure: /tree/ref/path...
    if len(path_parts) >= 4 and path_parts[2] == "tree":
        ref = path_parts[3]
        # Everything after tree/ref is the path
        if len(path_parts) > 4:
            path = "/".join(path_parts[4:])

    return ResolvedSource(
        type="github",
        owner=owner,
        repo=repo,
        path=path,
        ref=ref,
    )


def resolve_source(
    source_name: str,
    sources: dict[str, SourceConfig],
    default_branch: str
) -> ResolvedSource:
    """Resolve a named source to a fetchable location.

    Args:
        source_name: Name of the source from configuration
        sources: Dictionary of available source configurations
        default_branch: Default branch to use if source doesn't specify one

    Returns:
        ResolvedSource with location details

    Raises:
        ValueError: If source_name is not found in sources
    """
    if source_name not in sources:
        raise ValueError(f"Source '{source_name}' not found in configuration")

    source_config = sources[source_name]

    # Currently only GitHub sources are supported
    if source_config.type.value != "github":
        raise ValueError(f"Unsupported source type: {source_config.type}")

    # Parse repo format: "owner/repo"
    if "/" not in source_config.repo:
        raise ValueError(f"Invalid repo format: {source_config.repo}. Expected 'owner/repo'")

    owner, repo = source_config.repo.split("/", 1)

    # Use source's branch if specified, otherwise use default
    ref = source_config.branch if source_config.branch else default_branch

    return ResolvedSource(
        type="github",
        owner=owner,
        repo=repo,
        path=source_config.path,
        ref=ref,
    )


def resolve_compose_item(
    item: ComposeItemConfig,
    sources: dict[str, SourceConfig],
    default_branch: str
) -> ResolvedSource:
    """Resolve a compose item to a fetchable location.

    A compose item can specify either:
    - A named source + skill name
    - A direct URL
    - A local filesystem path

    Args:
        item: Compose item configuration to resolve
        sources: Dictionary of available source configurations
        default_branch: Default branch to use for sources without a specific branch

    Returns:
        ResolvedSource with location details

    Raises:
        ValueError: If the compose item cannot be resolved
    """
    # Case 1: Named source reference
    if item.source is not None:
        # Resolve the named source
        resolved = resolve_source(item.source, sources, default_branch)

        # Append the skill name to the path
        if resolved.path:
            resolved.path = f"{resolved.path}/{item.skill}"
        else:
            resolved.path = item.skill

        return resolved

    # Case 2: Direct URL (should be GitHub)
    if item.url is not None:
        return parse_github_url(item.url)

    # Case 3: Local filesystem path
    if item.path is not None:
        return ResolvedSource(
            type="local",
            local_path=expand_path(item.path),
        )

    # Should never reach here due to ComposeItemConfig validation
    raise ValueError("Compose item must have source, url, or path")
