"""GitHub skill fetcher using GitHub Contents API."""

import asyncio
from pathlib import Path
from typing import Any

import httpx

from skill_manager.core.skill import SkillSource


class GitHubFetcher:
    """Fetcher for downloading skills from GitHub repositories."""

    BASE_URL = "https://api.github.com"
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(self, token: str | None = None):
        """Initialize GitHub fetcher.

        Args:
            token: Optional GitHub personal access token for authenticated requests
        """
        self.token = token
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    async def fetch(
        self, owner: str, repo: str, path: str, ref: str, target_dir: Path
    ) -> SkillSource:
        """Fetch a skill from GitHub and return SkillSource.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name
            path: Path within the repository to the skill
            ref: Git reference (branch, tag, or commit SHA)
            target_dir: Local directory to download skill contents

        Returns:
            SkillSource object pointing to the downloaded skill

        Raises:
            ValueError: If the skill cannot be fetched or validated
            httpx.HTTPError: If API requests fail
        """
        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # Fetch the contents recursively
        async with httpx.AsyncClient(timeout=30.0) as client:
            await self._fetch_directory(client, owner, repo, path, ref, target_dir)

        # Extract skill name from path (last component)
        skill_name = path.rstrip("/").split("/")[-1]

        # Create source URL
        source_url = f"https://github.com/{owner}/{repo}/tree/{ref}/{path}"

        # Return SkillSource - validation happens in __post_init__
        return SkillSource(
            name=skill_name,
            path=target_dir,
            source_url=source_url,
            source_ref=ref,
        )

    async def _fetch_directory(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
        path: str,
        ref: str,
        target_dir: Path,
    ) -> None:
        """Recursively fetch directory contents from GitHub.

        Args:
            client: HTTP client for making requests
            owner: Repository owner
            repo: Repository name
            path: Path within the repository
            ref: Git reference
            target_dir: Local directory to save contents
        """
        # Get directory contents
        contents = await self._get_contents(client, owner, repo, path, ref)

        # Process each item
        tasks = []
        for item in contents:
            item_type = item.get("type")
            item_name = item.get("name")
            item_path = item.get("path")

            if not item_name or not item_path:
                continue

            if item_type == "file":
                # Download file
                task = self._download_file(
                    client, item, target_dir / item_name
                )
                tasks.append(task)
            elif item_type == "dir":
                # Recursively fetch subdirectory
                subdir = target_dir / item_name
                subdir.mkdir(parents=True, exist_ok=True)
                task = self._fetch_directory(
                    client, owner, repo, item_path, ref, subdir
                )
                tasks.append(task)

        # Execute all tasks concurrently
        if tasks:
            await asyncio.gather(*tasks)

    async def _get_contents(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> list[dict[str, Any]]:
        """Get contents of a directory from GitHub API.

        Args:
            client: HTTP client
            owner: Repository owner
            repo: Repository name
            path: Path within the repository
            ref: Git reference

        Returns:
            List of content items

        Raises:
            ValueError: If the API response is invalid
            httpx.HTTPError: If the request fails after retries
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.get(
                    url, headers=self._headers, params=params, follow_redirects=True
                )
                response.raise_for_status()

                data = response.json()
                if not isinstance(data, list):
                    raise ValueError(
                        f"Expected directory at {path}, got file or invalid response"
                    )
                return data

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Path not found: {path}") from e
                elif e.response.status_code == 403:
                    # Rate limiting - check if we should retry
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                raise
            except httpx.HTTPError as e:
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise

        raise httpx.HTTPError(f"Failed to fetch contents after {self.MAX_RETRIES} attempts")

    async def _download_file(
        self, client: httpx.AsyncClient, item: dict[str, Any], target_path: Path
    ) -> None:
        """Download a file from GitHub.

        Args:
            client: HTTP client
            item: Content item from GitHub API containing download_url
            target_path: Local path to save the file

        Raises:
            ValueError: If download_url is missing
            httpx.HTTPError: If the download fails after retries
        """
        download_url = item.get("download_url")
        if not download_url:
            raise ValueError(f"No download_url for file: {item.get('name')}")

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.get(
                    download_url, follow_redirects=True
                )
                response.raise_for_status()

                # Write file content
                target_path.write_bytes(response.content)
                return

            except httpx.HTTPError as e:
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise

        raise httpx.HTTPError(
            f"Failed to download file {target_path.name} after {self.MAX_RETRIES} attempts"
        )
