#!/bin/bash
# Unified deployment script for Content Aggregator
# This script deploys both the main content-aggregator Lambda function
# and all Step Functions workflow Lambda functions

set -e  # Exit on error

echo "=== Content Aggregator Unified Deployment ==="
echo "Starting deployment process at $(date)"

# Set variables
MAIN_DEPLOYMENT_BUCKET="content-aggregator-lambda-deployment-kanbo"
STEP_FUNCTIONS_BUCKET="content-aggregator-deployment"
REGION="us-east-1"  # Change to your preferred region

# Create deployment buckets if they don't exist
echo "Checking deployment buckets..."
aws s3api head-bucket --bucket $MAIN_DEPLOYMENT_BUCKET 2>/dev/null || aws s3 mb s3://$MAIN_DEPLOYMENT_BUCKET --region $REGION
aws s3api head-bucket --bucket $STEP_FUNCTIONS_BUCKET 2>/dev/null || aws s3 mb s3://$STEP_FUNCTIONS_BUCKET --region $REGION

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Part 1: Deploy main content-aggregator Lambda function
echo ""
echo "=== Deploying main content-aggregator Lambda function ==="

# Create the Lambda package
echo "Creating package for content-aggregator..."
MAIN_OUTPUT_ZIP="$TEMP_DIR/content-aggregator.zip"

# Get the project root directory
PROJECT_ROOT=$(pwd)
if [[ "$PROJECT_ROOT" == *"/aws" ]]; then
    PROJECT_ROOT=$(dirname "$PROJECT_ROOT")
fi

# Create the zip file for main Lambda
(
    cd "$PROJECT_ROOT"
    zip -r "$MAIN_OUTPUT_ZIP" aws/*.py backend -x "**/__pycache__/**" "**/*.pyc"
)

# Upload to S3
echo "Uploading content-aggregator.zip to S3..."
aws s3 cp "$MAIN_OUTPUT_ZIP" "s3://$MAIN_DEPLOYMENT_BUCKET/content-aggregator.zip"

# Update the Lambda function
echo "Updating content-aggregator Lambda function..."
aws lambda update-function-code \
    --function-name "content-aggregator" \
    --s3-bucket "$MAIN_DEPLOYMENT_BUCKET" \
    --s3-key "content-aggregator.zip" \
    --region "$REGION" \
    --publish

echo "Main content-aggregator Lambda function updated successfully!"

# Part 2: Deploy Step Functions workflow Lambda functions
echo ""
echo "=== Deploying Step Functions workflow Lambda functions ==="

# Function to package a Lambda function for Step Functions
package_function() {
    FUNCTION_NAME=$1
    FUNCTION_DIR="$PROJECT_ROOT/aws/step_functions/$FUNCTION_NAME"
    OUTPUT_ZIP="$TEMP_DIR/$FUNCTION_NAME.zip"
    
    echo "Packaging $FUNCTION_NAME..."
    
    # Create a temporary directory for the function
    mkdir -p "$TEMP_DIR/$FUNCTION_NAME"
    
    # Copy the function code
    cp "$FUNCTION_DIR/lambda_function.py" "$TEMP_DIR/$FUNCTION_NAME/"
    
    # Copy the backend directory (excluding __pycache__ directories)
    rsync -a --exclude="__pycache__" "$PROJECT_ROOT/backend/" "$TEMP_DIR/$FUNCTION_NAME/backend/"
    
    # Create config directories at both locations
    mkdir -p "$TEMP_DIR/$FUNCTION_NAME/config"
    mkdir -p "$TEMP_DIR/$FUNCTION_NAME/backend/config"
    
    # Copy the config files to both locations
    if [ -d "$PROJECT_ROOT/config" ]; then
        cp -r "$PROJECT_ROOT/config/"* "$TEMP_DIR/$FUNCTION_NAME/config/"
        cp -r "$PROJECT_ROOT/config/"* "$TEMP_DIR/$FUNCTION_NAME/backend/config/"
    else
        echo "Warning: config directory not found"
    fi
    
    # Create the zip file
    (
        cd "$TEMP_DIR/$FUNCTION_NAME"
        zip -r "$OUTPUT_ZIP" .
    )
    
    # Upload to S3
    aws s3 cp "$OUTPUT_ZIP" "s3://$STEP_FUNCTIONS_BUCKET/$FUNCTION_NAME.zip"
    
    echo "Uploaded $FUNCTION_NAME.zip to S3"
    
    # Update the Lambda function
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --s3-bucket "$STEP_FUNCTIONS_BUCKET" \
        --s3-key "$FUNCTION_NAME.zip" \
        --region "$REGION" \
        --publish
    
    echo "Function $FUNCTION_NAME updated successfully!"
}

# Package and deploy each Step Functions Lambda function
STEP_FUNCTIONS=(
    "content-fetcher"
    "content-filter"
    "batch-distributor"
    "content-summarizer"
    "batch-collector"
    "digest-generator"
)

for FUNCTION in "${STEP_FUNCTIONS[@]}"; do
    package_function "$FUNCTION"
    echo ""
done

# Clean up
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo ""
echo "=== Deployment Summary ==="
echo "Main content-aggregator Lambda function deployed"
echo "Step Functions workflow Lambda functions deployed:"
for FUNCTION in "${STEP_FUNCTIONS[@]}"; do
    echo "- $FUNCTION"
done

echo ""
echo "Deployment completed successfully at $(date)"
