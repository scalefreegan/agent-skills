"""Skill assembler orchestrator.

This module provides the main composition orchestrator that ties everything together.
For each composed skill, it:
1. Fetches all source skills (via resolver + fetcher)
2. Groups files by type (markdown vs other)
3. Applies markdown composer to .md files
4. Applies file composer to other files
5. Writes assembled skill to target dir

Handles both simple skills (single source) and composed skills (multiple sources).
"""

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from skill_manager.compose.files import compose_non_markdown_files
from skill_manager.compose.markdown import compose_markdown_files
from skill_manager.config.schema import (
    ComposeItemConfig,
    PrecedenceLevel,
    SkillConfig,
    SkillManagerConfig,
)
from skill_manager.core.resolver import resolve_compose_item, ResolvedSource
from skill_manager.core.skill import Skill, SkillSource
from skill_manager.fetch.cache import SkillCache
from skill_manager.fetch.github import GitHubFetcher
from skill_manager.utils.output import console, print_error, print_info, print_success
from skill_manager.utils.paths import ensure_dir, expand_path


@dataclass
class AssemblyContext:
    """Context for skill assembly.

    Attributes:
        config: The skill manager configuration
        cache: Cache for downloaded skills
        github_token: Optional GitHub token for authenticated requests
    """

    config: SkillManagerConfig
    cache: SkillCache
    github_token: Optional[str] = None


async def assemble_skill(
    skill_config: SkillConfig,
    context: AssemblyContext,
    target_dir: Path,
    force_refresh: bool = False,
) -> Skill:
    """Assemble a single skill (simple or composed).

    For simple skills: fetch and copy to target
    For composed skills: fetch all sources, compose, write to target

    Args:
        skill_config: The skill configuration to assemble
        context: Assembly context with config, cache, and tokens
        target_dir: Target directory where skill should be installed
        force_refresh: If True, bypass cache and fetch fresh

    Returns:
        Installed Skill object

    Raises:
        ValueError: If skill cannot be assembled
        OSError: If file operations fail
    """
    skill_name = skill_config.name
    skill_target_path = target_dir / skill_name

    print_info(f"Assembling skill: {skill_name}")

    # Determine if this is a simple or composed skill
    if skill_config.compose is not None:
        # Composed skill - fetch all sources and compose
        return await _assemble_composed_skill(
            skill_config, context, skill_target_path, force_refresh
        )
    else:
        # Simple skill - fetch single source and copy
        return await _assemble_simple_skill(
            skill_config, context, skill_target_path, force_refresh
        )


async def _assemble_simple_skill(
    skill_config: SkillConfig,
    context: AssemblyContext,
    target_path: Path,
    force_refresh: bool,
) -> Skill:
    """Assemble a simple skill from a single source.

    Args:
        skill_config: Skill configuration
        context: Assembly context
        target_path: Target directory for the skill
        force_refresh: Whether to bypass cache

    Returns:
        Installed Skill object
    """
    # Create a temporary ComposeItemConfig to reuse resolution logic
    item = ComposeItemConfig(
        source=skill_config.source,
        skill=skill_config.name if skill_config.source else None,
        path=skill_config.path,
        url=skill_config.url,
        level=PrecedenceLevel.DEFAULT,
    )

    # Resolve the source
    resolved = resolve_compose_item(
        item,
        context.config.sources,
        context.config.settings.default_branch,
    )

    # Fetch the source
    skill_source = await _fetch_source(resolved, context, force_refresh)

    # Clean target directory if it exists
    if target_path.exists():
        shutil.rmtree(target_path)

    # Copy skill to target
    ensure_dir(target_path)
    for item_path in skill_source.path.iterdir():
        if item_path.is_file():
            shutil.copy2(item_path, target_path / item_path.name)
        elif item_path.is_dir():
            shutil.copytree(item_path, target_path / item_path.name)

    # Create installed skill - use config name, not source name
    skill = Skill(
        name=skill_config.name,
        path=target_path,
        description=skill_config.description
        or (skill_source.metadata.description if skill_source.metadata else None),
        installed_at=datetime.now(timezone.utc).isoformat(),
    )

    print_success(f"Installed simple skill: {skill.name}")
    return skill


async def _assemble_composed_skill(
    skill_config: SkillConfig,
    context: AssemblyContext,
    target_path: Path,
    force_refresh: bool,
) -> Skill:
    """Assemble a composed skill from multiple sources.

    Args:
        skill_config: Skill configuration with compose list
        context: Assembly context
        target_path: Target directory for the skill
        force_refresh: Whether to bypass cache

    Returns:
        Installed Skill object
    """
    if not skill_config.compose:
        raise ValueError(f"Composed skill {skill_config.name} has no compose list")

    # Fetch all source skills
    source_skills: list[tuple[SkillSource, PrecedenceLevel]] = []
    source_names: list[str] = []

    for compose_item in skill_config.compose:
        # Resolve the compose item
        resolved = resolve_compose_item(
            compose_item,
            context.config.sources,
            context.config.settings.default_branch,
        )

        # Fetch the source
        skill_source = await _fetch_source(resolved, context, force_refresh)

        source_skills.append((skill_source, compose_item.level))
        source_names.append(skill_source.name)

        print_info(
            f"  Fetched source: {skill_source.name} (precedence: {compose_item.level.value})"
        )

    # Clean target directory if it exists
    if target_path.exists():
        shutil.rmtree(target_path)

    ensure_dir(target_path)

    # Compose markdown files
    markdown_output = target_path / "SKILL.md"
    try:
        compose_markdown_files(source_skills, markdown_output)
        print_info(f"  Composed markdown files -> {markdown_output.name}")
    except ValueError as e:
        # No markdown files to compose - this is ok for some skills
        print_info(f"  No markdown files to compose: {e}")

    # Compose non-markdown files
    manifest = compose_non_markdown_files(source_skills, target_path)
    if manifest:
        print_info(f"  Composed {len(manifest)} non-markdown files")

    # Create installed skill
    skill = Skill(
        name=skill_config.name,
        path=target_path,
        description=skill_config.description,
        composed_from=source_names,
        installed_at=datetime.now(timezone.utc).isoformat(),
    )

    print_success(f"Assembled composed skill: {skill.name}")
    return skill


async def _fetch_source(
    resolved: ResolvedSource,
    context: AssemblyContext,
    force_refresh: bool,
) -> SkillSource:
    """Fetch a source skill from either local path or GitHub.

    Args:
        resolved: Resolved source information
        context: Assembly context
        force_refresh: Whether to bypass cache

    Returns:
        SkillSource object

    Raises:
        ValueError: If source cannot be fetched
    """
    if resolved.type == "local":
        # Local path - just create SkillSource directly
        if not resolved.local_path:
            raise ValueError("Local source has no path")

        if not resolved.local_path.exists():
            raise ValueError(f"Local path does not exist: {resolved.local_path}")

        skill_name = resolved.local_path.name
        return SkillSource(
            name=skill_name,
            path=resolved.local_path,
        )

    elif resolved.type == "github":
        # GitHub source - check cache first, then fetch
        if not all([resolved.owner, resolved.repo, resolved.path, resolved.ref]):
            raise ValueError("GitHub source missing required components")

        # Type assertion for mypy - we know these are not None
        owner = resolved.owner
        repo = resolved.repo
        path = resolved.path
        ref = resolved.ref

        # Check cache unless force_refresh
        if not force_refresh:
            cached = context.cache.get_cached_skill(owner, repo, path, ref)
            if cached:
                print_info(f"  Using cached skill: {cached.name}")
                return cached

        # Fetch from GitHub
        fetcher = GitHubFetcher(token=context.github_token)

        # Create a temporary directory for fetching
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / path.split("/")[-1]

            print_info(f"  Fetching from GitHub: {owner}/{repo}/{path}@{ref}")
            skill_source = await fetcher.fetch(owner, repo, path, ref, temp_path)

            # Cache the skill (copy to cache before returning)
            try:
                context.cache.cache_skill(skill_source, owner, repo, path, ref)
                print_info(f"  Cached skill: {skill_source.name}")
            except OSError as e:
                # Caching failed - log but don't fail the operation
                print_info(f"  Warning: Failed to cache skill: {e}")

            # Return the cached version if available, otherwise the temp version
            cached = context.cache.get_cached_skill(owner, repo, path, ref)
            if cached:
                return cached

            # If caching failed, we need to copy the temp directory elsewhere
            # since it will be deleted when we exit the context
            # This should not normally happen, but handle it gracefully
            raise ValueError(
                f"Failed to cache skill and temp directory will be deleted"
            )

    else:
        raise ValueError(f"Unsupported source type: {resolved.type}")


async def assemble_all_skills(
    config: SkillManagerConfig,
    target_dir: Path,
    force_refresh: bool = False,
    github_token: Optional[str] = None,
) -> list[Skill]:
    """Assemble all skills from config.

    Main entry point for skill assembly. Fetches and composes all skills
    defined in the configuration.

    Args:
        config: Skill manager configuration
        target_dir: Target directory where skills will be installed
        force_refresh: If True, bypass cache and fetch fresh
        github_token: Optional GitHub token for authenticated requests

    Returns:
        List of installed Skill objects

    Raises:
        ValueError: If any skill cannot be assembled
        OSError: If file operations fail
    """
    # Ensure target directory exists
    target_dir = expand_path(str(target_dir))
    ensure_dir(target_dir)

    # Initialize cache
    cache_dir = expand_path(config.settings.cache_dir)
    cache = SkillCache(cache_dir)

    # Create assembly context
    context = AssemblyContext(
        config=config,
        cache=cache,
        github_token=github_token,
    )

    # Assemble all skills
    installed_skills: list[Skill] = []
    errors: list[tuple[str, Exception]] = []

    for skill_config in config.skills:
        try:
            skill = await assemble_skill(
                skill_config, context, target_dir, force_refresh
            )
            installed_skills.append(skill)
        except Exception as e:
            errors.append((skill_config.name, e))
            print_error(f"Failed to assemble skill {skill_config.name}: {e}")

    # Report summary
    console.print()
    if installed_skills:
        print_success(f"Successfully installed {len(installed_skills)} skill(s)")
        for skill in installed_skills:
            console.print(f"  • {skill.name} -> {skill.path}")

    if errors:
        console.print()
        print_error(f"Failed to install {len(errors)} skill(s)")
        for skill_name, error in errors:
            console.print(f"  • {skill_name}: {error}")

    # Raise if any errors occurred
    if errors:
        raise ValueError(
            f"Failed to install {len(errors)} skill(s). See errors above."
        )

    return installed_skills
