"""
Filtering strategy for StackOverflow.
"""

import numpy as np
from typing import List, Dict, Tuple
from model.filtering.base_strategy import FilteringStrategy


class StackOverflowFilteringStrategy(FilteringStrategy):
    """Filtering strategy for StackOverflow posts."""
    
    def filter_small(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Filter using text-embedding-3-small model."""
        dimensions = 512
        embed_model = "text-embedding-3-small"
        ml_model = self.load_model(
            "models-ml/stackoverflow/text-embedding-3-small/GaussianNB-overlap_product.joblib"
        )
        
        # Prepare texts for embedding
        texts_to_embed = []
        for so_post_infos in results:
            texts_to_embed.append(self.safe_non_empty_string_field_access("search_intent", so_post_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("title", so_post_infos))
            texts_to_embed.append(
                self.clean_html_for_embedding(
                    self.safe_non_empty_string_field_access("snippet", so_post_infos)
                )
            )
            texts_to_embed.append(self.safe_non_empty_string_field_access("url", so_post_infos))
        
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
            url_embedding = all_embeddings[index + 3]
            
            # Overlap / Product
            overlap_products = (
                self.overlap_product_vector(search_intent_embedding, title_embedding).tolist() +
                self.overlap_product_vector(search_intent_embedding, snippet_embedding).tolist() +
                self.overlap_product_vector(search_intent_embedding, url_embedding).tolist()
            )
            
            ml_inputs.append(overlap_products)
            index += 4
        
        # Predict
        x_for_pred = np.array(ml_inputs)
        prediction = ml_model.predict(x_for_pred)
        proba_pred = ml_model.predict_proba(x_for_pred)[:, 1]
        
        # Separate and sort results
        return self._separate_and_sort_results(results, prediction, proba_pred)
    
    def filter_large(self, results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Filter using text-embedding-3-large model."""
        dimensions = 1024
        embed_model = "text-embedding-3-large"
        ml_model = self.load_model(
            "models-ml/stackoverflow/text-embedding-3-large/Ridge-differences.joblib"
        )
        
        # Prepare texts for embedding
        texts_to_embed = []
        for so_post_infos in results:
            texts_to_embed.append(self.safe_non_empty_string_field_access("search_intent", so_post_infos))
            texts_to_embed.append(self.safe_non_empty_string_field_access("title", so_post_infos))
            texts_to_embed.append(
                self.clean_html_for_embedding(
                    self.safe_non_empty_string_field_access("snippet", so_post_infos)
                )
            )
            texts_to_embed.append(self.safe_non_empty_string_field_access("url", so_post_infos))
        
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
            url_embedding = all_embeddings[index + 3]
            
            # Differences
            differences = (
                self.difference_vector(search_intent_embedding, title_embedding).tolist() +
                self.difference_vector(search_intent_embedding, snippet_embedding).tolist() +
                self.difference_vector(search_intent_embedding, url_embedding).tolist()
            )
            
            ml_inputs.append(differences)
            index += 4
        
        # Predict
        x_for_pred = np.array(ml_inputs)
        prediction = ml_model.predict(x_for_pred)
        decision_scores = ml_model.decision_function(x_for_pred)  # Ridge uses decision function
        
        # Separate and sort results (different sorting for Ridge)
        return self._separate_and_sort_results_ridge(results, prediction, decision_scores)
    
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
    
    @staticmethod
    def _separate_and_sort_results_ridge(
        results: List[Dict],
        predictions,
        decision_scores
    ) -> Tuple[List[Dict], List[Dict]]:
        """Separate results for Ridge classifier (uses decision scores instead of probabilities)."""
        relevant_list = []
        irrelevant_list = []
        
        for result, pred_label, score in zip(results, predictions, decision_scores):
            entry = result.copy()
            entry["relevant"] = bool(pred_label)
            entry["relevant_score"] = float(score)
            
            if pred_label == 1:
                relevant_list.append(entry)
            else:
                irrelevant_list.append(entry)
        
        # For TRUE predictions: larger margin => more confident => descending
        relevant_list.sort(key=lambda x: x["relevant_score"], reverse=True)
        
        # For FALSE predictions: smaller (more negative) margin => more confident => ascending
        irrelevant_list.sort(key=lambda x: x["relevant_score"])
        
        return relevant_list, irrelevant_list
