"""Skill registry for tracking installed skills."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from skill_manager.core.skill import Skill
from skill_manager.utils.paths import ensure_dir


class SkillRegistry:
    """Manages the skill installation registry and manifest file.

    The registry tracks all installed skills in a .skill-manager-manifest.json
    file, storing metadata about each skill including composition sources,
    versions, and install timestamps.
    """

    MANIFEST_FILENAME = ".skill-manager-manifest.json"
    MANIFEST_VERSION = "1.0"

    def __init__(self, target_dir: Path):
        """Initialize the registry for a target directory.

        Args:
            target_dir: The directory where skills are installed
        """
        self.target_dir = Path(target_dir)
        self.manifest_path = self.target_dir / self.MANIFEST_FILENAME
        self._manifest_data: dict = {"version": self.MANIFEST_VERSION, "skills": {}}

    def load(self) -> dict:
        """Load the manifest from disk.

        Returns:
            The manifest data as a dictionary
        """
        if not self.manifest_path.exists():
            # Return empty manifest structure if file doesn't exist
            self._manifest_data = {
                "version": self.MANIFEST_VERSION,
                "skills": {}
            }
            return self._manifest_data

        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                self._manifest_data = json.load(f)

            # Ensure manifest has proper structure
            if "version" not in self._manifest_data:
                self._manifest_data["version"] = self.MANIFEST_VERSION
            if "skills" not in self._manifest_data:
                self._manifest_data["skills"] = {}

            return self._manifest_data
        except (json.JSONDecodeError, IOError) as e:
            # If manifest is corrupted, start fresh
            self._manifest_data = {
                "version": self.MANIFEST_VERSION,
                "skills": {}
            }
            return self._manifest_data

    def save(self) -> None:
        """Save the manifest to disk.

        Creates the target directory if it doesn't exist.
        """
        # Ensure the target directory exists
        ensure_dir(self.target_dir)

        # Write manifest with pretty formatting
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self._manifest_data, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline

    def add_skill(self, skill: Skill) -> None:
        """Add or update a skill in the registry.

        Args:
            skill: The skill to add to the registry
        """
        # Set installed_at timestamp if not already set
        if not skill.installed_at:
            skill.installed_at = datetime.now(timezone.utc).isoformat()

        # Create skill entry
        skill_entry = {
            "name": skill.name,
            "path": str(skill.path),
            "description": skill.description,
            "composed_from": skill.composed_from,
            "installed_at": skill.installed_at
        }

        # Add to manifest
        self._manifest_data["skills"][skill.name] = skill_entry

    def remove_skill(self, name: str) -> None:
        """Remove a skill from the registry.

        Args:
            name: The name of the skill to remove
        """
        if name in self._manifest_data["skills"]:
            del self._manifest_data["skills"][name]

    def get_skill(self, name: str) -> Optional[dict]:
        """Get a skill's metadata from the registry.

        Args:
            name: The name of the skill to retrieve

        Returns:
            The skill's metadata dictionary, or None if not found
        """
        return self._manifest_data["skills"].get(name)

    def list_skills(self) -> list[dict]:
        """Get a list of all installed skills.

        Returns:
            A list of skill metadata dictionaries
        """
        return list(self._manifest_data["skills"].values())

    def detect_conflicts(self, skill_name: str) -> list[str]:
        """Detect conflicts between a skill and existing installations.

        A conflict occurs when a skill with the same name is already installed.
        This method checks for name conflicts before installation.

        Args:
            skill_name: The name of the skill to check for conflicts

        Returns:
            A list of conflicting skill names (will be empty or contain the
            single conflicting skill name)
        """
        conflicts = []

        if skill_name in self._manifest_data["skills"]:
            conflicts.append(skill_name)

        return conflicts

    def has_skill(self, name: str) -> bool:
        """Check if a skill is installed.

        Args:
            name: The name of the skill to check

        Returns:
            True if the skill is installed, False otherwise
        """
        return name in self._manifest_data["skills"]

    def get_skill_path(self, name: str) -> Optional[Path]:
        """Get the installation path for a skill.

        Args:
            name: The name of the skill

        Returns:
            The Path to the installed skill, or None if not found
        """
        skill = self.get_skill(name)
        if skill and "path" in skill:
            return Path(skill["path"])
        return None
