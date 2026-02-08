#!/usr/bin/env python3
"""Demo script showing markdown composition with precedence markers."""

from pathlib import Path

from skill_manager.compose.markdown import compose_markdown_files
from skill_manager.config.schema import PrecedenceLevel
from skill_manager.core.skill import SkillSource


def main():
    """Demonstrate markdown composition."""
    # Get example directory
    example_dir = Path(__file__).parent

    # Create skill sources
    default_skill = SkillSource(
        name="code-reviewer",
        path=example_dir / "default_skill",
    )

    user_skill = SkillSource(
        name="code-reviewer-custom",
        path=example_dir / "user_skill",
    )

    # Compose markdown files with precedence
    output_path = example_dir / "composed_output" / "SKILL.md"

    print("Composing markdown files...")
    print(f"  Default skill: {default_skill.path}")
    print(f"  User skill: {user_skill.path}")
    print(f"  Output: {output_path}")

    compose_markdown_files(
        [
            (default_skill, PrecedenceLevel.DEFAULT),
            (user_skill, PrecedenceLevel.USER),
        ],
        output_path,
    )

    print(f"\nComposition complete! Output written to: {output_path}")
    print("\n--- Output Preview ---")
    print(output_path.read_text()[:500] + "...")


if __name__ == "__main__":
    main()
