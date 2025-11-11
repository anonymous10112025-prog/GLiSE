"""
Filtering strategies package for different GL providers.
"""

from .base_strategy import FilteringStrategy, NoFilteringStrategy
from .github_repos_strategy import GitHubReposFilteringStrategy
from .github_issues_strategy import GitHubIssuesFilteringStrategy
from .stackoverflow_strategy import StackOverflowFilteringStrategy
from .google_strategy import GoogleFilteringStrategy

__all__ = [
    "FilteringStrategy",
    "NoFilteringStrategy",
    "GitHubReposFilteringStrategy",
    "GitHubIssuesFilteringStrategy",
    "StackOverflowFilteringStrategy",
    "GoogleFilteringStrategy"
]
