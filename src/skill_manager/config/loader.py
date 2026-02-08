"""Configuration loader with merge logic and precedence handling."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import ValidationError

from skill_manager.config.defaults import DEFAULT_CONFIG
from skill_manager.config.schema import SkillManagerConfig
from skill_manager.utils.paths import expand_path


def find_config_files() -> list[Path]:
    """Find configuration files in standard locations.

    Searches for configuration files in order of precedence (lowest to highest):
    1. Project config (./skills.yaml in current directory)
    2. User config (~/.config/skill-manager/skills.yaml)

    Returns:
        List of Path objects for existing config files, ordered from lowest
        to highest precedence (so later configs override earlier ones)
    """
    config_files = []

    # Project config (lowest precedence)
    project_config = Path.cwd() / "skills.yaml"
    if project_config.exists():
        config_files.append(project_config)

    # User config (higher precedence)
    user_config = expand_path("~/.config/skill-manager/skills.yaml")
    if user_config.exists():
        config_files.append(user_config)

    return config_files


def load_yaml_file(file_path: Path) -> dict[str, Any]:
    """Load and parse a YAML configuration file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary containing the parsed YAML content

    Raises:
        yaml.YAMLError: If the file contains invalid YAML
        FileNotFoundError: If the file doesn't exist
    """
    with open(file_path, "r") as f:
        content = yaml.safe_load(f)
        return content if content is not None else {}


def merge_configs(configs: list[dict[str, Any]]) -> dict[str, Any]:
    """Deep merge multiple configuration dictionaries.

    Merges configs from lowest to highest precedence, where later configs
    override earlier ones. For nested dictionaries, performs a recursive
    deep merge. For lists, the later config completely replaces the earlier one.

    Args:
        configs: List of configuration dictionaries in order from lowest to
                highest precedence

    Returns:
        Merged configuration dictionary
    """
    if not configs:
        return {}

    result = {}

    for config in configs:
        result = _deep_merge(result, config)

    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary (lower precedence)
        override: Override dictionary (higher precedence)

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = _deep_merge(result[key], value)
        else:
            # For non-dict values (including lists), override completely replaces
            result[key] = value

    return result


def apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Supports the following environment variables:
    - SKILL_MANAGER_CACHE_DIR: Override settings.cache_dir
    - SKILL_MANAGER_DEFAULT_BRANCH: Override settings.default_branch
    - SKILL_MANAGER_TARGET_DIRS: Override settings.target_dirs (comma-separated)

    Args:
        config: Configuration dictionary to apply overrides to

    Returns:
        Configuration dictionary with environment overrides applied
    """
    result = config.copy()

    # Ensure settings exists
    if "settings" not in result:
        result["settings"] = {}

    # Apply cache_dir override
    if cache_dir := os.getenv("SKILL_MANAGER_CACHE_DIR"):
        result["settings"]["cache_dir"] = cache_dir

    # Apply default_branch override
    if default_branch := os.getenv("SKILL_MANAGER_DEFAULT_BRANCH"):
        result["settings"]["default_branch"] = default_branch

    # Apply target_dirs override (comma-separated list)
    if target_dirs := os.getenv("SKILL_MANAGER_TARGET_DIRS"):
        result["settings"]["target_dirs"] = [
            d.strip() for d in target_dirs.split(",") if d.strip()
        ]

    return result


def load_config(config_path: Optional[Path] = None) -> SkillManagerConfig:
    """Load and merge configuration from all sources.

    Configuration precedence (lowest to highest):
    1. Built-in defaults
    2. Project config (./skills.yaml)
    3. User config (~/.config/skill-manager/skills.yaml)
    4. Environment variables
    5. Explicitly provided config_path (if given)
    6. CLI flags (handled by caller)

    Args:
        config_path: Optional explicit path to a config file. If provided,
                    this will be merged on top of all other configs with
                    highest precedence (except CLI flags).

    Returns:
        Validated SkillManagerConfig instance

    Raises:
        ValidationError: If the merged configuration is invalid
        yaml.YAMLError: If a config file contains invalid YAML
        FileNotFoundError: If config_path is provided but doesn't exist
    """
    # Start with built-in defaults
    configs_to_merge = [DEFAULT_CONFIG.copy()]

    # Add standard config files
    for config_file in find_config_files():
        try:
            file_config = load_yaml_file(config_file)
            configs_to_merge.append(file_config)
        except Exception as e:
            # Re-raise with context about which file failed
            raise type(e)(f"Error loading {config_file}: {e}") from e

    # Add explicit config path if provided (highest precedence)
    if config_path is not None:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        explicit_config = load_yaml_file(config_path)
        configs_to_merge.append(explicit_config)

    # Merge all configs
    merged_config = merge_configs(configs_to_merge)

    # Apply environment variable overrides
    merged_config = apply_env_overrides(merged_config)

    # Validate and return as Pydantic model
    try:
        return SkillManagerConfig(**merged_config)
    except ValidationError as e:
        # Provide helpful error message
        raise ValidationError.from_exception_data(
            title="Configuration validation failed",
            line_errors=e.errors(),
        ) from e
