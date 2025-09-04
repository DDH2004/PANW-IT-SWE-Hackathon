from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.utils.logging import logger
import time

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=int(duration * 1000),
        )
        return response
