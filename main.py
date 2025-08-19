from fastapi import FastAPI
import os
from dotenv import load_dotenv
from src.common.settings import Settings
import coloredlogs
import logging
from src.api.routes import subscription
from contextlib import asynccontextmanager
import asyncio
import uvloop

settings = Settings()
coloredlogs.install()
load_dotenv()

LOGGER = logging.getLogger(__name__)
name_to_level = logging.getLevelNamesMapping()
logging.basicConfig(
    level=name_to_level[settings.LOG_LEVEL],
    format="[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s",
)


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
