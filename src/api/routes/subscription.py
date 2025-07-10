from fastapi import APIRouter, HTTPException
from src.common.schemas import SubscriptionRequest
from src.service.manager import handle_subscription, handle_unsubscription

router = APIRouter()


@router.post("/subscribe")
async def subscribe(request: SubscriptionRequest):
    try:
        await handle_subscription(request)
        return {
            "msg": "data channel is started - now you can subscribe to the channel name.",
            "result": f"{request.exchange.value}-{request.pair.value}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unsubscribe")
async def unsubscribe(request: SubscriptionRequest):
    try:
        await handle_unsubscription(request)
        return {"status": "subscription stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
