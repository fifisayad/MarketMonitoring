from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, FastAPI

from .deps import create_manager
from ...common.schemas import SubscriptionRequestSchema, SubscriptionResponseSchema
from ...service.manager import Manager

router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Checking running loop in before starting api gateway

    Args:
        app (FastAPI)
    """
    manager = Manager()
    yield
    await manager.stop()


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
        raise HTTPException(status_code=500, detail=str(e))
