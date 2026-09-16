"""FastAPI entrypoint.

Inicializa la app y monta los routers del proyecto (WhatsApp y Documentos).
"""

from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI

from api.documents.router import router as documents_router
from api.whatsapp.router import router as whatsapp_router
import db.connection as db_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    try:
        await db_conn.init_db()
        logging.info("Database schemas verified/initialized at startup.")
    except Exception as err:
        logging.warning("Database startup init skipped or failed: %s", err)
    yield


app = FastAPI(
    title="Financial Assistant Chat",
    description="Personal finance management via WhatsApp and Web Documents using multi-agent AI.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(whatsapp_router)
app.include_router(documents_router)


@app.get("/health")
async def health():
    """Health check para monitoreo."""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
