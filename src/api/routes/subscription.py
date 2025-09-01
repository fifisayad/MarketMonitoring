import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, FastAPI

from src.service.info.hyperliquid_info import HyperliquidInfo

from ...enums.data_type import DataType
from ...enums.exchange import Exchange
from ...enums.market import Market
from .deps import create_manager, create_info
from ...common.schemas import (
    SubscriptionRequestSchema,
    SubscriptionResponseSchema,
    CandleResponseSchema,
)
from ...service.manager import Manager

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Checking running loop in before starting api gateway

    Args:
        app (FastAPI)
    """
    manager = Manager()
    await manager.start_watcher()
    yield
    await manager.stop()


router = APIRouter(lifespan=lifespan)


@router.post("/subscribe", response_model=SubscriptionResponseSchema)
async def subscribe(
    request: SubscriptionRequestSchema, manager: Manager = Depends(create_manager)
):
    try:
        channel = await manager.subscribe(
            exchange=request.exchange,
            market=request.market,
            data_type=request.data_type,
        )
        return SubscriptionResponseSchema(channel=channel)

    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.post("/candle", response_model=CandleResponseSchema)
async def candle(
    request: SubscriptionRequestSchema,
    info=Depends(create_info),
):
    try:
        candles = info.candle_snapshots(
            exchange=request.exchange,
            market=request.market,
            data_type=request.data_type,
        )
        return CandleResponseSchema(type=request.data_type, response=candles)

    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())
