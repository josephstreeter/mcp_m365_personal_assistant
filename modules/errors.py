"""
Custom exception types and error handling utilities for M365 Assistant MCP.

Provides typed exceptions for different error scenarios to enable proper
error classification, logging, and retry logic.
"""

from enum import Enum


class ErrorType(str, Enum):
    """Classification of error types for MCP tool responses."""
    VALIDATION_ERROR = "ValidationError"
    GRAPH_API_ERROR = "GraphAPIError"
    AUTHENTICATION_ERROR = "AuthenticationError"
    AUTHORIZATION_ERROR = "AuthorizationError"
    NOT_FOUND_ERROR = "NotFoundError"
    TIMEOUT_ERROR = "TimeoutError"
    RATE_LIMIT_ERROR = "RateLimitError"
    CONFLICT_ERROR = "ConflictError"
    INTERNAL_ERROR = "InternalError"


class M365Exception(Exception):
    """Base exception for M365 Assistant operations."""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.INTERNAL_ERROR,
        retryable: bool = False,
        status_code: int | None = None,
    ):
        self.message = message
        self.error_type = error_type
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to MCP error response dict."""
        return {
            "error": self.message,
            "error_type": self.error_type.value,
            "retryable": self.retryable,
        }


class ValidationError(M365Exception):
    """Raised when input validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorType.VALIDATION_ERROR, retryable=False)


class GraphAPIError(M365Exception):
    """Raised when Graph API call fails."""
    
    def __init__(self, message: str, status_code: int | None = None, retryable: bool = False):
        # Infer retryability from status code if not explicitly set
        if status_code is not None:
            retryable = status_code >= 500 or status_code == 429
        super().__init__(message, ErrorType.GRAPH_API_ERROR, retryable=retryable, status_code=status_code)


class AuthenticationError(M365Exception):
    """Raised when authentication fails."""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorType.AUTHENTICATION_ERROR, retryable=False)


class AuthorizationError(M365Exception):
    """Raised when user lacks required permissions."""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorType.AUTHORIZATION_ERROR, retryable=False)


class NotFoundError(M365Exception):
    """Raised when a requested resource is not found."""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorType.NOT_FOUND_ERROR, retryable=False)


class TimeoutError(M365Exception):
    """Raised when a request times out."""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorType.TIMEOUT_ERROR, retryable=True)


class RateLimitError(M365Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message, ErrorType.RATE_LIMIT_ERROR, retryable=True)
        self.retry_after = retry_after


class ConflictError(M365Exception):
    """Raised when operation conflicts with existing state."""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorType.CONFLICT_ERROR, retryable=False)


def error_from_graph_exception(exc: Exception) -> M365Exception:
    """
    Convert Graph SDK exceptions to M365 custom exceptions.
    
    Args:
        exc: Exception from Graph SDK
        
    Returns:
        M365Exception with appropriate type and retryability
    """
    error_message = str(exc)
    
    # Handle timeouts
    if isinstance(exc, TimeoutError):
        return TimeoutError(f"Graph API request timeout: {error_message}")
    
    # Handle authentication errors
    if "401" in error_message or "Unauthorized" in error_message:
        return AuthenticationError(f"Authentication failed: {error_message}")
    
    # Handle authorization errors
    if "403" in error_message or "Forbidden" in error_message:
        return AuthorizationError(f"Permission denied: {error_message}")
    
    # Handle not found
    if "404" in error_message or "not found" in error_message.lower():
        return NotFoundError(f"Resource not found: {error_message}")
    
    # Handle rate limiting
    if "429" in error_message or "Too Many Requests" in error_message:
        return RateLimitError(f"Rate limit exceeded: {error_message}")
    
    # Handle conflicts
    if "409" in error_message or "Conflict" in error_message:
        return ConflictError(f"Conflict: {error_message}")
    
    # Extract status code if present
    status_code = None
    for code in [500, 502, 503, 504, 400, 401, 403, 404, 409, 429]:
        if str(code) in error_message:
            status_code = code
            break
    
    # Default to generic GraphAPIError
    return GraphAPIError(f"Graph API error: {error_message}", status_code=status_code)
