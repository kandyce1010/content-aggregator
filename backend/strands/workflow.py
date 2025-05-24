#!/usr/bin/env python3
"""
Strands Workflow for Content Aggregator

This module defines the workflow for content aggregation and summarization.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from strands import Workflow

from backend.strands.agents import (
    ContentFetcherAgent,
    ContentFilterAgent,
    SummarizationAgent,
    DigestGeneratorAgent
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContentAggregatorWorkflow(Workflow):
    """
    Workflow for content aggregation and summarization.
    """
    
    def __init__(self, 
                email: str = None, 
                days: int = 7, 
                max_items: int = 10, 
                category: str = "",
                enable_summarization: bool = True,
                batch_size: int = 10):
        """
        Initialize the ContentAggregatorWorkflow.
        
        Args:
            email: Recipient email address
            days: Number of days to filter content
            max_items: Maximum number of items per category
            category: Category to filter content
            enable_summarization: Whether to enable content summarization
            batch_size: Number of items to process in each summarization batch
        """
        super().__init__()
        self.email = email
        self.days = days
        self.max_items = max_items
        self.category = category
        self.enable_summarization = enable_summarization
        self.batch_size = batch_size
        
        # Set up checkpoint directory
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            # Use /tmp directory in Lambda environment (writable)
            self.checkpoint_dir = '/tmp/workflow_checkpoints'
        else:
            # Use regular path for local development
            self.checkpoint_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                '..', 'data', 'workflow_checkpoints'
            )
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        # Set up checkpoint file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.checkpoint_file = os.path.join(self.checkpoint_dir, f'checkpoint_{timestamp}.json')
    
    async def steps(self) -> List[Dict[str, Any]]:
        """
        Define the workflow steps.
        
        Returns:
            List of workflow steps
        """
        # Step 1: Fetch content from all sources
        fetch_step = {
            "name": "fetch_content",
            "agent": ContentFetcherAgent(),
            "input": {}
        }
        
        # Step 2: Filter and score content
        filter_step = {
            "name": "filter_content",
            "agent": ContentFilterAgent(),
            "input": lambda outputs: {
                "content_items": outputs["fetch_content"]["content_items"],
                "days": self.days,
                "category": self.category
            }
        }
        
        # Step 3: Summarize content (optional)
        if self.enable_summarization:
            summarize_step = {
                "name": "summarize_content",
                "agent": SummarizationAgent(batch_size=self.batch_size),
                "input": lambda outputs: {
                    "content_items": outputs["filter_content"]["content_items"]
                }
            }
            
            # Step 4: Generate digest from summarized content
            digest_step = {
                "name": "generate_digest",
                "agent": DigestGeneratorAgent(),
                "input": lambda outputs: {
                    "content_items": outputs["summarize_content"]["content_items"],
                    "email": self.email,
                    "max_items": self.max_items
                }
            }
        else:
            # Skip summarization step
            digest_step = {
                "name": "generate_digest",
                "agent": DigestGeneratorAgent(),
                "input": lambda outputs: {
                    "content_items": outputs["filter_content"]["content_items"],
                    "email": self.email,
                    "max_items": self.max_items
                }
            }
        
        # Define the workflow steps
        workflow_steps = [fetch_step, filter_step]
        
        if self.enable_summarization:
            workflow_steps.append(summarize_step)
        
        workflow_steps.append(digest_step)
        
        return workflow_steps
    
    async def run(self) -> Dict[str, Any]:
        """
        Run the workflow.
        
        Returns:
            Dict containing the workflow results
        """
        logger.info("Starting ContentAggregatorWorkflow")
        
        # Check for existing checkpoint
        checkpoint = self.load_checkpoint()
        if checkpoint:
            logger.info(f"Resuming workflow from checkpoint: {checkpoint['step']}")
        
        try:
            # Run the workflow
            results = await super().run()
            
            # Save final checkpoint
            self.save_checkpoint("completed", {
                "timestamp": datetime.now().isoformat(),
                "stats": {
                    "fetch_stats": results.get("fetch_content", {}).get("stats", {}),
                    "filter_stats": results.get("filter_content", {}).get("stats", {}),
                    "summarize_stats": results.get("summarize_content", {}).get("stats", {}) if self.enable_summarization else {},
                    "digest_stats": results.get("generate_digest", {}).get("stats", {})
                }
            })
            
            logger.info("ContentAggregatorWorkflow completed successfully")
            return results
        
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            # Save error checkpoint
            self.save_checkpoint("error", {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            })
            raise
    
    def save_checkpoint(self, step_name: str, data: Dict[str, Any]) -> None:
        """
        Save a checkpoint for the current workflow state.
        
        Args:
            step_name: Name of the current step
            data: Data to save in the checkpoint
        """
        try:
            checkpoint = {
                "step": step_name,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            with open(self.checkpoint_file, "w") as f:
                json.dump(checkpoint, f, indent=2)
            logger.info(f"Saved checkpoint for step: {step_name}")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Load the latest checkpoint.
        
        Returns:
            Dict containing the checkpoint data, or None if no checkpoint exists
        """
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, "r") as f:
                    checkpoint = json.load(f)
                logger.info(f"Loaded checkpoint for step: {checkpoint.get('step')}")
                return checkpoint
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
        return None
