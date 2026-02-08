"""Tests for skill assembler orchestrator."""

import shutil
import tempfile
from pathlib import Path

import anyio
import pytest

from skill_manager.compose.assembler import (
    AssemblyContext,
    assemble_all_skills,
    assemble_skill,
)
from skill_manager.config.schema import (
    ComposeItemConfig,
    PrecedenceLevel,
    SkillConfig,
    SkillManagerConfig,
    SettingsConfig,
)
from skill_manager.fetch.cache import SkillCache


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_target_dir():
    """Create a temporary target directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_skill_source(tmp_path):
    """Create a sample skill source directory."""
    skill_dir = tmp_path / "sample-skill"
    skill_dir.mkdir()

    # Create SKILL.md with frontmatter
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: sample-skill
description: A sample skill for testing
version: 1.0.0
---

# Sample Skill

This is a sample skill.
"""
    )

    # Create some additional files
    (skill_dir / "config.json").write_text('{"key": "value"}')
    (skill_dir / "script.py").write_text("print('hello')")

    return skill_dir


@pytest.fixture
def another_skill_source(tmp_path):
    """Create another sample skill source directory."""
    skill_dir = tmp_path / "another-skill"
    skill_dir.mkdir()

    # Create SKILL.md with frontmatter
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: another-skill
description: Another skill for testing
version: 2.0.0
---

# Another Skill

This is another skill.
"""
    )

    # Create different files
    (skill_dir / "data.txt").write_text("some data")

    return skill_dir


@pytest.mark.anyio
async def test_assemble_simple_skill_from_local_path(
    sample_skill_source, temp_target_dir, temp_cache_dir
):
    """Test assembling a simple skill from a local path."""
    # Create config
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(temp_target_dir)],
            cache_dir=str(temp_cache_dir),
        ),
        sources={},
        skills=[
            SkillConfig(
                name="sample-skill",
                path=str(sample_skill_source),
            )
        ],
    )

    # Create cache
    cache = SkillCache(temp_cache_dir)

    # Create context
    context = AssemblyContext(config=config, cache=cache)

    # Assemble the skill
    skill_config = config.skills[0]
    skill = await assemble_skill(skill_config, context, temp_target_dir)

    # Verify the skill was installed
    assert skill.name == "sample-skill"
    assert skill.path == temp_target_dir / "sample-skill"
    assert skill.path.exists()

    # Verify files were copied
    assert (skill.path / "SKILL.md").exists()
    assert (skill.path / "config.json").exists()
    assert (skill.path / "script.py").exists()

    # Verify content
    assert "Sample Skill" in (skill.path / "SKILL.md").read_text()
    assert "hello" in (skill.path / "script.py").read_text()


@pytest.mark.anyio
async def test_assemble_composed_skill(
    sample_skill_source, another_skill_source, temp_target_dir, temp_cache_dir
):
    """Test assembling a composed skill from multiple local sources."""
    # Create config
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(temp_target_dir)],
            cache_dir=str(temp_cache_dir),
        ),
        sources={},
        skills=[
            SkillConfig(
                name="composed-skill",
                compose=[
                    ComposeItemConfig(
                        path=str(sample_skill_source),
                        level=PrecedenceLevel.DEFAULT,
                    ),
                    ComposeItemConfig(
                        path=str(another_skill_source),
                        level=PrecedenceLevel.USER,
                    ),
                ],
            )
        ],
    )

    # Create cache
    cache = SkillCache(temp_cache_dir)

    # Create context
    context = AssemblyContext(config=config, cache=cache)

    # Assemble the skill
    skill_config = config.skills[0]
    skill = await assemble_skill(skill_config, context, temp_target_dir)

    # Verify the skill was installed
    assert skill.name == "composed-skill"
    assert skill.path == temp_target_dir / "composed-skill"
    assert skill.path.exists()

    # Verify markdown was composed
    assert (skill.path / "SKILL.md").exists()
    skill_md_content = (skill.path / "SKILL.md").read_text()
    assert "PRECEDENCE: default" in skill_md_content
    assert "PRECEDENCE: user" in skill_md_content
    assert "Sample Skill" in skill_md_content
    assert "Another Skill" in skill_md_content

    # Verify non-markdown files were copied
    assert (skill.path / "config.json").exists()
    assert (skill.path / "script.py").exists()
    assert (skill.path / "data.txt").exists()

    # Verify composed_from tracking
    assert len(skill.composed_from) == 2
    assert "sample-skill" in skill.composed_from
    assert "another-skill" in skill.composed_from


@pytest.mark.anyio
async def test_assemble_all_skills(
    sample_skill_source, another_skill_source, temp_target_dir, temp_cache_dir
):
    """Test assembling multiple skills."""
    # Create config with multiple skills
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(temp_target_dir)],
            cache_dir=str(temp_cache_dir),
        ),
        sources={},
        skills=[
            SkillConfig(
                name="skill1",
                path=str(sample_skill_source),
            ),
            SkillConfig(
                name="skill2",
                path=str(another_skill_source),
            ),
        ],
    )

    # Assemble all skills
    skills = await assemble_all_skills(config, temp_target_dir)

    # Verify both skills were installed
    assert len(skills) == 2
    assert skills[0].name == "skill1"
    assert skills[1].name == "skill2"

    # Verify both directories exist
    assert (temp_target_dir / "skill1").exists()
    assert (temp_target_dir / "skill2").exists()


@pytest.mark.anyio
async def test_assemble_skill_with_missing_local_path(temp_target_dir, temp_cache_dir):
    """Test that assembling a skill with missing local path fails gracefully."""
    # Create config with non-existent path
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(temp_target_dir)],
            cache_dir=str(temp_cache_dir),
        ),
        sources={},
        skills=[
            SkillConfig(
                name="missing-skill",
                path="/nonexistent/path/to/skill",
            )
        ],
    )

    # Create cache
    cache = SkillCache(temp_cache_dir)

    # Create context
    context = AssemblyContext(config=config, cache=cache)

    # Attempt to assemble the skill - should raise error
    skill_config = config.skills[0]
    with pytest.raises(ValueError, match="Local path does not exist"):
        await assemble_skill(skill_config, context, temp_target_dir)


@pytest.mark.anyio
async def test_assemble_skill_overwrites_existing(
    sample_skill_source, temp_target_dir, temp_cache_dir
):
    """Test that assembling a skill overwrites existing installation."""
    # Create an existing skill directory with some content
    existing_skill_dir = temp_target_dir / "sample-skill"
    existing_skill_dir.mkdir(parents=True)
    (existing_skill_dir / "old_file.txt").write_text("old content")

    # Create config
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(temp_target_dir)],
            cache_dir=str(temp_cache_dir),
        ),
        sources={},
        skills=[
            SkillConfig(
                name="sample-skill",
                path=str(sample_skill_source),
            )
        ],
    )

    # Create cache
    cache = SkillCache(temp_cache_dir)

    # Create context
    context = AssemblyContext(config=config, cache=cache)

    # Assemble the skill
    skill_config = config.skills[0]
    skill = await assemble_skill(skill_config, context, temp_target_dir)

    # Verify the skill was installed
    assert skill.path.exists()

    # Verify old file is gone
    assert not (skill.path / "old_file.txt").exists()

    # Verify new files are present
    assert (skill.path / "SKILL.md").exists()
    assert (skill.path / "config.json").exists()


@pytest.mark.anyio
async def test_compose_with_file_conflict(tmp_path, temp_target_dir, temp_cache_dir):
    """Test that user-level files override default-level files in composed skills."""
    # Create two skills with conflicting files
    default_skill = tmp_path / "default-skill"
    default_skill.mkdir()
    (default_skill / "SKILL.md").write_text("# Default")
    (default_skill / "config.json").write_text('{"level": "default"}')

    user_skill = tmp_path / "user-skill"
    user_skill.mkdir()
    (user_skill / "SKILL.md").write_text("# User")
    (user_skill / "config.json").write_text('{"level": "user"}')

    # Create config
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(temp_target_dir)],
            cache_dir=str(temp_cache_dir),
        ),
        sources={},
        skills=[
            SkillConfig(
                name="composed",
                compose=[
                    ComposeItemConfig(
                        path=str(default_skill),
                        level=PrecedenceLevel.DEFAULT,
                    ),
                    ComposeItemConfig(
                        path=str(user_skill),
                        level=PrecedenceLevel.USER,
                    ),
                ],
            )
        ],
    )

    # Create cache
    cache = SkillCache(temp_cache_dir)

    # Create context
    context = AssemblyContext(config=config, cache=cache)

    # Assemble the skill
    skill_config = config.skills[0]
    skill = await assemble_skill(skill_config, context, temp_target_dir)

    # Verify markdown was composed
    skill_md = (skill.path / "SKILL.md").read_text()
    assert "Default" in skill_md
    assert "User" in skill_md

    # Verify user-level config.json won
    config_content = (skill.path / "config.json").read_text()
    assert '"level": "user"' in config_content
    assert '"level": "default"' not in config_content
