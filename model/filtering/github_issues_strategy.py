"""
Filtering strategy for GitHub Issues.
"""

import numpy as np
from typing import List, Dict, Tuple
from model.filtering.base_strategy import FilteringStrategy


class GitHubIssuesFilteringStrategy(FilteringStrategy):
    """Filtering strategy for GitHub issues."""
    
    def filter_small(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Filter using text-embedding-3-small model."""
        dimensions = 1024
        embed_model = "text-embedding-3-small"
        ml_model = self.load_model(
            "models-ml/github-issues/text-embedding-3-small/GaussianNB-distances.joblib"
        )
        
        # Prepare texts for embedding
        texts_to_embed = []
        for issue_infos in results:
            texts_to_embed.append(self.safe_non_empty_string_field_access("search_intent", issue_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("title", issue_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("snippet", issue_infos))
        
        # Get embeddings
        all_embeddings = self.make_call_embeddings(
            texts=texts_to_embed,
            dimensions=dimensions,
            embedding_model=embed_model
        )
        
        # Compute features
        ml_inputs = []
        index = 0
        for _ in results:
            search_intent_embedding = all_embeddings[index]
            title_embedding = all_embeddings[index + 1]
            snippet_embedding = all_embeddings[index + 2]
            
            # Cosine Distances
            cos_distances = [
                self.cosine_distance(search_intent_embedding, title_embedding),
                self.cosine_distance(search_intent_embedding, snippet_embedding),
            ]
            
            # Euclidean Distances
            euclidean_distances = [
                self.euclidean_distance(search_intent_embedding, title_embedding),
                self.euclidean_distance(search_intent_embedding, snippet_embedding),
            ]
            
            # L1 Distances
            l1_distances = [
                self.l1_distance(search_intent_embedding, title_embedding),
                self.l1_distance(search_intent_embedding, snippet_embedding),
            ]
            
            # All distances
            distances = cos_distances + euclidean_distances + l1_distances
            ml_inputs.append(distances)
            index += 3
        
        # Predict
        x_for_pred = np.array(ml_inputs)
        prediction = ml_model.predict(x_for_pred)
        proba_pred = ml_model.predict_proba(x_for_pred)[:, 1]
        
        # Separate and sort results
        return self._separate_and_sort_results(results, prediction, proba_pred)
    
    def filter_large(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Filter using text-embedding-3-large model."""
        dimensions = 1536
        embed_model = "text-embedding-3-large"
        ml_model = self.load_model(
            "models-ml/github-issues/text-embedding-3-large/GaussianNB-distances.joblib"
        )
        
        # Prepare texts for embedding
        texts_to_embed = []
        for issue_infos in results:
            texts_to_embed.append(self.safe_non_empty_string_field_access("search_intent", issue_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("title", issue_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("snippet", issue_infos))
        
        # Get embeddings
        all_embeddings = self.make_call_embeddings(
            texts=texts_to_embed,
            dimensions=dimensions,
            embedding_model=embed_model
        )
        
        # Compute features
        ml_inputs = []
        index = 0
        for _ in results:
            search_intent_embedding = all_embeddings[index]
            title_embedding = all_embeddings[index + 1]
            snippet_embedding = all_embeddings[index + 2]
            
            # Cosine Distances
            cos_distances = [
                self.cosine_distance(search_intent_embedding, title_embedding),
                self.cosine_distance(search_intent_embedding, snippet_embedding),
            ]
            
            # Euclidean Distances
            euclidean_distances = [
                self.euclidean_distance(search_intent_embedding, title_embedding),
                self.euclidean_distance(search_intent_embedding, snippet_embedding),
            ]
            
            # L1 Distances
            l1_distances = [
                self.l1_distance(search_intent_embedding, title_embedding),
                self.l1_distance(search_intent_embedding, snippet_embedding),
            ]
            
            # All distances
            distances = cos_distances + euclidean_distances + l1_distances
            ml_inputs.append(distances)
            index += 3
        
        # Predict
        x_for_pred = np.array(ml_inputs)
        prediction = ml_model.predict(x_for_pred)
        proba_pred = ml_model.predict_proba(x_for_pred)[:, 1]
        
        # Separate and sort results
        return self._separate_and_sort_results(results, prediction, proba_pred)
    
    @staticmethod
    def _separate_and_sort_results(
        results: List[Dict],
        predictions,
        probabilities
    ) -> Tuple[List[Dict], List[Dict]]:
        """Separate results into relevant/irrelevant and sort by probability."""
        relevant_list = []
        irrelevant_list = []
        
        for result, pred_label, pred_proba in zip(results, predictions, probabilities):
            entry = result.copy()
            entry["relevant"] = bool(pred_label)
            entry["relevant_proba"] = float(pred_proba)
            
            if pred_label == 1:
                relevant_list.append(entry)
            else:
                irrelevant_list.append(entry)
        
        # Sort by probability descending
        relevant_list.sort(key=lambda x: x["relevant_proba"], reverse=True)
        irrelevant_list.sort(key=lambda x: x["relevant_proba"], reverse=True)
        
        return relevant_list, irrelevant_list
