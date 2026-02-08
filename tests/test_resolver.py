"""Tests for URL and source resolution."""

import pytest

from skill_manager.config.schema import (
    ComposeItemConfig,
    PrecedenceLevel,
    SourceConfig,
    SourceType,
)
from skill_manager.core.resolver import (
    ResolvedSource,
    parse_github_url,
    resolve_compose_item,
    resolve_source,
)


class TestParseGitHubUrl:
    """Test GitHub URL parsing."""

    def test_parse_full_url_with_https(self):
        """Test parsing full HTTPS GitHub URL."""
        url = "https://github.com/owner/repo/tree/main/path/to/skill"
        result = parse_github_url(url)

        assert result.type == "github"
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.ref == "main"
        assert result.path == "path/to/skill"

    def test_parse_url_without_https(self):
        """Test parsing URL without https:// prefix."""
        url = "github.com/owner/repo/tree/main/skills/my-skill"
        result = parse_github_url(url)

        assert result.type == "github"
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.ref == "main"
        assert result.path == "skills/my-skill"

    def test_parse_url_with_www(self):
        """Test parsing URL with www prefix."""
        url = "https://www.github.com/owner/repo/tree/main/skill"
        result = parse_github_url(url)

        assert result.type == "github"
        assert result.owner == "owner"
        assert result.repo == "repo"

    def test_parse_url_minimal(self):
        """Test parsing minimal URL (owner/repo only)."""
        url = "github.com/owner/repo"
        result = parse_github_url(url)

        assert result.type == "github"
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.ref is None
        assert result.path is None

    def test_parse_url_with_branch_no_path(self):
        """Test parsing URL with branch but no path."""
        url = "github.com/owner/repo/tree/develop"
        result = parse_github_url(url)

        assert result.type == "github"
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.ref == "develop"
        assert result.path is None

    def test_parse_url_with_tag(self):
        """Test parsing URL with tag reference."""
        url = "github.com/owner/repo/tree/v1.0.0/skills/my-skill"
        result = parse_github_url(url)

        assert result.ref == "v1.0.0"
        assert result.path == "skills/my-skill"

    def test_parse_url_with_nested_path(self):
        """Test parsing URL with deeply nested path."""
        url = "github.com/owner/repo/tree/main/level1/level2/level3/skill"
        result = parse_github_url(url)

        assert result.path == "level1/level2/level3/skill"

    def test_parse_invalid_url_not_github(self):
        """Test that non-GitHub URL raises error."""
        url = "https://gitlab.com/owner/repo"

        with pytest.raises(ValueError, match="Not a GitHub URL"):
            parse_github_url(url)

    def test_parse_invalid_url_missing_repo(self):
        """Test that URL with only owner raises error."""
        url = "github.com/owner"

        with pytest.raises(ValueError, match="Invalid GitHub URL format"):
            parse_github_url(url)

    def test_parse_url_with_commit_sha(self):
        """Test parsing URL with commit SHA."""
        url = "github.com/owner/repo/tree/abc123def456/path/to/skill"
        result = parse_github_url(url)

        assert result.ref == "abc123def456"


class TestResolveSource:
    """Test named source resolution."""

    def test_resolve_github_source_basic(self):
        """Test resolving basic GitHub source."""
        sources = {
            "my-source": SourceConfig(
                type=SourceType.GITHUB,
                repo="owner/repo",
                path="skills",
                branch="main",
            )
        }

        result = resolve_source("my-source", sources, default_branch="develop")

        assert result.type == "github"
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.path == "skills"
        assert result.ref == "main"  # Uses source's branch

    def test_resolve_source_uses_default_branch(self):
        """Test that source uses default branch when not specified."""
        sources = {
            "my-source": SourceConfig(
                type=SourceType.GITHUB,
                repo="owner/repo",
                path="skills",
            )
        }

        result = resolve_source("my-source", sources, default_branch="develop")

        assert result.ref == "develop"  # Uses default branch

    def test_resolve_source_no_path(self):
        """Test resolving source without path."""
        sources = {
            "my-source": SourceConfig(
                type=SourceType.GITHUB,
                repo="owner/repo",
            )
        }

        result = resolve_source("my-source", sources, default_branch="main")

        assert result.path is None

    def test_resolve_nonexistent_source(self):
        """Test that resolving nonexistent source raises error."""
        sources = {}

        with pytest.raises(ValueError, match="Source 'missing' not found"):
            resolve_source("missing", sources, default_branch="main")

    def test_resolve_source_with_special_characters(self):
        """Test resolving source with special characters in repo."""
        sources = {
            "special-source": SourceConfig(
                type=SourceType.GITHUB,
                repo="org-name/repo-name",
                path="my/path/to/skills",
            )
        }

        result = resolve_source("special-source", sources, default_branch="main")

        assert result.owner == "org-name"
        assert result.repo == "repo-name"
        assert result.path == "my/path/to/skills"


class TestResolveComposeItem:
    """Test compose item resolution."""

    def test_resolve_with_named_source(self):
        """Test resolving compose item with named source."""
        sources = {
            "my-source": SourceConfig(
                type=SourceType.GITHUB,
                repo="owner/repo",
                path="skills",
                branch="main",
            )
        }

        item = ComposeItemConfig(
            source="my-source",
            skill="my-skill",
            level=PrecedenceLevel.DEFAULT,
        )

        result = resolve_compose_item(item, sources, default_branch="develop")

        assert result.type == "github"
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.path == "skills/my-skill"  # Source path + skill name
        assert result.ref == "main"

    def test_resolve_with_named_source_no_base_path(self):
        """Test resolving when source has no base path."""
        sources = {
            "my-source": SourceConfig(
                type=SourceType.GITHUB,
                repo="owner/repo",
                branch="main",
            )
        }

        item = ComposeItemConfig(
            source="my-source",
            skill="my-skill",
            level=PrecedenceLevel.DEFAULT,
        )

        result = resolve_compose_item(item, sources, default_branch="develop")

        assert result.path == "my-skill"  # Just the skill name

    def test_resolve_with_direct_url(self):
        """Test resolving compose item with direct URL."""
        item = ComposeItemConfig(
            url="https://github.com/owner/repo/tree/main/skills/custom-skill",
            level=PrecedenceLevel.USER,
        )

        result = resolve_compose_item(item, {}, default_branch="main")

        assert result.type == "github"
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.ref == "main"
        assert result.path == "skills/custom-skill"

    def test_resolve_with_local_path(self):
        """Test resolving compose item with local path."""
        item = ComposeItemConfig(
            path="/local/path/to/skill",
            level=PrecedenceLevel.DEFAULT,
        )

        result = resolve_compose_item(item, {}, default_branch="main")

        assert result.type == "local"
        assert result.local_path is not None
        assert str(result.local_path) == "/local/path/to/skill"

    def test_resolve_with_relative_path(self):
        """Test resolving compose item with relative path."""
        item = ComposeItemConfig(
            path="./local-skills/my-skill",
            level=PrecedenceLevel.USER,
        )

        result = resolve_compose_item(item, {}, default_branch="main")

        assert result.type == "local"
        assert result.local_path is not None
        # Path should be expanded to absolute
        assert result.local_path.is_absolute()

    def test_resolve_with_home_path(self):
        """Test resolving compose item with ~ path."""
        item = ComposeItemConfig(
            path="~/skills/my-skill",
            level=PrecedenceLevel.DEFAULT,
        )

        result = resolve_compose_item(item, {}, default_branch="main")

        assert result.type == "local"
        assert result.local_path is not None
        # Path should be expanded
        assert not str(result.local_path).startswith("~")


class TestResolvedSource:
    """Test ResolvedSource dataclass."""

    def test_github_source(self):
        """Test creating GitHub resolved source."""
        source = ResolvedSource(
            type="github",
            owner="owner",
            repo="repo",
            path="skills/my-skill",
            ref="main",
        )

        assert source.type == "github"
        assert source.owner == "owner"
        assert source.repo == "repo"
        assert source.path == "skills/my-skill"
        assert source.ref == "main"
        assert source.local_path is None

    def test_local_source(self):
        """Test creating local resolved source."""
        from pathlib import Path

        source = ResolvedSource(
            type="local",
            local_path=Path("/local/path"),
        )

        assert source.type == "local"
        assert source.local_path == Path("/local/path")
        assert source.owner is None
        assert source.repo is None
        assert source.path is None
        assert source.ref is None


class TestComplexResolutionScenarios:
    """Test complex resolution scenarios."""

    def test_resolve_multiple_compose_items(self):
        """Test resolving multiple compose items."""
        sources = {
            "github-source": SourceConfig(
                type=SourceType.GITHUB,
                repo="org/repo",
                path="base",
            )
        }

        items = [
            ComposeItemConfig(
                source="github-source",
                skill="skill1",
                level=PrecedenceLevel.DEFAULT,
            ),
            ComposeItemConfig(
                url="https://github.com/other/repo/tree/main/skills/skill2",
                level=PrecedenceLevel.DEFAULT,
            ),
            ComposeItemConfig(
                path="/local/overrides",
                level=PrecedenceLevel.USER,
            ),
        ]

        results = [
            resolve_compose_item(item, sources, default_branch="main")
            for item in items
        ]

        assert len(results) == 3
        assert results[0].type == "github"
        assert results[0].path == "base/skill1"
        assert results[1].type == "github"
        assert results[1].owner == "other"
        assert results[2].type == "local"

    def test_resolve_with_different_branches(self):
        """Test that different sources can have different branches."""
        sources = {
            "stable": SourceConfig(
                type=SourceType.GITHUB,
                repo="org/repo",
                branch="main",
            ),
            "experimental": SourceConfig(
                type=SourceType.GITHUB,
                repo="org/repo",
                branch="develop",
            ),
        }

        stable_result = resolve_source("stable", sources, default_branch="fallback")
        experimental_result = resolve_source(
            "experimental", sources, default_branch="fallback"
        )

        assert stable_result.ref == "main"
        assert experimental_result.ref == "develop"

    def test_url_parsing_edge_cases(self):
        """Test URL parsing with various edge cases."""
        # URL with single-letter components
        url1 = "github.com/a/b/tree/c/d"
        result1 = parse_github_url(url1)
        assert result1.owner == "a"
        assert result1.repo == "b"
        assert result1.ref == "c"
        assert result1.path == "d"

        # URL with numeric components
        url2 = "github.com/org123/repo456/tree/v1.2.3/skill789"
        result2 = parse_github_url(url2)
        assert result2.owner == "org123"
        assert result2.ref == "v1.2.3"
