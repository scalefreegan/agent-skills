# Agent Instructions for Skill Manager

This document provides guidance for Claude Code agents working with the skill-manager project.

## Overview

skill-manager is a CLI tool for assembling composite skills from multiple sources. It fetches skills from GitHub repositories, local paths, and other sources, composes them using a precedence-based system (user > team > default), and installs them to target directories (typically `.claude/skills`).

Key features:
- Fetch skills from GitHub repos with caching
- Compose skills from multiple sources with precedence levels
- Track multiple project configurations
- Sync all tracked configs with a single command

## Workflow After Config Changes

**IMPORTANT**: After updating any `skills.yaml` file, always run:

```bash
uv run skill-manager sync-all
```

This syncs ALL tracked configs across your multi-project setup. This ensures:
- All projects stay in sync with the latest skill definitions
- Changes propagate to all target directories
- The skill registry is updated for each target

### When to Run sync-all

Run `uv run skill-manager sync-all` after:
- Adding or removing skills from any `skills.yaml`
- Modifying skill composition or precedence levels
- Updating source repositories or paths
- Changing settings (target directories, cache settings, etc.)
- Pulling changes that affect skill configurations

## Common Commands

### Initialize a New Config

Create a new `skills.yaml` configuration file:

```bash
# Create in current directory (./skills.yaml)
uv run skill-manager init

# Create at specific path
uv run skill-manager init /path/to/skills.yaml

# Overwrite existing config
uv run skill-manager init --force
```

### Sync Skills

Sync skills for a single config:

```bash
# Use config in current directory or ~/.config/skill-manager/skills.yaml
uv run skill-manager sync

# Use specific config
uv run skill-manager sync --config /path/to/skills.yaml

# Override target directory
uv run skill-manager sync --target /custom/target/dir

# Dry run (show what would be done)
uv run skill-manager sync --dry-run

# Force refresh (bypass cache)
uv run skill-manager sync --force
```

Sync all tracked configs:

```bash
# Sync all tracked configs
uv run skill-manager sync-all

# Dry run for all configs
uv run skill-manager sync-all --dry-run

# Force refresh for all configs
uv run skill-manager sync-all --force
```

### List Installed Skills

```bash
# List skills from default config
uv run skill-manager list

# List from specific config
uv run skill-manager list --config /path/to/skills.yaml

# List from specific target
uv run skill-manager list --target /path/to/target
```

### Remove a Skill

```bash
# Remove skill (with confirmation)
uv run skill-manager remove <skill-name>

# Remove without confirmation
uv run skill-manager remove <skill-name> --force

# Remove from specific config/target
uv run skill-manager remove <skill-name> --config /path/to/skills.yaml
```

### Validate Configuration

```bash
# Validate default config
uv run skill-manager validate

# Validate specific config
uv run skill-manager validate --config /path/to/skills.yaml
```

### Manage Tracked Configs

Track a config file for `sync-all`:

```bash
# Add config to tracked list
uv run skill-manager config add /path/to/skills.yaml

# List all tracked configs
uv run skill-manager config list

# Remove config from tracked list
uv run skill-manager config remove /path/to/skills.yaml
```

## Development Workflow

### Setting Up Development Environment

1. Clone the repository:
```bash
git clone <repo-url>
cd agent-skills
```

2. Install dependencies with uv:
```bash
# uv automatically creates a virtual environment and installs dependencies
uv sync
```

3. Run the CLI in development mode:
```bash
uv run skill-manager --help
```

### Making Changes

1. Make changes to source files in `src/skill_manager/`
2. Run tests to verify changes (see Testing section)
3. Test CLI commands manually with `uv run skill-manager <command>`
4. Update documentation as needed

### Project Structure

```
agent-skills/
├── src/skill_manager/
│   ├── cli.py              # CLI entry point with Typer commands
│   ├── config/             # Configuration schema and loader
│   ├── core/               # Core models (Skill, SkillRegistry)
│   ├── sources/            # Source fetchers (GitHub, local files)
│   ├── compose/            # Skill composition logic
│   ├── cache/              # Caching for remote sources
│   └── utils/              # Utility modules
├── tests/                  # Test suite
├── examples/               # Example usage scripts
├── skills.yaml             # Example config (if present)
└── pyproject.toml          # Project metadata and dependencies
```

### Adding New Features

When adding new features:

1. Update relevant modules in `src/skill_manager/`
2. Add tests in `tests/`
3. Update CLI commands in `src/skill_manager/cli.py` if needed
4. Update this documentation (AGENTS.md) and README.md
5. Test with `uv run` commands

## Testing

### Running Tests

Run all tests:
```bash
uv run pytest
```

Run specific test file:
```bash
uv run pytest tests/test_registry.py
```

Run tests with verbose output:
```bash
uv run pytest -v
```

Run tests with coverage:
```bash
uv run pytest --cov=skill_manager
```

### Test Files

The test suite includes:
- `test_registry.py` - SkillRegistry tests
- `test_cache_integration.py` - Cache system tests
- `test_files_composer.py` - File composition tests
- `test_markdown_composer.py` - Markdown composition tests
- `test_assembler.py` - Skill assembly orchestration tests

### Writing Tests

When writing tests:
1. Use pytest fixtures for common setup
2. Test both success and error cases
3. Use temporary directories for file operations
4. Mock external dependencies (GitHub API, file system) when appropriate

## Multi-Project Setup

### How Config Tracking Works

skill-manager supports tracking multiple `skills.yaml` files across different projects. This is useful when:
- You work on multiple projects that use Claude Code skills
- You want to sync all projects' skills with a single command
- You maintain shared skill configurations

### Registering a Project Config

When you start working on a new project with skill-manager:

1. Create or locate the project's `skills.yaml`:
```bash
cd /path/to/project
uv run skill-manager init
```

2. Register it with skill-manager:
```bash
uv run skill-manager config add /path/to/project/skills.yaml
```

3. The config is now tracked and will be synced with `sync-all`

### Example Multi-Project Workflow

```bash
# Set up project A
cd ~/projects/project-a
uv run skill-manager init
uv run skill-manager config add ~/projects/project-a/skills.yaml

# Set up project B
cd ~/projects/project-b
uv run skill-manager init
uv run skill-manager config add ~/projects/project-b/skills.yaml

# Later, sync all projects at once
uv run skill-manager sync-all
```

### Viewing Tracked Configs

```bash
# List all tracked configs and their status
uv run skill-manager config list
```

Output shows:
- ✓ Config exists and is accessible
- ✗ Config not found (may have been moved or deleted)

### Removing Stale Configs

If a project is deleted or moved:

```bash
# Remove from tracked list
uv run skill-manager config remove /old/path/to/skills.yaml
```

## Configuration File Format

### Basic Structure

```yaml
version: "1.0"

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

skills:
  - name: pdf
    source: anthropic
```

### Composable Skills

```yaml
skills:
  - name: code-review
    description: "Custom code review with company standards"
    compose:
      - source: anthropic
        skill: code-review
        level: default
      - path: "./local-skills/code-review-overrides"
        level: user
```

Composition levels (in order of precedence):
1. `user` - Highest priority (overrides everything)
2. `team` - Middle priority
3. `default` - Lowest priority (base implementation)

## Environment Variables

### GITHUB_TOKEN

For accessing private GitHub repositories or avoiding rate limits:

```bash
export GITHUB_TOKEN=ghp_your_token_here
uv run skill-manager sync
```

## Troubleshooting

### Config Not Found

If you see "No configuration file found":
1. Check if `skills.yaml` exists in current directory
2. Check if `~/.config/skill-manager/skills.yaml` exists
3. Use `--config` flag to specify path explicitly

### Sync Failures

If sync fails:
1. Run with `--dry-run` to see what would happen
2. Run `validate` to check config syntax
3. Use `--force` to bypass cache and refetch
4. Check GitHub token if accessing private repos

### Cache Issues

Clear the cache manually if needed:
```bash
rm -rf ~/.cache/skill-manager
```

## Best Practices

1. **Always use sync-all after config changes** - Keeps all projects in sync
2. **Track project configs** - Register configs with `config add` for easy management
3. **Use dry-run for verification** - Preview changes before applying
4. **Validate configs** - Run `validate` before syncing to catch errors early
5. **Use version control** - Keep `skills.yaml` in git for team sharing
6. **Document custom skills** - Add descriptions to composed skills
7. **Test locally first** - Use local paths for testing before GitHub sources

## Quick Reference

| Task | Command |
|------|---------|
| Create new config | `uv run skill-manager init` |
| Sync current config | `uv run skill-manager sync` |
| Sync all tracked configs | `uv run skill-manager sync-all` |
| Track a config | `uv run skill-manager config add <path>` |
| List tracked configs | `uv run skill-manager config list` |
| List installed skills | `uv run skill-manager list` |
| Remove a skill | `uv run skill-manager remove <name>` |
| Validate config | `uv run skill-manager validate` |
| Run tests | `uv run pytest` |
| Show help | `uv run skill-manager --help` |
