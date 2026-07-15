#!/usr/bin/env bash
# deploy.sh — build and deploy the content aggregator stack via SAM
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - SAM CLI installed (brew install aws-sam-cli)
#   - An S3 bucket for SAM deployment artifacts, or let SAM create one
#
# Usage:
#   ./deploy.sh                          # guided first deploy
#   ./deploy.sh --no-confirm-changeset   # re-deploy without prompts

set -euo pipefail

STACK_NAME="content-aggregator"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
SAM_CONFIG="samconfig.toml"

echo "Building Lambda deployment package..."
sam build --use-container 2>/dev/null || sam build

echo ""
echo "Deploying stack '${STACK_NAME}' to region '${REGION}'..."

if [ -f "$SAM_CONFIG" ] && grep -q "stack_name" "$SAM_CONFIG" 2>/dev/null; then
  # samconfig.toml exists from a previous deploy — use saved parameters
  sam deploy "$@"
else
  # First deploy — guided mode collects parameters and writes samconfig.toml
  sam deploy --guided \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameter-overrides \
      "DigestSchedule=cron(0 13 * * ? *)" \
    "$@"
fi

echo ""
echo "Deploy complete. Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs' \
  --output table
