"""Custom exceptions for Content Aggregator."""

class ContentAggregatorError(Exception):
    """Base exception for Content Aggregator."""
    pass

class ValidationError(ContentAggregatorError):
    """Raised when input validation fails."""
    pass

class FetchError(ContentAggregatorError):
    """Raised when content fetching fails."""
    pass

class SummarizationError(ContentAggregatorError):
    """Raised when content summarization fails."""
    pass

class EmailError(ContentAggregatorError):
    """Raised when email sending fails."""
    pass

class ConfigurationError(ContentAggregatorError):
    """Raised when configuration is invalid."""
    pass

def handle_error(error: Exception, context: str = "") -> str:
    """Handle errors and return user-friendly messages."""
    import logging
    logger = logging.getLogger(__name__)
    
    if isinstance(error, ValidationError):
        return f"Validation error: {str(error)}"
    elif isinstance(error, FetchError):
        return "Failed to fetch content from one or more sources"
    elif isinstance(error, SummarizationError):
        return "Content summarization failed"
    elif isinstance(error, EmailError):
        return "Failed to send email digest"
    elif isinstance(error, ConfigurationError):
        return f"Configuration error: {str(error)}"
    else:
        # Log the actual error but return generic message
        logger.error(f"Unexpected error in {context}: {error}", exc_info=True)
        return "An unexpected error occurred"
