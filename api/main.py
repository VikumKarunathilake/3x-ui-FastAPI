from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from api.config import settings
from api.routers import clients

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(f"Starting API with database: {settings.full_db_path}")
    if not settings.full_db_path.exists():
        logger.warning(f"Database file not found at {settings.full_db_path}")
    else:
        logger.info("Database file found")
    yield
    logger.info("Shutting down API")


app = FastAPI(
    title="Traffic API",
    description="API to read traffic data from database",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(clients.router, prefix="/api")


@app.get("/")
async def root():
    """API information"""
    return {
        "name": "Traffic API",
        "version": "1.0.0",
    }
