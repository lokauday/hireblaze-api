"""
Simple in-memory rate limiter for API endpoints.
"""
import logging
import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# Store for rate limit tracking: {ip: [(timestamp, count)]}
rate_limit_store: Dict[str, list] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded IP (from proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()
    
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def check_rate_limit(request: Request, max_requests: int = 10, window_seconds: int = 60) -> None:
    """
    Check if client has exceeded rate limit.
    
    Args:
        request: FastAPI request object
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
        
    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    ip = get_client_ip(request)
    now = time.time()
    
    # Clean old entries (older than window)
    cutoff = now - window_seconds
    rate_limit_store[ip] = [
        timestamp for timestamp in rate_limit_store[ip]
        if timestamp > cutoff
    ]
    
    # Check current count
    request_count = len(rate_limit_store[ip])
    
    if request_count >= max_requests:
        logger.warning(f"Rate limit exceeded for IP: {ip} ({request_count} requests in {window_seconds}s)")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."
        )
    
    # Record this request
    rate_limit_store[ip].append(now)
    
    logger.debug(f"Rate limit check passed for IP: {ip} ({request_count + 1}/{max_requests})")
