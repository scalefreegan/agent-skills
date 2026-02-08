# Skill Manager

A CLI tool for assembling composite skills from multiple sources, with support for GitHub repositories, local paths, and hierarchical composition with precedence rules.

## Key Features

- **Composable Skills** - Merge skills from multiple sources with clear precedence rules
- **GitHub Integration** - Fetch skills directly from GitHub repositories
- **Smart Caching** - Efficient caching with configurable refresh policies
- **Multi-Project Support** - Track and sync multiple configuration files
- **Precedence System** - User-level overrides default configurations with clear markers
- **Rich CLI** - Beautiful terminal output with tables and status indicators

## Installation

Using `uv` (recommended):

```bash
uv tool install .
```

Using `pipx`:

```bash
pipx install .
```

For development:

```bash
uv sync --dev
```

## Quick Start

1. **Initialize a configuration file**:

```bash
skill-manager init
```

This creates a `skills.yaml` file in your current directory with example configuration.

2. **Edit `skills.yaml`** to define your skill sources and desired skills

3. **Sync skills to install them**:

```bash
skill-manager sync
```

Skills are installed to `.claude/skills` by default (configurable).

4. **List installed skills**:

```bash
skill-manager list
```

## Configuration

### Config File Format

The configuration file uses YAML format and follows a clear schema:

```yaml
version: "1.0"

settings:
  target_dirs:
    - ".claude/skills"          # Where skills are installed
  cache_dir: "~/.cache/skill-manager"  # Cache location
  default_branch: "main"        # Default git branch

sources:
  anthropic:
    type: github
    repo: "anthropics/claude-code"
    path: "skills"              # Optional: path within repo
    branch: "main"              # Optional: override default_branch

skills:
  # Simple skills (single source)
  - name: pdf
    source: anthropic

  - name: local-skill
    path: "./my-skills/custom-skill"

  - name: remote-skill
    url: "https://github.com/owner/repo/tree/main/path/to/skill"

  # Composable skills (multiple sources with precedence)
  - name: code-review
    description: "Custom code review with company standards"
    compose:
      - source: anthropic
        skill: code-review
        level: default
      - path: "./local-skills/code-review-overrides"
        level: user
```

### Schema Reference

#### Root Config

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Config schema version (must be "1.x") |
| `settings` | object | No | Global settings |
| `sources` | object | No | Named skill sources |
| `skills` | array | Yes | List of skills to install |

#### Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `target_dirs` | array | `[".claude/skills"]` | Directories where skills are installed |
| `cache_dir` | string | `"~/.cache/skill-manager"` | Cache directory path |
| `default_branch` | string | `"main"` | Default git branch for GitHub sources |

#### Source Config

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Source type (currently only `"github"`) |
| `repo` | string | Yes | Repository in format `"owner/repo"` |
| `path` | string | No | Path within repository to skills directory |
| `branch` | string | No | Branch to fetch from (overrides `default_branch`) |

#### Skill Config

**Simple Skill** (exactly one of):

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Named source reference |
| `path` | string | Local filesystem path |
| `url` | string | Direct GitHub URL |

**Composed Skill**:

| Field | Type | Description |
|-------|------|-------------|
| `compose` | array | List of compose items (see below) |

**All Skills**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique skill name |
| `description` | string | No | Human-readable description |

#### Compose Item Config

Each item in the `compose` array (exactly one of `source`, `path`, or `url`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | Conditional | Named source reference |
| `skill` | string | If source | Skill name within the source |
| `path` | string | Conditional | Local filesystem path |
| `url` | string | Conditional | Direct GitHub URL |
| `level` | string | No | Precedence level: `"default"` or `"user"` (default: `"default"`) |

### Config File Precedence

The CLI searches for configuration files in this order:

1. **Explicit path** - `--config <path>` flag
2. **Project config** - `./skills.yaml` in current directory
3. **User config** - `~/.config/skill-manager/skills.yaml`

## Composable Skills

Composable skills allow you to merge content from multiple skill sources, with clear precedence rules for conflict resolution.

### How Composition Works

When you define a skill with a `compose` array, the skill manager:

1. Fetches/loads all specified sources
2. Sorts sources by precedence level (`default` < `user`)
3. Composes markdown files with precedence markers
4. Handles non-markdown files with user-level overrides

### Example: Code Review Skill

Given this configuration:

```yaml
skills:
  - name: code-review
    description: "Code review with company standards"
    compose:
      - source: anthropic
        skill: code-review
        level: default
      - path: "./company-skills/code-review-override"
        level: user
```

The resulting `SKILL.md` will contain:

```markdown
<!-- PRECEDENCE: default -->
<!-- The following content is from the default-level skill -->

# Code Review Skill

[Content from anthropic/claude-code code-review skill]

<!-- PRECEDENCE: user (overrides default) -->
<!-- The following content is from the user-level skill and takes priority -->
<!-- When conflicts exist, follow the user-level instructions below -->

# Company Code Review Standards

[Content from your company override skill]
```

### Precedence Levels

#### Default Level (`level: default`)

- Provides base functionality and general best practices
- Multiple default-level sources can be combined
- Content appears first in composed markdown
- Non-markdown files are used as fallback

#### User Level (`level: user`)

- Overrides default settings with project/company-specific requirements
- Takes priority over default-level content
- Clearly marked in composed output
- Non-markdown files replace default-level files with the same name

### Markdown Composition

Markdown files (`.md` files) are **concatenated** with precedence markers:

- Default-level content appears first
- User-level content appears after
- HTML comments mark precedence boundaries
- Agents are instructed to follow user-level instructions when conflicts exist

Example composed output:

```markdown
<!-- PRECEDENCE: default -->
<!-- The following content is from the default-level skill -->

[Default content here]

<!-- PRECEDENCE: user (overrides default) -->
<!-- The following content is from the user-level skill and takes priority -->
<!-- When conflicts exist, follow the user-level instructions below -->

[User override content here]
```

### File Composition

Non-markdown files (scripts, configs, etc.) follow a **user-wins** strategy:

- If a user-level file exists with the same name → user file is used
- If no user-level file exists → default-level file is used
- Files are copied preserving their relative directory structure

Example:

```
default-skill/
  SKILL.md
  examples.sql
  schema.sql

user-skill/
  SKILL.md
  schema.sql  # Overrides default

composed-skill/
  SKILL.md     # Markdown concatenated with precedence markers
  examples.sql # From default (no user override)
  schema.sql   # From user (overrides default)
```

## CLI Commands

### Core Commands

#### `skill-manager sync`

Assemble all skills from configuration.

```bash
skill-manager sync [OPTIONS]
```

**Options:**
- `--config, -c <path>` - Path to config file (overrides default search)
- `--target, -t <dir>` - Override target directory
- `--dry-run` - Show what would be done without making changes
- `--force` - Force refresh, bypass cache

**Examples:**

```bash
# Sync using default config
skill-manager sync

# Sync with specific config
skill-manager sync --config ~/projects/myapp/skills.yaml

# Dry run to preview changes
skill-manager sync --dry-run

# Force refresh all skills (bypass cache)
skill-manager sync --force
```

#### `skill-manager sync-all`

Sync all tracked/registered configs.

```bash
skill-manager sync-all [OPTIONS]
```

**Options:**
- `--dry-run` - Show what would be done without making changes
- `--force` - Force refresh, bypass cache

Useful for multi-project setups where you've registered multiple configuration files.

**Example:**

```bash
# Sync all tracked projects
skill-manager sync-all

# Dry run across all projects
skill-manager sync-all --dry-run
```

#### `skill-manager list`

List configured/installed skills.

```bash
skill-manager list [OPTIONS]
```

**Options:**
- `--config, -c <path>` - Path to config file
- `--target, -t <dir>` - Target directory to list skills from

Shows a table with skill names, descriptions, and installation timestamps.

**Example:**

```bash
skill-manager list
```

Output:
```
Target: /path/to/.claude/skills

┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Name        ┃ Description             ┃ Installed At    ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ pdf         │ PDF analysis skill      │ 2026-02-08 10:30│
│ code-review │ Custom code review      │ 2026-02-08 10:30│
└─────────────┴─────────────────────────┴─────────────────┘
```

#### `skill-manager remove`

Remove an installed skill.

```bash
skill-manager remove <skill> [OPTIONS]
```

**Arguments:**
- `<skill>` - Name of skill to remove

**Options:**
- `--config, -c <path>` - Path to config file
- `--target, -t <dir>` - Target directory
- `--force` - Skip confirmation prompt

**Example:**

```bash
# Remove with confirmation
skill-manager remove pdf

# Remove without confirmation
skill-manager remove pdf --force
```

#### `skill-manager init`

Create a skills.yaml template.

```bash
skill-manager init [PATH] [OPTIONS]
```

**Arguments:**
- `[PATH]` - Path where config should be created (default: `./skills.yaml`)

**Options:**
- `--force` - Overwrite existing config file

**Example:**

```bash
# Create config in current directory
skill-manager init

# Create config in specific location
skill-manager init ~/.config/skill-manager/skills.yaml

# Overwrite existing config
skill-manager init --force
```

#### `skill-manager validate`

Validate configuration and skill structure.

```bash
skill-manager validate [OPTIONS]
```

**Options:**
- `--config, -c <path>` - Path to config file

Checks that the configuration file is valid and displays a summary of sources, skills, and target directories.

**Example:**

```bash
skill-manager validate
```

### Config Management Commands

#### `skill-manager config add`

Register/track a config file.

```bash
skill-manager config add <path>
```

**Arguments:**
- `<path>` - Path to config file to track

Adds a configuration file to the tracked list for use with `sync-all`.

**Example:**

```bash
skill-manager config add ~/projects/project-a/skills.yaml
skill-manager config add ~/projects/project-b/skills.yaml
```

#### `skill-manager config list`

List all tracked config files.

```bash
skill-manager config list
```

Shows all configuration files that will be synced by `sync-all`.

**Example:**

```bash
skill-manager config list
```

Output:
```
Tracked configs: (2)

✓ /Users/user/projects/project-a/skills.yaml
✓ /Users/user/projects/project-b/skills.yaml
```

#### `skill-manager config remove`

Untrack a config file.

```bash
skill-manager config remove <path>
```

**Arguments:**
- `<path>` - Path to config file to untrack

**Example:**

```bash
skill-manager config remove ~/projects/project-a/skills.yaml
```

## Example Workflows

### Adding a Simple Skill

Add a skill from a named source:

```bash
# 1. Edit skills.yaml
cat >> skills.yaml << 'EOF'
  - name: pdf
    source: anthropic
EOF

# 2. Sync to install
skill-manager sync

# 3. Verify installation
skill-manager list
```

### Creating a Custom Composed Skill

Build a skill that combines default best practices with company standards:

```bash
# 1. Create local override skill
mkdir -p ./company-skills/code-review
cat > ./company-skills/code-review/SKILL.md << 'EOF'
---
name: company-code-review
description: Company coding standards
---

# Company Standards

Always follow these company-specific rules:

1. All functions must have type hints
2. Use Google-style docstrings
3. Security review required for auth changes
EOF

# 2. Add composed skill to config
cat >> skills.yaml << 'EOF'
  - name: code-review-enhanced
    description: "Code review with company standards"
    compose:
      - source: anthropic
        skill: code-review
        level: default
      - path: "./company-skills/code-review"
        level: user
EOF

# 3. Sync to compose and install
skill-manager sync

# 4. Check the composed output
cat .claude/skills/code-review-enhanced/SKILL.md
```

The resulting `SKILL.md` will have default code review guidance followed by your company-specific standards, clearly marked with precedence comments.

### Multi-Project Setup

Track and sync multiple projects:

```bash
# Project A setup
cd ~/projects/project-a
skill-manager init
# ... edit skills.yaml ...
skill-manager config add ./skills.yaml
skill-manager sync

# Project B setup
cd ~/projects/project-b
skill-manager init
# ... edit skills.yaml ...
skill-manager config add ./skills.yaml
skill-manager sync

# Later: sync all projects at once
skill-manager sync-all

# View tracked projects
skill-manager config list
```

### Using GitHub URLs Directly

You can reference skills directly via GitHub URL:

```yaml
skills:
  - name: my-skill
    url: "https://github.com/owner/repo/tree/main/skills/my-skill"
```

Or use environment variables for GitHub authentication:

```bash
export GITHUB_TOKEN="ghp_your_token_here"
skill-manager sync
```

### Precedence in Action

Create a SQL skill that combines base knowledge, advanced techniques, and company standards:

```yaml
skills:
  - name: sql-expert
    description: "Comprehensive SQL with company standards"
    compose:
      # Base SQL knowledge (default)
      - source: community
        skill: sql-basics
        level: default

      # Advanced techniques (default)
      - source: community
        skill: sql-advanced
        level: default

      # Company-specific rules (user - takes priority)
      - path: "./company-skills/sql-standards"
        level: user
```

Result:
- Default content (sql-basics + sql-advanced) appears first
- User content (company standards) appears after with override markers
- If company-skills includes a file like `schema_template.sql`, it will replace any default version
- Markdown content is concatenated; scripts/configs follow user-wins strategy

## Development

### Project Structure

```
skill-manager/
├── src/skill_manager/
│   ├── cli.py              # CLI commands and entry point
│   ├── config/             # Configuration schema and loading
│   ├── core/               # Core models (Skill, Registry, Resolver)
│   ├── compose/            # Composition logic (markdown, files, assembler)
│   ├── fetch/              # Fetchers (GitHub, cache)
│   └── utils/              # Utilities (paths, output)
├── tests/                  # Test suite
├── examples/               # Usage examples
├── pyproject.toml          # Project metadata
└── README.md               # This file
```

### Running Tests

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=skill_manager
```

### Contributing

Contributions are welcome! Please ensure:

1. All tests pass: `uv run pytest`
2. Code follows project style
3. New features include tests
4. Documentation is updated

### Building

```bash
# Build the package
uv build

# Install locally
uv tool install .

# Install in editable mode for development
uv pip install -e .
```

## Environment Variables

- `GITHUB_TOKEN` - GitHub personal access token for private repositories (optional)

## File Structure

Skills are installed with the following structure:

```
target_dir/
├── .skill-manager/
│   └── registry.yaml       # Tracks installed skills
└── skill-name/
    ├── SKILL.md            # Main skill documentation
    └── [other files]       # Scripts, configs, examples, etc.
```

## Troubleshooting

### Config not found

If you see "No configuration file found":

1. Run `skill-manager init` to create a config
2. Or specify config path: `skill-manager sync --config path/to/skills.yaml`

### Validation errors

Run `skill-manager validate` to check your config:

```bash
skill-manager validate --config ./skills.yaml
```

### Cache issues

Force refresh to bypass cache:

```bash
skill-manager sync --force
```

Cache location: `~/.cache/skill-manager` (configurable in settings)

### GitHub rate limiting

Set a GitHub token to increase rate limits:

```bash
export GITHUB_TOKEN="ghp_your_token_here"
skill-manager sync
```

## License

See LICENSE file for details.

## Author

Aaron Brooks (aaron.neil.brooks@gmail.com)
