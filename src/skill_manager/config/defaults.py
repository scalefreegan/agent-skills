"""Built-in default configuration for skill manager."""

# Default configuration that serves as the base for all other configs
DEFAULT_CONFIG = {
    "version": "1.0",
    "settings": {
        "target_dirs": [".claude/skills"],
        "cache_dir": "~/.cache/skill-manager",
        "default_branch": "main",
    },
    "sources": {},
    "skills": [],
}
