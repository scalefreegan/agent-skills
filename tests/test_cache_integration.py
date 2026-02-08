"""Integration tests for SkillCache with SkillSource."""

from pathlib import Path

import pytest

from skill_manager.core.skill import SkillSource
from skill_manager.fetch.cache import SkillCache


@pytest.fixture
def cache_dir(tmp_path):
    """Provide a temporary cache directory."""
    return tmp_path / "cache"


@pytest.fixture
def skill_dir(tmp_path):
    """Create a sample skill directory."""
    skill_path = tmp_path / "test-skill"
    skill_path.mkdir()

    # Create SKILL.md with frontmatter
    skill_md = skill_path / "SKILL.md"
    skill_md.write_text(
        """---
name: test-skill
description: A test skill
version: 1.0.0
author: Test Author
---

# Test Skill

This is a test skill for integration testing.

## Usage

Use this skill to test caching functionality.
"""
    )

    # Create additional files
    (skill_path / "helper.py").write_text(
        """def helper_function():
    return "Hello from helper"
"""
    )

    (skill_path / "README.md").write_text("# Test Skill README")

    # Create nested structure
    utils_dir = skill_path / "utils"
    utils_dir.mkdir()
    (utils_dir / "tools.py").write_text("# Utility tools")

    return skill_path


class TestCacheIntegration:
    """Integration tests for cache with real SkillSource objects."""

    def test_cache_preserves_skill_metadata(self, cache_dir, skill_dir):
        """Test that caching preserves skill metadata from SKILL.md."""
        cache = SkillCache(cache_dir)

        # Create a SkillSource (this parses SKILL.md)
        original = SkillSource(
            name="test-skill",
            path=skill_dir,
            source_url="https://github.com/test/repo/tree/main/skills/test-skill",
            source_ref="main",
        )

        # Verify original has metadata
        assert original.metadata is not None
        assert original.metadata.name == "test-skill"
        assert original.metadata.description == "A test skill"
        assert original.metadata.version == "1.0.0"
        assert original.metadata.author == "Test Author"

        # Cache it
        cache.cache_skill(original, "test", "repo", "skills/test-skill", "main")

        # Retrieve from cache
        cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "main")

        assert cached is not None
        assert cached.name == "test-skill"
        assert cached.metadata is not None
        assert cached.metadata.name == "test-skill"
        assert cached.metadata.description == "A test skill"
        assert cached.metadata.version == "1.0.0"
        assert cached.metadata.author == "Test Author"

    def test_cache_preserves_file_structure(self, cache_dir, skill_dir):
        """Test that caching preserves the complete file structure."""
        cache = SkillCache(cache_dir)

        original = SkillSource(
            name="test-skill",
            path=skill_dir,
            source_url="https://github.com/test/repo/tree/main/skills/test-skill",
            source_ref="main",
        )

        # Cache it
        cache.cache_skill(original, "test", "repo", "skills/test-skill", "main")

        # Retrieve from cache
        cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "main")

        assert cached is not None

        # Verify all files exist
        assert (cached.path / "SKILL.md").exists()
        assert (cached.path / "helper.py").exists()
        assert (cached.path / "README.md").exists()
        assert (cached.path / "utils" / "tools.py").exists()

        # Verify file contents
        assert "A test skill" in (cached.path / "SKILL.md").read_text()
        assert "helper_function" in (cached.path / "helper.py").read_text()
        assert "Utility tools" in (cached.path / "utils" / "tools.py").read_text()

    def test_cache_with_skill_source_methods(self, cache_dir, skill_dir):
        """Test that cached SkillSource supports all methods."""
        cache = SkillCache(cache_dir)

        original = SkillSource(
            name="test-skill",
            path=skill_dir,
            source_url="https://github.com/test/repo/tree/main/skills/test-skill",
            source_ref="main",
        )

        # Cache it
        cache.cache_skill(original, "test", "repo", "skills/test-skill", "main")

        # Retrieve from cache
        cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "main")

        assert cached is not None

        # Test get_files()
        files = cached.get_files()
        file_names = {f.name for f in files}
        assert "SKILL.md" in file_names
        assert "helper.py" in file_names
        assert "README.md" in file_names
        assert "tools.py" in file_names

        # Test get_markdown_files()
        md_files = cached.get_markdown_files()
        md_names = {f.name for f in md_files}
        assert "SKILL.md" in md_names
        assert "README.md" in md_names
        assert "helper.py" not in md_names

        # Test get_non_markdown_files()
        non_md_files = cached.get_non_markdown_files()
        non_md_names = {f.name for f in non_md_files}
        assert "helper.py" in non_md_names
        assert "tools.py" in non_md_names
        assert "SKILL.md" not in non_md_names

    def test_cache_workflow_with_force_refresh(self, cache_dir, skill_dir):
        """Test a typical cache workflow with force refresh."""
        cache = SkillCache(cache_dir, ttl_seconds=3600)

        # First fetch (cache miss)
        cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "main")
        assert cached is None

        # Download and cache
        original = SkillSource(
            name="test-skill",
            path=skill_dir,
            source_url="https://github.com/test/repo/tree/main/skills/test-skill",
            source_ref="main",
        )
        cache.cache_skill(original, "test", "repo", "skills/test-skill", "main")

        # Second fetch (cache hit)
        cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "main")
        assert cached is not None

        # Modify original
        (skill_dir / "new_file.py").write_text("# New file")

        # Cache still returns old version
        cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "main")
        assert not (cached.path / "new_file.py").exists()

        # Force refresh by re-caching
        updated_original = SkillSource(
            name="test-skill",
            path=skill_dir,
            source_url="https://github.com/test/repo/tree/main/skills/test-skill",
            source_ref="main",
        )
        cache.cache_skill(
            updated_original, "test", "repo", "skills/test-skill", "main"
        )

        # Now new file should be present
        cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "main")
        assert (cached.path / "new_file.py").exists()

    def test_cache_isolation_between_refs(self, cache_dir, skill_dir):
        """Test that different refs are cached separately."""
        cache = SkillCache(cache_dir)

        # Cache for 'main' ref
        main_source = SkillSource(
            name="test-skill",
            path=skill_dir,
            source_url="https://github.com/test/repo/tree/main/skills/test-skill",
            source_ref="main",
        )
        cache.cache_skill(main_source, "test", "repo", "skills/test-skill", "main")

        # Create modified version for 'dev' ref
        (skill_dir / "dev_feature.py").write_text("# Dev feature")

        dev_source = SkillSource(
            name="test-skill",
            path=skill_dir,
            source_url="https://github.com/test/repo/tree/dev/skills/test-skill",
            source_ref="dev",
        )
        cache.cache_skill(dev_source, "test", "repo", "skills/test-skill", "dev")

        # Retrieve both
        main_cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "main")
        dev_cached = cache.get_cached_skill("test", "repo", "skills/test-skill", "dev")

        # Verify they're different
        assert main_cached is not None
        assert dev_cached is not None
        assert main_cached.path != dev_cached.path

        # Main doesn't have dev feature
        assert not (main_cached.path / "dev_feature.py").exists()

        # Dev has dev feature
        assert (dev_cached.path / "dev_feature.py").exists()
