import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
import random


class QueryGeneration:
    """Represents a single query generation instance with all parameters and results."""
    
    def __init__(
        self,
        model: str,
        system_prompt: str,
        temperature: float,
        intent: str,
        sources_ids: List[str],
        languages: List[str],
        general_n: int,
        instance_id: Optional[str] = None
    ):
        """
        Initialize a query generation instance.
        
        Args:
            model: LLM model name
            system_prompt: System prompt for the LLM
            temperature: Temperature setting
            intent: User's search intent/description
            sources_ids: List of source provider IDs
            languages: List of language codes
            general_n: Number of queries per platform (Google auto-splits 50/50)
            instance_id: Unique identifier (auto-generated if not provided)
        """
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.intent = intent
        self.sources_ids = sources_ids
        self.languages = languages
        self.general_n = general_n
        
        # Generate unique instance ID: datetime + 10 chars from description
        if instance_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Clean the intent: remove spaces and special characters, take first 10 chars
            clean_intent = re.sub(r'[^a-zA-Z0-9]', '', intent)[:10]
            if clean_intent:
                self.instance_id = f"{timestamp}_{clean_intent}"
            else:
                # Fallback to random number if no valid characters
                random_num = random.randint(1000, 9999)
                self.instance_id = f"{timestamp}_{random_num}"
        else:
            self.instance_id = instance_id
        
        # Storage for results (source_id -> list of queries)
        self.results: Dict[str, List[str]] = {}
        
        # Timestamp
        self.created_at = datetime.now().isoformat()
    
    def add_results(self, source_id: str, queries: List[str]):
        """
        Add generated queries for a specific source.
        
        Args:
            source_id: Provider ID
            queries: List of generated query strings
        """
        self.results[source_id] = queries
    
    def get_storage_path(self, storage_root: str = "storage") -> str:
        """
        Get the directory path for this query generation instance.
        
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
        Save this query generation instance to disk.
        
        Creates a directory under storage_root with the instance_id as name,
        saves info.json with metadata and queries.json with results.
        
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
        
        # Prepare info data
        info_data = {
            "instance_id": save_id,
            "created_at": self.created_at,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "intent": self.intent,
            "sources_ids": self.sources_ids,
            "languages": self.languages,
            "general_n": self.general_n
        }
        
        # Save info.json
        info_path = os.path.join(storage_path, "info.json")
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info_data, f, indent=2, ensure_ascii=False)
        
        # Save queries.json
        queries_path = os.path.join(storage_path, "queries.json")
        with open(queries_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        return storage_path
    
    @staticmethod
    def load(instance_id: str, storage_root: str = "storage") -> "QueryGeneration":
        """
        Load a query generation instance from disk.
        
        Args:
            instance_id: Unique identifier of the instance
            storage_root: Root storage directory
            
        Returns:
            QueryGeneration instance loaded from disk
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        storage_path = os.path.join(project_root, storage_root, instance_id)
        
        # Load info.json
        info_path = os.path.join(storage_path, "info.json")
        with open(info_path, "r", encoding="utf-8") as f:
            info_data = json.load(f)
        
        # Create instance
        instance = QueryGeneration(
            model=info_data["model"],
            system_prompt=info_data["system_prompt"],
            temperature=info_data["temperature"],
            intent=info_data["intent"],
            sources_ids=info_data["sources_ids"],
            languages=info_data["languages"],
            general_n=info_data["general_n"],
            instance_id=info_data["instance_id"]
        )
        
        instance.created_at = info_data["created_at"]
        
        # Load queries.json
        queries_path = os.path.join(storage_path, "queries.json")
        if os.path.exists(queries_path):
            with open(queries_path, "r", encoding="utf-8") as f:
                instance.results = json.load(f)
        
        return instance
    
    @staticmethod
    def list_instances(storage_root: str = "storage") -> List[str]:
        """
        List all saved query generation instance IDs.
        
        Args:
            storage_root: Root storage directory
            
        Returns:
            List of instance IDs
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        storage_path = os.path.join(project_root, storage_root)
        
        if not os.path.exists(storage_path):
            return []
        
        # Return all subdirectories
        return [
            d for d in os.listdir(storage_path)
            if os.path.isdir(os.path.join(storage_path, d))
        ]
