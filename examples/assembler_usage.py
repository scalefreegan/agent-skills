#!/usr/bin/env python3
"""Example demonstrating the skill assembler usage."""

import asyncio
from pathlib import Path

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


async def example_simple_skill():
    """Example: Install a simple skill from a local path."""
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[".claude/skills"],
            cache_dir="~/.cache/skill-manager",
        ),
        skills=[
            SkillConfig(
                name="my-skill",
                path="./path/to/skill",  # Local path to skill
            )
        ],
    )

    target_dir = Path(".claude/skills")
    skills = await assemble_all_skills(config, target_dir)
    print(f"Installed {len(skills)} skill(s)")


async def example_composed_skill():
    """Example: Compose a skill from multiple sources."""
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[".claude/skills"],
            cache_dir="~/.cache/skill-manager",
        ),
        skills=[
            SkillConfig(
                name="sql-expert",
                description="SQL expert with company standards",
                compose=[
                    # Base SQL knowledge
                    ComposeItemConfig(
                        path="./skills/sql-base",
                        level=PrecedenceLevel.DEFAULT,
                    ),
                    # Advanced features
                    ComposeItemConfig(
                        path="./skills/sql-advanced",
                        level=PrecedenceLevel.DEFAULT,
                    ),
                    # Company-specific rules (overrides defaults)
                    ComposeItemConfig(
                        path="./skills/sql-company",
                        level=PrecedenceLevel.USER,
                    ),
                ],
            )
        ],
    )

    target_dir = Path(".claude/skills")
    skills = await assemble_all_skills(config, target_dir)
    print(f"Composed skill: {skills[0].name}")
    print(f"  From sources: {', '.join(skills[0].composed_from)}")


async def example_github_source():
    """Example: Install skills from GitHub (requires configuration)."""
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[".claude/skills"],
            cache_dir="~/.cache/skill-manager",
            default_branch="main",
        ),
        sources={
            "official": SourceConfig(
                type=SourceType.GITHUB,
                repo="owner/skill-repo",
                path="skills",
                branch="main",
            ),
        },
        skills=[
            SkillConfig(
                name="python-expert",
                source="official",  # Reference to named source
                # This will fetch from: owner/skill-repo/skills/python-expert
            )
        ],
    )

    target_dir = Path(".claude/skills")
    github_token = None  # Or get from environment: os.getenv("GITHUB_TOKEN")

    skills = await assemble_all_skills(
        config, target_dir, github_token=github_token
    )
    print(f"Installed from GitHub: {skills[0].name}")


async def example_force_refresh():
    """Example: Force refresh to bypass cache."""
    config = SkillManagerConfig(
        version="1.0",
        settings=SettingsConfig(
            target_dirs=[".claude/skills"],
            cache_dir="~/.cache/skill-manager",
        ),
        skills=[
            SkillConfig(
                name="my-skill",
                path="./path/to/skill",
            )
        ],
    )

    target_dir = Path(".claude/skills")

    # Force refresh bypasses cache and fetches fresh
    skills = await assemble_all_skills(
        config, target_dir, force_refresh=True
    )
    print(f"Force refreshed {len(skills)} skill(s)")


if __name__ == "__main__":
    print("Skill Assembler Usage Examples")
    print("=" * 50)
    print()

    print("1. Simple skill installation")
    print("   (uncomment to run)")
    # asyncio.run(example_simple_skill())
    print()

    print("2. Composed skill from multiple sources")
    print("   (uncomment to run)")
    # asyncio.run(example_composed_skill())
    print()

    print("3. GitHub source installation")
    print("   (uncomment to run)")
    # asyncio.run(example_github_source())
    print()

    print("4. Force refresh")
    print("   (uncomment to run)")
    # asyncio.run(example_force_refresh())
    print()

    print("See the source code for implementation details.")
