#!/bin/bash
# Script to test the Step Functions workflow locally

# Set variables
EMAIL="kanbo@amazon.com"  # Change to your email
DAYS=1
MAX_ITEMS=10
BATCH_SIZE=5

# Create a test input file
cat > test-input.json << EOF
{
  "email": "$EMAIL",
  "days": $DAYS,
  "max_items": $MAX_ITEMS,
  "batch_size": $BATCH_SIZE
}
EOF

# Get the state machine ARN
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks --stack-name content-aggregator-workflow --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" --output text)

if [ -z "$STATE_MACHINE_ARN" ]; then
    echo "Error: Could not find the state machine ARN. Make sure the stack is deployed."
    exit 1
fi

echo "Starting execution of state machine: $STATE_MACHINE_ARN"

# Start the execution
EXECUTION_ARN=$(aws stepfunctions start-execution \
    --state-machine-arn "$STATE_MACHINE_ARN" \
    --input file://test-input.json \
    --query executionArn \
    --output text)

echo "Execution started: $EXECUTION_ARN"
echo "Waiting for execution to complete..."

# Wait for the execution to complete
while true; do
    STATUS=$(aws stepfunctions describe-execution \
        --execution-arn "$EXECUTION_ARN" \
        --query status \
        --output text)
    
    echo "Current status: $STATUS"
    
    if [ "$STATUS" == "SUCCEEDED" ] || [ "$STATUS" == "FAILED" ] || [ "$STATUS" == "TIMED_OUT" ] || [ "$STATUS" == "ABORTED" ]; then
        break
    fi
    
    sleep 5
done

# Get the execution result
if [ "$STATUS" == "SUCCEEDED" ]; then
    echo "Execution succeeded!"
    aws stepfunctions describe-execution \
        --execution-arn "$EXECUTION_ARN" \
        --query output \
        --output json | jq .
else
    echo "Execution failed with status: $STATUS"
    aws stepfunctions describe-execution \
        --execution-arn "$EXECUTION_ARN" \
        --query errorMessage \
        --output text
fi
