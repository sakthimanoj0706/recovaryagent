"""
FastAPI Server for RecoverAI Command Center.
"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routes import router

app = FastAPI(
    title="RecoverAI Command Center API",
    description="Backend API powering the RecoverAI Financial Recovery Command Center",
    version="1.0.0",
)

# In production, restrict CORS
env = os.getenv("RECOVERAI_ENV", "production")
origins = ["*"] if env == "development" else ["https://dashboard.recoverai.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

from .routes import router
from .control import router as control_router

app.include_router(router, prefix="/api")
app.include_router(control_router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "RecoverAI Command Center API",
        "status": "online",
        "tagline": "Prove the money. Prioritize the chase. Recover it.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
