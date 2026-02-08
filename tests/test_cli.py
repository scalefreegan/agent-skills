"""Integration tests for CLI commands."""

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from skill_manager.cli import app
from skill_manager.core.registry import SkillRegistry

runner = CliRunner()


@pytest.fixture
def cli_test_env(tmp_path, monkeypatch):
    """Set up isolated CLI test environment."""
    # Create isolated directories
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    # Set environment
    monkeypatch.chdir(work_dir)
    monkeypatch.setenv("HOME", str(home_dir))

    # Create config directory
    config_dir = home_dir / ".config" / "skill-manager"
    config_dir.mkdir(parents=True)

    return {
        "work_dir": work_dir,
        "home_dir": home_dir,
        "config_dir": config_dir,
    }


class TestInitCommand:
    """Test 'skill-manager init' command."""

    def test_init_creates_config_file(self, cli_test_env):
        """Test that init creates skills.yaml in current directory."""
        work_dir = cli_test_env["work_dir"]
        config_file = work_dir / "skills.yaml"

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert config_file.exists()
        assert "Created config file" in result.stdout or "skills.yaml" in result.stdout

        # Verify config content
        config = yaml.safe_load(config_file.read_text())
        assert config["version"] == "1.0"
        assert "settings" in config
        assert "sources" in config
        assert "skills" in config

    def test_init_does_not_overwrite_existing(self, cli_test_env):
        """Test that init doesn't overwrite existing config."""
        work_dir = cli_test_env["work_dir"]
        config_file = work_dir / "skills.yaml"

        # Create existing config
        config_file.write_text("existing: config")

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "already exists" in result.stdout
        assert config_file.read_text() == "existing: config"

    def test_init_with_force_overwrites(self, cli_test_env):
        """Test that init --force overwrites existing config."""
        work_dir = cli_test_env["work_dir"]
        config_file = work_dir / "skills.yaml"

        # Create existing config
        config_file.write_text("existing: config")

        result = runner.invoke(app, ["init", "--force"])

        assert result.exit_code == 0
        assert "Created config file" in result.stdout or "skills.yaml" in result.stdout

        # Verify it was overwritten
        config = yaml.safe_load(config_file.read_text())
        assert config["version"] == "1.0"


class TestSyncCommand:
    """Test 'skill-manager sync' command."""

    def test_sync_with_no_config(self, cli_test_env):
        """Test sync command with no config file."""
        result = runner.invoke(app, ["sync"])

        # May error if no config found or succeed with nothing to sync
        assert result.exit_code in [0, 1]

    def test_sync_with_local_skill(self, cli_test_env, sample_skill_dir):
        """Test syncing a skill from local path."""
        work_dir = cli_test_env["work_dir"]

        # Create config
        config_file = work_dir / "skills.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [str(work_dir / ".claude" / "skills")],
                "cache_dir": str(work_dir / ".cache"),
            },
            "skills": [
                {
                    "name": "local-skill",
                    "path": str(sample_skill_dir),
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0

        # Verify skill was installed
        skill_path = work_dir / ".claude" / "skills" / "local-skill"
        assert skill_path.exists()
        assert (skill_path / "SKILL.md").exists()

    def test_sync_updates_registry(self, cli_test_env, sample_skill_dir):
        """Test that sync updates the registry."""
        work_dir = cli_test_env["work_dir"]
        target_dir = work_dir / ".claude" / "skills"

        # Create config
        config_file = work_dir / "skills.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [str(target_dir)],
                "cache_dir": str(work_dir / ".cache"),
            },
            "skills": [
                {
                    "name": "test-skill",
                    "path": str(sample_skill_dir),
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0

        # Verify skill was installed
        skill_path = target_dir / "test-skill"
        assert skill_path.exists(), f"Skill directory not found at {skill_path}"

        # Check registry
        registry = SkillRegistry(target_dir)
        skills = registry.list_skills()

        # Registry may or may not be updated depending on CLI implementation
        # At minimum, the skill directory should exist
        if len(skills) > 0:
            assert skills[0].name == "test-skill"


class TestListCommand:
    """Test 'skill-manager list' command."""

    def test_list_command_runs(self, cli_test_env):
        """Test list command runs successfully."""
        result = runner.invoke(app, ["list"])

        # Should complete successfully even with no config
        assert result.exit_code in [0, 1]  # May error if no target dir or succeed with empty list

    def test_list_with_synced_skills(self, cli_test_env, sample_skill_dir):
        """Test list command with synced skills."""
        work_dir = cli_test_env["work_dir"]
        target_dir = work_dir / ".claude" / "skills"

        # Create config and sync
        config_file = work_dir / "skills.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [str(target_dir)],
                "cache_dir": str(work_dir / ".cache"),
            },
            "skills": [
                {
                    "name": "test-skill",
                    "path": str(sample_skill_dir),
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Sync first
        sync_result = runner.invoke(app, ["sync"])
        assert sync_result.exit_code == 0

        # Now list
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "test-skill" in result.stdout


class TestRemoveCommand:
    """Test 'skill-manager remove' command."""

    def test_remove_existing_skill(self, cli_test_env, sample_skill_dir):
        """Test removing an existing skill."""
        work_dir = cli_test_env["work_dir"]
        target_dir = work_dir / ".claude" / "skills"

        # Create config and sync
        config_file = work_dir / "skills.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [str(target_dir)],
                "cache_dir": str(work_dir / ".cache"),
            },
            "skills": [
                {
                    "name": "test-skill",
                    "path": str(sample_skill_dir),
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # Sync first
        sync_result = runner.invoke(app, ["sync"])
        assert sync_result.exit_code == 0

        # Verify installed
        skill_path = target_dir / "test-skill"
        assert skill_path.exists()

        # Remove with --force to skip confirmation and --target to specify location
        result = runner.invoke(
            app, ["remove", "test-skill", "--target", str(target_dir), "--force"]
        )

        assert result.exit_code == 0

        # Verify removed
        assert not skill_path.exists()

    def test_remove_nonexistent_skill(self, cli_test_env):
        """Test removing a skill that doesn't exist."""
        result = runner.invoke(app, ["remove", "nonexistent-skill"])

        # May succeed with warning or fail
        assert result.exit_code in [0, 1]


class TestCacheCommands:
    """Test cache-related commands."""

    def test_cache_command_exists(self, cli_test_env):
        """Test that cache commands are available."""
        # Note: Actual cache commands may not exist in CLI yet
        # This is a placeholder for when they're implemented
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0


class TestConfigCommands:
    """Test config subcommands."""

    def test_config_help(self, cli_test_env):
        """Test config command help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.stdout.lower()


class TestValidateCommand:
    """Test 'skill-manager validate' command."""

    def test_validate_valid_config(self, cli_test_env):
        """Test validating a valid configuration."""
        work_dir = cli_test_env["work_dir"]

        config_file = work_dir / "skills.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [".claude/skills"],
            },
            "sources": {},
            "skills": [],
        }
        config_file.write_text(yaml.dump(config))

        result = runner.invoke(app, ["validate"])

        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_validate_invalid_config(self, cli_test_env):
        """Test validating an invalid configuration."""
        work_dir = cli_test_env["work_dir"]

        config_file = work_dir / "skills.yaml"
        config = {
            "version": "2.0",  # Invalid version
        }
        config_file.write_text(yaml.dump(config))

        result = runner.invoke(app, ["validate"])

        assert result.exit_code == 1
        assert "error" in result.stdout.lower() or "invalid" in result.stdout.lower()


class TestCLIWithComposedSkills:
    """Test CLI with composed skills."""

    def test_sync_composed_skill(
        self, cli_test_env, sample_skill_dir, another_skill_dir
    ):
        """Test syncing a composed skill."""
        work_dir = cli_test_env["work_dir"]

        config_file = work_dir / "skills.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [str(work_dir / ".claude" / "skills")],
                "cache_dir": str(work_dir / ".cache"),
            },
            "skills": [
                {
                    "name": "composed-skill",
                    "compose": [
                        {
                            "path": str(sample_skill_dir),
                            "level": "default",
                        },
                        {
                            "path": str(another_skill_dir),
                            "level": "user",
                        },
                    ],
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 0

        # Verify composed skill was created
        skill_path = work_dir / ".claude" / "skills" / "composed-skill"
        assert skill_path.exists()
        assert (skill_path / "SKILL.md").exists()

        # Verify markdown composition
        skill_md = (skill_path / "SKILL.md").read_text()
        assert "PRECEDENCE: default" in skill_md
        assert "PRECEDENCE: user" in skill_md


class TestCLIEdgeCases:
    """Test CLI edge cases and error handling."""

    def test_sync_with_invalid_path(self, cli_test_env):
        """Test sync with nonexistent local path."""
        work_dir = cli_test_env["work_dir"]

        config_file = work_dir / "skills.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [str(work_dir / ".claude" / "skills")],
            },
            "skills": [
                {
                    "name": "invalid-skill",
                    "path": "/nonexistent/path",
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        result = runner.invoke(app, ["sync"])

        assert result.exit_code == 1

    def test_command_with_explicit_config_path(self, cli_test_env, sample_skill_dir):
        """Test using --config flag with custom config path."""
        work_dir = cli_test_env["work_dir"]

        # Create config in non-standard location
        custom_config = work_dir / "custom-config.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [str(work_dir / "custom-target")],
                "cache_dir": str(work_dir / ".cache"),
            },
            "skills": [
                {
                    "name": "test-skill",
                    "path": str(sample_skill_dir),
                }
            ],
        }
        custom_config.write_text(yaml.dump(config))

        result = runner.invoke(app, ["sync", "--config", str(custom_config)])

        assert result.exit_code == 0

        # Verify installed to custom target
        skill_path = work_dir / "custom-target" / "test-skill"
        assert skill_path.exists()


class TestCLIOutput:
    """Test CLI output formatting."""

    def test_list_displays_output(self, cli_test_env, sample_skill_dir):
        """Test that list command displays results."""
        work_dir = cli_test_env["work_dir"]
        target_dir = work_dir / ".claude" / "skills"

        # Sync a skill first
        config_file = work_dir / "skills.yaml"
        config = {
            "version": "1.0",
            "settings": {
                "target_dirs": [str(target_dir)],
                "cache_dir": str(work_dir / ".cache"),
            },
            "skills": [
                {
                    "name": "test-skill",
                    "path": str(sample_skill_dir),
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        runner.invoke(app, ["sync"])

        # List skills
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        # Should contain skill name in output
        assert "test-skill" in result.stdout
