#!/bin/bash
# Script to update Lambda functions directly
# DEPRECATED: This script is deprecated in favor of the unified deploy-all.sh script.
# Please use ./aws/deploy-all.sh instead for all deployments.

# Set variables
DEPLOYMENT_BUCKET="content-aggregator-deployment"
REGION="us-east-1"  # Change to your preferred region

# List of Lambda functions to update
FUNCTIONS=(
  "content-fetcher"
  "content-filter"
  "batch-distributor"
  "content-summarizer"
  "batch-collector"
  "digest-generator"
)

# Update each Lambda function
for FUNCTION in "${FUNCTIONS[@]}"; do
  echo "Updating Lambda function: $FUNCTION"
  aws lambda update-function-code \
    --function-name "$FUNCTION" \
    --s3-bucket "$DEPLOYMENT_BUCKET" \
    --s3-key "$FUNCTION.zip" \
    --region "$REGION" \
    --publish
  
  # Wait for the update to complete
  echo "Waiting for function update to complete..."
  aws lambda wait function-updated \
    --function-name "$FUNCTION" \
    --region "$REGION"
  
  echo "Function $FUNCTION updated successfully!"
  echo
done

echo "All Lambda functions have been updated!"
