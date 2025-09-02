import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, FastAPI

from ...service.info.info_factory import get_info
from .deps import create_manager
from ...common.schemas import (
    MarketSubscriptionRequestSchema,
    IndicatorSubscriptionRequest,
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


# ----
# Market data endpoint
# ----
@router.post("/subscribe/market", response_model=SubscriptionResponseSchema)
async def subscribe_market(
    request: MarketSubscriptionRequestSchema,
    manager: Manager = Depends(create_manager),
):
    try:
        channel = await manager.subscribe(
            exchange=request.exchange,
            market=request.market,
            data_type=request.data_type,
        )
        return SubscriptionResponseSchema(channel=channel)
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


# ----
# Indicator endpoint
# ----
@router.post("/subscribe/indicator", response_model=SubscriptionResponseSchema)
async def subscribe_indicator(
    request: IndicatorSubscriptionRequest,
    manager: Manager = Depends(create_manager),
):
    try:
        channel = await manager.subscribe(
            exchange=request.exchange,
            market=request.market,
            data_type=request.indicator,
        )
        return SubscriptionResponseSchema(channel=channel)
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())


# ----
# info endpoint
# ----
@router.post("/candle", response_model=CandleResponseSchema)
async def candle(request: MarketSubscriptionRequestSchema):
    try:
        info = get_info(request.exchange)
        candles = info.candle_snapshot(
            market=request.market,
            interval=request.data_type,
        )
        return CandleResponseSchema(type=request.data_type, response=candles)

    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())
