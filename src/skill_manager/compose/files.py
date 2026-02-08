"""File composer for non-markdown files in skills."""

import shutil
from pathlib import Path

from skill_manager.config.schema import PrecedenceLevel
from skill_manager.core.skill import SkillSource


def compose_non_markdown_files(
    sources: list[tuple[SkillSource, PrecedenceLevel]], output_dir: Path
) -> dict[str, str]:
    """Compose non-markdown files from multiple sources.

    User-level files win on conflict (same filename). Default-level files are used
    when no user-level equivalent exists. Files are copied to output_dir preserving
    their relative paths.

    Args:
        sources: List of (SkillSource, precedence_level) tuples
        output_dir: Directory where files should be written

    Returns:
        Dict mapping output file path to source description
        (for tracking which source each file came from)
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group files by relative path and precedence level
    # Key: relative path, Value: dict with 'user' and 'default' entries
    files_by_path: dict[str, dict[str, tuple[Path, SkillSource]]] = {}

    # Collect all non-markdown files from all sources
    for skill_source, precedence_level in sources:
        non_md_files = skill_source.get_non_markdown_files()

        for file_path in non_md_files:
            # Calculate relative path from skill root
            rel_path = file_path.relative_to(skill_source.path)

            # Initialize dict for this path if needed
            if str(rel_path) not in files_by_path:
                files_by_path[str(rel_path)] = {}

            # Store file by precedence level (user or default)
            # First occurrence wins for same precedence level
            level_key = precedence_level.value  # 'user' or 'default'
            if level_key not in files_by_path[str(rel_path)]:
                files_by_path[str(rel_path)][level_key] = (file_path, skill_source)

    # Now compose: user-level wins, fallback to default-level
    manifest: dict[str, str] = {}

    for rel_path_str, level_files in files_by_path.items():
        # Determine which file to use (user wins over default)
        if "user" in level_files:
            source_file, skill_source = level_files["user"]
            level_name = "user"
        elif "default" in level_files:
            source_file, skill_source = level_files["default"]
            level_name = "default"
        else:
            # Should not happen, but skip if somehow no files
            continue

        # Copy file to output directory, preserving relative path
        dest_path = output_dir / rel_path_str
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, dest_path)

        # Track source in manifest
        source_desc = _format_source_description(skill_source, level_name)
        manifest[str(dest_path)] = source_desc

    return manifest


def _format_source_description(skill_source: SkillSource, level: str) -> str:
    """Format a human-readable description of where a file came from.

    Args:
        skill_source: The source skill containing the file
        level: Precedence level ('user' or 'default')

    Returns:
        Human-readable source description
    """
    parts = [f"{skill_source.name} ({level})"]

    if skill_source.source_url:
        parts.append(f"url={skill_source.source_url}")
    if skill_source.source_ref:
        parts.append(f"ref={skill_source.source_ref}")

    return " ".join(parts)
