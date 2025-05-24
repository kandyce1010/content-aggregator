# Using AWS Step Functions for Content Aggregator

This document outlines how to implement a distributed workflow using AWS Step Functions to improve the content aggregation and summarization process.

## Why Step Functions?

AWS Step Functions provides a serverless orchestration service that makes it easy to sequence AWS Lambda functions and other AWS services to build scalable applications. It addresses the current challenges with our content aggregator:

1. **Lambda Timeout Issues**: Our current implementation times out when summarizing large amounts of content with Amazon Bedrock
2. **Sequential Processing Bottlenecks**: Processing all content in a single function is inefficient
3. **Complex Orchestration**: Managing the flow between fetching, filtering, summarizing, and delivering content

## Proposed Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │     │                 │
│  Fetch Content  │────▶│ Filter Content  │────▶│   Summarize     │────▶│ Generate Digest │
│                 │     │                 │     │    Content      │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        │
                                                        ▼
                                            ┌─────────────────────┐
                                            │                     │
                                            │  Parallel Batch     │
                                            │  Processing         │
                                            │                     │
                                            └─────────────────────┘
```

## Implementation Steps

### 1. Create Lambda Functions for Each Step

#### 1.1 Content Fetcher Lambda

```python
def lambda_handler(event, context):
    """
    Fetch content from various sources.
    """
    # Initialize the aggregator
    aggregator = ContentAggregator(enable_summarization=False)
    
    # Fetch content from different sources
    rss_content = aggregator.fetch_rss_content()
    github_content = aggregator.fetch_github_content()
    youtube_content = []
    
    # Combine all content
    all_content = rss_content + github_content + youtube_content
    
    return {
        "content_items": all_content,
        "stats": {
            "rss_count": len(rss_content),
            "github_count": len(github_content),
            "youtube_count": len(youtube_content),
            "total_count": len(all_content)
        }
    }
```

#### 1.2 Content Filter Lambda

```python
def lambda_handler(event, context):
    """
    Filter and score content items.
    """
    content_items = event.get("content_items", [])
    days = event.get("days", 7)
    category = event.get("category", "")
    
    # Initialize the aggregator
    aggregator = ContentAggregator(enable_summarization=False)
    
    # Deduplicate content
    original_count = len(content_items)
    content_items = aggregator.deduplicate_content(content_items)
    
    # Filter by category if specified
    if category:
        content_items = aggregator.filter_content_by_category(content_items, category)
    
    # Filter by date
    content_items = aggregator.filter_content_by_date(content_items, int(days))
    
    # Calculate relevance scores
    for item in content_items:
        item['relevance_score'] = calculate_relevance_score(item)
    
    # Sort by relevance score (highest first)
    content_items.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return {
        "content_items": content_items,
        "stats": {
            "original_count": original_count,
            "filtered_count": len(content_items)
        }
    }
```

#### 1.3 Content Summarizer Lambda

```python
def lambda_handler(event, context):
    """
    Summarize a batch of content items.
    """
    content_items = event.get("content_items", [])
    batch_index = event.get("batch_index", 0)
    batch_size = event.get("batch_size", 10)
    
    # Calculate batch start and end indices
    start_idx = batch_index * batch_size
    end_idx = min(start_idx + batch_size, len(content_items))
    
    # Get the batch of items to summarize
    batch_items = content_items[start_idx:end_idx]
    
    # Initialize the summarizer
    from backend.summarization.bedrock_summarizer import BedrockSummarizer
    summarizer = BedrockSummarizer()
    
    # Summarize the batch
    summarized_items = summarizer.batch_summarize(batch_items)
    
    # Copy generated_summary to ai_summary for compatibility
    for item in summarized_items:
        if item.get('generated_summary'):
            item['ai_summary'] = item['generated_summary']
    
    return {
        "summarized_items": summarized_items,
        "batch_index": batch_index,
        "batch_size": batch_size,
        "total_items": len(content_items)
    }
```

#### 1.4 Batch Distributor Lambda

```python
def lambda_handler(event, context):
    """
    Distribute content items into batches for parallel processing.
    """
    content_items = event.get("content_items", [])
    batch_size = event.get("batch_size", 10)
    
    # Calculate the number of batches
    num_items = len(content_items)
    num_batches = (num_items + batch_size - 1) // batch_size  # Ceiling division
    
    # Create batch configurations
    batches = []
    for i in range(num_batches):
        batches.append({
            "content_items": content_items,
            "batch_index": i,
            "batch_size": batch_size
        })
    
    return {
        "batches": batches,
        "num_batches": num_batches,
        "total_items": num_items
    }
```

#### 1.5 Batch Collector Lambda

```python
def lambda_handler(event, context):
    """
    Collect and merge summarized batches.
    """
    batch_results = event.get("batch_results", [])
    content_items = event.get("content_items", [])
    
    # Create a copy of the original content items
    merged_items = content_items.copy()
    
    # Update items with summaries from batches
    for batch_result in batch_results:
        summarized_items = batch_result.get("summarized_items", [])
        batch_index = batch_result.get("batch_index", 0)
        batch_size = batch_result.get("batch_size", 10)
        
        # Calculate batch start and end indices
        start_idx = batch_index * batch_size
        end_idx = min(start_idx + batch_size, len(merged_items))
        
        # Update items with summaries
        for i, item in enumerate(summarized_items):
            if start_idx + i < len(merged_items):
                if item.get('ai_summary'):
                    merged_items[start_idx + i]['ai_summary'] = item['ai_summary']
                if item.get('generated_summary'):
                    merged_items[start_idx + i]['generated_summary'] = item['generated_summary']
    
    return {
        "content_items": merged_items,
        "stats": {
            "total_items": len(merged_items),
            "summarized_count": sum(1 for item in merged_items if item.get('ai_summary'))
        }
    }
```

#### 1.6 Digest Generator Lambda

```python
def lambda_handler(event, context):
    """
    Generate email digest from summarized content.
    """
    content_items = event.get("content_items", [])
    email = event.get("email", "")
    max_items = event.get("max_items", 10)
    
    # Generate the digest
    from backend.email_digest.digest_generator import DigestGenerator
    digest_generator = DigestGenerator()
    digest = digest_generator.generate_digest(content_items, max_items=max_items)
    
    # Send the email if requested
    if email:
        from backend.email_digest.email_sender import EmailSender
        sender = EmailSender()
        response = sender.send_digest(email, "Your Daily Content Digest", digest)
    
    return {
        "digest": digest,
        "email": email,
        "stats": {
            "items_count": len(content_items)
        }
    }
```

### 2. Define the Step Functions State Machine

```json
{
  "Comment": "Content Aggregator Workflow",
  "StartAt": "FetchContent",
  "States": {
    "FetchContent": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:content-fetcher",
      "Next": "FilterContent"
    },
    "FilterContent": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:content-filter",
      "Parameters": {
        "content_items.$": "$.content_items",
        "days.$": "$.days",
        "category.$": "$.category"
      },
      "Next": "DistributeBatches"
    },
    "DistributeBatches": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:batch-distributor",
      "Parameters": {
        "content_items.$": "$.content_items",
        "batch_size.$": "$.batch_size"
      },
      "Next": "SummarizeBatches"
    },
    "SummarizeBatches": {
      "Type": "Map",
      "ItemsPath": "$.batches",
      "MaxConcurrency": 10,
      "Iterator": {
        "StartAt": "SummarizeBatch",
        "States": {
          "SummarizeBatch": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:region:account:function:content-summarizer",
            "End": true
          }
        }
      },
      "ResultPath": "$.batch_results",
      "Next": "CollectBatches"
    },
    "CollectBatches": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:batch-collector",
      "Parameters": {
        "batch_results.$": "$.batch_results",
        "content_items.$": "$.content_items"
      },
      "Next": "GenerateDigest"
    },
    "GenerateDigest": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:region:account:function:digest-generator",
      "Parameters": {
        "content_items.$": "$.content_items",
        "email.$": "$.email",
        "max_items.$": "$.max_items"
      },
      "End": true
    }
  }
}
```

### 3. CloudFormation Template

Create a CloudFormation template to deploy the Step Functions workflow and Lambda functions:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Content Aggregator with Step Functions Workflow'

Resources:
  ContentFetcherFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: content-fetcher
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: python3.9
      Timeout: 300
      MemorySize: 256
      Code:
        S3Bucket: your-deployment-bucket
        S3Key: content-fetcher.zip

  ContentFilterFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: content-filter
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: python3.9
      Timeout: 300
      MemorySize: 256
      Code:
        S3Bucket: your-deployment-bucket
        S3Key: content-filter.zip

  BatchDistributorFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: batch-distributor
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: python3.9
      Timeout: 60
      MemorySize: 128
      Code:
        S3Bucket: your-deployment-bucket
        S3Key: batch-distributor.zip

  ContentSummarizerFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: content-summarizer
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: python3.9
      Timeout: 900
      MemorySize: 512
      Code:
        S3Bucket: your-deployment-bucket
        S3Key: content-summarizer.zip

  BatchCollectorFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: batch-collector
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: python3.9
      Timeout: 60
      MemorySize: 256
      Code:
        S3Bucket: your-deployment-bucket
        S3Key: batch-collector.zip

  DigestGeneratorFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: digest-generator
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Runtime: python3.9
      Timeout: 300
      MemorySize: 256
      Code:
        S3Bucket: your-deployment-bucket
        S3Key: digest-generator.zip

  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        - arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
        - arn:aws:iam::aws:policy/AmazonSESFullAccess
        - arn:aws:iam::aws:policy/AmazonBedrockFullAccess

  StepFunctionsExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: states.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaRole

  ContentAggregatorStateMachine:
    Type: AWS::StepFunctions::StateMachine
    Properties:
      StateMachineName: ContentAggregatorWorkflow
      RoleArn: !GetAtt StepFunctionsExecutionRole.Arn
      DefinitionString: !Sub |
        {
          "Comment": "Content Aggregator Workflow",
          "StartAt": "FetchContent",
          "States": {
            "FetchContent": {
              "Type": "Task",
              "Resource": "${ContentFetcherFunction.Arn}",
              "Next": "FilterContent"
            },
            "FilterContent": {
              "Type": "Task",
              "Resource": "${ContentFilterFunction.Arn}",
              "Parameters": {
                "content_items.$": "$.content_items",
                "days.$": "$.days",
                "category.$": "$.category"
              },
              "Next": "DistributeBatches"
            },
            "DistributeBatches": {
              "Type": "Task",
              "Resource": "${BatchDistributorFunction.Arn}",
              "Parameters": {
                "content_items.$": "$.content_items",
                "batch_size.$": "$.batch_size"
              },
              "Next": "SummarizeBatches"
            },
            "SummarizeBatches": {
              "Type": "Map",
              "ItemsPath": "$.batches",
              "MaxConcurrency": 10,
              "Iterator": {
                "StartAt": "SummarizeBatch",
                "States": {
                  "SummarizeBatch": {
                    "Type": "Task",
                    "Resource": "${ContentSummarizerFunction.Arn}",
                    "End": true
                  }
                }
              },
              "ResultPath": "$.batch_results",
              "Next": "CollectBatches"
            },
            "CollectBatches": {
              "Type": "Task",
              "Resource": "${BatchCollectorFunction.Arn}",
              "Parameters": {
                "batch_results.$": "$.batch_results",
                "content_items.$": "$.content_items"
              },
              "Next": "GenerateDigest"
            },
            "GenerateDigest": {
              "Type": "Task",
              "Resource": "${DigestGeneratorFunction.Arn}",
              "Parameters": {
                "content_items.$": "$.content_items",
                "email.$": "$.email",
                "max_items.$": "$.max_items"
              },
              "End": true
            }
          }
        }

  EventRule:
    Type: AWS::Events::Rule
    Properties:
      Name: DailyContentAggregatorTrigger
      Description: Triggers the Content Aggregator workflow daily
      ScheduleExpression: cron(0 12 * * ? *)
      State: ENABLED
      Targets:
        - Arn: !Ref ContentAggregatorStateMachine
          Id: ContentAggregatorWorkflow
          RoleArn: !GetAtt EventsExecutionRole.Arn
          Input: |
            {
              "days": 1,
              "email": "your-email@example.com",
              "max_items": 10,
              "batch_size": 10
            }

  EventsExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: events.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: StepFunctionsExecutionPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: states:StartExecution
                Resource: !Ref ContentAggregatorStateMachine

Outputs:
  StateMachineArn:
    Description: ARN of the Content Aggregator State Machine
    Value: !Ref ContentAggregatorStateMachine
```

## Benefits of This Approach

1. **Scalability**: Process content in parallel across multiple Lambda functions
2. **Resilience**: Built-in error handling and retry mechanisms
3. **Flexibility**: Easy to modify workflow without changing code
4. **Performance**: Avoid Lambda timeout issues by distributing work
5. **Visibility**: Step Functions provides visual workflow monitoring
6. **Cost-Effective**: Pay only for the execution time of each step

## Next Steps

1. Implement the Lambda functions for each step
2. Create the Step Functions state machine
3. Deploy using CloudFormation
4. Test with a small subset of content sources
5. Monitor performance and optimize as needed
