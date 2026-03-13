import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.api import auth, users, classes, uploads, summary, plans, discrepancies, export

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Школа 71 - Учёт питания",
    description="Система учёта школьного питания МБУ «Школа № 71»",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(classes.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(discrepancies.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
