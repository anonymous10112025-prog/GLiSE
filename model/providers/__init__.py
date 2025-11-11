"""
Grey Literature Providers package.
Contains base provider class and concrete implementations for different search sources.
"""

from model.providers.base_provider import GLProvider
from model.providers.google_provider import GoogleProvider
from model.providers.github_issues_provider import GitHubIssuesProvider
from model.providers.github_repos_provider import GitHubReposProvider
from model.providers.stackoverflow_provider import StackOverflowProvider

# Provider registry mapping IDs to classes
PROVIDER_CLASSES = {
    "google": GoogleProvider,
    "gh_issues": GitHubIssuesProvider,
    "gh_repos": GitHubReposProvider,
    "so": StackOverflowProvider,
}

def get_provider(provider_id: str) -> GLProvider:
    """
    Factory function to get a provider instance by ID.
    
    Args:
        provider_id: Unique identifier for the provider
        
    Returns:
        Provider instance
        
    Raises:
        ValueError: If provider_id is not recognized
    """
    provider_class = PROVIDER_CLASSES.get(provider_id)
    if not provider_class:
        raise ValueError(f"Unknown provider ID: {provider_id}")
    
    return provider_class()

def get_all_providers() -> dict:
    """
    Get all available provider instances.
    
    Returns:
        Dictionary mapping provider IDs to provider instances
    """
    return {pid: get_provider(pid) for pid in PROVIDER_CLASSES.keys()}

__all__ = [
    'GLProvider',
    'GoogleProvider',
    'GitHubIssuesProvider',
    'GitHubReposProvider',
    'StackOverflowProvider',
    'get_provider',
    'get_all_providers',
    'PROVIDER_CLASSES',
]
