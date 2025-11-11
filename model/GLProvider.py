"""
Grey Literature Provider - Backward compatibility layer.

This module maintains backward compatibility with existing code while
delegating to the new provider architecture in model.providers.
"""

from typing import Dict, List, Optional
from model.providers import get_provider, get_all_providers, GLProvider as BaseGLProvider


class GLProvider:
    """
    Backward compatibility wrapper for Grey Literature providers.
    
    This class maintains the same interface as before but delegates to the new
    provider architecture. Use model.providers directly for new code.
    """
    
    def __init__(self, id: str, name: str, prompt_template_path: str = ""):
        """
        Initialize a Grey Literature provider.
        
        Args:
            id: Unique identifier for the provider
            name: Name of the provider
            prompt_template_path: Path to the prompt template file
        """
        self.id = id
        self.name = name
        self.prompt_template_path = prompt_template_path
        self._provider_instance = None
    
    def _get_provider_instance(self) -> BaseGLProvider:
        """Get the actual provider instance (lazy loaded)."""
        if self._provider_instance is None:
            try:
                self._provider_instance = get_provider(self.id)
            except ValueError:
                # Fallback for unknown providers - create a dummy instance
                # This shouldn't happen in production but provides safety
                pass
        return self._provider_instance
    
    def generateQueries(
        self,
        llm_provider,
        intent: str,
        queries_number: int,
        languages: Optional[List[str]]
    ) -> List[str]:
        """
        Generate search queries for grey literature using an LLM.
        
        Args:
            llm_provider: LLMProvider instance to use for generation
            intent: Search intent or topic description
            queries_number: Number of queries to generate (Google auto-splits 50/50)
            languages: List of language codes to restrict search, or None for all
            
        Returns:
            List of generated search query strings
        """
        provider = self._get_provider_instance()
        if provider:
            return provider.generate_queries(
                llm_provider=llm_provider,
                intent=intent,
                queries_number=queries_number,
                languages=languages
            )
        return []
    
    def search(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Execute a search query on this provider.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of result dictionaries
        """
        provider = self._get_provider_instance()
        if provider:
            return provider.search(query, max_results)
        return []
    
    @staticmethod
    def get_providers_list(providers_path: str = "data/data.json") -> Dict[str, "GLProvider"]:
        """
        Get all available Grey Literature providers.
        
        Args:
            providers_path: Path to the JSON configuration file (ignored in new architecture)
            
        Returns:
            Dictionary mapping provider IDs to GLProvider instances
        """
        # Get all providers from the new architecture
        providers = get_all_providers()
        
        # Wrap them in the old GLProvider class for backward compatibility
        result = {}
        for provider_id, provider in providers.items():
            wrapped = GLProvider(
                id=provider.id,
                name=provider.name,
                prompt_template_path=provider.prompt_template_path
            )
            wrapped._provider_instance = provider
            result[provider_id] = wrapped
        
        return result
    
    @staticmethod
    def get_provider_id_by_name(name: str, providers_path: str = "data/data.json") -> Optional[str]:
        """
        Get the provider ID by its name.
        
        Args:
            name: Name of the provider
            providers_path: Path to the JSON configuration file (ignored in new architecture)
            
        Returns:
            Provider ID if found, else None
        """
        providers = GLProvider.get_providers_list(providers_path)
        for pid, provider in providers.items():
            if provider.name == name:
                return pid
        return None
