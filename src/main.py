from fastapi import FastAPI
from src.api.routes import subscription

import asyncio
import logging
import uvloop

app = FastAPI()

app.include_router(subscription.router)
LOGGER = logging.getLogger("uvicorn.error")


@app.on_event("startup")
async def check_loop():
    loop = asyncio.get_running_loop()
    LOGGER.info(f"Checking Uvloop: {type(loop) == uvloop.Loop}")
