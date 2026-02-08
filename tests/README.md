# Test Suite

This directory contains comprehensive tests for the skill-manager project.

## Test Structure

### Unit Tests

- **test_schema.py** - Pydantic model validation tests
  - Tests for all configuration models (SettingsConfig, SourceConfig, ComposeItemConfig, SkillConfig, SkillManagerConfig)
  - Validation rule testing
  - Complex scenario testing
  - 32 tests

- **test_config.py** - Configuration loading and merging tests
  - YAML file loading
  - Config merging with precedence
  - Environment variable overrides
  - Config file discovery
  - 28 tests

- **test_resolver.py** - URL and source resolution tests
  - GitHub URL parsing
  - Named source resolution
  - Compose item resolution
  - Edge cases and error handling
  - 27 tests

- **test_cache.py** - Skill cache functionality tests
  - Cache initialization and storage
  - TTL and expiration handling
  - Cache key generation
  - Metadata handling
  - 18 tests

- **test_github_fetcher.py** - GitHub API fetcher tests (with mocked responses)
  - Skill fetching from GitHub
  - Recursive directory fetching
  - Authentication
  - Retry logic
  - Error handling
  - 14 tests

- **test_markdown_composer.py** - Markdown composition tests
  - Single and multiple source composition
  - Precedence marker injection
  - File ordering
  - 10 tests

- **test_files_composer.py** - File composition tests
  - Non-markdown file copying
  - Precedence handling
  - Directory structure preservation
  - Manifest generation
  - 10 tests

- **test_registry.py** - Skill registry tests
  - Skill registration and tracking
  - Manifest persistence
  - Conflict detection
  - 24 tests

### Integration Tests

- **test_assembler.py** - Skill assembler orchestration tests
  - Simple skill assembly from local paths
  - Composed skill assembly
  - File conflict resolution
  - 6 tests

- **test_assembler_integration.py** - End-to-end assembly tests
  - Realistic composition workflows
  - Multiple independent skills
  - Reassembly and updates
  - 3 tests

- **test_cache_integration.py** - Cache integration tests
  - Skill metadata preservation
  - File structure preservation
  - Cache workflow with force refresh
  - 5 tests

- **test_cli.py** - CLI command tests
  - init command
  - sync command
  - list command
  - remove command
  - validate command
  - Config commands
  - Composed skill workflows
  - 18 tests

## Running Tests

Run all tests:
```bash
uv run pytest tests/
```

Run specific test file:
```bash
uv run pytest tests/test_schema.py
```

Run with verbose output:
```bash
uv run pytest tests/ -v
```

Run specific test:
```bash
uv run pytest tests/test_schema.py::TestSettingsConfig::test_default_values
```

## Test Coverage Summary

**Total Tests: 194**

### Coverage by Module

1. **Config parsing (test_config.py + test_schema.py)**: 60 tests
   - All Pydantic models validated
   - Config loading with merging and precedence
   - Environment variable overrides

2. **Composition logic (test_assembler.py + test_markdown_composer.py + test_files_composer.py + test_assembler_integration.py)**: 29 tests
   - Markdown composition with precedence markers
   - File composition with conflict resolution
   - End-to-end assembly workflows

3. **URL parsing (test_resolver.py)**: 27 tests
   - GitHub URL parsing
   - Named source resolution
   - Compose item resolution

4. **GitHub integration (test_github_fetcher.py)**: 14 tests
   - Mocked GitHub API responses
   - Authentication and retry logic
   - Error handling

5. **Cache functionality (test_cache.py + test_cache_integration.py)**: 23 tests
   - Cache storage and retrieval
   - TTL and expiration
   - Integration with skill fetching

6. **Registry operations (test_registry.py)**: 24 tests
   - Skill registration and tracking
   - Manifest persistence
   - Conflict detection

7. **CLI integration (test_cli.py)**: 18 tests
   - All major CLI commands
   - Config file handling
   - Composed skill workflows

## Fixtures

Shared fixtures are defined in `conftest.py`:
- `temp_dir` - Temporary directory for tests
- `temp_cache_dir` - Temporary cache directory
- `temp_target_dir` - Temporary target directory for skill installation
- `sample_skill_dir` - Sample skill directory with SKILL.md
- `another_skill_dir` - Another sample skill for composition testing
- `minimal_config_dict` - Minimal valid configuration
- `github_source_config` - GitHub source configuration
- `sample_config_with_skills` - Complete configuration with skills

## Test Dependencies

- pytest>=8.0.0
- pytest-anyio>=0.0.0 (for async tests)
- respx>=0.21.0 (for HTTP mocking)

## Key Test Areas

### 1. Config Parsing
- ✅ All Pydantic models validated
- ✅ Field validation rules tested
- ✅ Complex composition scenarios tested
- ✅ Config merging with precedence
- ✅ Environment variable overrides

### 2. Composition Logic
- ✅ Markdown composition with precedence markers
- ✅ File composition with conflict resolution
- ✅ Directory structure preservation
- ✅ Manifest generation

### 3. URL Parsing
- ✅ GitHub URL parsing (various formats)
- ✅ Named source resolution
- ✅ Compose item resolution
- ✅ Edge cases and special characters

### 4. CLI Integration
- ✅ init command
- ✅ sync command
- ✅ list command
- ✅ remove command
- ✅ validate command
- ✅ Config subcommands

### 5. Mock HTTP
- ✅ GitHub API responses mocked
- ✅ Authentication testing
- ✅ Retry logic
- ✅ Error handling

### 6. Composed Output Format
- ✅ Precedence markers verified
- ✅ File conflict resolution tested
- ✅ Deterministic ordering
