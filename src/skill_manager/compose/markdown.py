"""Markdown file composition with precedence markers."""

from pathlib import Path

from skill_manager.config.schema import PrecedenceLevel
from skill_manager.core.skill import SkillSource


def compose_markdown_files(
    sources: list[tuple[SkillSource, PrecedenceLevel]], output_path: Path
) -> None:
    """Compose markdown files from multiple sources with precedence markers.

    Args:
        sources: List of (SkillSource, precedence_level) tuples
        output_path: Path where composed markdown should be written

    Raises:
        ValueError: If sources list is empty
        FileNotFoundError: If markdown files are not found in sources
    """
    if not sources:
        raise ValueError("Cannot compose markdown files from empty sources list")

    # Sort sources by precedence: default before user
    # This ensures default content comes first, user content overrides
    sorted_sources = sorted(
        sources, key=lambda x: 0 if x[1] == PrecedenceLevel.DEFAULT else 1
    )

    # Collect all markdown content with precedence markers
    composed_content_parts = []

    for skill_source, precedence_level in sorted_sources:
        # Get all markdown files from this source
        markdown_files = skill_source.get_markdown_files()

        if not markdown_files:
            # Skip sources without markdown files
            continue

        # Add precedence marker header
        if precedence_level == PrecedenceLevel.DEFAULT:
            marker_header = _create_default_precedence_marker()
        else:
            marker_header = _create_user_precedence_marker()

        composed_content_parts.append(marker_header)

        # Concatenate all markdown files from this source
        for md_file in sorted(markdown_files):  # Sort for deterministic output
            content = md_file.read_text()
            # Strip leading/trailing whitespace but preserve internal structure
            content = content.strip()
            if content:
                composed_content_parts.append(content)

        # Add spacing between precedence sections
        composed_content_parts.append("")

    # Join all parts with double newlines for readability
    final_content = "\n\n".join(composed_content_parts)

    # Write to output path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_content)


def _create_default_precedence_marker() -> str:
    """Create precedence marker for default-level content."""
    return """<!-- PRECEDENCE: default -->
<!-- The following content is from the default-level skill -->""".strip()


def _create_user_precedence_marker() -> str:
    """Create precedence marker for user-level content."""
    return """<!-- PRECEDENCE: user (overrides default) -->
<!-- The following content is from the user-level skill and takes priority -->
<!-- When conflicts exist, follow the user-level instructions below -->""".strip()
