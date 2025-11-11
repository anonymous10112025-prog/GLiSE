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
    
    def search(self, query: str, max_results: int = 50, from_date: str = None, to_date: str = None) -> List[Dict]:
        """
        Execute a Google search using Google Custom Search Engine API.
        
        Google snippets include dates in format "Aug 12, 2024 ..." which we extract
        and use for client-side filtering.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            from_date: Optional start date filter in YYYY-MM-DD format
            to_date: Optional end date filter in YYYY-MM-DD format
            
        Returns:
            List of search result dictionaries
        """
        settings = get_settings()
        sleep_between = float(settings.get('SEARCH_SLEEP_BETWEEN', 1.0))
        
        # Fetch results from Google
        results = self._search_google_cse(query, max_results, sleep_between)
        
        print(f"[Google] Fetched {len(results)} results from API")
        
        # Filter by date using snippet dates (e.g., "Aug 12, 2024 ...")
        if (from_date or to_date) and results:
            print(f"[Google] Applying date filter: from={from_date}, to={to_date}")
            from controller.date_helpers import filter_google_results_by_date
            filtered_results = filter_google_results_by_date(results, from_date, to_date)
            print(f"[Google] After filtering: {len(filtered_results)} results remain")
            results = filtered_results
        
        return results
    
    def _search_google_cse(self, query: str, max_results: int, sleep_between: float) -> List[Dict]:
        """
        Search using Google Custom Search Engine API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            sleep_between: Seconds to sleep between API calls
        """
        settings = get_settings()
        api_key = settings.get('GOOGLE_API_KEY')
        cx = settings.get('GOOGLE_CSE_CX')
        
        if not api_key or not cx:
            print("[Google API] Missing API key or CX ID")
            return []
        
        results = []
        start = 1
        
        print(f"[Google API] Starting search for query: '{query}', max_results={max_results}")
        
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
            
            print(f"[Google API] Request #{(start-1)//10 + 1}: start={start}, num={params['num']}")
            
            try:
                r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=30)
                
                print(f"[Google API] Response status: {r.status_code}")
                
                # Check status code
                if r.status_code != 200:
                    # Try to parse error message
                    try:
                        error_data = r.json()
                        error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                        print(f"[Google API] Error: {error_msg}")
                        print(f"[Google API] Full error: {error_data}")
                    except:
                        print(f"[Google API] HTTP Error {r.status_code}, could not parse error message")
                    break
                
                data = r.json()
                
                items = data.get("items", [])
                
                print(f"[Google API] Received {len(items)} items in this batch")
                
                # Check if no items but response is valid
                if not items:
                    print(f"[Google API] No more items, stopping pagination")
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
                    print(f"[Google API] No next page available")
                    break
                
                start += 10
                time.sleep(sleep_between)
                
            except requests.exceptions.RequestException as e:
                print(f"[Google API] Request exception: {e}")
                break
            except Exception as e:
                print(f"[Google API] Unexpected exception: {e}")
                import traceback
                traceback.print_exc()
                break
        
        print(f"[Google API] Total results collected: {len(results)}")
        deduped = self._dedupe_by_url(results)
        print(f"[Google API] After deduplication: {len(deduped)}")
        return deduped[:max_results]
    
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
