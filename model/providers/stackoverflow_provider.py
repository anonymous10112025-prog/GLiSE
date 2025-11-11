"""
Stack Overflow Search provider implementation.
"""

import requests
from typing import List, Dict

from model.providers.base_provider import GLProvider
from model.Settings import get_settings


class StackOverflowProvider(GLProvider):
    """Provider for Stack Overflow/Stack Exchange API Search."""
    
    @classmethod
    def get_id(cls) -> str:
        return "so"
    
    @classmethod
    def get_name(cls) -> str:
        return "Stack Overflow"
    
    @classmethod
    def get_prompt_template_path(cls) -> str:
        return "data/GLProvidersPrompts/StackExchangePrompt.txt"
    
    @classmethod
    def are_all_keys_set(cls) -> bool:
        """
        Check if Stack Overflow provider has required API keys.
        Requires STACKEXCHANGE_API_KEY.
        
        Returns:
            True if STACKEXCHANGE_API_KEY is set
        """
        settings = get_settings()
        return bool(settings.get('STACKEXCHANGE_API_KEY'))
    
    @classmethod
    def get_filtering_strategy(cls):
        """Get the filtering strategy for Stack Overflow."""
        from model.filtering import StackOverflowFilteringStrategy
        return StackOverflowFilteringStrategy()
    
    def search(self, query: str, max_results: int = 50, from_date: str = None, to_date: str = None) -> List[Dict]:
        """
        Execute a Stack Overflow search using Stack Exchange API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            from_date: Optional start date filter in YYYY-MM-DD format
            to_date: Optional end date filter in YYYY-MM-DD format
            
        Returns:
            List of Stack Overflow search result dictionaries
        """
        settings = get_settings()
        stackexchange_key = settings.get('STACKEXCHANGE_API_KEY')
        
        if not query:
            return []
        
        params = {
            "order": "desc",
            "sort": "relevance",
            "q": query,
            "site": "stackoverflow",
            "pagesize": min(100, max_results),
            "filter": "withbody"
        }
        
        # Add date filters using Unix epoch seconds
        if from_date:
            from controller.date_helpers import to_unix_epoch_seconds
            params["fromdate"] = to_unix_epoch_seconds(from_date)
        
        if to_date:
            from controller.date_helpers import to_unix_epoch_seconds
            params["todate"] = to_unix_epoch_seconds(to_date, end_of_day=True)
        
        if stackexchange_key:
            params["key"] = stackexchange_key
        
        results = []
        
        try:
            r = requests.get(
                "https://api.stackexchange.com/2.3/search/advanced",
                params=params,
                timeout=30
            )
            
            if r.status_code != 200:
                return results
            
            data = r.json()
            
            for it in data.get("items", []):
                results.append({
                    "source": self.id,
                    "title": it.get("title"),
                    "url": it.get("link"),
                    "snippet": it.get("body"),
                    "search_query": query,
                    "is_answered": it.get("is_answered"),
                    "score": it.get("score")
                })
        
        except Exception as e:
            pass  # Silent fail for search errors
        
        return self._dedupe_by_url(results)[:max_results]
