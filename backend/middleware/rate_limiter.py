import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Identify client by IP (prioritize X-Forwarded-For for proxies/testing)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Current time
        now = time.time()
        
        # Clean up old requests
        request_times = self.clients[client_ip]
        self.clients[client_ip] = [t for t in request_times if now - t < self.window_seconds]
        
        # Check limit
        if len(self.clients[client_ip]) >= self.max_requests:
            return await self._error_response()

        # Add new request
        self.clients[client_ip].append(now)
        
        response = await call_next(request)
        return response

    async def _error_response(self):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests. Please try again later."}
        )
