# Content Summarization Module

This module provides functionality to summarize content using Amazon Bedrock.

## Features

- Summarize text content using Amazon Bedrock's foundation models
- Support for multiple model types (Claude, Titan)
- Caching mechanism to avoid redundant API calls
- Batch processing for multiple content items
- Error handling and retries

## Usage

### Basic Usage

```python
from backend.summarization import BedrockSummarizer

# Initialize the summarizer
summarizer = BedrockSummarizer(
    region_name='us-east-1',
    model_id='anthropic.claude-v2',
    max_tokens=300,
    temperature=0.2
)

# Summarize a single text
text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit..."
summary = summarizer.summarize_text(text, max_length=150)
print(summary)
```

### Summarizing Content Items

```python
# Summarize a content item
content_item = {
    'title': 'Example Article',
    'summary': 'This is the original summary or description...',
    'link': 'https://example.com/article'
}

summarized_item = summarizer.summarize_content_item(content_item)
print(summarized_item['ai_summary'])
```

### Batch Summarization

```python
# Summarize multiple items in parallel
items = [item1, item2, item3, ...]
summarized_items = summarizer.batch_summarize(items, max_concurrent=5)
```

## Configuration

The summarizer can be configured with the following parameters:

- `region_name`: AWS region name (default: 'us-east-1')
- `model_id`: Bedrock model ID (default: 'anthropic.claude-v2')
- `max_tokens`: Maximum number of tokens to generate (default: 300)
- `temperature`: Temperature for text generation (default: 0.2)
- `profile_name`: AWS profile name (optional)

## Supported Models

- Anthropic Claude models (`anthropic.claude-v2`, `anthropic.claude-instant-v1`, etc.)
- Amazon Titan models (`amazon.titan-text-express-v1`, etc.)

## Cache Management

The summarizer includes a caching mechanism to avoid redundant API calls:

```python
# Clear old cache entries
summarizer.clear_old_cache_entries(max_age_days=30)
```
