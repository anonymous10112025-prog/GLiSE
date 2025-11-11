"""
OpenAI Tier information management.
"""

import json
import os
from typing import List, Dict, Optional


def get_tiers_data() -> List[Dict]:
    """
    Load OpenAI tier information from data.json.
    
    Returns:
        List of tier dictionaries
    """
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data',
        'data.json'
    )
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('openai_tiers', [])
    except Exception as e:
        print(f"Error loading tiers data: {e}")
        return []


def get_tier_choices() -> List[str]:
    """
    Get list of tier display names for UI dropdowns.
    
    Returns:
        List of formatted tier names (e.g., "Tier 1 - After first successful payment")
    """
    tiers = get_tiers_data()
    choices = []
    
    for tier in tiers:
        # Format: "Tier Name - Description"
        choice = f"{tier['name']} - {tier['description']}"
        choices.append(choice)
    
    return choices


def get_tier_by_id(tier_id: str) -> Optional[Dict]:
    """
    Get tier information by ID.
    
    Args:
        tier_id: Tier ID (e.g., 'tier_1')
    
    Returns:
        Tier dictionary or None if not found
    """
    tiers = get_tiers_data()
    for tier in tiers:
        if tier['id'] == tier_id:
            return tier
    return None


def get_tier_id_from_choice(choice: str) -> str:
    """
    Extract tier ID from a UI choice string.
    
    Args:
        choice: Formatted choice string (e.g., "Tier 1 - After first successful payment")
    
    Returns:
        Tier ID (e.g., 'tier_1')
    """
    tiers = get_tiers_data()
    for tier in tiers:
        choice_format = f"{tier['name']} - {tier['description']}"
        if choice_format == choice:
            return tier['id']
    
    # Default fallback
    return "tier_1"


def get_choice_from_tier_id(tier_id: str) -> str:
    """
    Get UI choice string from tier ID.
    
    Args:
        tier_id: Tier ID (e.g., 'tier_1')
    
    Returns:
        Formatted choice string
    """
    tier = get_tier_by_id(tier_id)
    if tier:
        return f"{tier['name']} - {tier['description']}"
    
    # Default fallback
    return "Free Tier - Free trial with limited usage"
