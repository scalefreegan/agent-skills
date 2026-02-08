"""Tests for non-markdown file composer."""

import tempfile
from pathlib import Path

import pytest

from skill_manager.compose.files import compose_non_markdown_files
from skill_manager.config.schema import PrecedenceLevel
from skill_manager.core.skill import SkillSource


@pytest.fixture
def temp_skill_dir():
    """Create a temporary directory for skill testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def default_skill(temp_skill_dir):
    """Create a default-level skill with non-markdown files."""
    skill_path = temp_skill_dir / "default_skill"
    skill_path.mkdir()

    # Create SKILL.md
    skill_md = skill_path / "SKILL.md"
    skill_md.write_text(
        """---
name: default-skill
description: A default skill
---

# Default Skill
"""
    )

    # Create some non-markdown files
    (skill_path / "script.py").write_text("print('default script')\n")
    (skill_path / "config.json").write_text('{"key": "default"}\n')

    # Create a nested directory with files
    (skill_path / "tools").mkdir()
    (skill_path / "tools" / "helper.sh").write_text("#!/bin/bash\necho 'default'\n")

    return SkillSource(
        name="default-skill",
        path=skill_path,
        source_url="https://github.com/example/default",
        source_ref="main",
    )


@pytest.fixture
def user_skill(temp_skill_dir):
    """Create a user-level skill with non-markdown files."""
    skill_path = temp_skill_dir / "user_skill"
    skill_path.mkdir()

    # Create SKILL.md
    skill_md = skill_path / "SKILL.md"
    skill_md.write_text(
        """---
name: user-skill
description: A user skill
---

# User Skill
"""
    )

    # Create non-markdown files (some overlap with default)
    (skill_path / "script.py").write_text("print('user script')\n")
    (skill_path / "user_config.yaml").write_text("key: user\n")

    # Create a nested directory with files
    (skill_path / "tools").mkdir()
    (skill_path / "tools" / "helper.sh").write_text("#!/bin/bash\necho 'user'\n")

    return SkillSource(
        name="user-skill",
        path=skill_path,
        source_url="https://github.com/example/user",
        source_ref="custom",
    )


def test_compose_single_source(temp_skill_dir, default_skill):
    """Test composing files from a single source."""
    output_dir = temp_skill_dir / "output"
    sources = [(default_skill, PrecedenceLevel.DEFAULT)]

    manifest = compose_non_markdown_files(sources, output_dir)

    # Check that files were copied
    assert (output_dir / "script.py").exists()
    assert (output_dir / "config.json").exists()
    assert (output_dir / "tools" / "helper.sh").exists()

    # Check content
    assert (output_dir / "script.py").read_text() == "print('default script')\n"
    assert (output_dir / "config.json").read_text() == '{"key": "default"}\n'

    # Check manifest
    assert len(manifest) == 3
    assert all("default-skill (default)" in desc for desc in manifest.values())
    assert any("url=https://github.com/example/default" in desc for desc in manifest.values())


def test_compose_user_wins_over_default(temp_skill_dir, default_skill, user_skill):
    """Test that user-level files win over default-level files."""
    output_dir = temp_skill_dir / "output"
    sources = [
        (default_skill, PrecedenceLevel.DEFAULT),
        (user_skill, PrecedenceLevel.USER),
    ]

    manifest = compose_non_markdown_files(sources, output_dir)

    # User's script.py should win
    assert (output_dir / "script.py").exists()
    assert (output_dir / "script.py").read_text() == "print('user script')\n"

    # User's helper.sh should win
    assert (output_dir / "tools" / "helper.sh").exists()
    assert (output_dir / "tools" / "helper.sh").read_text() == "#!/bin/bash\necho 'user'\n"

    # Default's unique file should be present
    assert (output_dir / "config.json").exists()
    assert (output_dir / "config.json").read_text() == '{"key": "default"}\n'

    # User's unique file should be present
    assert (output_dir / "user_config.yaml").exists()
    assert (output_dir / "user_config.yaml").read_text() == "key: user\n"

    # Check manifest descriptions
    script_manifest = manifest[str(output_dir / "script.py")]
    assert "user-skill (user)" in script_manifest

    config_manifest = manifest[str(output_dir / "config.json")]
    assert "default-skill (default)" in config_manifest


def test_compose_preserves_directory_structure(temp_skill_dir, default_skill):
    """Test that nested directory structure is preserved."""
    output_dir = temp_skill_dir / "output"
    sources = [(default_skill, PrecedenceLevel.DEFAULT)]

    manifest = compose_non_markdown_files(sources, output_dir)

    # Check nested structure
    assert (output_dir / "tools").is_dir()
    assert (output_dir / "tools" / "helper.sh").exists()
    assert (output_dir / "tools" / "helper.sh").read_text() == "#!/bin/bash\necho 'default'\n"


def test_compose_excludes_markdown_files(temp_skill_dir):
    """Test that markdown files are excluded from composition."""
    skill_path = temp_skill_dir / "test_skill"
    skill_path.mkdir()

    # Create SKILL.md and other markdown files
    (skill_path / "SKILL.md").write_text("# Skill\n")
    (skill_path / "README.md").write_text("# README\n")
    (skill_path / "docs.md").write_text("# Docs\n")

    # Create non-markdown files
    (skill_path / "script.py").write_text("print('hello')\n")

    skill_source = SkillSource(name="test-skill", path=skill_path)
    output_dir = temp_skill_dir / "output"
    sources = [(skill_source, PrecedenceLevel.DEFAULT)]

    manifest = compose_non_markdown_files(sources, output_dir)

    # Only non-markdown file should be copied
    assert (output_dir / "script.py").exists()
    assert not (output_dir / "SKILL.md").exists()
    assert not (output_dir / "README.md").exists()
    assert not (output_dir / "docs.md").exists()

    # Manifest should only contain the non-markdown file
    assert len(manifest) == 1


def test_compose_empty_sources(temp_skill_dir):
    """Test composing with no sources."""
    output_dir = temp_skill_dir / "output"
    sources = []

    manifest = compose_non_markdown_files(sources, output_dir)

    # Output dir should be created but empty
    assert output_dir.exists()
    assert len(list(output_dir.iterdir())) == 0
    assert len(manifest) == 0


def test_compose_skill_with_no_files(temp_skill_dir):
    """Test composing a skill that has no non-markdown files."""
    skill_path = temp_skill_dir / "empty_skill"
    skill_path.mkdir()

    # Only create SKILL.md
    (skill_path / "SKILL.md").write_text("# Empty Skill\n")

    skill_source = SkillSource(name="empty-skill", path=skill_path)
    output_dir = temp_skill_dir / "output"
    sources = [(skill_source, PrecedenceLevel.DEFAULT)]

    manifest = compose_non_markdown_files(sources, output_dir)

    # No files should be copied
    assert output_dir.exists()
    assert len(manifest) == 0


def test_compose_creates_output_dir(temp_skill_dir, default_skill):
    """Test that output directory is created if it doesn't exist."""
    output_dir = temp_skill_dir / "nested" / "output" / "dir"
    sources = [(default_skill, PrecedenceLevel.DEFAULT)]

    # Output dir shouldn't exist yet
    assert not output_dir.exists()

    manifest = compose_non_markdown_files(sources, output_dir)

    # Should be created and populated
    assert output_dir.exists()
    assert len(manifest) > 0
    assert (output_dir / "script.py").exists()


def test_compose_multiple_default_sources(temp_skill_dir):
    """Test composing multiple default-level sources (first wins on conflict)."""
    # Create two default-level skills
    skill1_path = temp_skill_dir / "skill1"
    skill1_path.mkdir()
    (skill1_path / "SKILL.md").write_text("# Skill 1\n")
    (skill1_path / "script.py").write_text("print('skill1')\n")
    (skill1_path / "file1.txt").write_text("from skill1\n")

    skill2_path = temp_skill_dir / "skill2"
    skill2_path.mkdir()
    (skill2_path / "SKILL.md").write_text("# Skill 2\n")
    (skill2_path / "script.py").write_text("print('skill2')\n")
    (skill2_path / "file2.txt").write_text("from skill2\n")

    skill1 = SkillSource(name="skill1", path=skill1_path)
    skill2 = SkillSource(name="skill2", path=skill2_path)

    output_dir = temp_skill_dir / "output"
    sources = [
        (skill1, PrecedenceLevel.DEFAULT),
        (skill2, PrecedenceLevel.DEFAULT),
    ]

    manifest = compose_non_markdown_files(sources, output_dir)

    # Both unique files should be present
    assert (output_dir / "file1.txt").exists()
    assert (output_dir / "file2.txt").exists()

    # For the conflict (script.py), first default source wins
    assert (output_dir / "script.py").exists()
    assert (output_dir / "script.py").read_text() == "print('skill1')\n"


def test_manifest_format(temp_skill_dir, user_skill):
    """Test that manifest contains properly formatted source descriptions."""
    output_dir = temp_skill_dir / "output"
    sources = [(user_skill, PrecedenceLevel.USER)]

    manifest = compose_non_markdown_files(sources, output_dir)

    # Check that each manifest entry has expected format
    for path, desc in manifest.items():
        assert "user-skill (user)" in desc
        assert "url=https://github.com/example/user" in desc
        assert "ref=custom" in desc


def test_compose_binary_files(temp_skill_dir):
    """Test that binary files are copied correctly."""
    skill_path = temp_skill_dir / "binary_skill"
    skill_path.mkdir()

    (skill_path / "SKILL.md").write_text("# Binary Skill\n")

    # Create a simple binary file
    binary_content = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
    (skill_path / "image.png").write_bytes(binary_content)

    skill_source = SkillSource(name="binary-skill", path=skill_path)
    output_dir = temp_skill_dir / "output"
    sources = [(skill_source, PrecedenceLevel.DEFAULT)]

    manifest = compose_non_markdown_files(sources, output_dir)

    # Binary file should be copied
    assert (output_dir / "image.png").exists()
    assert (output_dir / "image.png").read_bytes() == binary_content
    assert len(manifest) == 1
