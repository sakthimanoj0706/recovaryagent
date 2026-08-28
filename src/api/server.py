"""
FastAPI Server for RecoverAI Command Center.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router

app = FastAPI(
    title="RecoverAI Command Center API",
    description="Backend API powering the RecoverAI Financial Recovery Command Center",
    version="1.0.0",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


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
