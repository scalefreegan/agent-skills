"""Tests for GitHub fetcher with mocked API responses."""

from pathlib import Path

import httpx
import pytest
import respx

from skill_manager.fetch.github import GitHubFetcher


@pytest.fixture
def github_fetcher():
    """Create a GitHubFetcher instance."""
    return GitHubFetcher()


@pytest.fixture
def github_fetcher_with_token():
    """Create a GitHubFetcher instance with token."""
    return GitHubFetcher(token="test-token-123")


class TestGitHubFetcherInit:
    """Test GitHubFetcher initialization."""

    def test_init_without_token(self, github_fetcher):
        """Test initialization without token."""
        assert github_fetcher.token is None
        assert "Authorization" not in github_fetcher._headers
        assert github_fetcher._headers["Accept"] == "application/vnd.github+json"

    def test_init_with_token(self, github_fetcher_with_token):
        """Test initialization with token."""
        assert github_fetcher_with_token.token == "test-token-123"
        assert (
            github_fetcher_with_token._headers["Authorization"]
            == "Bearer test-token-123"
        )


@pytest.mark.anyio
class TestGitHubFetcherFetch:
    """Test GitHubFetcher fetch method."""

    @respx.mock
    async def test_fetch_simple_skill(self, github_fetcher, tmp_path):
        """Test fetching a simple skill with one file."""
        # Mock GitHub API response for directory listing
        contents_url = (
            "https://api.github.com/repos/owner/repo/contents/skills/my-skill"
        )
        respx.get(contents_url).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "type": "file",
                        "name": "SKILL.md",
                        "path": "skills/my-skill/SKILL.md",
                        "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md",
                    }
                ],
            )
        )

        # Mock file download
        file_content = """---
name: my-skill
description: Test skill
---

# My Skill
"""
        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md"
        ).mock(return_value=httpx.Response(200, content=file_content.encode()))

        # Fetch the skill
        target_dir = tmp_path / "my-skill"
        skill = await github_fetcher.fetch(
            owner="owner",
            repo="repo",
            path="skills/my-skill",
            ref="main",
            target_dir=target_dir,
        )

        # Verify SkillSource
        assert skill.name == "my-skill"
        assert skill.path == target_dir
        assert (
            skill.source_url
            == "https://github.com/owner/repo/tree/main/skills/my-skill"
        )
        assert skill.source_ref == "main"

        # Verify file was downloaded
        assert (target_dir / "SKILL.md").exists()
        assert "# My Skill" in (target_dir / "SKILL.md").read_text()

    @respx.mock
    async def test_fetch_skill_with_subdirectory(self, github_fetcher, tmp_path):
        """Test fetching skill with nested directories."""
        # Mock root directory
        respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/complex"
        ).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "type": "file",
                        "name": "SKILL.md",
                        "path": "skills/complex/SKILL.md",
                        "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/complex/SKILL.md",
                    },
                    {
                        "type": "dir",
                        "name": "utils",
                        "path": "skills/complex/utils",
                    },
                ],
            )
        )

        # Mock subdirectory
        respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/complex/utils"
        ).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "type": "file",
                        "name": "helper.py",
                        "path": "skills/complex/utils/helper.py",
                        "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/complex/utils/helper.py",
                    }
                ],
            )
        )

        # Mock file downloads
        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/complex/SKILL.md"
        ).mock(
            return_value=httpx.Response(
                200,
                content=b"---\nname: complex\n---\n# Complex Skill",
            )
        )
        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/complex/utils/helper.py"
        ).mock(
            return_value=httpx.Response(
                200,
                content=b"# Helper code",
            )
        )

        # Fetch the skill
        target_dir = tmp_path / "complex"
        skill = await github_fetcher.fetch(
            owner="owner",
            repo="repo",
            path="skills/complex",
            ref="main",
            target_dir=target_dir,
        )

        # Verify structure
        assert (target_dir / "SKILL.md").exists()
        assert (target_dir / "utils").is_dir()
        assert (target_dir / "utils" / "helper.py").exists()

    @respx.mock
    async def test_fetch_404_error(self, github_fetcher, tmp_path):
        """Test fetching nonexistent skill raises error."""
        respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/nonexistent"
        ).mock(return_value=httpx.Response(404))

        target_dir = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Path not found"):
            await github_fetcher.fetch(
                owner="owner",
                repo="repo",
                path="skills/nonexistent",
                ref="main",
                target_dir=target_dir,
            )

    @respx.mock
    async def test_fetch_with_authentication(self, github_fetcher_with_token, tmp_path):
        """Test that authentication token is included in requests."""
        # Mock with route to capture request headers
        route = respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/my-skill"
        ).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "type": "file",
                        "name": "SKILL.md",
                        "path": "skills/my-skill/SKILL.md",
                        "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md",
                    }
                ],
            )
        )

        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md"
        ).mock(
            return_value=httpx.Response(
                200,
                content=b"---\nname: my-skill\n---\n# My Skill",
            )
        )

        target_dir = tmp_path / "my-skill"
        await github_fetcher_with_token.fetch(
            owner="owner",
            repo="repo",
            path="skills/my-skill",
            ref="main",
            target_dir=target_dir,
        )

        # Verify Authorization header was sent
        assert route.called
        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer test-token-123"

    @respx.mock
    async def test_fetch_skill_without_skill_md(self, github_fetcher, tmp_path):
        """Test fetching skill without SKILL.md succeeds but has no metadata."""
        # Mock response without SKILL.md
        respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/no-skill-md"
        ).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "type": "file",
                        "name": "README.md",
                        "path": "skills/no-skill-md/README.md",
                        "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/no-skill-md/README.md",
                    }
                ],
            )
        )

        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/no-skill-md/README.md"
        ).mock(return_value=httpx.Response(200, content=b"# README"))

        target_dir = tmp_path / "no-skill-md"

        # Should succeed even without SKILL.md
        skill = await github_fetcher.fetch(
            owner="owner",
            repo="repo",
            path="skills/no-skill-md",
            ref="main",
            target_dir=target_dir,
        )

        # Verify skill was fetched
        assert skill.name == "no-skill-md"
        assert (target_dir / "README.md").exists()
        # Metadata should be None since no SKILL.md
        assert skill.metadata is None

    @respx.mock
    async def test_fetch_creates_target_dir(self, github_fetcher, tmp_path):
        """Test that fetch creates target directory if it doesn't exist."""
        respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/my-skill"
        ).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "type": "file",
                        "name": "SKILL.md",
                        "path": "skills/my-skill/SKILL.md",
                        "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md",
                    }
                ],
            )
        )

        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md"
        ).mock(
            return_value=httpx.Response(
                200,
                content=b"---\nname: my-skill\n---\n# Skill",
            )
        )

        # Use nested path that doesn't exist
        target_dir = tmp_path / "nested" / "path" / "my-skill"
        assert not target_dir.exists()

        await github_fetcher.fetch(
            owner="owner",
            repo="repo",
            path="skills/my-skill",
            ref="main",
            target_dir=target_dir,
        )

        assert target_dir.exists()

    @respx.mock
    async def test_fetch_binary_file(self, github_fetcher, tmp_path):
        """Test fetching skill with binary files."""
        respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/with-binary"
        ).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "type": "file",
                        "name": "SKILL.md",
                        "path": "skills/with-binary/SKILL.md",
                        "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/with-binary/SKILL.md",
                    },
                    {
                        "type": "file",
                        "name": "image.png",
                        "path": "skills/with-binary/image.png",
                        "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/with-binary/image.png",
                    },
                ],
            )
        )

        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/with-binary/SKILL.md"
        ).mock(
            return_value=httpx.Response(
                200,
                content=b"---\nname: with-binary\n---\n# Skill",
            )
        )

        # Mock binary file
        binary_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/with-binary/image.png"
        ).mock(return_value=httpx.Response(200, content=binary_content))

        target_dir = tmp_path / "with-binary"
        await github_fetcher.fetch(
            owner="owner",
            repo="repo",
            path="skills/with-binary",
            ref="main",
            target_dir=target_dir,
        )

        # Verify binary file was written correctly
        assert (target_dir / "image.png").exists()
        assert (target_dir / "image.png").read_bytes() == binary_content


@pytest.mark.anyio
class TestGitHubFetcherRetry:
    """Test retry logic for failed requests."""

    @respx.mock
    async def test_retry_on_network_error(self, github_fetcher, tmp_path):
        """Test that network errors trigger retries."""
        # First two attempts fail, third succeeds
        route = respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/my-skill"
        ).mock(
            side_effect=[
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
                httpx.Response(
                    200,
                    json=[
                        {
                            "type": "file",
                            "name": "SKILL.md",
                            "path": "skills/my-skill/SKILL.md",
                            "download_url": "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md",
                        }
                    ],
                ),
            ]
        )

        respx.get(
            "https://raw.githubusercontent.com/owner/repo/main/skills/my-skill/SKILL.md"
        ).mock(
            return_value=httpx.Response(
                200,
                content=b"---\nname: my-skill\n---\n# Skill",
            )
        )

        target_dir = tmp_path / "my-skill"
        skill = await github_fetcher.fetch(
            owner="owner",
            repo="repo",
            path="skills/my-skill",
            ref="main",
            target_dir=target_dir,
        )

        # Should succeed after retries
        assert skill.name == "my-skill"
        assert route.call_count == 3

    @respx.mock
    async def test_max_retries_exceeded(self, github_fetcher, tmp_path):
        """Test that max retries are respected."""
        # All attempts fail
        respx.get(
            "https://api.github.com/repos/owner/repo/contents/skills/my-skill"
        ).mock(side_effect=httpx.ConnectError("Connection failed"))

        target_dir = tmp_path / "my-skill"

        with pytest.raises(httpx.HTTPError):
            await github_fetcher.fetch(
                owner="owner",
                repo="repo",
                path="skills/my-skill",
                ref="main",
                target_dir=target_dir,
            )


class TestGitHubFetcherConstants:
    """Test GitHubFetcher constants."""

    def test_base_url(self):
        """Test BASE_URL constant."""
        assert GitHubFetcher.BASE_URL == "https://api.github.com"

    def test_max_retries(self):
        """Test MAX_RETRIES constant."""
        assert GitHubFetcher.MAX_RETRIES == 3

    def test_retry_delay(self):
        """Test RETRY_DELAY constant."""
        assert GitHubFetcher.RETRY_DELAY == 1.0
