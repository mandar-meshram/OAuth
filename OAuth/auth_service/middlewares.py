from fastapi import Request, HTTPException
import redis
import logging
from typing import Optional
from fastapi.responses import JSONResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    r.ping()
    logger.info("Redis connection established")
except redis.ConnectionError as e:
    logger.error(f'Redis connection failed: {e}')
    r = None


RATE_LIMIT = 5     
WINDOW = 60         


def get_client_ip(request:Request) -> str:
    
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real_IP")
    if real_ip:
        return real_ip
    
   
    return request.client.host if request.client else "unknown"

async def combined_logger_and_limiter(request: Request, call_next):
    method = request.method
    url = str(request.url)
    path = request.url.path
    ip = get_client_ip(request)

    
    logger.info(f'{method} {url} from {ip}')

    
    if path in ['login', 'signup']:
       
        if r is None:
            logger.warning("Redis unavailable, skipping rate limiting")
        else:
            try:
                key = f'rate:{ip}:{path}'     
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
                        r.delete(key)   

                
                pipe = r.pipeline()
                pipe.incr(key,1)              
                pipe.expire(key, WINDOW)      
                pipe.execute()                

            except redis.RedisError as e:
                logger.error(f'Redis error during rate limiting: {e}')
                

    
    try:
        response = await call_next(request)

        logger.info(f'{method} {path} - Status: {response.status_code}')
        return response
    except Exception as e:
        logger.error(f'Error processing request {method} {path}: {e}')
        raise