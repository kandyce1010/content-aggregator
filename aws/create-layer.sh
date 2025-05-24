#!/bin/bash
# Script to create a Lambda layer with dependencies

# Set variables
LAYER_NAME="content-aggregator-dependencies"
DEPLOYMENT_BUCKET="content-aggregator-deployment"
REGION="us-east-1"  # Change to your preferred region

# Create a temporary directory for the layer
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Create the layer structure
mkdir -p "$TEMP_DIR/python"

# Install dependencies
pip install -r aws/layer/requirements.txt -t "$TEMP_DIR/python"

# Create the zip file
cd "$TEMP_DIR"
zip -r "$TEMP_DIR/layer.zip" .
cd - > /dev/null

# Upload to S3
aws s3 cp "$TEMP_DIR/layer.zip" "s3://$DEPLOYMENT_BUCKET/layer.zip"

# Create or update the layer
LAYER_VERSION=$(aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "Dependencies for Content Aggregator" \
    --content "S3Bucket=$DEPLOYMENT_BUCKET,S3Key=layer.zip" \
    --compatible-runtimes python3.9 \
    --region "$REGION" \
    --query 'Version' \
    --output text)

echo "Created layer version: $LAYER_VERSION"

# Update all Lambda functions to use the layer
FUNCTIONS=("content-fetcher" "content-filter" "batch-distributor" "content-summarizer" "batch-collector" "digest-generator")

for FUNCTION in "${FUNCTIONS[@]}"; do
    echo "Updating function $FUNCTION to use layer version $LAYER_VERSION"
    aws lambda update-function-configuration \
        --function-name "$FUNCTION" \
        --layers "arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query 'Account' --output text):layer:$LAYER_NAME:$LAYER_VERSION" \
        --region "$REGION"
done

# Clean up
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo "Layer creation and function updates complete!"
