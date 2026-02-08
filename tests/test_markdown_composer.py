"""Tests for markdown file composition with precedence markers."""

import pytest
from pathlib import Path

from skill_manager.compose.markdown import compose_markdown_files
from skill_manager.config.schema import PrecedenceLevel
from skill_manager.core.skill import SkillSource


def test_compose_single_source_default(tmp_path):
    """Test composing markdown from a single default-level source."""
    # Create a skill with markdown files
    skill_dir = tmp_path / "default_skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: Test skill
---

# Test Skill

This is a test skill.""")

    readme = skill_dir / "README.md"
    readme.write_text("# Additional Info\n\nMore details here.")

    # Create skill source
    source = SkillSource(name="test-skill", path=skill_dir)

    # Compose
    output_path = tmp_path / "output" / "SKILL.md"
    compose_markdown_files([(source, PrecedenceLevel.DEFAULT)], output_path)

    # Verify output
    assert output_path.exists()
    content = output_path.read_text()

    # Check for precedence marker
    assert "<!-- PRECEDENCE: default -->" in content
    assert "The following content is from the default-level skill" in content

    # Check that both markdown files are included
    assert "Test Skill" in content
    assert "Additional Info" in content


def test_compose_multiple_sources_with_precedence(tmp_path):
    """Test composing markdown from multiple sources with different precedence levels."""
    # Create default skill
    default_skill_dir = tmp_path / "default_skill"
    default_skill_dir.mkdir()
    default_md = default_skill_dir / "SKILL.md"
    default_md.write_text("# Default Content\n\nThis is the base configuration.")

    # Create user skill
    user_skill_dir = tmp_path / "user_skill"
    user_skill_dir.mkdir()
    user_md = user_skill_dir / "SKILL.md"
    user_md.write_text("# User Override\n\nThis overrides the default.")

    # Create skill sources
    default_source = SkillSource(name="default-skill", path=default_skill_dir)
    user_source = SkillSource(name="user-skill", path=user_skill_dir)

    # Compose with user source first (should be reordered)
    output_path = tmp_path / "output" / "SKILL.md"
    compose_markdown_files(
        [(user_source, PrecedenceLevel.USER), (default_source, PrecedenceLevel.DEFAULT)],
        output_path,
    )

    # Verify output
    content = output_path.read_text()

    # Check for both precedence markers
    assert "<!-- PRECEDENCE: default -->" in content
    assert "<!-- PRECEDENCE: user (overrides default) -->" in content
    assert "When conflicts exist, follow the user-level instructions below" in content

    # Verify order: default content should come before user content
    default_pos = content.find("Default Content")
    user_pos = content.find("User Override")
    assert default_pos < user_pos, "Default content should appear before user content"


def test_compose_preserves_precedence_order(tmp_path):
    """Test that sources are sorted by precedence level (default first, user second)."""
    # Create multiple skills
    default1_dir = tmp_path / "default1"
    default1_dir.mkdir()
    (default1_dir / "SKILL.md").write_text("# Default 1")

    user1_dir = tmp_path / "user1"
    user1_dir.mkdir()
    (user1_dir / "SKILL.md").write_text("# User 1")

    default2_dir = tmp_path / "default2"
    default2_dir.mkdir()
    (default2_dir / "SKILL.md").write_text("# Default 2")

    user2_dir = tmp_path / "user2"
    user2_dir.mkdir()
    (user2_dir / "SKILL.md").write_text("# User 2")

    # Create sources in mixed order
    sources = [
        (SkillSource(name="user1", path=user1_dir), PrecedenceLevel.USER),
        (SkillSource(name="default1", path=default1_dir), PrecedenceLevel.DEFAULT),
        (SkillSource(name="user2", path=user2_dir), PrecedenceLevel.USER),
        (SkillSource(name="default2", path=default2_dir), PrecedenceLevel.DEFAULT),
    ]

    # Compose
    output_path = tmp_path / "output" / "SKILL.md"
    compose_markdown_files(sources, output_path)

    # Verify all default content comes before all user content
    content = output_path.read_text()

    # Find positions
    default1_pos = content.find("# Default 1")
    default2_pos = content.find("# Default 2")
    user1_pos = content.find("# User 1")
    user2_pos = content.find("# User 2")

    # All defaults should be before all users
    assert default1_pos < user1_pos
    assert default1_pos < user2_pos
    assert default2_pos < user1_pos
    assert default2_pos < user2_pos


def test_compose_empty_sources_raises_error(tmp_path):
    """Test that composing with empty sources list raises ValueError."""
    output_path = tmp_path / "output" / "SKILL.md"

    with pytest.raises(ValueError, match="Cannot compose markdown files from empty sources list"):
        compose_markdown_files([], output_path)


def test_compose_skips_sources_without_markdown(tmp_path):
    """Test that sources without markdown files are skipped gracefully."""
    # Create skill with no markdown files
    skill1_dir = tmp_path / "skill1"
    skill1_dir.mkdir()
    (skill1_dir / "script.py").write_text("print('hello')")

    # Create skill with markdown
    skill2_dir = tmp_path / "skill2"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text("# Has Markdown")

    sources = [
        (SkillSource(name="skill1", path=skill1_dir), PrecedenceLevel.DEFAULT),
        (SkillSource(name="skill2", path=skill2_dir), PrecedenceLevel.DEFAULT),
    ]

    # Compose
    output_path = tmp_path / "output" / "SKILL.md"
    compose_markdown_files(sources, output_path)

    # Verify only the skill with markdown is included
    content = output_path.read_text()
    assert "Has Markdown" in content


def test_compose_creates_output_directory(tmp_path):
    """Test that output directory is created if it doesn't exist."""
    # Create a skill
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test")

    source = SkillSource(name="test", path=skill_dir)

    # Output to nested directory that doesn't exist
    output_path = tmp_path / "nested" / "output" / "dir" / "SKILL.md"
    compose_markdown_files([(source, PrecedenceLevel.DEFAULT)], output_path)

    assert output_path.exists()
    assert output_path.parent.exists()


def test_compose_multiple_markdown_files_in_source(tmp_path):
    """Test composing when a source has multiple markdown files."""
    # Create skill with multiple markdown files
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text("# Main Skill")
    (skill_dir / "README.md").write_text("# Readme")
    (skill_dir / "docs.md").write_text("# Documentation")

    source = SkillSource(name="multi-md", path=skill_dir)

    # Compose
    output_path = tmp_path / "output" / "SKILL.md"
    compose_markdown_files([(source, PrecedenceLevel.DEFAULT)], output_path)

    # Verify all markdown files are included
    content = output_path.read_text()
    assert "Main Skill" in content
    assert "Readme" in content
    assert "Documentation" in content


def test_compose_strips_whitespace_but_preserves_structure(tmp_path):
    """Test that leading/trailing whitespace is stripped but internal structure preserved."""
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    # Create markdown with extra whitespace
    (skill_dir / "SKILL.md").write_text("""

# Title

Some content with

proper spacing.

""")

    source = SkillSource(name="test", path=skill_dir)

    # Compose
    output_path = tmp_path / "output" / "SKILL.md"
    compose_markdown_files([(source, PrecedenceLevel.DEFAULT)], output_path)

    content = output_path.read_text()

    # Should not start or end with excessive whitespace
    assert not content.startswith("\n\n\n")
    assert not content.endswith("\n\n\n")

    # But internal structure should be preserved
    assert "proper spacing." in content


def test_compose_deterministic_file_order(tmp_path):
    """Test that markdown files are processed in deterministic order."""
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    # Create files in non-alphabetical order
    (skill_dir / "z_file.md").write_text("# Z")
    (skill_dir / "a_file.md").write_text("# A")
    (skill_dir / "m_file.md").write_text("# M")

    source = SkillSource(name="test", path=skill_dir)

    # Compose multiple times
    output_path1 = tmp_path / "output1" / "SKILL.md"
    output_path2 = tmp_path / "output2" / "SKILL.md"

    compose_markdown_files([(source, PrecedenceLevel.DEFAULT)], output_path1)
    compose_markdown_files([(source, PrecedenceLevel.DEFAULT)], output_path2)

    # Both outputs should be identical
    assert output_path1.read_text() == output_path2.read_text()


def test_precedence_markers_format(tmp_path):
    """Test that precedence markers have the correct format."""
    # Create default skill
    default_dir = tmp_path / "default"
    default_dir.mkdir()
    (default_dir / "SKILL.md").write_text("# Default")

    # Create user skill
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    (user_dir / "SKILL.md").write_text("# User")

    sources = [
        (SkillSource(name="default", path=default_dir), PrecedenceLevel.DEFAULT),
        (SkillSource(name="user", path=user_dir), PrecedenceLevel.USER),
    ]

    # Compose
    output_path = tmp_path / "output" / "SKILL.md"
    compose_markdown_files(sources, output_path)

    content = output_path.read_text()

    # Verify exact marker formats
    assert "<!-- PRECEDENCE: default -->" in content
    assert "<!-- The following content is from the default-level skill -->" in content

    assert "<!-- PRECEDENCE: user (overrides default) -->" in content
    assert "<!-- The following content is from the user-level skill and takes priority -->" in content
    assert "<!-- When conflicts exist, follow the user-level instructions below -->" in content
