"""
Base filtering strategy with common utilities.
"""

import os
import time
import joblib
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from openai import OpenAI
from bs4 import BeautifulSoup

from model.Settings import get_settings


class FilteringStrategy(ABC):
    """Abstract base class for filtering strategies with common utilities."""
    
    def __init__(self):
        """Initialize the filtering strategy with OpenAI client."""
        settings = get_settings()
        openai_key = settings.get('OPENAI_API_KEY')
        self.client = OpenAI(api_key=openai_key) if openai_key else None
    
    @abstractmethod
    def filter_small(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter results using text-embedding-3-small model.
        
        Args:
            results: List of result dictionaries with 'search_intent' field
            
        Returns:
            Tuple of (relevant_results, irrelevant_results)
        """
        pass
    
    @abstractmethod
    def filter_large(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter results using text-embedding-3-large model.
        
        Args:
            results: List of result dictionaries with 'search_intent' field
            
        Returns:
            Tuple of (relevant_results, irrelevant_results)
        """
        pass
    
    # ============= Common Utility Methods =============
    
    @staticmethod
    def load_model(relative_path: str):
        """
        Load a joblib model using a cross-platform relative path.
        
        Args:
            relative_path: Path relative to the model directory
            
        Returns:
            Loaded model
        """
        # Get the project root (3 levels up from model/filtering/)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base_dir, relative_path)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        return joblib.load(model_path)
    
    @staticmethod
    def safe_non_empty_string_field_access(field: str, dictionary: dict, placeholder: str = "N/A") -> str:
        """
        Safely access a string field from a dictionary.
        
        Args:
            field: Field name to access
            dictionary: Dictionary to access from
            placeholder: Default value if field is missing or empty
            
        Returns:
            Field value or placeholder
        """
        val_obtained = dictionary.get(field, placeholder)
        if not isinstance(val_obtained, str):
            return placeholder
        
        text = val_obtained.strip()
        if len(text) == 0:
            return placeholder
        return val_obtained
    
    @staticmethod
    def clean_html_for_embedding(html: str) -> str:
        """
        Clean HTML content for embedding generation.
        
        Args:
            html: HTML string
            
        Returns:
            Cleaned text
        """
        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts/styles
        for tag in soup(["script", "style"]):
            tag.decompose()
        # Extract text
        text = soup.get_text(separator=" ", strip=True)
        # Collapse multiple whitespace into single space
        import re
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def make_call_embeddings(
        self,
        texts: List[str],
        dimensions: int,
        embedding_model: str
    ) -> List[List[float]]:
        """
        Call OpenAI embeddings API with batching and token management.
        
        Args:
            texts: List of texts to embed
            dimensions: Embedding dimensions
            embedding_model: Model name
            
        Returns:
            List of embeddings
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY in settings.")
        
        # Import token utilities
        import sys
        import os
        controller_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'controller', 'judgment'
        )
        if controller_path not in sys.path:
            sys.path.insert(0, controller_path)
        
        from controller.utils_tokens import text_batches_to_send
        
        texts_batches = text_batches_to_send(texts=texts, model=embedding_model)
        
        list_embeddings = []
        
        for texts_batch in texts_batches:
            print(f"Getting the embeddings of {len(texts_batch)} strings")
            response = self.client.embeddings.create(
                model=embedding_model,
                input=texts_batch,
                encoding_format="float",
                dimensions=dimensions
            )
            
            list_embeddings.extend([d.embedding for d in response.data])
            time.sleep(1)  # Rate limiting
        
        return list_embeddings
    
    # ============= Distance Metrics =============
    
    @staticmethod
    def cosine_similarity(a, b) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm == 0:
            return 0
        return dot / norm
    
    @staticmethod
    def cosine_distance(a, b) -> float:
        """Calculate cosine distance between two vectors."""
        return 1 - FilteringStrategy.cosine_similarity(a, b)
    
    @staticmethod
    def euclidean_distance(a, b) -> float:
        """Calculate Euclidean distance between two vectors."""
        a = np.array(a)
        b = np.array(b)
        return np.linalg.norm(a - b)
    
    @staticmethod
    def l1_distance(a, b) -> float:
        """Calculate L1 (Manhattan) distance between two vectors."""
        a = np.array(a)
        b = np.array(b)
        return np.sum(np.abs(a - b))
    
    @staticmethod
    def difference_vector(a, b) -> np.ndarray:
        """Calculate element-wise absolute difference between vectors."""
        a = np.array(a)
        b = np.array(b)
        return np.abs(a - b)
    
    @staticmethod
    def overlap_product_vector(a, b) -> np.ndarray:
        """Calculate element-wise product between vectors."""
        a = np.array(a)
        b = np.array(b)
        return a * b


class NoFilteringStrategy(FilteringStrategy):
    """Strategy for providers that don't support ML filtering."""
    
    def __init__(self):
        """Initialize without OpenAI client (not needed)."""
        pass
    
    def filter_small(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Return all results as-is (no filtering available)."""
        return results, []
    
    def filter_large(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Return all results as-is (no filtering available)."""
        return results, []
