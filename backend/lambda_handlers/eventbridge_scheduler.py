#!/usr/bin/env python3
"""
EventBridge Scheduler

This script sets up an EventBridge rule to schedule the content aggregator
to run on a regular basis.
"""

import argparse
import logging
import re
from boto3 import Session
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def sanitize_log_message(message):
    """Sanitize log messages to prevent log injection attacks."""
    if isinstance(message, Exception):
        message = str(message)
    # Remove newlines and carriage returns to prevent log injection
    return re.sub(r'[\r\n]', ' ', str(message))

def create_eventbridge_rule(rule_name, schedule_expression, region_name='us-east-1', profile_name=None):
    """
    Create an EventBridge rule with a schedule expression.
    
    Args:
        rule_name (str): Name of the EventBridge rule
        schedule_expression (str): Schedule expression (e.g., 'cron(0 8 * * ? *)')
        region_name (str): AWS region name
        profile_name (str, optional): AWS profile name
        
    Returns:
        str: ARN of the created rule
    """
    # Initialize AWS session
    session_kwargs = {'region_name': region_name}
    if profile_name:
        session_kwargs['profile_name'] = profile_name
        
    session = Session(**session_kwargs)
    events_client = session.client('events')
    
    try:
        # Create the rule
        response = events_client.put_rule(
            Name=rule_name,
            ScheduleExpression=schedule_expression,
            State='ENABLED',
            Description='Schedule for Content Aggregator digest generation'
        )
        
        rule_arn = response['RuleArn']
        logger.info(f"Created EventBridge rule: {rule_arn}")
        return rule_arn
    
    except ClientError as e:
        logger.error(f"Error creating EventBridge rule: {sanitize_log_message(e)}")
        raise

def add_lambda_target(rule_name, lambda_function_name, input_json=None, region_name='us-east-1', profile_name=None):
    """
    Add a Lambda function as a target for an EventBridge rule.
    
    Args:
        rule_name (str): Name of the EventBridge rule
        lambda_function_name (str): Name or ARN of the Lambda function
        input_json (str, optional): JSON input to pass to the Lambda function
        region_name (str): AWS region name
        profile_name (str, optional): AWS profile name
        
    Returns:
        str: ID of the target
    """
    # Initialize AWS session
    session_kwargs = {'region_name': region_name}
    if profile_name:
        session_kwargs['profile_name'] = profile_name
        
    session = Session(**session_kwargs)
    events_client = session.client('events')
    lambda_client = session.client('lambda')
    
    try:
        # Get the Lambda function ARN if a name was provided
        if not lambda_function_name.startswith('arn:'):
            response = lambda_client.get_function(FunctionName=lambda_function_name)
            lambda_arn = response['Configuration']['FunctionArn']
        else:
            lambda_arn = lambda_function_name
        
        # Create the target
        target_id = f"{rule_name}-target"
        target = {
            'Id': target_id,
            'Arn': lambda_arn
        }
        
        if input_json:
            target['Input'] = input_json
        
        events_client.put_targets(
            Rule=rule_name,
            Targets=[target]
        )
        
        logger.info("Added Lambda target to EventBridge rule")
        return target_id
    
    except ClientError as e:
        logger.error(f"Error adding Lambda target: {sanitize_log_message(e)}")
        raise

def add_lambda_permission(rule_name, rule_arn, lambda_function_name, region_name='us-east-1', profile_name=None):
    """
    Add permission for EventBridge to invoke the Lambda function.
    
    Args:
        rule_name (str): Name of the EventBridge rule
        rule_arn (str): ARN of the EventBridge rule
        lambda_function_name (str): Name or ARN of the Lambda function
        region_name (str): AWS region name
        profile_name (str, optional): AWS profile name
    """
    # Initialize AWS session
    session_kwargs = {'region_name': region_name}
    if profile_name:
        session_kwargs['profile_name'] = profile_name
        
    session = Session(**session_kwargs)
    lambda_client = session.client('lambda')
    
    try:
        # Get the Lambda function ARN if a name was provided
        if not lambda_function_name.startswith('arn:'):
            response = lambda_client.get_function(FunctionName=lambda_function_name)
            lambda_arn = response['Configuration']['FunctionArn']
        else:
            lambda_arn = lambda_function_name
        
        # Add permission
        lambda_client.add_permission(
            FunctionName=lambda_arn,
            StatementId=f"{rule_name}-permission",
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=rule_arn
        )
        
        logger.info("Added permission for EventBridge rule to invoke Lambda function")
    
    except ClientError as e:
        if 'ResourceConflictException' in str(e) and 'already exists' in str(e):
            logger.info("Permission for EventBridge rule to invoke Lambda function already exists")
        else:
            logger.error(f"Error adding Lambda permission: {sanitize_log_message(e)}")
            raise

def setup_eventbridge_schedule(rule_name, schedule_expression, lambda_function_name, input_json=None, region_name='us-east-1', profile_name=None):
    """
    Set up a complete EventBridge schedule with a Lambda target.
    
    Args:
        rule_name (str): Name of the EventBridge rule
        schedule_expression (str): Schedule expression (e.g., 'cron(0 8 * * ? *)')
        lambda_function_name (str): Name or ARN of the Lambda function
        input_json (str, optional): JSON input to pass to the Lambda function
        region_name (str): AWS region name
        profile_name (str, optional): AWS profile name
        
    Returns:
        dict: Information about the created resources
    """
    try:
        # Create the rule
        rule_arn = create_eventbridge_rule(rule_name, schedule_expression, region_name, profile_name)
        
        # Add the Lambda target
        target_id = add_lambda_target(rule_name, lambda_function_name, input_json, region_name, profile_name)
        
        # Add permission for EventBridge to invoke the Lambda function
        add_lambda_permission(rule_name, rule_arn, lambda_function_name, region_name, profile_name)
        
        return {
            'rule_name': rule_name,
            'rule_arn': rule_arn,
            'target_id': target_id,
            'lambda_function': lambda_function_name,
            'schedule_expression': schedule_expression
        }
    
    except Exception as e:
        logger.error(f"Error setting up EventBridge schedule: {sanitize_log_message(e)}")
        raise

def main():
    """
    Main function to set up an EventBridge schedule.
    """
    parser = argparse.ArgumentParser(description='Set up EventBridge scheduling for Content Aggregator')
    parser.add_argument('--rule-name', default='content-aggregator-daily', help='Name of the EventBridge rule')
    parser.add_argument('--schedule', default='cron(0 8 * * ? *)', help='Schedule expression (cron or rate)')
    parser.add_argument('--lambda-function', required=True, help='Name or ARN of the Lambda function')
    parser.add_argument('--input-json', help='JSON input to pass to the Lambda function')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')
    
    args = parser.parse_args()
    
    try:
        result = setup_eventbridge_schedule(
            args.rule_name,
            args.schedule,
            args.lambda_function,
            args.input_json,
            args.region,
            args.profile
        )
        
        logger.info("EventBridge schedule set up successfully")
        
    except Exception as e:
        logger.error(f"Failed to set up EventBridge schedule: {sanitize_log_message(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
