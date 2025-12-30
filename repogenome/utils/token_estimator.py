"""Token estimation utilities for context budget management."""

from typing import Any, Dict, List, Union

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count for text.
    
    Uses tiktoken if available, otherwise falls back to character-based estimation.
    
    Args:
        text: Text to estimate tokens for
        model: Model name for tiktoken encoding (default: "gpt-4")
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fall back to character-based estimation
            pass
    
    # Fallback: approximate 4 characters per token
    return len(text) // 4


def estimate_dict_tokens(data: Dict[str, Any], model: str = "gpt-4") -> int:
    """
    Estimate token count for dictionary (JSON-serialized).
    
    Args:
        data: Dictionary to estimate tokens for
        model: Model name for tiktoken encoding
        
    Returns:
        Estimated token count
    """
    import json
    
    json_str = json.dumps(data, ensure_ascii=False)
    return estimate_tokens(json_str, model)


def estimate_context_tokens(context: Dict[str, Any], model: str = "gpt-4") -> Dict[str, int]:
    """
    Estimate token counts per tier in context.
    
    Args:
        context: Context dictionary with tier_0, tier_1, tier_2, tier_3
        model: Model name for tiktoken encoding
        
    Returns:
        Dictionary mapping tier names to token counts
    """
    counts: Dict[str, int] = {}
    
    for tier in ["tier_0", "tier_1", "tier_2", "tier_3"]:
        if tier in context:
            counts[tier] = estimate_dict_tokens(context[tier], model)
    
    # Estimate metadata tokens
    if "metadata" in context:
        counts["metadata"] = estimate_dict_tokens(context["metadata"], model)
    
    counts["total"] = sum(counts.values())
    
    return counts


def truncate_to_budget(
    text: str,
    max_tokens: int,
    model: str = "gpt-4",
    suffix: str = "..."
) -> str:
    """
    Truncate text to fit within token budget.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum token count
        model: Model name for tiktoken encoding
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if not text:
        return text
    
    # Estimate tokens for suffix
    suffix_tokens = estimate_tokens(suffix, model)
    available_tokens = max(0, max_tokens - suffix_tokens)
    
    if available_tokens == 0:
        return suffix if len(text) > 0 else text
    
    # Binary search for optimal truncation point
    low = 0
    high = len(text)
    best_pos = 0
    
    while low <= high:
        mid = (low + high) // 2
        truncated = text[:mid]
        tokens = estimate_tokens(truncated, model)
        
        if tokens <= available_tokens:
            best_pos = mid
            low = mid + 1
        else:
            high = mid - 1
    
    if best_pos < len(text):
        # Try to truncate at word boundary
        if best_pos > 0:
            last_space = text.rfind(" ", 0, best_pos)
            if last_space > best_pos * 0.8:  # Only use if we keep most of the text
                best_pos = last_space
        
        return text[:best_pos] + suffix
    
    return text

