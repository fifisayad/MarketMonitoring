from fastapi import FastAPI
from fifi import GetLogger
from src.api.routes import subscription

from contextlib import asynccontextmanager
import asyncio
import uvloop

LOGGER = GetLogger().get()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Checking running loop in before starting api gateway

    Args:
        app (FastAPI)
    """
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.get_running_loop()
    LOGGER.info(f"Checking Uvloop: {type(loop) == uvloop.Loop}")

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(subscription.router)
