"""Integration tests for the skill assembler with realistic scenarios."""

import tempfile
from pathlib import Path

import pytest

from skill_manager.compose.assembler import assemble_all_skills
from skill_manager.config.schema import (
    ComposeItemConfig,
    PrecedenceLevel,
    SkillConfig,
    SkillManagerConfig,
    SettingsConfig,
    SourceConfig,
    SourceType,
)


@pytest.fixture
def skill_library(tmp_path):
    """Create a mock skill library with multiple skills."""
    library = tmp_path / "skill-library"
    library.mkdir()

    # Create base SQL skill
    sql_base = library / "sql-base"
    sql_base.mkdir()
    (sql_base / "SKILL.md").write_text(
        """---
name: sql-base
description: Basic SQL query assistance
version: 1.0.0
---

# SQL Base Skill

Help with basic SQL queries.

## Capabilities
- SELECT statements
- WHERE clauses
- JOIN operations
"""
    )
    (sql_base / "examples.sql").write_text(
        """-- Basic SELECT
SELECT * FROM users;

-- JOIN example
SELECT u.name, o.total
FROM users u
JOIN orders o ON u.id = o.user_id;
"""
    )

    # Create advanced SQL skill
    sql_advanced = library / "sql-advanced"
    sql_advanced.mkdir()
    (sql_advanced / "SKILL.md").write_text(
        """---
name: sql-advanced
description: Advanced SQL techniques
version: 1.0.0
---

# SQL Advanced Skill

Advanced SQL optimization and techniques.

## Advanced Capabilities
- Query optimization
- Index usage
- Complex subqueries
- Window functions
"""
    )
    (sql_advanced / "optimization.sql").write_text(
        """-- Use indexes
CREATE INDEX idx_user_email ON users(email);

-- Window function example
SELECT
    name,
    salary,
    AVG(salary) OVER (PARTITION BY department) as dept_avg
FROM employees;
"""
    )

    # Create company-specific SQL customization
    sql_company = library / "sql-company"
    sql_company.mkdir()
    (sql_company / "SKILL.md").write_text(
        """---
name: sql-company
description: Company-specific SQL guidelines
version: 1.0.0
---

# Company SQL Guidelines

Always follow our company standards:

## Company Rules
- Always use snake_case for table names
- Always add created_at and updated_at columns
- Always use UTC for timestamps
"""
    )
    (sql_company / "schema_template.sql").write_text(
        """-- Company standard table template
CREATE TABLE example_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
    )

    return library


@pytest.mark.anyio
async def test_realistic_composition_workflow(skill_library, tmp_path):
    """Test a realistic skill composition workflow with base + advanced + company override."""
    target_dir = tmp_path / "skills"
    cache_dir = tmp_path / "cache"

    # Create a configuration that composes a comprehensive SQL skill
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(target_dir)],
            cache_dir=str(cache_dir),
        ),
        sources={},
        skills=[
            SkillConfig(
                name="sql-expert",
                description="Comprehensive SQL expert with company standards",
                compose=[
                    # Base SQL knowledge (default precedence)
                    ComposeItemConfig(
                        path=str(skill_library / "sql-base"),
                        level=PrecedenceLevel.DEFAULT,
                    ),
                    # Advanced SQL features (default precedence)
                    ComposeItemConfig(
                        path=str(skill_library / "sql-advanced"),
                        level=PrecedenceLevel.DEFAULT,
                    ),
                    # Company-specific overrides (user precedence)
                    ComposeItemConfig(
                        path=str(skill_library / "sql-company"),
                        level=PrecedenceLevel.USER,
                    ),
                ],
            )
        ],
    )

    # Assemble all skills
    skills = await assemble_all_skills(config, target_dir)

    # Verify the composed skill
    assert len(skills) == 1
    skill = skills[0]
    assert skill.name == "sql-expert"
    assert skill.description == "Comprehensive SQL expert with company standards"
    assert len(skill.composed_from) == 3

    # Verify the SKILL.md was composed correctly
    skill_md = (skill.path / "SKILL.md").read_text()

    # Check precedence markers are present
    assert "PRECEDENCE: default" in skill_md
    assert "PRECEDENCE: user" in skill_md

    # Check content from all sources is present
    assert "SQL Base Skill" in skill_md
    assert "SQL Advanced Skill" in skill_md
    assert "Company SQL Guidelines" in skill_md

    # Verify all SQL files are present
    assert (skill.path / "examples.sql").exists()
    assert (skill.path / "optimization.sql").exists()
    assert (skill.path / "schema_template.sql").exists()

    # Check SQL file contents
    examples = (skill.path / "examples.sql").read_text()
    assert "SELECT * FROM users" in examples

    optimization = (skill.path / "optimization.sql").read_text()
    assert "CREATE INDEX" in optimization
    assert "Window function" in optimization

    schema = (skill.path / "schema_template.sql").read_text()
    assert "created_at" in schema
    assert "updated_at" in schema


@pytest.mark.anyio
async def test_multiple_independent_skills(skill_library, tmp_path):
    """Test assembling multiple independent skills."""
    target_dir = tmp_path / "skills"
    cache_dir = tmp_path / "cache"

    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(target_dir)],
            cache_dir=str(cache_dir),
        ),
        sources={},
        skills=[
            # Simple skills that are just copied
            SkillConfig(
                name="sql-basic",
                path=str(skill_library / "sql-base"),
            ),
            SkillConfig(
                name="sql-pro",
                path=str(skill_library / "sql-advanced"),
            ),
            # A composed skill
            SkillConfig(
                name="sql-custom",
                compose=[
                    ComposeItemConfig(
                        path=str(skill_library / "sql-base"),
                        level=PrecedenceLevel.DEFAULT,
                    ),
                    ComposeItemConfig(
                        path=str(skill_library / "sql-company"),
                        level=PrecedenceLevel.USER,
                    ),
                ],
            ),
        ],
    )

    # Assemble all skills
    skills = await assemble_all_skills(config, target_dir)

    # Verify all three skills were installed
    assert len(skills) == 3

    # Verify simple skills
    assert skills[0].name == "sql-basic"
    assert skills[0].composed_from == []
    assert (skills[0].path / "SKILL.md").exists()

    assert skills[1].name == "sql-pro"
    assert skills[1].composed_from == []
    assert (skills[1].path / "SKILL.md").exists()

    # Verify composed skill
    assert skills[2].name == "sql-custom"
    assert len(skills[2].composed_from) == 2
    assert (skills[2].path / "SKILL.md").exists()

    # Check that composed skill has content from both sources
    composed_md = (skills[2].path / "SKILL.md").read_text()
    assert "SQL Base Skill" in composed_md
    assert "Company SQL Guidelines" in composed_md


@pytest.mark.anyio
async def test_reassemble_updates_existing_skill(skill_library, tmp_path):
    """Test that reassembling updates an existing skill."""
    target_dir = tmp_path / "skills"
    cache_dir = tmp_path / "cache"

    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[str(target_dir)],
            cache_dir=str(cache_dir),
        ),
        sources={},
        skills=[
            SkillConfig(
                name="my-skill",
                path=str(skill_library / "sql-base"),
            )
        ],
    )

    # Assemble first time
    skills = await assemble_all_skills(config, target_dir)
    first_install_time = skills[0].installed_at

    # Create a marker file to verify it gets removed
    marker_file = skills[0].path / "marker.txt"
    marker_file.write_text("this should be removed")

    # Assemble again (simulating an update)
    skills = await assemble_all_skills(config, target_dir)
    second_install_time = skills[0].installed_at

    # Verify the skill was updated
    assert second_install_time != first_install_time

    # Verify marker file is gone (skill was replaced)
    assert not marker_file.exists()

    # Verify the skill still has the correct files
    assert (skills[0].path / "SKILL.md").exists()
    assert (skills[0].path / "examples.sql").exists()
