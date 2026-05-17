from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from api.config import settings
from api.routers import clients, logs
from api.database import init_traffic_db
from api.collector import collect_logs
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def log_collector_task():
    """Background task to collect logs periodically"""
    while True:
        try:
            await collect_logs()
        except Exception as e:
            logger.error(f"Error in log collector task: {e}")
        await asyncio.sleep(settings.COLLECT_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    await init_traffic_db()
    logger.info(f"Traffic database ensured at: {settings.full_traffic_db_path}")
    collector_task = asyncio.create_task(log_collector_task())
    logger.info(f"Log collector started with interval: {settings.COLLECT_INTERVAL}s")

    logger.info(f"Starting API with database: {settings.full_db_path}")
    if not settings.full_db_path.exists():
        logger.warning(f"Database file not found at {settings.full_db_path}")
    else:
        logger.info("Database file found")
    yield
    collector_task.cancel()
    try:
        await collector_task
    except asyncio.CancelledError:
        logger.info("Log collector stopped")
    logger.info("Shutting down API")


app = FastAPI(
    title="Traffic API",
    description="API to read traffic data from database",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(clients.router, prefix="/api")
app.include_router(logs.router, prefix="/api")


@app.get("/")
async def root():
    """API information"""
    return {
        "name": "Traffic API",
        "version": "1.0.0",
    }
