from fastapi import Request, HTTPException
import redis
import logging
from typing import Optional
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to Redis with connection pooling and error handling
try:
    r = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )
    # Test connection
    r.ping()
    logger.info("Redis connection established")
except redis.ConnectionError as e:
    logger.error(f'Redis connection failed: {e}')
    r = None

# Rate limiting configuration
RATE_LIMIT = 5     # Allow max 5 requests
WINDOW = 60         # ...within 60 seconds


def get_client_ip(request:Request) -> str:
    '''Extract client IP with proper forwarded header handling'''
    # Check for forwarded headers (useful when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real_IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client host
    return request.client.host if request.client else "unknown"

async def combined_logger_and_limiter(request: Request, call_next):
    method = request.method
    url = str(request.url)
    path = request.url.path
    ip = get_client_ip(request)

    # Log every request
    logger.info(f'{method} {url} from {ip}')

    # Apply rate limiting only to login and signup routes
    if path in ['login', 'signup']:
        # Skip rate limiting if Redis is unavailable
        if r is None:
            logger.warning("Redis unavailable, skipping rate limiting")
        else:
            try:
                key = f'rate:{ip}:{path}'     # Example: rate:127.0.0.1:/login
                current = r.get(key)

                if current:
                    try:
                        if int(current) >= RATE_LIMIT:
                            logger.warning(f'Rate limit exceeded for {ip} on {path}')
                            return JSONResponse(
                                status_code=429,
                                content={
                                    "detail" : f'Too many requests. Try again in some time.',
                                    "retry_after" : WINDOW
                                }
                            )
                    except ValueError:
                        logger.error(f'Redis has invalid value for key {key}, resetting...')
                        r.delete(key)   # Clean up invalid key

                # Begin a Redis pipeline (batch multiple operations)
                pipe = r.pipeline()
                pipe.incr(key,1)              # increase the request count
                pipe.expire(key, WINDOW)      # set expiration window (60s)
                pipe.execute()                # execute both commands automatically

            except redis.RedisError as e:
                logger.error(f'Redis error during rate limiting: {e}')
                # continue without rate limiting if Redis fails

    # continue to route or next middleware
    try:
        response = await call_next(request)
        # log response status
        logger.info(f'{method} {path} - Status: {response.status_code}')
        return response
    except Exception as e:
        logger.error(f'Error processing request {method} {path}: {e}')
        raise