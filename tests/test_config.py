"""Tests for configuration loading and merging logic."""

import os
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from skill_manager.config.loader import (
    apply_env_overrides,
    find_config_files,
    load_config,
    load_yaml_file,
    merge_configs,
)
from skill_manager.config.schema import SkillManagerConfig


class TestLoadYamlFile:
    """Test YAML file loading."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading a valid YAML file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "version": "1.0",
            "settings": {"cache_dir": "/custom/cache"},
        }
        config_file.write_text(yaml.dump(config_data))

        result = load_yaml_file(config_file)
        assert result["version"] == "1.0"
        assert result["settings"]["cache_dir"] == "/custom/cache"

    def test_load_empty_yaml(self, tmp_path):
        """Test loading an empty YAML file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = load_yaml_file(config_file)
        assert result == {}

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading a nonexistent file raises error."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_yaml_file(config_file)

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            load_yaml_file(config_file)


class TestMergeConfigs:
    """Test configuration merging logic."""

    def test_merge_empty_list(self):
        """Test merging empty config list."""
        result = merge_configs([])
        assert result == {}

    def test_merge_single_config(self):
        """Test merging a single config."""
        config = {"version": "1.0", "settings": {"cache_dir": "/cache"}}
        result = merge_configs([config])
        assert result == config

    def test_merge_two_configs_simple(self):
        """Test merging two configs with simple values."""
        config1 = {"version": "1.0", "key1": "value1"}
        config2 = {"version": "1.1", "key2": "value2"}

        result = merge_configs([config1, config2])
        assert result["version"] == "1.1"  # Later config wins
        assert result["key1"] == "value1"  # From first config
        assert result["key2"] == "value2"  # From second config

    def test_merge_nested_dicts(self):
        """Test deep merging of nested dictionaries."""
        config1 = {
            "settings": {
                "cache_dir": "/cache1",
                "default_branch": "main",
            }
        }
        config2 = {
            "settings": {
                "cache_dir": "/cache2",
                "target_dirs": ["/target"],
            }
        }

        result = merge_configs([config1, config2])
        assert result["settings"]["cache_dir"] == "/cache2"  # Overridden
        assert result["settings"]["default_branch"] == "main"  # Preserved
        assert result["settings"]["target_dirs"] == ["/target"]  # Added

    def test_merge_list_replacement(self):
        """Test that lists are replaced, not merged."""
        config1 = {"skills": ["skill1", "skill2"]}
        config2 = {"skills": ["skill3"]}

        result = merge_configs([config1, config2])
        assert result["skills"] == ["skill3"]  # Completely replaced

    def test_merge_multiple_configs(self):
        """Test merging multiple configs in precedence order."""
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 3, "c": 4}
        config3 = {"c": 5, "d": 6}

        result = merge_configs([config1, config2, config3])
        assert result["a"] == 1  # From first
        assert result["b"] == 3  # From second (overrides first)
        assert result["c"] == 5  # From third (overrides second)
        assert result["d"] == 6  # From third


class TestApplyEnvOverrides:
    """Test environment variable overrides."""

    def test_no_env_vars(self):
        """Test that config is unchanged when no env vars are set."""
        config = {"settings": {"cache_dir": "/cache"}}

        result = apply_env_overrides(config)
        assert result["settings"]["cache_dir"] == "/cache"

    def test_cache_dir_override(self, monkeypatch):
        """Test SKILL_MANAGER_CACHE_DIR override."""
        monkeypatch.setenv("SKILL_MANAGER_CACHE_DIR", "/env/cache")

        config = {"settings": {"cache_dir": "/original"}}
        result = apply_env_overrides(config)

        assert result["settings"]["cache_dir"] == "/env/cache"

    def test_default_branch_override(self, monkeypatch):
        """Test SKILL_MANAGER_DEFAULT_BRANCH override."""
        monkeypatch.setenv("SKILL_MANAGER_DEFAULT_BRANCH", "develop")

        config = {"settings": {"default_branch": "main"}}
        result = apply_env_overrides(config)

        assert result["settings"]["default_branch"] == "develop"

    def test_target_dirs_override(self, monkeypatch):
        """Test SKILL_MANAGER_TARGET_DIRS override."""
        monkeypatch.setenv("SKILL_MANAGER_TARGET_DIRS", "/dir1,/dir2,/dir3")

        config = {"settings": {"target_dirs": ["/original"]}}
        result = apply_env_overrides(config)

        assert result["settings"]["target_dirs"] == ["/dir1", "/dir2", "/dir3"]

    def test_target_dirs_override_strips_whitespace(self, monkeypatch):
        """Test that target_dirs override strips whitespace."""
        monkeypatch.setenv("SKILL_MANAGER_TARGET_DIRS", "/dir1 , /dir2 , /dir3")

        config = {"settings": {}}
        result = apply_env_overrides(config)

        assert result["settings"]["target_dirs"] == ["/dir1", "/dir2", "/dir3"]

    def test_multiple_env_overrides(self, monkeypatch):
        """Test multiple environment overrides at once."""
        monkeypatch.setenv("SKILL_MANAGER_CACHE_DIR", "/env/cache")
        monkeypatch.setenv("SKILL_MANAGER_DEFAULT_BRANCH", "develop")
        monkeypatch.setenv("SKILL_MANAGER_TARGET_DIRS", "/target1,/target2")

        config = {"settings": {"cache_dir": "/original"}}
        result = apply_env_overrides(config)

        assert result["settings"]["cache_dir"] == "/env/cache"
        assert result["settings"]["default_branch"] == "develop"
        assert result["settings"]["target_dirs"] == ["/target1", "/target2"]

    def test_env_creates_settings_if_missing(self, monkeypatch):
        """Test that env overrides create settings dict if missing."""
        monkeypatch.setenv("SKILL_MANAGER_CACHE_DIR", "/cache")

        config = {}
        result = apply_env_overrides(config)

        assert "settings" in result
        assert result["settings"]["cache_dir"] == "/cache"


class TestFindConfigFiles:
    """Test config file discovery."""

    def test_no_config_files(self, tmp_path, monkeypatch):
        """Test when no config files exist."""
        # Change to temp directory with no config
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))

        result = find_config_files()
        assert result == []

    def test_project_config_only(self, tmp_path, monkeypatch):
        """Test finding only project config."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        project_config = tmp_path / "skills.yaml"
        project_config.write_text("version: '1.0'")

        result = find_config_files()
        assert len(result) == 1
        assert result[0] == project_config

    def test_user_config_only(self, tmp_path, monkeypatch):
        """Test finding only user config."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        monkeypatch.chdir(work_dir)
        monkeypatch.setenv("HOME", str(tmp_path))

        user_config_dir = tmp_path / ".config" / "skill-manager"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "skills.yaml"
        user_config.write_text("version: '1.0'")

        result = find_config_files()
        assert len(result) == 1
        assert result[0] == user_config

    def test_both_configs(self, tmp_path, monkeypatch):
        """Test finding both project and user configs."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))

        # Create project config
        project_config = tmp_path / "skills.yaml"
        project_config.write_text("version: '1.0'")

        # Create user config
        user_config_dir = tmp_path / ".config" / "skill-manager"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "skills.yaml"
        user_config.write_text("version: '1.0'")

        result = find_config_files()
        assert len(result) == 2
        assert result[0] == project_config  # Lower precedence first
        assert result[1] == user_config  # Higher precedence last


class TestLoadConfig:
    """Test full config loading with merging."""

    def test_load_default_config_only(self, tmp_path, monkeypatch):
        """Test loading with only default config."""
        # Set empty environment
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        config = load_config()

        # Should have default values
        assert config.version.startswith("1.")
        assert ".claude/skills" in config.settings.target_dirs
        assert "skill-manager" in config.settings.cache_dir

    def test_load_with_project_config(self, tmp_path, monkeypatch):
        """Test loading with project config override."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        project_config = tmp_path / "skills.yaml"
        project_config.write_text(
            yaml.dump(
                {
                    "version": "1.0",
                    "settings": {"cache_dir": "/project/cache"},
                }
            )
        )

        config = load_config()
        assert config.settings.cache_dir == "/project/cache"

    def test_load_with_explicit_config(self, tmp_path, monkeypatch):
        """Test loading with explicit config path."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        explicit_config = tmp_path / "custom.yaml"
        explicit_config.write_text(
            yaml.dump(
                {
                    "version": "1.0",
                    "settings": {"default_branch": "custom"},
                }
            )
        )

        config = load_config(config_path=explicit_config)
        assert config.settings.default_branch == "custom"

    def test_load_with_env_override(self, tmp_path, monkeypatch):
        """Test that env vars override file configs."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("SKILL_MANAGER_CACHE_DIR", "/env/cache")

        project_config = tmp_path / "skills.yaml"
        project_config.write_text(
            yaml.dump(
                {
                    "version": "1.0",
                    "settings": {"cache_dir": "/project/cache"},
                }
            )
        )

        config = load_config()
        assert config.settings.cache_dir == "/env/cache"  # Env wins

    def test_load_invalid_config_raises_error(self, tmp_path, monkeypatch):
        """Test that invalid config raises validation error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        project_config = tmp_path / "skills.yaml"
        project_config.write_text(
            yaml.dump(
                {
                    "version": "2.0",  # Invalid version
                }
            )
        )

        with pytest.raises(ValidationError):
            load_config()

    def test_load_nonexistent_explicit_config(self, tmp_path):
        """Test that nonexistent explicit config raises error."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config(config_path=nonexistent)

    def test_precedence_order(self, tmp_path, monkeypatch):
        """Test full precedence order: defaults < project < user < explicit < env."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("SKILL_MANAGER_DEFAULT_BRANCH", "env-branch")

        # Create project config
        project_config = tmp_path / "skills.yaml"
        project_config.write_text(
            yaml.dump(
                {
                    "version": "1.0",
                    "settings": {
                        "cache_dir": "/project/cache",
                        "default_branch": "project-branch",
                    },
                }
            )
        )

        # Create user config
        user_config_dir = tmp_path / ".config" / "skill-manager"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "skills.yaml"
        user_config.write_text(
            yaml.dump(
                {
                    "version": "1.0",
                    "settings": {
                        "cache_dir": "/user/cache",
                    },
                }
            )
        )

        config = load_config()

        # User cache_dir overrides project
        assert config.settings.cache_dir == "/user/cache"
        # Env default_branch overrides project
        assert config.settings.default_branch == "env-branch"
        # Default target_dirs (not overridden)
        assert ".claude/skills" in config.settings.target_dirs


class TestConfigIntegration:
    """Integration tests for config loading."""

    def test_full_config_with_skills(self, tmp_path, monkeypatch):
        """Test loading a complete config with sources and skills."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        config_file = tmp_path / "skills.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "version": "1.0",
                    "settings": {
                        "target_dirs": [".claude/skills"],
                        "cache_dir": "~/.cache/skill-manager",
                    },
                    "sources": {
                        "github-source": {
                            "type": "github",
                            "repo": "owner/repo",
                            "path": "skills",
                        }
                    },
                    "skills": [
                        {
                            "name": "test-skill",
                            "source": "github-source",
                        }
                    ],
                }
            )
        )

        config = load_config()
        assert isinstance(config, SkillManagerConfig)
        assert "github-source" in config.sources
        assert len(config.skills) == 1
        assert config.skills[0].name == "test-skill"
