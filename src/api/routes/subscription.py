import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, FastAPI

from ...enums.data_type import DataType
from ...enums.exchange import Exchange
from ...enums.market import Market
from .deps import create_manager
from ...common.schemas import SubscriptionRequestSchema, SubscriptionResponseSchema
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
    rsi_key = await manager.subscribe(
        exchange=Exchange.HYPERLIQUID, market=Market.BTCUSD_PERP, data_type=DataType.RSI
    )
    LOGGER.info(f"{rsi_key=}")
    macd_key = await manager.subscribe(
        exchange=Exchange.HYPERLIQUID,
        market=Market.BTCUSD_PERP,
        data_type=DataType.MACD,
    )
    LOGGER.info(f"{macd_key=}")
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
