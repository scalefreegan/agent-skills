"""Pydantic models for skill manager configuration."""

from enum import Enum
from pathlib import Path
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, field_validator, HttpUrl


class PrecedenceLevel(str, Enum):
    """Precedence levels for composed skills."""

    DEFAULT = "default"
    USER = "user"


class SourceType(str, Enum):
    """Types of skill sources."""

    GITHUB = "github"


class SettingsConfig(BaseModel):
    """Global settings for skill manager."""

    target_dirs: list[str] = Field(
        default=[".claude/skills"],
        description="Target directories where skills will be installed",
    )
    cache_dir: str = Field(
        default="~/.cache/skill-manager",
        description="Directory for caching downloaded skills",
    )
    default_branch: str = Field(
        default="main", description="Default git branch for fetching skills"
    )


class SourceConfig(BaseModel):
    """Configuration for a named skill source."""

    type: SourceType = Field(description="Type of source (github, etc)")
    repo: str = Field(description="Repository in format 'owner/repo'")
    path: Optional[str] = Field(
        default=None, description="Path within repository to skills directory"
    )
    branch: Optional[str] = Field(
        default=None, description="Branch to fetch from (overrides default_branch)"
    )

    @field_validator("repo")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        """Validate repository format is owner/repo."""
        if "/" not in v or v.count("/") != 1:
            raise ValueError("Repository must be in format 'owner/repo'")
        return v


class ComposeItemConfig(BaseModel):
    """A single source in a composed skill."""

    source: Optional[str] = Field(
        default=None, description="Named source reference (mutually exclusive with path/url)"
    )
    skill: Optional[str] = Field(
        default=None,
        description="Skill name within the source (required when using source)",
    )
    path: Optional[str] = Field(
        default=None,
        description="Local filesystem path to skill (mutually exclusive with source/url)",
    )
    url: Optional[str] = Field(
        default=None,
        description="Direct GitHub URL to skill (mutually exclusive with source/path)",
    )
    level: PrecedenceLevel = Field(
        default=PrecedenceLevel.DEFAULT, description="Precedence level for this source"
    )

    @field_validator("skill")
    @classmethod
    def validate_skill_with_source(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that skill is provided when source is used."""
        if "source" in info.data and info.data["source"] is not None:
            if v is None:
                raise ValueError("skill name required when using source")
        return v

    def model_post_init(self, __context) -> None:
        """Validate that exactly one of source/path/url is provided."""
        sources = [self.source, self.path, self.url]
        non_none = [s for s in sources if s is not None]
        if len(non_none) != 1:
            raise ValueError(
                "Exactly one of source, path, or url must be provided"
            )


class SkillConfig(BaseModel):
    """Configuration for a single skill."""

    name: str = Field(description="Unique skill name")
    description: Optional[str] = Field(
        default=None, description="Human-readable description"
    )
    # Simple skill (single source)
    source: Optional[str] = Field(
        default=None,
        description="Named source reference (for simple non-composed skills)",
    )
    path: Optional[str] = Field(
        default=None, description="Local path (for simple non-composed skills)"
    )
    url: Optional[str] = Field(
        default=None, description="Direct URL (for simple non-composed skills)"
    )
    # Composed skill (multiple sources)
    compose: Optional[list[ComposeItemConfig]] = Field(
        default=None, description="List of sources to compose (for composed skills)"
    )

    def model_post_init(self, __context) -> None:
        """Validate that skill is either simple (source/path/url) OR composed."""
        simple_sources = [self.source, self.path, self.url]
        has_simple = any(s is not None for s in simple_sources)
        has_compose = self.compose is not None and len(self.compose) > 0

        if has_simple and has_compose:
            raise ValueError(
                "Skill cannot have both compose list and simple source/path/url"
            )
        if not has_simple and not has_compose:
            raise ValueError(
                "Skill must have either compose list or one of source/path/url"
            )


class SkillManagerConfig(BaseModel):
    """Root configuration for skill manager."""

    version: str = Field(description="Config schema version")
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    sources: dict[str, SourceConfig] = Field(
        default_factory=dict, description="Named skill sources"
    )
    skills: list[SkillConfig] = Field(
        default_factory=list, description="Skills to install"
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format."""
        if not v.startswith("1."):
            raise ValueError(
                f"Unsupported config version: {v}. Only version 1.x is supported."
            )
        return v
