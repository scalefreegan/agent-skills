"""Core skill models and parsing."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class SkillMetadata:
    """Metadata parsed from a skill's SKILL.md frontmatter."""

    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> "SkillMetadata":
        """Create metadata from parsed YAML."""
        name = data.pop("name")
        description = data.pop("description", None)
        version = data.pop("version", None)
        author = data.pop("author", None)
        return cls(
            name=name,
            description=description,
            version=version,
            author=author,
            extra=data,
        )


@dataclass
class SkillSource:
    """Represents a fetched skill before composition."""

    name: str
    path: Path
    metadata: Optional[SkillMetadata] = None
    source_url: Optional[str] = None
    source_ref: Optional[str] = None

    def __post_init__(self):
        """Validate skill structure and parse metadata if available."""
        if not self.path.exists():
            raise ValueError(f"Skill path does not exist: {self.path}")
        if not self.path.is_dir():
            raise ValueError(f"Skill path is not a directory: {self.path}")

        # Try to parse SKILL.md if it exists
        skill_md = self.path / "SKILL.md"
        if skill_md.exists():
            try:
                self.metadata = self._parse_skill_md(skill_md)
            except Exception as e:
                # Non-fatal - skill can exist without valid metadata
                pass

    def _parse_skill_md(self, skill_md_path: Path) -> Optional[SkillMetadata]:
        """Parse YAML frontmatter from SKILL.md."""
        content = skill_md_path.read_text()

        # Match YAML frontmatter: --- at start, content, --- to close
        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return None

        frontmatter = match.group(1)
        try:
            data = yaml.safe_load(frontmatter)
            if not isinstance(data, dict):
                return None
            if "name" not in data:
                return None
            return SkillMetadata.from_yaml(data)
        except yaml.YAMLError:
            return None

    def get_files(self) -> list[Path]:
        """Get all files in the skill directory recursively."""
        return [f for f in self.path.rglob("*") if f.is_file()]

    def get_markdown_files(self) -> list[Path]:
        """Get all markdown files in the skill directory."""
        return [f for f in self.get_files() if f.suffix.lower() == ".md"]

    def get_non_markdown_files(self) -> list[Path]:
        """Get all non-markdown files in the skill directory."""
        return [f for f in self.get_files() if f.suffix.lower() != ".md"]


@dataclass
class Skill:
    """Represents an installed skill."""

    name: str
    path: Path
    description: Optional[str] = None
    composed_from: list[str] = field(default_factory=list)
    installed_at: Optional[str] = None

    @classmethod
    def from_source(cls, source: SkillSource, target_path: Path) -> "Skill":
        """Create a Skill from a SkillSource."""
        description = None
        if source.metadata:
            description = source.metadata.description

        return cls(
            name=source.name,
            path=target_path,
            description=description,
        )
