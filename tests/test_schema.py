"""Tests for Pydantic schema models and validation rules."""

import pytest
from pydantic import ValidationError

from skill_manager.config.schema import (
    ComposeItemConfig,
    PrecedenceLevel,
    SkillConfig,
    SkillManagerConfig,
    SourceConfig,
    SourceType,
    SettingsConfig,
)


class TestSettingsConfig:
    """Test SettingsConfig model."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = SettingsConfig()
        assert settings.target_dirs == [".claude/skills"]
        assert settings.cache_dir == "~/.cache/skill-manager"
        assert settings.default_branch == "main"

    def test_custom_values(self):
        """Test setting custom values."""
        settings = SettingsConfig(
            target_dirs=["/custom/path"],
            cache_dir="/custom/cache",
            default_branch="develop",
        )
        assert settings.target_dirs == ["/custom/path"]
        assert settings.cache_dir == "/custom/cache"
        assert settings.default_branch == "develop"

    def test_multiple_target_dirs(self):
        """Test multiple target directories."""
        settings = SettingsConfig(target_dirs=["/path1", "/path2", "/path3"])
        assert len(settings.target_dirs) == 3


class TestSourceConfig:
    """Test SourceConfig model."""

    def test_valid_github_source(self):
        """Test creating a valid GitHub source."""
        source = SourceConfig(
            type=SourceType.GITHUB,
            repo="owner/repo",
            path="skills",
            branch="main",
        )
        assert source.type == SourceType.GITHUB
        assert source.repo == "owner/repo"
        assert source.path == "skills"
        assert source.branch == "main"

    def test_invalid_repo_format_no_slash(self):
        """Test that repo without slash is invalid."""
        with pytest.raises(ValidationError, match="Repository must be in format"):
            SourceConfig(
                type=SourceType.GITHUB,
                repo="invalidrepo",
            )

    def test_invalid_repo_format_multiple_slashes(self):
        """Test that repo with multiple slashes is invalid."""
        with pytest.raises(ValidationError, match="Repository must be in format"):
            SourceConfig(
                type=SourceType.GITHUB,
                repo="owner/repo/extra",
            )

    def test_optional_path_and_branch(self):
        """Test that path and branch are optional."""
        source = SourceConfig(
            type=SourceType.GITHUB,
            repo="owner/repo",
        )
        assert source.path is None
        assert source.branch is None


class TestComposeItemConfig:
    """Test ComposeItemConfig model."""

    def test_source_with_skill(self):
        """Test compose item with named source."""
        item = ComposeItemConfig(
            source="my-source",
            skill="my-skill",
            level=PrecedenceLevel.DEFAULT,
        )
        assert item.source == "my-source"
        assert item.skill == "my-skill"
        assert item.level == PrecedenceLevel.DEFAULT

    def test_path_only(self):
        """Test compose item with local path."""
        item = ComposeItemConfig(
            path="/local/path/to/skill",
            level=PrecedenceLevel.USER,
        )
        assert item.path == "/local/path/to/skill"
        assert item.source is None
        assert item.url is None

    def test_url_only(self):
        """Test compose item with direct URL."""
        item = ComposeItemConfig(
            url="https://github.com/owner/repo/tree/main/skills/my-skill",
            level=PrecedenceLevel.DEFAULT,
        )
        assert item.url == "https://github.com/owner/repo/tree/main/skills/my-skill"
        assert item.source is None
        assert item.path is None

    def test_source_without_skill_allowed_but_useless(self):
        """Test that source without skill is technically allowed during construction.

        Note: This creates a compose item that would fail the 'exactly one of' validation
        since source alone doesn't count as a valid specification without skill.
        """
        # This creates an item but it's not useful - would fail in actual use
        item = ComposeItemConfig(
            source="my-source",
            level=PrecedenceLevel.DEFAULT,
        )
        assert item.source == "my-source"
        assert item.skill is None

    def test_multiple_sources_fails(self):
        """Test that multiple sources are not allowed."""
        with pytest.raises(ValidationError, match="Exactly one of source, path, or url"):
            ComposeItemConfig(
                source="my-source",
                skill="my-skill",
                path="/local/path",
                level=PrecedenceLevel.DEFAULT,
            )

    def test_no_source_fails(self):
        """Test that at least one source is required."""
        with pytest.raises(ValidationError, match="Exactly one of source, path, or url"):
            ComposeItemConfig(level=PrecedenceLevel.DEFAULT)

    def test_default_precedence_level(self):
        """Test default precedence level is DEFAULT."""
        item = ComposeItemConfig(path="/local/path")
        assert item.level == PrecedenceLevel.DEFAULT


class TestSkillConfig:
    """Test SkillConfig model."""

    def test_simple_skill_with_source(self):
        """Test simple skill with named source."""
        skill = SkillConfig(
            name="my-skill",
            source="my-source",
            description="A test skill",
        )
        assert skill.name == "my-skill"
        assert skill.source == "my-source"
        assert skill.description == "A test skill"
        assert skill.compose is None

    def test_simple_skill_with_path(self):
        """Test simple skill with local path."""
        skill = SkillConfig(
            name="my-skill",
            path="/local/path/to/skill",
        )
        assert skill.path == "/local/path/to/skill"
        assert skill.compose is None

    def test_simple_skill_with_url(self):
        """Test simple skill with direct URL."""
        skill = SkillConfig(
            name="my-skill",
            url="https://github.com/owner/repo/tree/main/skills/my-skill",
        )
        assert skill.url == "https://github.com/owner/repo/tree/main/skills/my-skill"
        assert skill.compose is None

    def test_composed_skill(self):
        """Test composed skill with multiple sources."""
        skill = SkillConfig(
            name="composed-skill",
            compose=[
                ComposeItemConfig(
                    source="source1",
                    skill="skill1",
                    level=PrecedenceLevel.DEFAULT,
                ),
                ComposeItemConfig(
                    path="/local/overrides",
                    level=PrecedenceLevel.USER,
                ),
            ],
        )
        assert skill.name == "composed-skill"
        assert len(skill.compose) == 2
        assert skill.source is None
        assert skill.path is None
        assert skill.url is None

    def test_skill_with_both_simple_and_compose_fails(self):
        """Test that skill cannot have both simple source and compose."""
        with pytest.raises(
            ValidationError,
            match="cannot have both compose list and simple source",
        ):
            SkillConfig(
                name="invalid-skill",
                source="my-source",
                compose=[
                    ComposeItemConfig(path="/local/path"),
                ],
            )

    def test_skill_with_neither_simple_nor_compose_fails(self):
        """Test that skill must have either simple source or compose."""
        with pytest.raises(
            ValidationError,
            match="must have either compose list or one of source/path/url",
        ):
            SkillConfig(name="invalid-skill")

    def test_empty_compose_list_fails(self):
        """Test that empty compose list is invalid."""
        with pytest.raises(
            ValidationError,
            match="must have either compose list or one of source/path/url",
        ):
            SkillConfig(
                name="invalid-skill",
                compose=[],
            )


class TestSkillManagerConfig:
    """Test SkillManagerConfig model."""

    def test_minimal_valid_config(self):
        """Test minimal valid configuration."""
        config = SkillManagerConfig(
            version="1.0",
            settings=SettingsConfig(),
            sources={},
            skills=[],
        )
        assert config.version == "1.0"
        assert isinstance(config.settings, SettingsConfig)
        assert config.sources == {}
        assert config.skills == []

    def test_config_with_sources_and_skills(self):
        """Test configuration with sources and skills."""
        config = SkillManagerConfig(
            version="1.0",
            sources={
                "test-source": SourceConfig(
                    type=SourceType.GITHUB,
                    repo="owner/repo",
                    path="skills",
                ),
            },
            skills=[
                SkillConfig(
                    name="test-skill",
                    source="test-source",
                ),
            ],
        )
        assert "test-source" in config.sources
        assert len(config.skills) == 1
        assert config.skills[0].name == "test-skill"

    def test_version_validation_invalid_major(self):
        """Test that version must start with 1."""
        with pytest.raises(ValidationError, match="Unsupported config version"):
            SkillManagerConfig(
                version="2.0",
            )

    def test_version_validation_valid_minor(self):
        """Test that minor version variations are accepted."""
        config = SkillManagerConfig(version="1.5")
        assert config.version == "1.5"

    def test_default_settings_created(self):
        """Test that default settings are created if not provided."""
        config = SkillManagerConfig(version="1.0")
        assert isinstance(config.settings, SettingsConfig)
        assert config.settings.default_branch == "main"

    def test_precedence_level_enum_values(self):
        """Test that PrecedenceLevel enum has correct values."""
        assert PrecedenceLevel.DEFAULT.value == "default"
        assert PrecedenceLevel.USER.value == "user"

    def test_source_type_enum_values(self):
        """Test that SourceType enum has correct values."""
        assert SourceType.GITHUB.value == "github"


class TestComplexSkillScenarios:
    """Test complex skill configuration scenarios."""

    def test_multi_level_composed_skill(self):
        """Test skill composed from multiple precedence levels."""
        skill = SkillConfig(
            name="complex-skill",
            description="Complex composed skill",
            compose=[
                ComposeItemConfig(
                    source="base-source",
                    skill="base-skill",
                    level=PrecedenceLevel.DEFAULT,
                ),
                ComposeItemConfig(
                    url="https://github.com/org/repo/tree/main/skills/override",
                    level=PrecedenceLevel.USER,
                ),
                ComposeItemConfig(
                    path="/local/custom",
                    level=PrecedenceLevel.USER,
                ),
            ],
        )
        assert len(skill.compose) == 3
        assert skill.compose[0].level == PrecedenceLevel.DEFAULT
        assert skill.compose[1].level == PrecedenceLevel.USER
        assert skill.compose[2].level == PrecedenceLevel.USER

    def test_config_with_multiple_skills(self):
        """Test configuration with multiple skills of different types."""
        config = SkillManagerConfig(
            version="1.0",
            sources={
                "github-source": SourceConfig(
                    type=SourceType.GITHUB,
                    repo="owner/repo",
                ),
            },
            skills=[
                SkillConfig(name="simple-skill", source="github-source"),
                SkillConfig(name="local-skill", path="/local/skill"),
                SkillConfig(
                    name="composed-skill",
                    compose=[
                        ComposeItemConfig(source="github-source", skill="base"),
                        ComposeItemConfig(path="/local/override"),
                    ],
                ),
            ],
        )
        assert len(config.skills) == 3
        assert config.skills[0].source == "github-source"
        assert config.skills[1].path == "/local/skill"
        assert config.skills[2].compose is not None
