"""Configuration loading and management."""

from skill_manager.config.loader import (
    find_config_files,
    load_config,
    merge_configs,
)
from skill_manager.config.schema import (
    ComposeItemConfig,
    PrecedenceLevel,
    SettingsConfig,
    SkillConfig,
    SkillManagerConfig,
    SourceConfig,
    SourceType,
)

__all__ = [
    # Loader functions
    "find_config_files",
    "load_config",
    "merge_configs",
    # Schema classes
    "ComposeItemConfig",
    "PrecedenceLevel",
    "SettingsConfig",
    "SkillConfig",
    "SkillManagerConfig",
    "SourceConfig",
    "SourceType",
]
