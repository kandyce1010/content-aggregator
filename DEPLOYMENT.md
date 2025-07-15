# Deployment Guide

## Overview

This document provides instructions for deploying the Content Aggregator application to AWS Lambda and Step Functions.

## Unified Deployment

The recommended way to deploy all Lambda functions is using the unified deployment script:

```bash
./aws/deploy-all.sh
```

This script will:
1. Package and deploy the main content-aggregator Lambda function
2. Package and deploy all Step Functions workflow Lambda functions:
   - content-fetcher
   - content-filter
   - batch-distributor
   - content-summarizer
   - batch-collector
   - digest-generator

## Running the Step Functions Workflow

After deployment, you can start a new execution of the Step Functions workflow:

```bash
aws stepfunctions start-execution \
  --state-machine-arn "arn:aws:states:us-east-1:797963488632:stateMachine:ContentAggregatorWorkflow"
```

## Configuration

Content sources are configured in `config/sources.json`. After updating this file, you need to redeploy the Lambda functions for the changes to take effect.

## Troubleshooting

Common issues:

1. **"Unable to import module 'lambda_function'"**: This indicates an issue with the Lambda deployment package structure. Run the unified deployment script to fix.

2. **"NoneType object has no attribute 'lower'"**: This indicates an issue with handling None values in the code. Check for proper null handling in the digest_generator.py file.

## Deprecated Scripts

The following scripts are deprecated and should not be used directly:
- `aws/deploy.py`
- `aws/package-step-functions.sh`
- `aws/update-lambda-functions.sh`

Please use the unified `deploy-all.sh` script instead.
