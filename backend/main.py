from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.api_v1.api import api_router

print("--- Initializing FastAPI application ---")
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Custom middleware to log all requests
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    print(f"--- Middleware: Received request: {request.method} {request.url.path} ---")
    response = await call_next(request)
    print(f"--- Middleware: Sending response: {response.status_code} for {request.url.path} ---")
    return response

# 设置CORS，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境下允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Physio-Monitoring System API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

