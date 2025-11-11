"""
GitHub Issues/PRs Search provider implementation.
"""

import time
import requests
from typing import List, Dict

from model.providers.base_provider import GLProvider
from model.Settings import get_settings


class GitHubIssuesProvider(GLProvider):
    """Provider for GitHub Issues and Pull Requests Search."""
    
    @classmethod
    def get_id(cls) -> str:
        return "gh_issues"
    
    @classmethod
    def get_name(cls) -> str:
        return "GitHub Search Issues"
    
    @classmethod
    def get_prompt_template_path(cls) -> str:
        return "data/GLProvidersPrompts/GitHubSearchIssuesPrompt.txt"
    
    @classmethod
    def are_all_keys_set(cls) -> bool:
        """
        Check if GitHub Issues provider has required API keys.
        Requires GITHUB_TOKEN.
        
        Returns:
            True if GITHUB_TOKEN is set
        """
        settings = get_settings()
        return bool(settings.get('GITHUB_TOKEN'))
    
    @classmethod
    def get_filtering_strategy(cls):
        """Get the filtering strategy for GitHub issues."""
        from model.filtering import GitHubIssuesFilteringStrategy
        return GitHubIssuesFilteringStrategy()
    
    def search(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Execute a GitHub issues/PRs search.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of issues/PRs search result dictionaries
        """
        settings = get_settings()
        github_token = settings.get('GITHUB_TOKEN')
        sleep_between = float(settings.get('SEARCH_SLEEP_BETWEEN', 1.0))
        
        if not github_token:
            return []
        
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }
        
        params = {"q": query, "per_page": 100, "page": 1}
        results = []
        
        while len(results) < max_results:
            try:
                r = requests.get(
                    "https://api.github.com/search/issues",
                    headers=headers,
                    params=params,
                    timeout=30
                )
                
                if r.status_code != 200:
                    break
                
                data = r.json()
                items = data.get("items", [])
                
                if not items:
                    break
                
                for it in items:
                    results.append({
                        "source": self.id,
                        "title": it.get("title"),
                        "url": it.get("html_url"),
                        "snippet": (it.get("body") or ""),
                        "search_query": query,
                        "state": it.get("state"),
                        "comments": it.get("comments"),
                    })
                    
                    if len(results) >= max_results:
                        break
                
                if "next" not in r.links:
                    break
                
                params["page"] += 1
                time.sleep(sleep_between)
                
            except Exception as e:
                print(f"GitHub Issues search error: {e}")
                break
        
        return self._dedupe_by_url(results)[:max_results]
