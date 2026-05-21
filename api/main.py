from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
import time
from api.config import settings
from api.routers import clients, logs
from api.database import init_traffic_db
from api.collector import collect_logs
import asyncio

# Setup log directory
log_dir = settings.BASE_DIR / "logs"
log_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(log_dir / "api.log", maxBytes=5242880, backupCount=5),
        logging.StreamHandler(),
    ],
)
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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f'{request.client.host} - "{request.method} {request.url.path}" {response.status_code} - {process_time:.4f}s'
    )
    return response


app.include_router(clients.router, prefix="/api")
app.include_router(logs.router, prefix="/api")


@app.get("/")
async def root():
    """API information"""
    return {
        "name": "Traffic API",
        "version": "1.0.0",
    }
