"""Tests for the skill registry."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from skill_manager.core.registry import SkillRegistry
from skill_manager.core.skill import Skill


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_dir):
    """Create a registry instance for testing."""
    return SkillRegistry(temp_dir)


class TestSkillRegistry:
    """Test suite for SkillRegistry."""

    def test_init(self, temp_dir):
        """Test registry initialization."""
        registry = SkillRegistry(temp_dir)
        assert registry.target_dir == temp_dir
        assert registry.manifest_path == temp_dir / ".skill-manager-manifest.json"

    def test_load_empty_manifest(self, registry):
        """Test loading when manifest doesn't exist."""
        manifest = registry.load()
        assert manifest["version"] == "1.0"
        assert manifest["skills"] == {}

    def test_save_and_load(self, registry, temp_dir):
        """Test saving and loading manifest."""
        # Add some data
        registry._manifest_data["skills"]["test-skill"] = {
            "name": "test-skill",
            "path": "/path/to/skill",
            "description": "A test skill",
            "composed_from": ["source1"],
            "installed_at": "2024-01-01T00:00:00Z"
        }

        # Save
        registry.save()

        # Verify file exists
        assert registry.manifest_path.exists()

        # Load in new registry instance
        new_registry = SkillRegistry(temp_dir)
        manifest = new_registry.load()

        assert "test-skill" in manifest["skills"]
        assert manifest["skills"]["test-skill"]["name"] == "test-skill"

    def test_save_creates_directory(self, temp_dir):
        """Test that save creates the target directory if it doesn't exist."""
        non_existent_dir = temp_dir / "subdir" / "nested"
        registry = SkillRegistry(non_existent_dir)

        registry.save()

        assert non_existent_dir.exists()
        assert registry.manifest_path.exists()

    def test_add_skill(self, registry):
        """Test adding a skill to the registry."""
        skill = Skill(
            name="test-skill",
            path=Path("/path/to/skill"),
            description="A test skill",
            composed_from=["source1", "source2"]
        )

        registry.load()
        registry.add_skill(skill)

        skill_data = registry.get_skill("test-skill")
        assert skill_data is not None
        assert skill_data["name"] == "test-skill"
        assert skill_data["path"] == "/path/to/skill"
        assert skill_data["description"] == "A test skill"
        assert skill_data["composed_from"] == ["source1", "source2"]
        assert "installed_at" in skill_data

    def test_add_skill_with_timestamp(self, registry):
        """Test that add_skill sets installed_at timestamp."""
        skill = Skill(
            name="test-skill",
            path=Path("/path/to/skill"),
        )

        registry.load()
        registry.add_skill(skill)

        skill_data = registry.get_skill("test-skill")
        assert skill_data["installed_at"] is not None

        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(skill_data["installed_at"])

    def test_add_skill_preserves_timestamp(self, registry):
        """Test that add_skill preserves existing installed_at timestamp."""
        timestamp = "2024-01-01T00:00:00Z"
        skill = Skill(
            name="test-skill",
            path=Path("/path/to/skill"),
            installed_at=timestamp
        )

        registry.load()
        registry.add_skill(skill)

        skill_data = registry.get_skill("test-skill")
        assert skill_data["installed_at"] == timestamp

    def test_remove_skill(self, registry):
        """Test removing a skill from the registry."""
        skill = Skill(
            name="test-skill",
            path=Path("/path/to/skill"),
        )

        registry.load()
        registry.add_skill(skill)

        assert registry.get_skill("test-skill") is not None

        registry.remove_skill("test-skill")

        assert registry.get_skill("test-skill") is None

    def test_remove_nonexistent_skill(self, registry):
        """Test removing a skill that doesn't exist (should not raise error)."""
        registry.load()
        registry.remove_skill("nonexistent-skill")  # Should not raise

    def test_get_skill(self, registry):
        """Test getting a skill's metadata."""
        skill = Skill(
            name="test-skill",
            path=Path("/path/to/skill"),
            description="Test description"
        )

        registry.load()
        registry.add_skill(skill)

        skill_data = registry.get_skill("test-skill")
        assert skill_data["name"] == "test-skill"
        assert skill_data["description"] == "Test description"

    def test_get_nonexistent_skill(self, registry):
        """Test getting a skill that doesn't exist."""
        registry.load()
        skill_data = registry.get_skill("nonexistent-skill")
        assert skill_data is None

    def test_list_skills_empty(self, registry):
        """Test listing skills when registry is empty."""
        registry.load()
        skills = registry.list_skills()
        assert skills == []

    def test_list_skills(self, registry):
        """Test listing all installed skills."""
        skill1 = Skill(name="skill1", path=Path("/path/to/skill1"))
        skill2 = Skill(name="skill2", path=Path("/path/to/skill2"))

        registry.load()
        registry.add_skill(skill1)
        registry.add_skill(skill2)

        skills = registry.list_skills()
        assert len(skills) == 2

        skill_names = [s["name"] for s in skills]
        assert "skill1" in skill_names
        assert "skill2" in skill_names

    def test_detect_conflicts_none(self, registry):
        """Test conflict detection when no conflicts exist."""
        registry.load()
        conflicts = registry.detect_conflicts("new-skill")
        assert conflicts == []

    def test_detect_conflicts_exists(self, registry):
        """Test conflict detection when skill already exists."""
        skill = Skill(name="existing-skill", path=Path("/path/to/skill"))

        registry.load()
        registry.add_skill(skill)

        conflicts = registry.detect_conflicts("existing-skill")
        assert len(conflicts) == 1
        assert "existing-skill" in conflicts

    def test_has_skill(self, registry):
        """Test checking if a skill is installed."""
        skill = Skill(name="test-skill", path=Path("/path/to/skill"))

        registry.load()

        assert not registry.has_skill("test-skill")

        registry.add_skill(skill)

        assert registry.has_skill("test-skill")

    def test_get_skill_path(self, registry):
        """Test getting the path to an installed skill."""
        skill = Skill(name="test-skill", path=Path("/path/to/skill"))

        registry.load()
        registry.add_skill(skill)

        path = registry.get_skill_path("test-skill")
        assert path == Path("/path/to/skill")

    def test_get_skill_path_nonexistent(self, registry):
        """Test getting path for nonexistent skill."""
        registry.load()
        path = registry.get_skill_path("nonexistent")
        assert path is None

    def test_persistence(self, registry, temp_dir):
        """Test that changes persist across registry instances."""
        skill = Skill(
            name="persistent-skill",
            path=Path("/path/to/skill"),
            description="This should persist"
        )

        # Add skill and save
        registry.load()
        registry.add_skill(skill)
        registry.save()

        # Create new registry instance and verify data persists
        new_registry = SkillRegistry(temp_dir)
        new_registry.load()

        skill_data = new_registry.get_skill("persistent-skill")
        assert skill_data is not None
        assert skill_data["name"] == "persistent-skill"
        assert skill_data["description"] == "This should persist"

    def test_update_skill(self, registry):
        """Test updating an existing skill."""
        skill1 = Skill(
            name="test-skill",
            path=Path("/path/to/skill"),
            description="Original description"
        )

        registry.load()
        registry.add_skill(skill1)

        # Update the skill
        skill2 = Skill(
            name="test-skill",
            path=Path("/new/path/to/skill"),
            description="Updated description",
            composed_from=["new-source"]
        )
        registry.add_skill(skill2)

        skill_data = registry.get_skill("test-skill")
        assert skill_data["path"] == "/new/path/to/skill"
        assert skill_data["description"] == "Updated description"
        assert skill_data["composed_from"] == ["new-source"]

    def test_manifest_json_format(self, registry, temp_dir):
        """Test that manifest is saved in correct JSON format."""
        skill = Skill(
            name="test-skill",
            path=Path("/path/to/skill"),
            description="Test skill",
            composed_from=["source1", "source2"],
            installed_at="2024-01-01T00:00:00Z"
        )

        registry.load()
        registry.add_skill(skill)
        registry.save()

        # Read raw JSON
        with open(registry.manifest_path, 'r') as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert "skills" in data
        assert "test-skill" in data["skills"]

        skill_data = data["skills"]["test-skill"]
        assert skill_data["name"] == "test-skill"
        assert skill_data["path"] == "/path/to/skill"
        assert skill_data["description"] == "Test skill"
        assert skill_data["composed_from"] == ["source1", "source2"]
        assert skill_data["installed_at"] == "2024-01-01T00:00:00Z"

    def test_load_corrupted_manifest(self, registry, temp_dir):
        """Test loading a corrupted manifest file."""
        # Write corrupted JSON
        with open(registry.manifest_path, 'w') as f:
            f.write("{ invalid json }")

        # Should not raise, should return empty manifest
        manifest = registry.load()
        assert manifest["version"] == "1.0"
        assert manifest["skills"] == {}

    def test_load_manifest_without_version(self, registry, temp_dir):
        """Test loading manifest that's missing version field."""
        # Write manifest without version
        with open(registry.manifest_path, 'w') as f:
            json.dump({"skills": {}}, f)

        manifest = registry.load()
        assert manifest["version"] == "1.0"
        assert manifest["skills"] == {}

    def test_load_manifest_without_skills(self, registry, temp_dir):
        """Test loading manifest that's missing skills field."""
        # Write manifest without skills
        with open(registry.manifest_path, 'w') as f:
            json.dump({"version": "1.0"}, f)

        manifest = registry.load()
        assert manifest["version"] == "1.0"
        assert manifest["skills"] == {}
