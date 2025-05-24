# Using Strands for Content Aggregator

This document outlines how to implement an agentic workflow using [Strands](https://github.com/strands-agents) to improve the content aggregation and summarization process.

## Why Strands?

Strands provides a framework for building agentic workflows that can help address the current challenges with our content aggregator:

1. **Lambda Timeout Issues**: Our current implementation times out when summarizing large amounts of content with Amazon Bedrock
2. **Sequential Processing Bottlenecks**: Processing all content in a single function is inefficient
3. **Complex Orchestration**: Managing the flow between fetching, filtering, summarizing, and delivering content

## Proposed Architecture

![Strands Architecture](https://mermaid.ink/img/pako:eNp1kU1PwzAMhv9KlBOgSf0BHHZAQkgcEBInLlVwSd3FIklGkk5Mqv47aVdtMG0-Jc_r17HtI1RGI0hYWvNkHLFVrUlbZVeKqHXWrJQjZ6lWK0fWrZXrjDFqSc6qVjVIXxTZKF3b1hBdUCfVWvJGNc7QVtm1ov-QD-KYxzw_5XEcn_E4jvM4zuOTOD6P4_NvfMbjOM7jOI_P4_gijvM4vvzGl3Ecx3kc5_FFHOdxfPWNr-I4jvM4zuPLOM7j-Pob_4_P4jiP4-tv_CaO8zi--cb3cZzH8e03fhfHeRzff-OHOM7j-PEbP8VxHsdP3_g5jvM4fvnGr3Gcx_HrN36L4zyO377xexxfxPHHN_6M4zyOv77xdxzncfzzjX_jOI_jv2_8H8d5HJNvnMRx_gU6sKE9)

## Implementation Steps

### 1. Define Workflow Components

Create specialized agents for each part of the content aggregation process:

```python
from strands import Agent, Workflow

class ContentFetcherAgent(Agent):
    def process(self, sources):
        """Fetch content from various sources (RSS, GitHub, YouTube)"""
        results = []
        for source in sources:
            if source["type"] == "rss":
                results.extend(self.fetch_rss(source))
            elif source["type"] == "github":
                results.extend(self.fetch_github(source))
            # Add other source types
        return results

class ContentFilterAgent(Agent):
    def process(self, content_items):
        """Filter content based on relevance and criteria"""
        filtered_items = []
        for item in content_items:
            score = self.calculate_relevance_score(item)
            if score > self.threshold:
                filtered_items.append(item)
        return filtered_items

class SummarizationAgent(Agent):
    def process(self, content_items):
        """Summarize content using Amazon Bedrock"""
        # Process in smaller batches to avoid timeouts
        all_summaries = []
        for batch in self.create_batches(content_items, batch_size=10):
            summaries = self.summarize_batch(batch)
            all_summaries.extend(summaries)
        return all_summaries

class DigestGeneratorAgent(Agent):
    def process(self, summarized_items):
        """Generate email digest from summarized content"""
        return self.create_email_digest(summarized_items)
```

### 2. Define the Workflow

```python
class ContentAggregatorWorkflow(Workflow):
    def steps(self):
        return [
            {
                "name": "fetch_content",
                "agent": ContentFetcherAgent(),
                "input": self.get_sources_config()
            },
            {
                "name": "filter_content",
                "agent": ContentFilterAgent(),
                "input": lambda outputs: outputs["fetch_content"]
            },
            {
                "name": "summarize_content",
                "agent": SummarizationAgent(),
                "input": lambda outputs: outputs["filter_content"]
            },
            {
                "name": "generate_digest",
                "agent": DigestGeneratorAgent(),
                "input": lambda outputs: outputs["summarize_content"]
            }
        ]
```

### 3. Implement Asynchronous Processing

For the summarization step, which is the most time-consuming:

```python
class SummarizationAgent(Agent):
    async def process(self, content_items):
        """Summarize content using Amazon Bedrock asynchronously"""
        tasks = []
        for batch in self.create_batches(content_items, batch_size=10):
            task = asyncio.create_task(self.summarize_batch_async(batch))
            tasks.append(task)
        
        # Wait for all tasks to complete
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        all_summaries = []
        for batch_result in batch_results:
            all_summaries.extend(batch_result)
            
        return all_summaries
```

### 4. Add State Management and Checkpointing

```python
class ContentAggregatorWorkflow(Workflow):
    def __init__(self):
        super().__init__()
        self.checkpoint_path = "/tmp/workflow_checkpoint.json"
    
    def save_checkpoint(self, step_name, data):
        checkpoint = {
            "step": step_name,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        with open(self.checkpoint_path, "w") as f:
            json.dump(checkpoint, f)
    
    def load_checkpoint(self):
        if os.path.exists(self.checkpoint_path):
            with open(self.checkpoint_path, "r") as f:
                return json.load(f)
        return None
```

## Integration with AWS Services

### Lambda Integration

Create a Lambda function that initiates the Strands workflow:

```python
def lambda_handler(event, context):
    workflow = ContentAggregatorWorkflow()
    result = workflow.run()
    
    # Store results in S3
    s3_client = boto3.client('s3')
    s3_client.put_object(
        Bucket='content-aggregator-results',
        Key=f'digest-{datetime.now().strftime("%Y-%m-%d")}.json',
        Body=json.dumps(result)
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Workflow completed successfully')
    }
```

### Step Functions Integration

For more complex workflows, integrate with AWS Step Functions:

```python
{
  "Comment": "Content Aggregator Workflow",
  "StartAt": "FetchContent",
  "States": {
    "FetchContent": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:fetch-content",
      "Next": "FilterContent"
    },
    "FilterContent": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:filter-content",
      "Next": "SummarizeContent"
    },
    "SummarizeContent": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:summarize-content",
      "Next": "GenerateDigest"
    },
    "GenerateDigest": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:generate-digest",
      "End": true
    }
  }
}
```

## Benefits of This Approach

1. **Scalability**: Process content in parallel across multiple agents
2. **Resilience**: Checkpoint-based recovery from failures
3. **Flexibility**: Easily add new content sources or processing steps
4. **Performance**: Avoid Lambda timeout issues by distributing work
5. **Maintainability**: Clear separation of concerns between different agents

## Next Steps

1. Install Strands: `pip install strands`
2. Implement the basic workflow structure
3. Test with a small subset of content sources
4. Gradually migrate the existing content aggregator functionality to the Strands-based workflow
5. Deploy to AWS using Lambda and potentially Step Functions for orchestration
