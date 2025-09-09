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
    CandleSubscriptionRequestSchema,
)
from ...service.manager import Manager

LOGGER = logging.getLogger(__name__)


# ----
# Lifespan
# ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Checking running loop in before starting api gateway

    Args:
        app (FastAPI)
    """
    manager = Manager()
    await manager.start_watcher()
    try:
        yield
    finally:
        await manager.stop()


router = APIRouter(lifespan=lifespan)


# ----
# Helpers
# ----
def handle_exception(exc: Exception) -> HTTPException:
    """Convert any exception into HTTPException with traceback for debugging."""
    LOGGER.error("API error: %s", exc, exc_info=True)
    return HTTPException(status_code=500, detail=traceback.format_exc())


# ----
# Market data endpoint
# ----
@router.post("/subscribe/market", response_model=SubscriptionResponseSchema)
async def subscribe_market(
    request: MarketSubscriptionRequestSchema,
    manager: Manager = Depends(create_manager),
) -> SubscriptionResponseSchema:
    try:
        channel = await manager.subscribe(
            exchange=request.exchange,
            market=request.market,
            data_type=request.data_type,
            **request.model_dump(exclude={"exchange", "market", "data_type"}),
        )
        return SubscriptionResponseSchema(channel=channel)
    except Exception as e:
        raise handle_exception(e)


# ----
# Indicator endpoint
# ----
@router.post("/subscribe/indicator", response_model=SubscriptionResponseSchema)
async def subscribe_indicator(
    request: IndicatorSubscriptionRequest,
    manager: Manager = Depends(create_manager),
) -> SubscriptionResponseSchema:
    try:
        channel = await manager.subscribe(
            exchange=request.exchange,
            market=request.market,
            data_type=request.indicator,
            **request.model_dump(exclude={"exchange", "market", "indicator"}),
        )
        return SubscriptionResponseSchema(channel=channel)
    except Exception as e:
        raise handle_exception(e)


# ----
# info endpoint
# ----
@router.post("/candle", response_model=CandleResponseSchema)
async def candle(request: CandleSubscriptionRequestSchema) -> CandleResponseSchema:
    try:
        info = get_info(request.exchange)
        candles = info.candle_snapshot(
            market=request.market,
            timeframe=request.timeframe,

        )
        return CandleResponseSchema(type=request.data_type, response=candles)
    except Exception as e:
        raise handle_exception(e)
