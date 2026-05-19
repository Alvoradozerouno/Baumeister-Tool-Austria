"""
Rate Limiting Middleware
Prevents API abuse and ensures fair usage
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import redis
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Redis connection for distributed rate limiting
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except redis.RedisError as e:
    logging.warning(f"Redis connection failed, falling back to in-memory rate limiting: {e}")
    redis_client = None  # Fall back to in-memory
except Exception as e:
    logging.error(f"Unexpected error connecting to Redis: {type(e).__name__}: {e}")
    redis_client = None

# In-memory rate limit storage (fallback)
rate_limit_storage: Dict[str, Dict] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with multiple strategies
    """

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_id = self._get_client_id(request)

        # Get rate limit tier
        tier = self._get_rate_limit_tier(request)

        # Check rate limit
        allowed, retry_after = self._check_rate_limit(client_id, tier)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded. Try again in {retry_after} seconds."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(tier["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self._get_remaining_requests(client_id, tier)
        reset_time = self._get_reset_time(client_id)

        response.headers["X-RateLimit-Limit"] = str(tier["limit"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"

        # Try JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return f"token:{token[:20]}"  # Use prefix for privacy

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host

        return f"ip:{ip}"

    def _get_rate_limit_tier(self, request: Request) -> Dict:
        """Get rate limit configuration based on user tier"""
        # Check if premium user (would check database in production)
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key.startswith("orion_premium_"):
            return {"limit": 10000, "window": 3600}  # 10k requests per hour

        # Check if authenticated
        auth_header = request.headers.get("Authorization")
        if auth_header:
            return {"limit": 1000, "window": 3600}  # 1k requests per hour

        # Anonymous users
        return {"limit": 100, "window": 3600}  # 100 requests per hour

    def _check_rate_limit(self, client_id: str, tier: Dict) -> tuple[bool, int]:
        """Check if client has exceeded rate limit"""
        if redis_client:
            return self._check_rate_limit_redis(client_id, tier)
        else:
            return self._check_rate_limit_memory(client_id, tier)

    def _check_rate_limit_redis(self, client_id: str, tier: Dict) -> tuple[bool, int]:
        """Check rate limit using Redis"""
        try:
            current_time = int(time.time())
            window_start = current_time - tier["window"]

            # Use Redis sorted set for sliding window
            key = f"rate_limit:{client_id}"

            # Remove old entries
            redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            count = redis_client.zcard(key)

            if count >= tier["limit"]:
                # Get oldest request time to calculate retry_after
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = int(oldest[0][1])
                    retry_after = oldest_time + tier["window"] - current_time
                    return False, retry_after
                return False, tier["window"]

            # Add current request
            redis_client.zadd(key, {str(current_time): current_time})
            redis_client.expire(key, tier["window"])

            return True, 0

        except Exception as e:
            # If Redis fails, allow request (fail open)
            return True, 0

    def _check_rate_limit_memory(self, client_id: str, tier: Dict) -> tuple[bool, int]:
        """Check rate limit using in-memory storage (fallback)"""
        current_time = time.time()

        if client_id not in rate_limit_storage:
            rate_limit_storage[client_id] = {"requests": [], "window_start": current_time}

        client_data = rate_limit_storage[client_id]

        # Remove old requests
        window_start = current_time - tier["window"]
        client_data["requests"] = [
            req_time for req_time in client_data["requests"] if req_time > window_start
        ]

        # Check limit
        if len(client_data["requests"]) >= tier["limit"]:
            oldest_request = min(client_data["requests"])
            retry_after = int(oldest_request + tier["window"] - current_time)
            return False, retry_after

        # Add current request
        client_data["requests"].append(current_time)

        return True, 0

    def _get_remaining_requests(self, client_id: str, tier: Dict) -> int:
        """Get remaining requests in current window"""
        if redis_client:
            try:
                key = f"rate_limit:{client_id}"
                count = redis_client.zcard(key)
                return max(0, tier["limit"] - count)
            except redis.RedisError as e:
                logging.warning(f"Redis query failed in rate limit check: {e}")
                return tier["limit"]  # Fail open on Redis error
        else:
            if client_id in rate_limit_storage:
                count = len(rate_limit_storage[client_id]["requests"])
                return max(0, tier["limit"] - count)
            return tier["limit"]

    def _get_reset_time(self, client_id: str) -> int:
        """Get timestamp when rate limit resets"""
        if redis_client:
            try:
                key = f"rate_limit:{client_id}"
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    # Get window from tier (assume 3600 for now)
                    return int(oldest[0][1]) + 3600
            except redis.RedisError as e:
                logging.debug(f"Redis query failed getting reset time: {e}")
            except (IndexError, ValueError) as e:
                logging.warning(f"Invalid reset time data from Redis: {e}")

        return int(time.time()) + 3600


# Decorator for specific endpoint rate limits
def rate_limit(requests: int, window: int = 3600):
    """
    Decorator for custom rate limits on specific endpoints

    Example:
        @router.post("/expensive-calculation")
        @rate_limit(requests=10, window=3600)
        async def expensive_calculation():
            ...
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = kwargs.get("request")
            if request:
                client_id = f"endpoint:{func.__name__}:{request.client.host}"
                tier = {"limit": requests, "window": window}

                middleware = RateLimitMiddleware(None)
                allowed, retry_after = middleware._check_rate_limit(client_id, tier)

                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit for this endpoint exceeded. Try again in {retry_after} seconds.",
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
