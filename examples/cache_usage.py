"""Example demonstrating SkillCache usage.

This shows how to use the cache to store and retrieve downloaded skills,
reducing redundant network requests.
"""

import asyncio
from pathlib import Path

from skill_manager.fetch.cache import SkillCache
from skill_manager.fetch.github import GitHubFetcher


async def main():
    """Demonstrate cache usage with GitHub fetcher."""
    # Initialize cache with 1-hour TTL
    cache_dir = Path.home() / ".cache" / "skill-manager"
    cache = SkillCache(cache_dir, ttl_seconds=3600)

    # GitHub repo details
    owner = "anthropics"
    repo = "anthropic-skills"
    path = "skills/example-skill"
    ref = "main"

    print(f"Looking for cached skill: {owner}/{repo}/{path}@{ref}")

    # Try to get from cache first
    cached_skill = cache.get_cached_skill(owner, repo, path, ref)

    if cached_skill:
        print(f"✓ Found in cache: {cached_skill.path}")
        print(f"  Name: {cached_skill.name}")
        if cached_skill.metadata:
            print(f"  Description: {cached_skill.metadata.description}")
            print(f"  Version: {cached_skill.metadata.version}")
    else:
        print("✗ Not in cache, fetching from GitHub...")

        # Fetch from GitHub
        fetcher = GitHubFetcher()  # Can pass token for private repos
        temp_dir = Path("/tmp/skill-download")

        try:
            skill = await fetcher.fetch(owner, repo, path, ref, temp_dir)
            print(f"✓ Downloaded to: {skill.path}")

            # Cache for future use
            cache.cache_skill(skill, owner, repo, path, ref)
            print(f"✓ Cached at: {cache.cache_dir / cache.get_cache_key(owner, repo, path, ref)}")

        except Exception as e:
            print(f"✗ Error fetching: {e}")
            return

    # Demonstrate cache key generation
    print("\nCache key examples:")
    print(f"  main:  {cache.get_cache_key(owner, repo, path, 'main')}")
    print(f"  dev:   {cache.get_cache_key(owner, repo, path, 'dev')}")
    print(f"  v1.0:  {cache.get_cache_key(owner, repo, path, 'v1.0')}")

    # Show cache statistics
    print("\nCache contents:")
    if cache.cache_dir.exists():
        cached_items = list(cache.cache_dir.iterdir())
        print(f"  Total cached skills: {len(cached_items)}")
        for item in cached_items[:5]:  # Show first 5
            print(f"    - {item.name}")
        if len(cached_items) > 5:
            print(f"    ... and {len(cached_items) - 5} more")
    else:
        print("  Cache is empty")

    # Demonstrate force refresh
    print("\n--- Force Refresh ---")
    print("To force refresh, simply fetch and cache again:")
    print("  cache.cache_skill(new_skill, owner, repo, path, ref)")
    print("This will overwrite the existing cached version.")

    # Demonstrate cache clearing
    print("\n--- Cache Management ---")
    print("To clear all cached skills:")
    print("  cache.clear_cache()")
    print("\nTo check if a specific cache is expired:")
    cache_key = cache.get_cache_key(owner, repo, path, ref)
    cache_path = cache.cache_dir / cache_key
    if cache_path.exists():
        is_expired = cache.is_expired(cache_path)
        print(f"  Is expired: {is_expired}")


if __name__ == "__main__":
    # Note: This is a demo script. In real usage, the GitHub fetch
    # would only happen if the skill doesn't exist on GitHub.
    print("Skill Cache Usage Example")
    print("=" * 50)
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
