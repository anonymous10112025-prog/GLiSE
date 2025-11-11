import json
import os
import tiktoken

DEFAULT_OVERHEAD_PER_INPUT = 150  # https://github.com/timescale/pgai/issues/728


def get_tier_info(tier_id: str = None):
    """
    Get OpenAI tier information from data.json.
    
    Args:
        tier_id: Tier ID (e.g., 'tier_1', 'tier_2'). If None, uses setting or default.
    
    Returns:
        Dictionary with tier information including tokens_per_minute
    """
    # Import here to avoid circular dependency
    from model.Settings import get_settings
    
    # Get tier from settings if not specified
    if tier_id is None:
        settings = get_settings()
        tier_id = settings.get('OPENAI_TIER', 'free')
    
    # Load tier data from data.json
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'data',
        'data.json'
    )
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tiers = data.get('openai_tiers', [])
        for tier in tiers:
            if tier['id'] == tier_id:
                return tier
    except Exception as e:
        print(f"Error loading tier info: {e}")
    
    # Default fallback (Free Tier)
    return {
        "id": "free",
        "name": "Free Tier",
        "tokens_per_minute": 200000,
        "requests_per_minute": 500,
        "requests_per_day": 10000
    }


def get_safe_max_tokens_req(tier_id: str = None):
    """
    Calculate safe maximum tokens per request based on tier.
    Uses 15% of tokens_per_minute as safe limit.
    
    Args:
        tier_id: OpenAI tier ID. If None, uses current setting.
    
    Returns:
        Safe maximum tokens per request
    """
    tier_info = get_tier_info(tier_id)
    tokens_per_minute = tier_info.get('tokens_per_minute', 200000)
    
    # Use 15% of TPM as safe limit per request to avoid rate limiting
    safe_max = int(tokens_per_minute * 0.15)
    
    return safe_max


def get_overhead_per_input():
    """
    Get the overhead tokens per input from settings.
    
    Returns:
        Overhead tokens per input
    """
    from model.Settings import get_settings
    settings = get_settings()
    return settings.get('EMBEDDING_OVERHEAD_PER_INPUT', DEFAULT_OVERHEAD_PER_INPUT)

def truncate_to_X_tokens(text: str, model: str = "gpt-4o", truncate_limit: int = 8100):
    """
    Count tokens using tiktoken, truncate to <=8100 tokens, and return:
      - truncated or original text
      - number of tokens in returned text
    """

    # Load encoding for the given model
    encoding = tiktoken.encoding_for_model(model)

    # Encode text -> tokens
    tokens = encoding.encode(text)
    original_count = len(tokens)

    # If ≤truncate_limit tokens → return original
    if original_count <= truncate_limit:
        return text, original_count

    # Else → truncate
    # truncated_tokens = tokens[:(truncate_limit-1)]  # keep first 8099
    ellipsis_tokens = encoding.encode("...")
    ellipsis_tokens_nbr = len(ellipsis_tokens)
    truncated_tokens = tokens[:(truncate_limit-ellipsis_tokens_nbr)]

    # Add ellipsis (may be >1 token depending on tokenizer, but that's fine)
    final_tokens = truncated_tokens + ellipsis_tokens

    # Decode back to string
    text_out = encoding.decode(final_tokens)

    # Count returned tokens
    returned_count = len(final_tokens)

    return text_out, returned_count


def text_batches_to_send(texts: list[str], model: str = "gpt-4o", tier_id: str = None):
    """
    Group texts into batches that fit within tier limits.
    
    Args:
        texts: List of texts to batch
        model: Model name for tokenization
        tier_id: OpenAI tier ID. If None, uses current setting.
    
    Returns:
        List of text batches
    """
    # Get tier-specific limits
    safe_max_tokens = get_safe_max_tokens_req(tier_id)
    overhead_per_input = get_overhead_per_input()
    
    tokens_count = 0
    grouped_texts = []
    text_group = []
    
    for text in texts:
        adj_text, adj_text_token_count = truncate_to_X_tokens(text=text, model=model)

        if (tokens_count + adj_text_token_count + overhead_per_input) > safe_max_tokens:
            grouped_texts.append(text_group.copy())
            text_group = [adj_text]
            tokens_count = adj_text_token_count + overhead_per_input
        else:
            text_group.append(adj_text)
            tokens_count += adj_text_token_count + overhead_per_input

    if len(text_group) > 0:
        grouped_texts.append(text_group.copy())

    return grouped_texts