"""
Google Search provider implementation.
"""

import os
import time
import requests
from typing import List, Dict, Optional, TYPE_CHECKING

from model.providers.base_provider import GLProvider
from model.Settings import get_settings

if TYPE_CHECKING:
    from model.filtering.base_strategy import FilteringStrategy


class GoogleProvider(GLProvider):
    """Provider for Google Custom Search Engine API."""
    
    @classmethod
    def get_id(cls) -> str:
        return "google"
    
    @classmethod
    def get_name(cls) -> str:
        return "Google Custom Search API"
    
    @classmethod
    def get_prompt_template_path(cls) -> str:
        return "data/GLProvidersPrompts/GooglePrompt.txt"
    
    def get_filtering_strategy(self) -> Optional["FilteringStrategy"]:
        """Get the filtering strategy for Google search results."""
        from model.filtering.google_strategy import GoogleFilteringStrategy
        return GoogleFilteringStrategy()
    
    @classmethod
    def are_all_keys_set(cls) -> bool:
        """
        Check if Google provider has required API keys.
        Requires GOOGLE_API_KEY AND GOOGLE_CSE_CX.
        
        Returns:
            True if Google CSE credentials are present
        """
        settings = get_settings()
        
        # Check if Google CSE credentials are set
        return bool(settings.get('GOOGLE_API_KEY')) and bool(settings.get('GOOGLE_CSE_CX'))
    
    def search(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Execute a Google search using Google Custom Search Engine API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of search result dictionaries
        """
        settings = get_settings()
        sleep_between = float(settings.get('SEARCH_SLEEP_BETWEEN', 1.0))
        
        return self._search_google_cse(query, max_results, sleep_between)
    
    def _search_google_cse(self, query: str, max_results: int, sleep_between: float) -> List[Dict]:
        """Search using Google Custom Search Engine API."""
        settings = get_settings()
        api_key = settings.get('GOOGLE_API_KEY')
        cx = settings.get('GOOGLE_CSE_CX')
        
        if not api_key or not cx:
            return []
        
        results = []
        start = 1
        
        while len(results) < max_results and start <= 91:
            params = {
                "key": api_key,
                "cx": cx,
                "q": query,
                "num": min(10, max_results - len(results)),
                "start": start,
                "gl": "us",
                "hl": "en",
                "fields": "items(title,link,snippet,htmlSnippet,pagemap)"
            }
            
            try:
                r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=30)
                
                # Check status code
                if r.status_code != 200:
                    # Try to parse error message
                    try:
                        error_data = r.json()
                        error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                    except:
                        pass
                    break
                
                data = r.json()
                
                items = data.get("items", [])
                
                # Check if no items but response is valid
                if not items:
                    break
                
                for it in items:
                    pagemap = it.get("pagemap", {})
                    results.append({
                        "source": self.id,
                        "title": it.get("title"),
                        "url": it.get("link"),
                        "snippet": it.get("snippet"),
                        "html_snippet": it.get("htmlSnippet"),
                        "meta_desc": self._get_metatag_description(pagemap),
                        "schema_desc": self._get_schema_description(pagemap),
                        "search_query": query,
                    })
                
                if not items or "nextPage" not in data.get("queries", {}):
                    break
                
                start += 10
                time.sleep(sleep_between)
                
            except requests.exceptions.RequestException as e:
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                break
        
        return self._dedupe_by_url(results)[:max_results]
    
    def _get_metatag_description(self, pagemap: dict) -> str:
        """Extract description from metatags in pagemap."""
        if not pagemap:
            return ""
        
        metatags = pagemap.get("metatags", [])
        descriptions = []
        
        for tag in metatags:
            for key, value in tag.items():
                if "description" in key.lower():
                    descriptions.append(value)
        
        return " ".join(descriptions)
    
    def _get_schema_description(self, pagemap: dict) -> str:
        """Extract description from schema data in pagemap."""
        if not pagemap:
            return ""
        
        descriptions = []
        for key, entries in pagemap.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and "description" in entry:
                    descriptions.append(entry["description"])
        
        return " ".join(descriptions)
