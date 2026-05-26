import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.whatsapp.router import router as whatsapp_router

app = FastAPI(
    title="Financial Assistant Chat",
    description="Multi-agent financial assistant powered by LangGraph",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router, prefix="/api/v1/whatsapp")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
