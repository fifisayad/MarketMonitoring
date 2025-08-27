import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, FastAPI

from ...enums.data_type import DataType
from ...enums.exchange import Exchange
from ...enums.market import Market
from .deps import create_manager
from ...common.schemas import (
    MarketSubscriptionRequestSchema,
    IndicatorSubscriptionRequest,
    SubscriptionResponseSchema,
    CandleResponseSchema,
)
from ...service.manager import Manager
from ...service.info.info_factory import get_candle_snapshots

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


@router.post("/candle", response_model=CandleResponseSchema)
async def candle(request: MarketSubscriptionRequestSchema):
    try:
        candles = get_candle_snapshots(
            exchange=request.exchange,
            market=request.market,
            data_type=request.data_type,
        )
        return CandleResponseSchema(type=request.data_type, response=candles)

    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())
