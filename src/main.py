from fastapi import FastAPI
from src.api.routes import subscription
from fifi.helpers.get_logger import GetLogger
import asyncio
import logging

app = FastAPI()

app.include_router(subscription.router)
LOGGER = logging.getLogger("uvicorn.error")


@app.on_event("startup")
async def check_loop():
    loop = asyncio.get_running_loop()
    LOGGER.info(f"USING UVLOOP: {type(loop)}")
