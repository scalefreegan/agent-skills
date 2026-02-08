"""Cache for downloaded skills with TTL-based expiration."""

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from skill_manager.core.skill import SkillSource
from skill_manager.utils.paths import ensure_dir, expand_path


class SkillCache:
    """Cache for downloaded skills with TTL-based expiration.

    Skills are cached by owner/repo/path/ref combination and stored in
    individual directories under the cache root. Each cached skill includes
    metadata about when it was cached and where it came from.
    """

    METADATA_FILE = ".cache-metadata.json"

    def __init__(self, cache_dir: Path, ttl_seconds: int = 86400):
        """Initialize skill cache.

        Args:
            cache_dir: Root directory for the cache (e.g., ~/.cache/skill-manager)
            ttl_seconds: Time-to-live in seconds for cached skills (default: 24 hours)
        """
        self.cache_dir = expand_path(str(cache_dir))
        self.ttl_seconds = ttl_seconds
        ensure_dir(self.cache_dir)

    def get_cache_key(self, owner: str, repo: str, path: str, ref: str) -> str:
        """Generate a unique cache key for a skill.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within the repository to the skill
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            Unique cache key string (hash-based directory name)
        """
        # Create a stable identifier
        identifier = f"{owner}/{repo}/{path}@{ref}"

        # Hash it to create a safe directory name
        hash_digest = hashlib.sha256(identifier.encode()).hexdigest()[:16]

        # Create a human-readable prefix
        safe_owner = owner.replace("/", "-").replace(".", "-")
        safe_repo = repo.replace("/", "-").replace(".", "-")
        safe_ref = ref.replace("/", "-").replace(".", "-")

        return f"{safe_owner}-{safe_repo}-{safe_ref}-{hash_digest}"

    def get_cached_skill(
        self, owner: str, repo: str, path: str, ref: str
    ) -> Optional[SkillSource]:
        """Retrieve a cached skill if it exists and hasn't expired.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within the repository to the skill
            ref: Git reference

        Returns:
            SkillSource if cached and valid, None otherwise
        """
        cache_key = self.get_cache_key(owner, repo, path, ref)
        cache_path = self.cache_dir / cache_key

        # Check if cache directory exists
        if not cache_path.exists() or not cache_path.is_dir():
            return None

        # Check if expired
        if self.is_expired(cache_path):
            # Clean up expired cache
            shutil.rmtree(cache_path, ignore_errors=True)
            return None

        # Verify metadata file exists
        metadata_path = cache_path / self.METADATA_FILE
        if not metadata_path.exists():
            return None

        # Try to load metadata and verify it matches
        try:
            metadata = json.loads(metadata_path.read_text())
            if (
                metadata.get("owner") != owner
                or metadata.get("repo") != repo
                or metadata.get("path") != path
                or metadata.get("ref") != ref
            ):
                # Metadata mismatch - cache is corrupted
                return None
        except (json.JSONDecodeError, OSError):
            return None

        # Extract skill name from path
        skill_name = path.rstrip("/").split("/")[-1]

        # Create source URL
        source_url = f"https://github.com/{owner}/{repo}/tree/{ref}/{path}"

        # Try to create SkillSource - validation happens in __post_init__
        try:
            return SkillSource(
                name=skill_name,
                path=cache_path,
                source_url=source_url,
                source_ref=ref,
            )
        except (ValueError, OSError):
            # Invalid skill structure
            return None

    def cache_skill(
        self, skill: SkillSource, owner: str, repo: str, path: str, ref: str
    ) -> None:
        """Cache a downloaded skill.

        Args:
            skill: The SkillSource to cache
            owner: Repository owner
            repo: Repository name
            path: Path within the repository to the skill
            ref: Git reference

        Raises:
            OSError: If caching fails
        """
        cache_key = self.get_cache_key(owner, repo, path, ref)
        cache_path = self.cache_dir / cache_key

        # Remove existing cache if present
        if cache_path.exists():
            shutil.rmtree(cache_path, ignore_errors=True)

        # Create cache directory
        ensure_dir(cache_path)

        # Copy skill contents to cache
        for item in skill.path.iterdir():
            if item.is_file():
                shutil.copy2(item, cache_path / item.name)
            elif item.is_dir():
                shutil.copytree(item, cache_path / item.name)

        # Write metadata
        metadata = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "owner": owner,
            "repo": repo,
            "path": path,
            "ref": ref,
        }
        metadata_path = cache_path / self.METADATA_FILE
        metadata_path.write_text(json.dumps(metadata, indent=2))

    def is_expired(self, cache_path: Path) -> bool:
        """Check if a cached skill has expired.

        Args:
            cache_path: Path to the cached skill directory

        Returns:
            True if expired or invalid, False otherwise
        """
        metadata_path = cache_path / self.METADATA_FILE
        if not metadata_path.exists():
            return True

        try:
            metadata = json.loads(metadata_path.read_text())
            cached_at_str = metadata.get("cached_at")
            if not cached_at_str:
                return True

            cached_at = datetime.fromisoformat(cached_at_str)
            now = datetime.now(timezone.utc)

            # Handle naive datetimes by assuming UTC
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)

            age = now - cached_at
            return age > timedelta(seconds=self.ttl_seconds)

        except (json.JSONDecodeError, ValueError, OSError):
            return True

    def clear_cache(self) -> None:
        """Remove all cached skills.

        Raises:
            OSError: If clearing the cache fails
        """
        if self.cache_dir.exists():
            for item in self.cache_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                elif item.is_file():
                    item.unlink(missing_ok=True)
