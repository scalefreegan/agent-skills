"""CLI application entry point."""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from skill_manager.compose.assembler import assemble_all_skills
from skill_manager.config.loader import load_config, find_config_files
from skill_manager.config.schema import SkillManagerConfig
from skill_manager.core.registry import SkillRegistry
from skill_manager.utils.output import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from skill_manager.utils.paths import ensure_dir, expand_path

app = typer.Typer(
    name="skill-manager",
    help="CLI tool for assembling composite skills from multiple sources",
    no_args_is_help=True,
)

# Config subcommand group
config_app = typer.Typer(
    name="config",
    help="Manage tracked configuration files",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


# Constants
TRACKED_CONFIGS_FILE = expand_path("~/.config/skill-manager/tracked-configs.yaml")


# Template for init command
TEMPLATE_CONFIG = """version: "1.0"

settings:
  target_dirs:
    - ".claude/skills"
  cache_dir: "~/.cache/skill-manager"
  default_branch: "main"

sources:
  anthropic:
    type: github
    repo: "anthropics/claude-code"
    path: "skills"

skills: []
  # Example: Simple skill from named source
  # - name: pdf
  #   source: anthropic

  # Example: Composable skill
  # - name: code-review
  #   description: "Custom code review with company standards"
  #   compose:
  #     - source: anthropic
  #       skill: code-review
  #       level: default
  #     - path: "./local-skills/code-review-overrides"
  #       level: user
"""


def get_config_path(config: Optional[Path]) -> Optional[Path]:
    """Resolve config path according to precedence order.

    1. --config <path> flag (explicit)
    2. ./skills.yaml (project config)
    3. ~/.config/skill-manager/skills.yaml (user config)

    Args:
        config: Config path from --config flag

    Returns:
        Resolved config path or None if no config exists
    """
    if config:
        return config

    # Check for project config
    project_config = Path.cwd() / "skills.yaml"
    if project_config.exists():
        return project_config

    # Check for user config
    user_config = expand_path("~/.config/skill-manager/skills.yaml")
    if user_config.exists():
        return user_config

    return None


def load_tracked_configs() -> list[str]:
    """Load the list of tracked config files.

    Returns:
        List of config file paths
    """
    if not TRACKED_CONFIGS_FILE.exists():
        return []

    try:
        with open(TRACKED_CONFIGS_FILE) as f:
            data = yaml.safe_load(f)
            if data and "configs" in data:
                return data["configs"]
    except Exception:
        pass

    return []


def save_tracked_configs(configs: list[str]) -> None:
    """Save the list of tracked config files.

    Args:
        configs: List of config file paths to save
    """
    ensure_dir(TRACKED_CONFIGS_FILE.parent)

    with open(TRACKED_CONFIGS_FILE, "w") as f:
        yaml.dump({"configs": configs}, f)


@app.command()
def sync(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (overrides default search)",
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        "-t",
        help="Override target directory",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without making changes",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force refresh, bypass cache",
    ),
):
    """Assemble all skills from configuration.

    Fetches and composes skills according to the configuration file,
    installing them to the target directory.
    """
    try:
        # Resolve config path
        config_path = get_config_path(config)
        if not config_path:
            print_error("No configuration file found")
            print_info("Run 'skill-manager init' to create a config file")
            raise typer.Exit(1)

        print_info(f"Using config: {config_path}")

        # Load config
        try:
            cfg = load_config(config_path)
        except ValidationError as e:
            print_error("Configuration validation failed:")
            console.print(e)
            raise typer.Exit(1)
        except Exception as e:
            print_error(f"Failed to load config: {e}")
            raise typer.Exit(1)

        # Determine target directory
        if target:
            target_dirs = [target]
        else:
            target_dirs = cfg.settings.target_dirs

        if dry_run:
            print_warning("DRY RUN MODE - No changes will be made")
            console.print()

        # Get GitHub token
        github_token = os.getenv("GITHUB_TOKEN")

        # Assemble all skills for each target directory
        for target_dir_str in target_dirs:
            target_dir = expand_path(target_dir_str)
            print_info(f"Target directory: {target_dir}")

            if dry_run:
                print_info(f"Would install {len(cfg.skills)} skill(s) to {target_dir}")
                for skill_config in cfg.skills:
                    console.print(f"  • {skill_config.name}")
                console.print()
                continue

            # Run assembly
            try:
                skills = asyncio.run(
                    assemble_all_skills(
                        cfg,
                        target_dir,
                        force_refresh=force,
                        github_token=github_token,
                    )
                )

                # Update registry
                registry = SkillRegistry(target_dir)
                registry.load()

                for skill in skills:
                    registry.add_skill(skill)

                registry.save()

                console.print()
                print_success(f"Updated registry: {registry.manifest_path}")

            except Exception as e:
                print_error(f"Failed to sync skills: {e}")
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


@app.command()
def sync_all(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without making changes",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force refresh, bypass cache",
    ),
):
    """Sync all tracked/registered configs.

    Useful for multi-project setups where you've registered multiple
    configuration files.
    """
    tracked = load_tracked_configs()

    if not tracked:
        print_warning("No tracked configs found")
        print_info("Use 'skill-manager config add <path>' to track a config")
        return

    print_info(f"Syncing {len(tracked)} tracked config(s)")
    console.print()

    errors = []

    for config_path_str in tracked:
        config_path = Path(config_path_str)

        if not config_path.exists():
            print_warning(f"Config not found, skipping: {config_path}")
            continue

        console.print(f"[bold]Config:[/bold] {config_path}")
        console.print()

        # Call sync directly
        try:
            sync(config=config_path, target=None, dry_run=dry_run, force=force)
        except typer.Exit as e:
            if e.exit_code != 0:
                errors.append((config_path, f"Exit code {e.exit_code}"))
        except Exception as e:
            errors.append((config_path, str(e)))

        console.print()
        console.print("-" * 60)
        console.print()

    # Report any errors
    if errors:
        console.print()
        print_error(f"Failed to sync {len(errors)} config(s):")
        for config_path, error in errors:
            console.print(f"  • {config_path}: {error}")
        raise typer.Exit(1)


@app.command()
def list(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (overrides default search)",
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        "-t",
        help="Target directory to list skills from",
    ),
):
    """List configured/installed skills.

    Shows skills that are currently installed in the target directory.
    """
    try:
        # Resolve config path
        config_path = get_config_path(config)
        if not config_path:
            print_error("No configuration file found")
            print_info("Run 'skill-manager init' to create a config file")
            raise typer.Exit(1)

        # Load config
        try:
            cfg = load_config(config_path)
        except Exception as e:
            print_error(f"Failed to load config: {e}")
            raise typer.Exit(1)

        # Determine target directory
        if target:
            target_dirs = [target]
        else:
            target_dirs = cfg.settings.target_dirs

        for target_dir_str in target_dirs:
            target_dir = expand_path(target_dir_str)

            console.print(f"[bold]Target:[/bold] {target_dir}")
            console.print()

            # Load registry
            registry = SkillRegistry(target_dir)
            registry.load()

            skills = registry.list_skills()

            if not skills:
                print_info("No skills installed")
                console.print()
                continue

            # Create table
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Name", style="green")
            table.add_column("Description")
            table.add_column("Installed At")

            for skill in skills:
                name = skill.get("name", "")
                desc = skill.get("description", "")
                installed = skill.get("installed_at", "")

                # Format timestamp
                if installed:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(installed)
                        installed = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass

                table.add_row(name, desc, installed)

            console.print(table)
            console.print()

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


@app.command()
def remove(
    skill: str = typer.Argument(..., help="Name of skill to remove"),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file",
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        "-t",
        help="Target directory",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip confirmation prompt",
    ),
):
    """Remove an installed skill.

    Removes a skill from the target directory and updates the registry.
    """
    try:
        # Resolve config path
        config_path = get_config_path(config)
        if not config_path:
            print_error("No configuration file found")
            raise typer.Exit(1)

        # Load config
        try:
            cfg = load_config(config_path)
        except Exception as e:
            print_error(f"Failed to load config: {e}")
            raise typer.Exit(1)

        # Determine target directory
        if target:
            target_dirs = [target]
        else:
            target_dirs = cfg.settings.target_dirs

        for target_dir_str in target_dirs:
            target_dir = expand_path(target_dir_str)

            # Load registry
            registry = SkillRegistry(target_dir)
            registry.load()

            # Check if skill exists
            if not registry.has_skill(skill):
                print_warning(f"Skill '{skill}' not found in {target_dir}")
                continue

            skill_path = registry.get_skill_path(skill)

            # Confirm deletion
            if not force:
                confirm = typer.confirm(
                    f"Remove skill '{skill}' from {target_dir}?",
                    default=False,
                )
                if not confirm:
                    print_info("Cancelled")
                    return

            # Remove skill directory
            if skill_path and skill_path.exists():
                shutil.rmtree(skill_path)
                print_success(f"Removed skill directory: {skill_path}")

            # Update registry
            registry.remove_skill(skill)
            registry.save()

            print_success(f"Removed skill '{skill}' from registry")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


@app.command()
def init(
    path: Optional[Path] = typer.Argument(
        None,
        help="Path where config should be created (default: ./skills.yaml)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing config file",
    ),
):
    """Create a skills.yaml template.

    Initializes a new configuration file with example skills and sources.
    """
    try:
        # Default to current directory
        if path is None:
            path = Path.cwd() / "skills.yaml"

        # Check if file exists
        if path.exists() and not force:
            print_error(f"Config file already exists: {path}")
            print_info("Use --force to overwrite")
            raise typer.Exit(1)

        # Write template
        with open(path, "w") as f:
            f.write(TEMPLATE_CONFIG)

        print_success(f"Created config file: {path}")
        print_info("Edit the file to configure your skills")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to create config: {e}")
        raise typer.Exit(1)


@app.command()
def validate(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file",
    ),
):
    """Validate configuration and skill structure.

    Checks that the configuration file is valid and all referenced
    skills can be resolved.
    """
    try:
        # Resolve config path
        config_path = get_config_path(config)
        if not config_path:
            print_error("No configuration file found")
            print_info("Run 'skill-manager init' to create a config file")
            raise typer.Exit(1)

        print_info(f"Validating config: {config_path}")

        # Load and validate config
        try:
            cfg = load_config(config_path)
            print_success("Configuration is valid")

            # Print summary
            console.print()
            console.print(f"[bold]Sources:[/bold] {len(cfg.sources)}")
            for name in cfg.sources:
                console.print(f"  • {name}")

            console.print()
            console.print(f"[bold]Skills:[/bold] {len(cfg.skills)}")
            for skill in cfg.skills:
                console.print(f"  • {skill.name}")

            console.print()
            console.print(f"[bold]Target directories:[/bold]")
            for target in cfg.settings.target_dirs:
                console.print(f"  • {target}")

        except ValidationError as e:
            print_error("Configuration validation failed:")
            console.print(e)
            raise typer.Exit(1)
        except Exception as e:
            print_error(f"Failed to load config: {e}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


@config_app.command("add")
def config_add(
    path: Path = typer.Argument(..., help="Path to config file to track"),
):
    """Register/track a config file.

    Adds a configuration file to the list of tracked configs,
    allowing it to be synced with 'sync-all'.
    """
    try:
        # Expand path
        config_path = path.resolve()

        if not config_path.exists():
            print_error(f"Config file not found: {config_path}")
            raise typer.Exit(1)

        # Load tracked configs
        tracked = load_tracked_configs()

        # Check if already tracked
        config_str = str(config_path)
        if config_str in tracked:
            print_warning(f"Config already tracked: {config_path}")
            return

        # Add to tracked
        tracked.append(config_str)
        save_tracked_configs(tracked)

        print_success(f"Added config to tracked list: {config_path}")
        print_info(f"Total tracked configs: {len(tracked)}")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to add config: {e}")
        raise typer.Exit(1)


@config_app.command("list")
def config_list():
    """List all tracked config files.

    Shows all configuration files that will be synced by 'sync-all'.
    """
    try:
        tracked = load_tracked_configs()

        if not tracked:
            print_info("No tracked configs")
            print_info("Use 'skill-manager config add <path>' to track a config")
            return

        console.print(f"[bold]Tracked configs:[/bold] ({len(tracked)})")
        console.print()

        for config_path in tracked:
            path = Path(config_path)
            exists = path.exists()
            status = "[green]✓[/green]" if exists else "[red]✗ (not found)[/red]"
            console.print(f"{status} {config_path}")

    except Exception as e:
        print_error(f"Failed to list configs: {e}")
        raise typer.Exit(1)


@config_app.command("remove")
def config_remove(
    path: Path = typer.Argument(..., help="Path to config file to untrack"),
):
    """Untrack a config file.

    Removes a configuration file from the tracked list.
    """
    try:
        # Expand path
        config_path = path.resolve()

        # Load tracked configs
        tracked = load_tracked_configs()

        # Remove from tracked
        config_str = str(config_path)
        if config_str not in tracked:
            print_warning(f"Config not tracked: {config_path}")
            return

        tracked.remove(config_str)
        save_tracked_configs(tracked)

        print_success(f"Removed config from tracked list: {config_path}")
        print_info(f"Total tracked configs: {len(tracked)}")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to remove config: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
