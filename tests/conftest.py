"""Shared pytest fixtures for skill manager tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test isolation."""
    return tmp_path


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Provide a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def temp_target_dir(tmp_path):
    """Provide a temporary target directory for skill installation."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    return target_dir


@pytest.fixture
def sample_skill_dir(tmp_path):
    """Create a sample skill directory with SKILL.md."""
    skill_dir = tmp_path / "sample-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: sample-skill
description: A sample skill for testing
version: 1.0.0
---

# Sample Skill

This is a sample skill for testing purposes.

## Usage

Use this skill to test things.
"""
    )

    # Add some additional files
    (skill_dir / "config.json").write_text('{"setting": "value"}')
    (skill_dir / "script.py").write_text("print('Hello from sample skill')")

    return skill_dir


@pytest.fixture
def another_skill_dir(tmp_path):
    """Create another sample skill directory."""
    skill_dir = tmp_path / "another-skill"
    skill_dir.mkdir()

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

    (skill_dir / "data.txt").write_text("some data")

    return skill_dir


@pytest.fixture
def minimal_config_dict():
    """Provide a minimal valid configuration dictionary."""
    return {
        "version": "1.0",
        "settings": {
            "target_dirs": [".claude/skills"],
            "cache_dir": "~/.cache/skill-manager",
            "default_branch": "main",
        },
        "sources": {},
        "skills": [],
    }


@pytest.fixture
def github_source_config():
    """Provide a GitHub source configuration."""
    return {
        "type": "github",
        "repo": "test-owner/test-repo",
        "path": "skills",
        "branch": "main",
    }


@pytest.fixture
def sample_config_with_skills(tmp_path):
    """Provide a complete configuration with skills."""
    return {
        "version": "1.0",
        "settings": {
            "target_dirs": [str(tmp_path / "skills")],
            "cache_dir": str(tmp_path / "cache"),
            "default_branch": "main",
        },
        "sources": {
            "test-source": {
                "type": "github",
                "repo": "test/repo",
                "path": "skills",
                "branch": "main",
            }
        },
        "skills": [
            {
                "name": "test-skill",
                "source": "test-source",
            }
        ],
    }
