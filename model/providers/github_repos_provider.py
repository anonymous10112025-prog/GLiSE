"""
GitHub Repositories Search provider implementation.
"""

import time
import requests
from typing import List, Dict

from model.providers.base_provider import GLProvider
from model.Settings import get_settings


# Common README filename candidates
README_CANDIDATES = [
    "README.md",
    "README.MD",
    "readme.md",
    "README.rst",
    "readme.rst",
    "README",
    "readme",
]


class GitHubReposProvider(GLProvider):
    """Provider for GitHub Repositories Search."""
    
    @classmethod
    def get_id(cls) -> str:
        return "gh_repos"
    
    @classmethod
    def get_name(cls) -> str:
        return "GitHub Search Repositories"
    
    @classmethod
    def get_prompt_template_path(cls) -> str:
        return "data/GLProvidersPrompts/GitHubSearchReposPrompt.txt"
    
    @classmethod
    def are_all_keys_set(cls) -> bool:
        """
        Check if GitHub Repos provider has required API keys.
        Requires GITHUB_TOKEN.
        
        Returns:
            True if GITHUB_TOKEN is set
        """
        settings = get_settings()
        return bool(settings.get('GITHUB_TOKEN'))
    
    @classmethod
    def get_filtering_strategy(cls):
        """Get the filtering strategy for GitHub repositories."""
        from model.filtering import GitHubReposFilteringStrategy
        return GitHubReposFilteringStrategy()
    
    def search(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Execute a GitHub repositories search with README fetching.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of repository search result dictionaries with README content
        """
        settings = get_settings()
        github_token = settings.get('GITHUB_TOKEN')
        sleep_between = float(settings.get('SEARCH_SLEEP_BETWEEN', 1.0))
        
        if not github_token:
            return []
        
        # Step 1: Search repositories using REST API
        repos = self._search_repositories(query, max_results, github_token, sleep_between)
        
        if not repos:
            return []
        
        # Step 2: Fetch READMEs using GraphQL
        self._fetch_readmes(repos, github_token)
        
        return repos
    
    def _search_repositories(
        self,
        query: str,
        max_results: int,
        github_token: str,
        sleep_between: float
    ) -> List[Dict]:
        """Search for repositories using GitHub REST API."""
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }
        
        params = {"q": query, "per_page": 100, "page": 1}
        repos = []
        
        while len(repos) < max_results:
            try:
                r = requests.get(
                    "https://api.github.com/search/repositories",
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
                    repos.append({
                        "source": self.id,
                        "owner": it["owner"]["login"],
                        "name": it["name"],
                        "title": it.get("full_name"),
                        "url": it.get("html_url"),
                        "snippet": (it.get("description") or "")[:240],
                        "search_query": query,
                        "stargazers_count": it.get("stargazers_count"),
                        "language": it.get("language"),
                        "readme": "",  # Will be filled by GraphQL
                    })
                    
                    if len(repos) >= max_results:
                        break
                
                if "next" not in r.links:
                    break
                
                params["page"] += 1
                time.sleep(sleep_between)
                
            except Exception as e:
                break
        
        return self._dedupe_by_url(repos)[:max_results]
    
    def _fetch_readmes(self, repos: List[Dict], github_token: str) -> None:
        """Fetch README contents for repositories using GraphQL batching."""
        if not repos:
            return
        
        gql_headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }
        
        # Build GraphQL query for batch fetching READMEs
        repo_aliases = {}
        gql_parts = []
        
        for idx, rinfo in enumerate(repos):
            alias = f"r{idx}"
            repo_aliases[alias] = rinfo
            owner = rinfo["owner"]
            name = rinfo["name"]
            
            # Try multiple README filenames
            tries = []
            for fname in README_CANDIDATES:
                tries.append(f"""
                    x_{fname.replace('.', '_')} : object(expression: "HEAD:{fname}") {{
                        ... on Blob {{ text }}
                    }}
                """)
            
            gql_parts.append(f"""
            {alias}: repository(owner: "{owner}", name: "{name}") {{
                {"".join(tries)}
            }}
            """)
        
        gql_query = "query { " + "\n".join(gql_parts) + " }"
        
        try:
            gql_res = requests.post(
                "https://api.github.com/graphql",
                json={"query": gql_query},
                headers=gql_headers,
                timeout=30
            )
            
            if gql_res.status_code == 200:
                gql_data = gql_res.json().get("data", {})
                
                for alias, repo_info in repo_aliases.items():
                    repo_node = gql_data.get(alias, {})
                    readme_content = ""
                    
                    # Try each candidate in order — first match wins
                    for fname in README_CANDIDATES:
                        key = "x_" + fname.replace(".", "_")
                        blob = repo_node.get(key)
                        if blob and blob.get("text"):
                            readme_content = blob["text"]
                            break
                    
                    repo_info["readme"] = readme_content
        
        except Exception as e:
            pass  # Silent fail for README fetching