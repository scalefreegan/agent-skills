"""Tests for skill cache functionality."""

import json
import time
from datetime import datetime, timedelta, timezone
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
    skill_path = tmp_path / "sample-skill"
    skill_path.mkdir()

    # Create SKILL.md
    skill_md = skill_path / "SKILL.md"
    skill_md.write_text(
        """---
name: sample-skill
description: A sample skill
version: 1.0.0
---

# Sample Skill

This is a sample skill for testing.
"""
    )

    # Create other files
    (skill_path / "helper.py").write_text("# Helper code")
    (skill_path / "README.md").write_text("# README")

    # Create subdirectory
    subdir = skill_path / "utils"
    subdir.mkdir()
    (subdir / "tools.py").write_text("# Tools")

    return skill_path


@pytest.fixture
def skill_source(skill_dir):
    """Create a SkillSource for testing."""
    return SkillSource(
        name="sample-skill",
        path=skill_dir,
        source_url="https://github.com/test/repo/tree/main/skills/sample-skill",
        source_ref="main",
    )


class TestSkillCache:
    """Test SkillCache functionality."""

    def test_init(self, cache_dir):
        """Test cache initialization."""
        cache = SkillCache(cache_dir)
        assert cache.cache_dir == cache_dir
        assert cache.ttl_seconds == 86400
        assert cache_dir.exists()

    def test_init_custom_ttl(self, cache_dir):
        """Test cache initialization with custom TTL."""
        cache = SkillCache(cache_dir, ttl_seconds=3600)
        assert cache.ttl_seconds == 3600

    def test_get_cache_key(self, cache_dir):
        """Test cache key generation."""
        cache = SkillCache(cache_dir)

        key1 = cache.get_cache_key("owner", "repo", "path/to/skill", "main")
        key2 = cache.get_cache_key("owner", "repo", "path/to/skill", "main")
        key3 = cache.get_cache_key("owner", "repo", "path/to/skill", "dev")

        # Same inputs produce same key
        assert key1 == key2

        # Different ref produces different key
        assert key1 != key3

        # Key should be safe for filesystem
        assert "/" not in key1
        assert ":" not in key1

        # Key should contain human-readable parts
        assert "owner" in key1
        assert "repo" in key1
        assert "main" in key1

    def test_cache_and_retrieve_skill(self, cache_dir, skill_source):
        """Test caching and retrieving a skill."""
        cache = SkillCache(cache_dir)

        # Cache the skill
        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        # Retrieve the cached skill
        cached = cache.get_cached_skill("test", "repo", "skills/sample-skill", "main")

        assert cached is not None
        assert cached.name == "sample-skill"
        assert cached.source_url == "https://github.com/test/repo/tree/main/skills/sample-skill"
        assert cached.source_ref == "main"

        # Verify files were copied
        assert (cached.path / "SKILL.md").exists()
        assert (cached.path / "helper.py").exists()
        assert (cached.path / "README.md").exists()
        assert (cached.path / "utils" / "tools.py").exists()

        # Verify metadata was written
        metadata_path = cached.path / SkillCache.METADATA_FILE
        assert metadata_path.exists()

        metadata = json.loads(metadata_path.read_text())
        assert metadata["owner"] == "test"
        assert metadata["repo"] == "repo"
        assert metadata["path"] == "skills/sample-skill"
        assert metadata["ref"] == "main"
        assert "cached_at" in metadata

    def test_cache_miss(self, cache_dir):
        """Test retrieving a skill that isn't cached."""
        cache = SkillCache(cache_dir)

        cached = cache.get_cached_skill("test", "repo", "skills/nonexistent", "main")
        assert cached is None

    def test_cache_different_refs(self, cache_dir, skill_source):
        """Test caching the same skill with different refs."""
        cache = SkillCache(cache_dir)

        # Cache with 'main' ref
        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        # Cache with 'dev' ref
        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "dev")

        # Both should be retrievable
        main_cached = cache.get_cached_skill("test", "repo", "skills/sample-skill", "main")
        dev_cached = cache.get_cached_skill("test", "repo", "skills/sample-skill", "dev")

        assert main_cached is not None
        assert dev_cached is not None
        assert main_cached.path != dev_cached.path

    def test_is_expired_fresh(self, cache_dir, skill_source):
        """Test that freshly cached skills are not expired."""
        cache = SkillCache(cache_dir, ttl_seconds=3600)

        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        cache_key = cache.get_cache_key("test", "repo", "skills/sample-skill", "main")
        cache_path = cache_dir / cache_key

        assert not cache.is_expired(cache_path)

    def test_is_expired_old(self, cache_dir, skill_source):
        """Test that old cached skills are expired."""
        cache = SkillCache(cache_dir, ttl_seconds=1)  # 1 second TTL

        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        cache_key = cache.get_cache_key("test", "repo", "skills/sample-skill", "main")
        cache_path = cache_dir / cache_key

        # Wait for expiration
        time.sleep(1.1)

        assert cache.is_expired(cache_path)

    def test_is_expired_no_metadata(self, cache_dir):
        """Test that cache without metadata is considered expired."""
        cache = SkillCache(cache_dir)

        # Create a cache directory without metadata
        cache_path = cache_dir / "test-cache"
        cache_path.mkdir(parents=True)

        assert cache.is_expired(cache_path)

    def test_is_expired_invalid_metadata(self, cache_dir):
        """Test that cache with invalid metadata is considered expired."""
        cache = SkillCache(cache_dir)

        # Create a cache directory with invalid metadata
        cache_path = cache_dir / "test-cache"
        cache_path.mkdir(parents=True)

        metadata_path = cache_path / SkillCache.METADATA_FILE
        metadata_path.write_text("invalid json")

        assert cache.is_expired(cache_path)

    def test_expired_cache_cleaned_on_get(self, cache_dir, skill_source):
        """Test that expired cache is cleaned up when retrieved."""
        cache = SkillCache(cache_dir, ttl_seconds=1)

        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        cache_key = cache.get_cache_key("test", "repo", "skills/sample-skill", "main")
        cache_path = cache_dir / cache_key

        # Verify cache exists
        assert cache_path.exists()

        # Wait for expiration
        time.sleep(1.1)

        # Try to retrieve - should return None and clean up
        cached = cache.get_cached_skill("test", "repo", "skills/sample-skill", "main")
        assert cached is None
        assert not cache_path.exists()

    def test_cache_overwrite(self, cache_dir, skill_source):
        """Test that caching overwrites existing cache."""
        cache = SkillCache(cache_dir)

        # Cache first time
        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        cached1 = cache.get_cached_skill("test", "repo", "skills/sample-skill", "main")
        first_cached_at = json.loads(
            (cached1.path / SkillCache.METADATA_FILE).read_text()
        )["cached_at"]

        # Wait a moment
        time.sleep(0.1)

        # Cache again
        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        cached2 = cache.get_cached_skill("test", "repo", "skills/sample-skill", "main")
        second_cached_at = json.loads(
            (cached2.path / SkillCache.METADATA_FILE).read_text()
        )["cached_at"]

        # Timestamps should be different
        assert first_cached_at != second_cached_at

    def test_clear_cache(self, cache_dir, skill_source):
        """Test clearing all cached skills."""
        cache = SkillCache(cache_dir)

        # Cache multiple skills
        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")
        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "dev")
        cache.cache_skill(skill_source, "test", "other", "skills/sample-skill", "main")

        # Verify they exist
        assert len(list(cache_dir.iterdir())) == 3

        # Clear cache
        cache.clear_cache()

        # Verify all removed
        assert len(list(cache_dir.iterdir())) == 0

    def test_clear_empty_cache(self, cache_dir):
        """Test clearing an empty cache doesn't raise errors."""
        cache = SkillCache(cache_dir)
        cache.clear_cache()  # Should not raise

    def test_cache_metadata_mismatch(self, cache_dir, skill_source):
        """Test that metadata mismatch returns None."""
        cache = SkillCache(cache_dir)

        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        # Try to retrieve with different parameters
        cached = cache.get_cached_skill("test", "repo", "skills/other-skill", "main")
        assert cached is None

    def test_cache_with_path_expansion(self, skill_source, tmp_path):
        """Test that cache dir path expansion works."""
        # Use a path with ~ (if we're not already in tmp)
        cache_dir_str = str(tmp_path / "test-cache")

        cache = SkillCache(Path(cache_dir_str))

        # Should work without errors
        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        cached = cache.get_cached_skill("test", "repo", "skills/sample-skill", "main")
        assert cached is not None

    def test_cache_invalid_skill_structure(self, cache_dir, tmp_path):
        """Test that cached skill with invalid structure returns None."""
        cache = SkillCache(cache_dir)

        # Create a skill directory without SKILL.md
        skill_path = tmp_path / "invalid-skill"
        skill_path.mkdir()

        skill_source = SkillSource(
            name="invalid-skill",
            path=skill_path,
            source_url="https://github.com/test/repo/tree/main/skills/invalid-skill",
            source_ref="main",
        )

        cache.cache_skill(skill_source, "test", "repo", "skills/invalid-skill", "main")

        # Now delete SKILL.md from cache to make it invalid
        cache_key = cache.get_cache_key("test", "repo", "skills/invalid-skill", "main")
        cache_path = cache_dir / cache_key

        # Remove all files to make it invalid
        for item in cache_path.iterdir():
            if item.is_file():
                item.unlink()

        # Should return None due to validation failure
        cached = cache.get_cached_skill("test", "repo", "skills/invalid-skill", "main")
        assert cached is None

    def test_cache_handles_special_characters(self, cache_dir):
        """Test cache key generation with special characters."""
        cache = SkillCache(cache_dir)

        # Test with various special characters
        key = cache.get_cache_key(
            "owner.name", "repo-name", "path/to/skill", "feature/branch-name"
        )

        # Should create valid filesystem name
        assert "/" not in key
        assert "\\" not in key
        assert ":" not in key

    def test_is_expired_with_naive_datetime(self, cache_dir, skill_source):
        """Test expiration handling with naive datetime (no timezone)."""
        cache = SkillCache(cache_dir, ttl_seconds=3600)

        cache.cache_skill(skill_source, "test", "repo", "skills/sample-skill", "main")

        cache_key = cache.get_cache_key("test", "repo", "skills/sample-skill", "main")
        cache_path = cache_dir / cache_key

        # Modify metadata to have naive datetime
        metadata_path = cache_path / SkillCache.METADATA_FILE
        metadata = json.loads(metadata_path.read_text())

        # Create naive datetime (no timezone) - use UTC time to ensure it's recent
        naive_time = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        metadata["cached_at"] = naive_time
        metadata_path.write_text(json.dumps(metadata))

        # Should handle gracefully and treat as UTC
        assert not cache.is_expired(cache_path)
