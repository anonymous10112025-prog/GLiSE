"""
Base class for Grey Literature providers.
Defines the interface and common functionality for all search providers.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class GLProvider(ABC):
    """Abstract base class for Grey Literature providers."""
    
    def __init__(self):
        """Initialize a Grey Literature provider."""
        self.id = self.get_id()
        self.name = self.get_name()
        self.prompt_template_path = self.get_prompt_template_path()
    
    @classmethod
    @abstractmethod
    def get_id(cls) -> str:
        """
        Get the unique identifier for this provider.
        
        Returns:
            Provider ID (e.g., "so", "gh_code", "google")
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """
        Get the display name for this provider.
        
        Returns:
            Provider name (e.g., "Stack Overflow", "GitHub Code Search")
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_prompt_template_path(cls) -> str:
        """
        Get the path to the prompt template file.
        
        Returns:
            Relative path to prompt template (e.g., "data/GLProvidersPrompts/GooglePrompt.txt")
        """
        pass
    
    @classmethod
    def are_all_keys_set(cls) -> bool:
        """
        Check if all required API keys are configured for this provider.
        
        Default implementation returns True (no API keys required).
        Providers should override this method to check their specific requirements.
        
        Returns:
            True if all required API keys are set, False otherwise
        """
        return True
    
    @classmethod
    def get_filtering_strategy(cls):
        """
        Get the filtering strategy for this provider.
        
        Default implementation returns None (no filtering available).
        Providers that support ML filtering should override this method.
        
        Returns:
            FilteringStrategy instance or None if filtering not supported
        """
        return None
    
    @abstractmethod
    def search(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Execute a search query on this provider.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of result dictionaries with keys like:
                - source: Provider identifier
                - title: Result title
                - url: Result URL
                - snippet: Result snippet/description
                - search_query: Original query
                - (other provider-specific fields)
        """
        pass
    
    def _extract_queries(self, json_str: str) -> List[str]:
        """
        Extract queries array from LLM JSON response.
        
        Args:
            json_str: JSON string from LLM containing {"queries": [...]}
            
        Returns:
            List of query strings
            
        Raises:
            ValueError: If JSON is invalid or missing queries field
        """
        try:
            data = json.loads(json_str)
            queries = data.get("queries")
            if queries is None:
                raise ValueError("JSON response missing 'queries' field")
            return queries
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}")
    
    def _languages_instruction(self, langs: Optional[List[str]]) -> str:
        """
        Generate language instruction string for query generation.
        
        Args:
            langs: List of language codes, or None/"all" for no restriction
            
        Returns:
            Instruction string for language qualifiers
        """
        if not langs or langs == ["all"]:
            return "No language restriction. Do NOT add any language: qualifier unless inherently required."
        return "Use language qualifiers among: " + ", ".join(sorted(set(langs)))
    
    def generate_queries(
        self,
        llm_provider,
        intent: str,
        queries_number: int,
        languages: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate search queries for this provider using an LLM.
        
        Args:
            llm_provider: LLMProvider instance to use for generation
            intent: Search intent or topic description
            queries_number: Total number of queries to generate
            languages: List of language codes to restrict search, or None for all
            
        Returns:
            List of generated search query strings
        """
        # Load prompt template - convert to absolute path if needed
        template_path = self.prompt_template_path
        if not os.path.isabs(template_path):
            # Get the project root (parent of 'model' folder)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_path = os.path.join(project_root, template_path)
        
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        # Handle Google-specific doc/gray split (auto-calculate)
        if self.id == "google":
            documentation_queries_number = queries_number // 2
            gl_queries_number = queries_number - documentation_queries_number
            template = template.replace("{doc_n}", str(documentation_queries_number))
            template = template.replace("{gray_n}", str(gl_queries_number))
        
        # Format prompt
        instr = self._languages_instruction(languages)
        prompt = template.format(
            intent=intent,
            n=queries_number,
            languages_instruction=instr
        )
        
        # Call LLM and extract queries
        llm_response = llm_provider.call_llm(prompt)
        return self._extract_queries(llm_response)
        
    def _dedupe_by_url(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate results based on URL."""
        seen = set()
        out = []
        for it in items:
            url = it.get("url")
            if url and url not in seen:
                seen.add(url)
                out.append(it)
        return out
    
    def __str__(self) -> str:
        return f"{self.name} ({self.id})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id='{self.id}' name='{self.name}'>"
