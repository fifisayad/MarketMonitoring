import traceback

from fastapi import APIRouter, Depends, HTTPException, FastAPI
from contextlib import asynccontextmanager
from fifi.helpers.get_logger import LoggerFactory
from fifi.schema import (
    MarketSubscriptionRequestSchema,
    IndicatorSubscriptionRequest,
    SubscriptionResponseSchema,
    CandleResponseSchema,
)

from ...service.info.info_factory import get_info
from ...service.manager import Manager
from .deps import create_manager

LOGGER = LoggerFactory().get(__name__)


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
    LOGGER.error("API Error: %s", exc, exc_info=True)
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
async def candle(request: MarketSubscriptionRequestSchema) -> CandleResponseSchema:
    try:
        info = get_info(request.exchange)
        candles = info.candle_snapshot(
            market=request.market,
            timeframe=request.timeframe,
        )
        return CandleResponseSchema(type=request.data_type, response=candles)
    except Exception as e:
        raise handle_exception(e)
