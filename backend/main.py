from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from backend.db import Base, engine
from backend.security.middleware import LoggingMiddleware
from backend.routes import upload, transactions, insights, forecast, subscriptions, coach, health, dashboard, settings, goals, anomalies, enrichment, breakdown, invest, auth

load_dotenv()  # Load environment variables from .env if present
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Financial Coach")
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_COUNT = Counter('app_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Latency per endpoint', ['endpoint'])

@app.middleware("http")
async def metrics_middleware(request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(time.time() - start)
    return response

@app.get('/metrics')
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Include routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(transactions.router)
app.include_router(insights.router)
app.include_router(forecast.router)
app.include_router(subscriptions.router)
app.include_router(coach.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(goals.router)
app.include_router(anomalies.router)
app.include_router(enrichment.router)
app.include_router(breakdown.router)
app.include_router(invest.router)
app.include_router(auth.router)

@app.get('/')
async def root():
    return {"message": "Smart Financial Coach API"}
