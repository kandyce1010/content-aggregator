def should_summarize(content_item):
    """Only summarize content that needs it"""
    # Skip if already short
    if len(content_item.get('description', '')) < 200:
        return False
    
    # Skip if already has summary
    if content_item.get('summary'):
        return False
        
    # Skip low-relevance content
    if content_item.get('relevance_score', 0) < 0.3:
        return False
        
    return True

def batch_optimize(items, max_batch_size=5):
    """Smaller batches to avoid timeouts"""
    return [items[i:i + max_batch_size] for i in range(0, len(items), max_batch_size)]
