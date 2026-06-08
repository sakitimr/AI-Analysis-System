"""FastAPI application."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title="Competitive Analysis Agent System", version="1.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"service": "Competitive Analysis Agent System", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
