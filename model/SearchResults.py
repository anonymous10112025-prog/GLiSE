"""
SearchResults model for managing search execution results.
Stores results grouped by provider with flexible schema support.
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional


class SearchResults:
    """Represents a search execution instance with results from multiple providers."""
    
    def __init__(
        self,
        query_generation_id: str,
        intent: str,
        providers: List[str],
        instance_id: Optional[str] = None,
        filter_model: Optional[str] = None
    ):
        """
        Initialize a search results instance.
        
        Args:
            query_generation_id: ID of the QueryGeneration instance these results are from
            intent: User's search intent/description
            providers: List of provider IDs that were searched
            instance_id: Unique identifier (auto-generated if not provided)
            filter_model: Name of the ML model used for filtering (if any)
        """
        self.query_generation_id = query_generation_id
        self.intent = intent
        self.providers = providers
        self.filter_model = filter_model
        
        # Generate unique instance ID: datetime + 10 chars from description (no filter suffix)
        if instance_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_intent = re.sub(r'[^a-zA-Z0-9]', '', intent)[:10]
            
            if clean_intent:
                self.instance_id = f"{timestamp}_{clean_intent}_results"
            else:
                import random
                random_num = random.randint(1000, 9999)
                self.instance_id = f"{timestamp}_{random_num}_results"
        else:
            self.instance_id = instance_id
        
        # Storage for results (provider_id -> list of result dicts)
        # Each provider can have different schema
        self.results: Dict[str, List[Dict]] = {}
        
        # Storage for queries used (provider_id -> list of query strings)
        self.queries: Dict[str, List[str]] = {}
        
        # Metadata
        self.created_at = datetime.now().isoformat()
        self.total_results = 0
        self.queries_executed: Dict[str, int] = {}  # provider_id -> number of queries
    
    def add_results(self, provider_id: str, results: List[Dict], queries: List[str] = None, queries_count: int = 0):
        """
        Add search results for a specific provider.
        
        Args:
            provider_id: Provider ID
            results: List of result dictionaries (flexible schema per provider)
            queries: List of query strings used for this provider (optional)
            queries_count: Number of queries executed for this provider (auto-computed if queries provided)
        """
        self.results[provider_id] = results
        
        # Store queries if provided
        if queries is not None:
            self.queries[provider_id] = queries
            self.queries_executed[provider_id] = len(queries)
        else:
            self.queries_executed[provider_id] = queries_count
            
        self._update_total()
    
    def _update_total(self):
        """Update total results count."""
        self.total_results = sum(len(results) for results in self.results.values())
    
    def add_filter_metadata(self, provider_id: str, result_index: int, filter_model: str, score: float):
        """
        Add filter metadata to a specific result.
        
        Args:
            provider_id: Provider ID
            result_index: Index of the result in the provider's results list
            filter_model: Name of the filter model
            score: Relevance score/probability (0.0 to 1.0)
        """
        if provider_id not in self.results or result_index >= len(self.results[provider_id]):
            return
        
        result = self.results[provider_id][result_index]
        
        # Initialize _filters dict if not exists
        if "_filters" not in result:
            result["_filters"] = {}
        
        # Add filter metadata (save the score/probability)
        result["_filters"][filter_model] = score
    
    def get_filtered_results(self, filter_model: str, threshold: float = 0.5) -> Dict[str, List[Dict]]:
        """
        Get filtered results for a specific filter model.
        Returns results with score >= threshold, sorted by score (descending).
        
        Args:
            filter_model: Name of the filter model
            threshold: Minimum score to consider relevant (default 0.5)
            
        Returns:
            Dict mapping provider_id to list of relevant results (sorted by score)
        """
        filtered = {}
        
        for provider_id, results in self.results.items():
            filtered_provider_results = []
            
            for result in results:
                # Check if result has filter metadata for this model
                if "_filters" in result and filter_model in result["_filters"]:
                    score = result["_filters"][filter_model]
                    
                    # Keep if score >= threshold
                    if isinstance(score, (int, float)) and score >= threshold:
                        # Create a copy with score promoted to top level
                        result_copy = result.copy()
                        result_copy["relevant_score"] = score
                        result_copy["relevant"] = True
                        filtered_provider_results.append(result_copy)
            
            # Sort by score (highest first)
            if filtered_provider_results:
                filtered_provider_results.sort(key=lambda x: x.get("relevant_score", 0), reverse=True)
                filtered[provider_id] = filtered_provider_results
        
        return filtered
    
    def get_available_filters(self) -> List[str]:
        """
        Get list of filter models that have been applied to these results.
        
        Returns:
            List of filter model names that have metadata in results
        """
        filters = set()
        for provider_results in self.results.values():
            for result in provider_results:
                if "_filters" in result:
                    filters.update(result["_filters"].keys())
        return sorted(list(filters))
    
    def has_filter(self, filter_model: str) -> bool:
        """
        Check if a specific filter has been applied to these results.
        
        Args:
            filter_model: Name of the filter model
            
        Returns:
            True if filter metadata exists for this model
        """
        return filter_model in self.get_available_filters()
    
    def get_storage_path(self, storage_root: str = "storage") -> str:
        """
        Get the directory path for this search results instance.
        
        Args:
            storage_root: Root storage directory
            
        Returns:
            Absolute path to instance directory
        """
        # Check if storage_root is already an absolute path
        if os.path.isabs(storage_root):
            # Use absolute path directly
            storage_dir = os.path.join(storage_root, self.instance_id)
        else:
            # Treat as relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_dir = os.path.join(project_root, storage_root, self.instance_id)
        return storage_dir
    
    def save(self, storage_root: str = "storage", folder_name: str = None):
        """
        Save this search results instance to disk.
        
        Creates a directory under storage_root with the instance_id as name,
        saves info.json with metadata and results file based on filter type.
        
        Args:
            storage_root: Root storage directory
            folder_name: Optional custom folder name (uses instance_id if None)
        """
        # Use custom folder name if provided, otherwise use instance_id
        save_id = folder_name if folder_name else self.instance_id
        
        # Temporarily swap instance_id for path calculation
        original_id = self.instance_id
        self.instance_id = save_id
        storage_path = self.get_storage_path(storage_root)
        self.instance_id = original_id
        
        # Create directory if it doesn't exist
        os.makedirs(storage_path, exist_ok=True)
        
        # Update info.json if it exists, otherwise create it
        info_path = os.path.join(storage_path, "info.json")
        if os.path.exists(info_path):
            # Load existing info to preserve original creation time and other metadata
            with open(info_path, "r", encoding="utf-8") as f:
                existing_info = json.load(f)
            # Keep original created_at
            created_at = existing_info.get("created_at", self.created_at)
        else:
            created_at = self.created_at
        
        # Prepare info data
        info_data = {
            "instance_id": save_id,
            "created_at": created_at,
            "query_generation_id": self.query_generation_id,
            "intent": self.intent,
            "providers": self.providers,
            "total_results": self.total_results,
            "queries_executed": self.queries_executed,
            "filter_model": self.filter_model
        }
        
        # Save info.json
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info_data, f, indent=2, ensure_ascii=False)
        
        # Always save to results.json (single file with embedded filter metadata)
        results_filename = "results.json"
        
        # Save results file
        results_path = os.path.join(storage_path, results_filename)
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Save queries.json if queries exist (only once, not per filter)
        if self.queries:
            queries_path = os.path.join(storage_path, "queries.json")
            if not os.path.exists(queries_path):
                with open(queries_path, "w", encoding="utf-8") as f:
                    json.dump(self.queries, f, indent=2, ensure_ascii=False)
        
        return storage_path
    
    @staticmethod
    def load(instance_id: str, storage_root: str = "storage", filter_model: Optional[str] = None) -> "SearchResults":
        """
        Load a search results instance from disk.
        
        Args:
            instance_id: Unique identifier of the instance
            storage_root: Root storage directory
            filter_model: Specific filter to load (None for unfiltered results.json)
            
        Returns:
            SearchResults instance loaded from disk
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        storage_path = os.path.join(project_root, storage_root, instance_id)
        
        # Load info.json
        info_path = os.path.join(storage_path, "info.json")
        with open(info_path, "r", encoding="utf-8") as f:
            info_data = json.load(f)
        
        # Create instance
        instance = SearchResults(
            query_generation_id=info_data["query_generation_id"],
            intent=info_data["intent"],
            providers=info_data["providers"],
            instance_id=info_data["instance_id"],
            filter_model=filter_model if filter_model else info_data.get("filter_model")
        )
        
        instance.created_at = info_data["created_at"]
        instance.total_results = info_data.get("total_results", 0)
        instance.queries_executed = info_data.get("queries_executed", {})
        
        # Load results.json (single file with embedded filter metadata)
        results_filename = "results.json"
        results_path = os.path.join(storage_path, results_filename)
        
        if os.path.exists(results_path):
            with open(results_path, "r", encoding="utf-8") as f:
                all_results = json.load(f)
            
            # If a specific filter is requested, use get_filtered_results
            if filter_model:
                # Temporarily store all results to extract filtered ones
                temp_instance = SearchResults(
                    query_generation_id=instance.query_generation_id,
                    intent=instance.intent,
                    providers=instance.providers,
                    instance_id=instance.instance_id
                )
                temp_instance.results = all_results
                instance.results = temp_instance.get_filtered_results(filter_model)
            else:
                instance.results = all_results
        
        # Load queries.json if it exists
        queries_path = os.path.join(storage_path, "queries.json")
        if os.path.exists(queries_path):
            with open(queries_path, "r", encoding="utf-8") as f:
                instance.queries = json.load(f)
        
        return instance
    
    @staticmethod
    def list_instances(storage_root: str = "storage") -> List[str]:
        """
        List all saved search results instance IDs.
        
        Args:
            storage_root: Root storage directory
            
        Returns:
            List of instance IDs (only those ending with '_results')
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        storage_path = os.path.join(project_root, storage_root)
        
        if not os.path.exists(storage_path):
            return []
        
        # Return all subdirectories ending with '_results'
        return [
            d for d in os.listdir(storage_path)
            if os.path.isdir(os.path.join(storage_path, d)) and d.endswith('_results')
        ]
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "instance_id": self.instance_id,
            "created_at": self.created_at,
            "query_generation_id": self.query_generation_id,
            "intent": self.intent,
            "providers": self.providers,
            "total_results": self.total_results,
            "queries_executed": self.queries_executed,
            "filter_model": self.filter_model,
            "queries": self.queries,
            "results": self.results
        }
