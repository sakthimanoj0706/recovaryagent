import time
from collections import defaultdict
from fastapi import Request, HTTPException

# Simple in-memory token bucket for rate limiting per IP
# In production, use Redis.
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.buckets = defaultdict(lambda: {"tokens": requests_per_minute, "last_update": time.monotonic()})
        
    def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.monotonic()
        
        bucket = self.buckets[client_ip]
        elapsed = now - bucket["last_update"]
        
        # Refill tokens
        bucket["tokens"] = min(self.requests_per_minute, bucket["tokens"] + elapsed * (self.requests_per_minute / 60.0))
        bucket["last_update"] = now
        
        if bucket["tokens"] < 1:
            raise HTTPException(status_code=429, detail="Too Many Requests")
            
        bucket["tokens"] -= 1

limiter = RateLimiter(requests_per_minute=100) # Default API limiter
webhook_limiter = RateLimiter(requests_per_minute=300) # Higher capacity for webhooks
expensive_limiter = RateLimiter(requests_per_minute=10) # Protect LLM/simulation routes
