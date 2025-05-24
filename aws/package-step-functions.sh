#!/bin/bash
# Script to package and deploy the Step Functions workflow

# Set variables
DEPLOYMENT_BUCKET="content-aggregator-deployment"
REGION="us-east-1"  # Change to your preferred region

# Create deployment bucket if it doesn't exist
aws s3api head-bucket --bucket $DEPLOYMENT_BUCKET 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Creating deployment bucket: $DEPLOYMENT_BUCKET"
    aws s3 mb s3://$DEPLOYMENT_BUCKET --region $REGION
fi

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Function to package a Lambda function
package_function() {
    FUNCTION_NAME=$1
    FUNCTION_DIR="aws/step_functions/$FUNCTION_NAME"
    OUTPUT_ZIP="$FUNCTION_NAME.zip"
    
    echo "Packaging $FUNCTION_NAME..."
    
    # Create a temporary directory for the function
    mkdir -p "$TEMP_DIR/$FUNCTION_NAME"
    
    # Copy the function code
    cp "$FUNCTION_DIR/lambda_function.py" "$TEMP_DIR/$FUNCTION_NAME/"
    
    # Copy the backend directory (excluding __pycache__ directories)
    rsync -a --exclude="__pycache__" backend/ "$TEMP_DIR/$FUNCTION_NAME/backend/"
    
    # Create config directories at both locations
    mkdir -p "$TEMP_DIR/$FUNCTION_NAME/config"
    mkdir -p "$TEMP_DIR/$FUNCTION_NAME/backend/config"
    
    # Copy the config files to both locations
    if [ -d "config" ]; then
        cp -r config/* "$TEMP_DIR/$FUNCTION_NAME/config/"
        cp -r config/* "$TEMP_DIR/$FUNCTION_NAME/backend/config/"
    else
        echo "Warning: config directory not found"
    fi
    
    # Create the zip file
    cd "$TEMP_DIR/$FUNCTION_NAME"
    zip -r "$TEMP_DIR/$OUTPUT_ZIP" .
    cd - > /dev/null
    
    # Upload to S3
    aws s3 cp "$TEMP_DIR/$OUTPUT_ZIP" "s3://$DEPLOYMENT_BUCKET/$OUTPUT_ZIP"
    
    echo "Uploaded $OUTPUT_ZIP to s3://$DEPLOYMENT_BUCKET/$OUTPUT_ZIP"
}

# Package each Lambda function
package_function "content-fetcher"
package_function "content-filter"
package_function "batch-distributor"
package_function "content-summarizer"
package_function "batch-collector"
package_function "digest-generator"

# Deploy the CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file aws/step-functions-cloudformation.yaml \
    --stack-name content-aggregator-workflow \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        DeploymentBucket=$DEPLOYMENT_BUCKET \
        RecipientEmail="kanbo@amazon.com" \
        FilterDays=1 \
        MaxItems=10 \
        BatchSize=10

# Clean up
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo "Deployment complete!"
