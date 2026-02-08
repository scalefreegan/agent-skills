"""Abstract interface for fetching skills from various sources."""

from pathlib import Path
from typing import Protocol

from skill_manager.core.skill import SkillSource


class SkillFetcher(Protocol):
    """Abstract interface for fetching skills from various sources."""

    async def fetch(
        self, owner: str, repo: str, path: str, ref: str, target_dir: Path
    ) -> SkillSource:
        """Fetch a skill and return SkillSource.

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
        """
        ...
